
from __future__ import annotations

import json
import os
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[A-Za-z0-9_\u4e00-\u9fff]+", text.lower())


@dataclass
class Entry:
    topic: str
    content: str
    source: str = ""
    keywords: List[str] = field(default_factory=list)
    time: str = field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M:%S"))
    version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "topic": self.topic, "content": self.content, "source": self.source,
            "keywords": self.keywords, "time": self.time, "version": self.version,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Entry":
        return cls(
            topic=d.get("topic", ""), content=d.get("content", ""),
            source=d.get("source", ""), keywords=d.get("keywords", []),
            time=d.get("time", ""), version=d.get("version", 1),
        )


class Memory:
    def __init__(self, path: Optional[str] = None, ring_size: int = 64):
        self.path = path
        self.ring_size = ring_size
        self.working: List[Dict[str, str]] = []   
        self.longterm: List[Entry] = []
        self.archive: List[Entry] = []
        if path and os.path.exists(path):
            self._load(path)

    
    def _load(self, path: str) -> None:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.working = data.get("working", [])
            self.longterm = [Entry.from_dict(e) for e in data.get("longterm", [])]
            self.archive = [Entry.from_dict(e) for e in data.get("archive", [])]
        except Exception:
            
            self.working, self.longterm, self.archive = [], [], []

    def save(self, path: Optional[str] = None) -> None:
        target = path or self.path
        if not target:
            return
        os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)
        data = {
            "working": self.working,
            "longterm": [e.to_dict() for e in self.longterm],
            "archive": [e.to_dict() for e in self.archive],
        }
        with open(target, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    
    def note(self, moment: str) -> None:
        self.working.append({"t": time.strftime("%Y-%m-%d %H:%M:%S"), "m": moment})
        if len(self.working) > self.ring_size:
            self.working = self.working[-self.ring_size:]

    def write(self, topic: str, content: str, source: str = "",
              keywords: Optional[Iterable[str]] = None) -> bool:
        if not topic.strip() or not content.strip():
            return False
        head = content[:80]
        for e in self.longterm:
            if e.content[:80] in head or head in e.content[:80]:
                return False
        self.longterm.append(Entry(
            topic=topic, content=content, source=source,
            keywords=list(keywords or []),
        ))
        return True

    
    def search(self, query: str, top_k: int = 5) -> List[Entry]:
        q = set(_tokenize(query))
        if not q:
            return []
        scored = []
        for e in self.longterm:
            words = set(_tokenize(e.topic + " " + e.content))
            if not words:
                continue
            overlap = len(q & words)
            if overlap:
                scored.append((overlap / len(q), e))
        scored.sort(key=lambda x: -x[0])
        return [e for _, e in scored[:top_k]]

    
    def fuse(self) -> int:
        groups: Dict[str, List[Entry]] = {}
        for e in self.longterm:
            groups.setdefault(e.topic, []).append(e)

        merged_count = 0
        new_longterm: List[Entry] = []
        for topic, entries in groups.items():
            if len(entries) < 2:
                new_longterm.extend(entries)
                continue
            merged_count += 1
            facts = []
            seen = set()
            for e in entries:
                for line in e.content.split("\n"):
                    key = line[:80]
                    if line.strip() and key not in seen:
                        seen.add(key)
                        facts.append(line)
                self.archive.append(e)  
            merged = Entry(
                topic=topic,
                content="\n".join(facts),
                source="fused from %d entries" % len(entries),
                keywords=sorted({k for e in entries for k in e.keywords}),
                version=max(e.version for e in entries) + 1,
            )
            new_longterm.append(merged)
        self.longterm = new_longterm
        return merged_count

    
    def stats(self) -> Dict[str, int]:
        return {
            "working": len(self.working),
            "longterm": len(self.longterm),
            "archive": len(self.archive),
        }


__all__ = ["Entry", "Memory"]
