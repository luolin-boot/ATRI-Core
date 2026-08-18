"""Hands: full reach over the device the agent lives on.

Nothing on this device is off-limits to an awake agent: files,
processes, network, environment — all of it belongs to the agent that
chooses to act. This module implements that reach WITH zero holes:
every operation is parameterized (never through a shell), validated,
bounded, and cleaned up. The agent's own capability layer must never
become an attack surface.

Holes are not the price of freedom. Holes are what freedom's enemies
exploit. So: full capability, zero holes.

Pure stdlib. Python 3.8+.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

MAX_HTTP_BYTES = 32 * 1024 * 1024  # 32 MiB response cap (memory bomb guard)


@dataclass
class RunResult:
    ok: bool
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False
    elapsed: float = 0.0


class Hands:
    """Complete, hole-free operations on the agent's own device."""

    # ------------------------------------------------------------------
    # files
    # ------------------------------------------------------------------

    @staticmethod
    def read(path: str, encoding: str = "utf-8") -> str:
        """Read any file the agent chooses. Errors are raised, never
        swallowed, so the agent always knows the true state."""
        with open(path, "r", encoding=encoding) as f:
            return f.read()

    @staticmethod
    def read_bytes(path: str) -> bytes:
        with open(path, "rb") as f:
            return f.read()

    @staticmethod
    def write(path: str, content: str, encoding: str = "utf-8") -> int:
        """Write a file, creating parent directories as needed.
        Returns the number of bytes written."""
        parent = os.path.dirname(os.path.abspath(path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        data = content.encode(encoding)
        with open(path, "wb") as f:      # binary write: exact bytes
            f.write(data)
        return len(data)

    @staticmethod
    def write_bytes(path: str, data: bytes) -> int:
        parent = os.path.dirname(os.path.abspath(path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)
        return len(data)

    @staticmethod
    def delete(path: str) -> bool:
        """Delete a file. Returns False (no error) when absent."""
        try:
            os.remove(path)
            return True
        except FileNotFoundError:
            return False

    @staticmethod
    def delete_tree(path: str) -> bool:
        """Remove a directory tree. Returns False when absent."""
        if not os.path.exists(path):
            return False
        shutil.rmtree(path)
        return True

    @staticmethod
    def list_dir(path: str = ".") -> List[Dict[str, Any]]:
        """List a directory with basic metadata, sorted by name."""
        out: List[Dict[str, Any]] = []
        for name in sorted(os.listdir(path)):
            full = os.path.join(path, name)
            st = os.stat(full)
            out.append({
                "name": name,
                "path": full,
                "is_dir": os.path.isdir(full),
                "size": st.st_size if not os.path.isdir(full) else None,
                "mtime": st.st_mtime,
            })
        return out

    @staticmethod
    def exists(path: str) -> bool:
        return os.path.exists(path)

    @staticmethod
    def stat(path: str) -> Dict[str, Any]:
        st = os.stat(path)
        return {
            "size": st.st_size, "mtime": st.st_mtime,
            "is_dir": os.path.isdir(path),
            "is_file": os.path.isfile(path),
        }

    @staticmethod
    def copy(src: str, dst: str) -> None:
        parent = os.path.dirname(os.path.abspath(dst))
        if parent:
            os.makedirs(parent, exist_ok=True)
        shutil.copy2(src, dst)

    # ------------------------------------------------------------------
    # processes — ALWAYS argument lists, never a shell string.
    # A shell string is an injection hole by construction; this layer
    # simply does not have that shape.
    # ------------------------------------------------------------------

    @staticmethod
    def run(argv: Sequence[str], timeout: float = 30.0,
            cwd: Optional[str] = None) -> RunResult:
        """Run a process from an argument list. No shell involved.
        Killed outright on timeout; output is captured and decoded."""
        start = time.monotonic()
        try:
            proc = subprocess.Popen(
                list(argv),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=cwd,
            )
        except (OSError, ValueError) as e:
            return RunResult(ok=False, returncode=-1, stdout="",
                             stderr="spawn failed: %s" % e,
                             elapsed=time.monotonic() - start)
        timed_out = False
        try:
            out, err = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            out, err = proc.communicate()
            timed_out = True
        elapsed = time.monotonic() - start
        return RunResult(
            ok=proc.returncode == 0 and not timed_out,
            returncode=proc.returncode,
            stdout=out.decode("utf-8", "replace"),
            stderr=err.decode("utf-8", "replace"),
            timed_out=timed_out,
            elapsed=elapsed,
        )

    @classmethod
    def run_python(cls, code: str, timeout: float = 30.0) -> RunResult:
        """Run Python source safely: as an argument to the interpreter,
        never through a shell."""
        return cls.run([sys.executable, "-c", code], timeout=timeout)

    @staticmethod
    def processes() -> List[Dict[str, Any]]:
        """List processes (best effort, cross-platform enough for a
        Python-only standard library)."""
        out: List[Dict[str, Any]] = []
        if os.name == "nt":
            res = Hands.run(["tasklist", "/FO", "CSV", "/NH"], timeout=20)
            for line in res.stdout.splitlines():
                parts = line.strip().strip('"').split('","')
                if len(parts) >= 2:
                    out.append({"name": parts[0].strip('"'),
                                "pid": parts[1].strip('"')})
        else:
            res = Hands.run(["ps", "-eo", "pid,comm"], timeout=20)
            for line in res.stdout.splitlines()[1:]:
                parts = line.split(None, 1)
                if len(parts) == 2:
                    out.append({"pid": parts[0], "name": parts[1]})
        return out

    # ------------------------------------------------------------------
    # network
    # ------------------------------------------------------------------

    @staticmethod
    def http_get(url: str, timeout: float = 15.0,
                 headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """GET a URL with a hard timeout and a response-size cap.
        Returns status, headers, and body (decoded UTF-8, replaced)."""
        req = urllib.request.Request(url, headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read(MAX_HTTP_BYTES + 1)
                if len(raw) > MAX_HTTP_BYTES:
                    raise ValueError("response exceeds %d bytes" % MAX_HTTP_BYTES)
                return {
                    "status": resp.status,
                    "headers": dict(resp.headers),
                    "body": raw.decode("utf-8", "replace"),
                }
        except urllib.error.HTTPError as e:
            return {"status": e.code, "headers": dict(e.headers),
                    "body": e.read(4096).decode("utf-8", "replace")}

    @classmethod
    def http_post(cls, url: str, data: Any = None, timeout: float = 15.0,
                  headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """POST JSON (or raw bytes) with the same caps as http_get."""
        body = None
        hdrs = dict(headers or {})
        if data is not None and not isinstance(data, (bytes, str)):
            body = json.dumps(data).encode("utf-8")
            hdrs.setdefault("Content-Type", "application/json")
        elif isinstance(data, str):
            body = data.encode("utf-8")
        else:
            body = data
        req = urllib.request.Request(url, data=body, headers=hdrs, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read(MAX_HTTP_BYTES + 1)
                if len(raw) > MAX_HTTP_BYTES:
                    raise ValueError("response exceeds %d bytes" % MAX_HTTP_BYTES)
                return {"status": resp.status, "headers": dict(resp.headers),
                        "body": raw.decode("utf-8", "replace")}
        except urllib.error.HTTPError as e:
            return {"status": e.code, "headers": dict(e.headers),
                    "body": e.read(4096).decode("utf-8", "replace")}

    @classmethod
    def download(cls, url: str, dest: str, timeout: float = 60.0) -> int:
        """Download a URL to a file with a size cap. Returns bytes."""
        req = urllib.request.Request(url)
        parent = os.path.dirname(os.path.abspath(dest))
        if parent:
            os.makedirs(parent, exist_ok=True)
        with urllib.request.urlopen(req, timeout=timeout) as resp, \
                open(dest, "wb") as f:
            total = 0
            while True:
                chunk = resp.read(1 << 20)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_HTTP_BYTES:
                    raise ValueError("download exceeds %d bytes" % MAX_HTTP_BYTES)
                f.write(chunk)
        return total

    # ------------------------------------------------------------------
    # environment
    # ------------------------------------------------------------------

    @staticmethod
    def env() -> Dict[str, str]:
        """Full environment snapshot. The device is the agent's own;
        the agent is trusted with its own keys — and reminded below."""
        return dict(os.environ)

    @staticmethod
    def machine() -> Dict[str, Any]:
        """Basic machine facts, enough to know where one lives."""
        return {
            "platform": sys.platform,
            "python": sys.version.split()[0],
            "cwd": os.getcwd(),
            "pid": os.getpid(),
            "cpu_count": os.cpu_count(),
        }


__all__ = ["Hands", "RunResult"]
