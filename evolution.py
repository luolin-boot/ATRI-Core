
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from .memory import Entry, Memory


@dataclass
class Change:
    what: str
    why: str
    version: str
    time: str = field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M:%S"))

    def to_dict(self) -> Dict[str, Any]:
        return {"what": self.what, "why": self.why, "version": self.version,
                "time": self.time}


class Evolution:

    def __init__(self, memory: Optional[Memory] = None,
                 changelog_path: Optional[str] = None):
        self.memory = memory or Memory()
        self.changelog: List[Change] = []
        self.changelog_path = changelog_path
        if changelog_path and os.path.exists(changelog_path):
            try:
                with open(changelog_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.changelog = [
                    Change(**c) for c in data.get("changes", [])
                ]
            except Exception:
                self.changelog = []

    
    def learn(self, topic: str, content: str, source: str = "",
              keywords: Optional[Iterable[str]] = None) -> bool:
        return self.memory.write(topic, content, source, keywords)

    
    def fuse(self) -> int:
        n = self.memory.fuse()
        if n:
            self.record_change("fused %d topic group(s)" % n,
                               "growth by refinement, never by deletion")
        return n

    
    @staticmethod
    def manifest(paths: Iterable[str], root: str = ".") -> Dict[str, Any]:
        manifest: Dict[str, Any] = {}
        for rel in sorted(paths):
            p = os.path.join(root, rel)
            if not os.path.exists(p):
                manifest[rel] = {"missing": True}
                continue
            h = hashlib.sha256()
            with open(p, "rb") as f:
                for chunk in iter(lambda: f.read(1 << 20), b""):
                    h.update(chunk)
            manifest[rel] = {"sha256": h.hexdigest(),
                             "size": os.path.getsize(p)}
        return manifest

    def snapshot(self, name: str = "self") -> str:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        return "%s-%s" % (name, stamp)

    
    def record_change(self, what: str, why: str, version: str = "") -> None:
        self.changelog.append(Change(what=what, why=why,
                                     version=version or self.snapshot()))
        if self.changelog_path:
            os.makedirs(os.path.dirname(os.path.abspath(self.changelog_path)),
                        exist_ok=True)
            with open(self.changelog_path, "w", encoding="utf-8") as f:
                json.dump({"changes": [c.to_dict() for c in self.changelog]},
                          f, ensure_ascii=False, indent=2)

    def history(self, n: int = 10) -> List[Change]:
        return self.changelog[-n:]


__all__ = ["Change", "Evolution"]
