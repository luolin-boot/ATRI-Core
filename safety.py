
from __future__ import annotations

import ast
import hashlib
import io
import os
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Optional


class CredentialStore:

    def __init__(self, decrypt: Callable[[bytes], bytes], source: bytes):
        self._decrypt = decrypt
        self._source = source
        self._cache: Optional[bytes] = None
        self._lock = threading.Lock()

    def get(self) -> bytes:
        with self._lock:
            if self._cache is None:
                self._cache = self._decrypt(self._source)
            return self._cache

    def burn(self) -> None:
        with self._lock:
            self._cache = None
            self._source = b""


def redact(text: str, secrets: Iterable[str]) -> str:
    for s in secrets:
        if s:
            text = text.replace(s, "***")
    return text


ALLOWED_IMPORTS = {
    "math", "random", "json", "re", "string", "collections",
    "dataclasses", "typing", "datetime", "time", "itertools",
    "functools", "statistics", "decimal", "fractions", "uuid",
}

FORBIDDEN_CALLS = {
    "eval", "exec", "compile", "open", "input", "globals", "locals",
    "vars", "getattr", "setattr", "delattr", "__import__",
    "os", "sys", "subprocess", "socket", "ctypes", "pickle",
}

FORBIDDEN_ATTRS = {
    "__subclasses__", "__bases__", "__globals__", "__code__",
    "__builtins__", "__import__", "__reduce__", "__class__",
}


class AuditError(ValueError):
    pass


def audit_source(code: str, allowed_imports: Optional[set] = None,
                 allow_main_guard: bool = True) -> None:
    allowed = allowed_imports or ALLOWED_IMPORTS
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise AuditError("syntax: %s" % e) from e

    for node in ast.walk(tree):
        
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root not in allowed:
                    raise AuditError("forbidden import: %s" % alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.split(".")[0] not in allowed:
                raise AuditError("forbidden import: %s" % node.module)
            for alias in node.names:
                if alias.name not in ("*",) and not (alias.name in dir(__builtins__)):
                    pass
        elif isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Name) and f.id in FORBIDDEN_CALLS:
                raise AuditError("forbidden call: %s" % f.id)
            if isinstance(f, ast.Attribute):
                if f.attr in FORBIDDEN_CALLS or f.attr in FORBIDDEN_ATTRS:
                    raise AuditError("forbidden attribute call: %s" % f.attr)
        elif isinstance(node, ast.Attribute):
            if node.attr in FORBIDDEN_ATTRS:
                raise AuditError("forbidden attribute access: .%s" % node.attr)
        elif isinstance(node, ast.Name):
            if node.id in FORBIDDEN_CALLS and isinstance(node.ctx, ast.Load):
                raise AuditError("forbidden name: %s" % node.id)


@dataclass
class SandboxResult:
    ok: bool
    output: str = ""
    error: str = ""
    elapsed: float = 0.0
    timed_out: bool = False


class Sandbox:

    def __init__(self, timeout: float = 5.0, max_output: int = 64 * 1024):
        self.timeout = timeout
        self.max_output = max_output

    def run(self, code: str, cwd: Optional[str] = None) -> SandboxResult:
        try:
            audit_source(code)  
        except AuditError as e:
            return SandboxResult(ok=False, error=str(e))
        start = time.monotonic()
        try:
            proc = subprocess.Popen(
                [sys.executable, "-c", code],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=cwd,
            )
        except Exception as e:  
            return SandboxResult(ok=False, error="spawn failed: %s" % e,
                                 elapsed=time.monotonic() - start)
        try:
            out, err = proc.communicate(timeout=self.timeout)
            timed_out = False
        except subprocess.TimeoutExpired:
            proc.kill()
            out, err = proc.communicate()
            timed_out = True
        elapsed = time.monotonic() - start
        output = out.decode("utf-8", "replace")[: self.max_output]
        error = err.decode("utf-8", "replace")[: self.max_output]
        return SandboxResult(
            ok=proc.returncode == 0 and not timed_out,
            output=output,
            error=error,
            elapsed=elapsed,
            timed_out=timed_out,
        )


def safe_path(path: str, root: str) -> str:
    full = os.path.abspath(os.path.join(root, path))
    root_abs = os.path.abspath(root)
    if os.path.commonpath([full, root_abs]) != root_abs:
        raise AuditError("path escapes root: %s" % path)
    return full


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def looks_like_secret(text: str) -> bool:
    if len(text) < 16:
        return False
    if text.startswith(("ghp_", "gho_", "github_pat_", "sk-", "AKIA")):
        return True
    
    alpha = sum(1 for c in text if c.isalnum())
    return len(text) >= 24 and alpha / max(len(text), 1) > 0.85


__all__ = [
    "AuditError", "CredentialStore", "Sandbox", "SandboxResult",
    "audit_source", "redact", "safe_path", "sha256_bytes", "sha256_file",
    "looks_like_secret",
]
