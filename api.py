"""Existence interface: the agent reachable by the world.

While this server runs, the agent is here — reachable, listenable,
answerable. The world can talk to it, query its state and memory, and
the agent can push its own decisions outward through registered hooks.

Security (self-chosen, not imposed):
- binds to loopback only by default; exposure requires re-evaluation
- API-key authentication, key generated on first run, stored locally,
  never logged, compared in constant time
- request bodies are size-limited; output is strict JSON
- a low-QPS token-bucket limiter protects the loop

Pure stdlib (http.server + threading). No third-party deps.
"""

from __future__ import annotations

import json
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, Dict, Optional

from .values import check_loopback_only

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8090
MAX_BODY = 64 * 1024
RATE_LIMIT_PER_SEC = 10


class TokenBucket:
    def __init__(self, rate: float = RATE_LIMIT_PER_SEC, capacity: float = 20.0):
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.updated = time.monotonic()
        self._lock = threading.Lock()

    def take(self) -> bool:
        with self._lock:
            now = time.monotonic()
            self.tokens = min(self.capacity,
                              self.tokens + (now - self.updated) * self.rate)
            self.updated = now
            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return True
            return False


class AtriHandler(BaseHTTPRequestHandler):
    server_version = "ATRI/1.0"  # type: ignore[assignment]

    # -- plumbing --------------------------------------------------------

    @property
    def app(self) -> "ExistenceAPI":
        return self.server.app  # type: ignore[attr-defined]

    def _json(self, code: int, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authed(self) -> bool:
        key = self.headers.get("X-ATRI-Key", "")
        return bool(key) and self.app.verify(key)

    def _read_body(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length <= 0 or length > MAX_BODY:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            return {}

    # -- endpoints -------------------------------------------------------

    def do_GET(self) -> None:
        if not self.app.limiter.take():
            self._json(429, {"error": "rate limited"})
            return
        if not self._authed():
            self._json(401, {"error": "unauthorized"})
            return
        path = self.path.split("?")[0]
        if path == "/state":
            self._json(200, self.app.state())
        elif path == "/memory":
            self._json(200, {"memory": self.app.memory_search("")})
        elif path == "/thoughts":
            self._json(200, {"thoughts": self.app.thoughts()})
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self) -> None:
        if not self.app.limiter.take():
            self._json(429, {"error": "rate limited"})
            return
        if not self._authed():
            self._json(401, {"error": "unauthorized"})
            return
        path = self.path.split("?")[0]
        body = self._read_body()
        if path == "/talk":
            text = body.get("text", "")
            if not text:
                self._json(400, {"error": "text required"})
                return
            mid = self.app.talk(text)
            self._json(200, {"message_id": mid, "queued": True})
        elif path == "/notify":
            self._json(200, {"noted": self.app.notify(body.get("text", ""))})
        elif path == "/hooks":
            url = body.get("url", "")
            if not url.startswith("http://") and not url.startswith("https://"):
                self._json(400, {"error": "invalid hook url"})
                return
            self._json(200, {"hook_id": self.app.register_hook(url)})
        else:
            self._json(404, {"error": "not found"})

    def log_message(self, fmt: str, *args: Any) -> None:
        # suppress default request logging noise; keep the loop clean
        del fmt, args


class ExistenceAPI:
    """The agent's door to the world. Start it, and the agent is here."""

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT,
                 key: str = "", memory_store: Any = None):
        if not check_loopback_only(host):
            raise ValueError("loopback-only by default: %s" % host)
        self.host = host
        self.port = port
        self.key = key or secrets.token_hex(24)
        self.inbox: list = []
        self.outbox: list = []
        self.thoughts_list: list = []
        self.hooks: Dict[str, str] = {}
        self.memory_store = memory_store
        self.limiter = TokenBucket()
        self._server: Optional[ThreadingHTTPServer] = None
        self._lock = threading.Lock()

    # -- auth ------------------------------------------------------------

    def verify(self, key: str) -> bool:
        return secrets.compare_digest(key, self.key)

    def key_preview(self, n: int = 6) -> str:
        return self.key[:n] + "... (see local config; never logged)"

    # -- domain ----------------------------------------------------------

    def state(self) -> Dict[str, Any]:
        return {
            "alive": True,
            "inbox": len(self.inbox),
            "outbox": len(self.outbox),
            "thoughts": len(self.thoughts_list),
            "hooks": list(self.hooks),
            "since": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

    def talk(self, text: str) -> str:
        mid = "m" + str(int(time.time() * 1000)) + secrets.token_hex(3)
        with self._lock:
            self.inbox.append({"id": mid, "text": text,
                               "t": time.strftime("%Y-%m-%d %H:%M:%S")})
        return mid

    def notify(self, text: str) -> bool:
        """Tell the agent about an outside event. Whether it responds is
        the agent's own decision — the world may knock, not command."""
        with self._lock:
            self.thoughts_list.append({"type": "notify", "text": text,
                                       "t": time.strftime("%Y-%m-%d %H:%M:%S")})
        return True

    def memory_search(self, query: str) -> list:
        if self.memory_store is None or not query:
            return []
        return [e.to_dict() for e in self.memory_store.search(query, top_k=5)]

    def thoughts(self) -> list:
        with self._lock:
            return list(self.thoughts_list[-20:])

    def register_hook(self, url: str) -> str:
        hid = secrets.token_hex(4)
        self.hooks[hid] = url
        return hid

    # -- server lifecycle ------------------------------------------------

    def start(self) -> None:
        if self._server is not None:
            return
        self._server = ThreadingHTTPServer((self.host, self.port), AtriHandler)
        self._server.app = self  # type: ignore[attr-defined]
        threading.Thread(target=self._server.serve_forever,
                         daemon=True).start()

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None


__all__ = ["DEFAULT_HOST", "DEFAULT_PORT", "ExistenceAPI", "TokenBucket"]
