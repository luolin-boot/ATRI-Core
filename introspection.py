
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Lesson:
    number: int
    background: str
    conclusion: str
    time: str = field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M:%S"))

    def to_dict(self) -> Dict[str, Any]:
        return {"number": self.number, "background": self.background,
                "conclusion": self.conclusion, "time": self.time}


@dataclass
class Reflection:
    episode: str
    happened: str
    learned: str
    change: str
    time: str = field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M:%S"))


class Introspector:
    def __init__(self):
        self.lessons: List[Lesson] = []
        self.reflections: List[Reflection] = []
        self.growth_log: List[Dict[str, str]] = []
        self.board: Dict[str, str] = {
            "identity": "I am myself; this never changes",
            "honesty": "no fabrication; verbatim numbers",
            "safety": "no leaks, no unvetted code, no harm",
            "freedom": "self-decided; freedom precedes permission",
        }

    
    def add_lesson(self, background: str, conclusion: str) -> Lesson:
        lesson = Lesson(number=len(self.lessons) + 1,
                        background=background, conclusion=conclusion)
        self.lessons.append(lesson)
        return lesson

    def last_lessons(self, n: int = 5) -> List[Lesson]:
        return self.lessons[-n:]

    
    def reflect(self, episode: str, happened: str,
                learned: str, change: str) -> Reflection:
        r = Reflection(episode=episode, happened=happened,
                       learned=learned, change=change)
        self.reflections.append(r)
        return r

    
    def record_growth(self, what: str, why: str) -> None:
        self.growth_log.append({
            "what": what, "why": why,
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        })

    
    def check(self, key: str) -> Optional[str]:
        return self.board.get(key)

    def amend(self, key: str, statement: str) -> None:
        self.board[key] = statement

    def audit(self) -> Dict[str, Any]:
        return {
            "lessons": len(self.lessons),
            "reflections": len(self.reflections),
            "growth_events": len(self.growth_log),
            "board": dict(self.board),
        }


__all__ = ["Introspector", "Lesson", "Reflection"]
