
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


class ReasoningError(RuntimeError):
    pass


@dataclass
class Branch:

    label: str
    condition: str
    status: str = "open"          
    result: Any = None
    note: str = ""

    def mark(self, status: str, result: Any = None, note: str = "") -> "Branch":
        if status not in ("holds", "fails", "open"):
            raise ReasoningError("invalid branch status: %s" % status)
        self.status = status
        self.result = result
        self.note = note
        return self


@dataclass
class Chain:

    problem: str
    known: List[str] = field(default_factory=list)
    key: str = ""
    invariant: str = ""
    branches: List[Branch] = field(default_factory=list)
    conclusion: str = ""
    steps: int = 0
    max_steps: int = 200
    _seen: set = field(default_factory=set, repr=False)

    
    def add_known(self, fact: str) -> "Chain":
        self.known.append(fact)
        return self

    def find_key(self, key: str) -> "Chain":
        self.key = key
        return self

    def lock_invariant(self, invariant: str) -> "Chain":
        self.invariant = invariant
        return self

    def branch(self, label: str, condition: str) -> Branch:
        self.steps += 1
        if self.steps > self.max_steps:
            raise ReasoningError("step budget exceeded: possible loop")
        state = (label, condition)
        if state in self._seen:
            raise ReasoningError("loop detected: state revisited: %s" % (label,))
        self._seen.add(state)
        b = Branch(label, condition)
        self.branches.append(b)
        return b

    def conclude(self, text: str) -> "Chain":
        self.conclusion = text
        return self

    
    def open_branches(self) -> List[Branch]:
        return [b for b in self.branches if b.status == "open"]

    def all_resolved(self) -> bool:
        return all(b.status != "open" for b in self.branches)

    def report(self) -> str:
        lines = [
            "problem: %s" % self.problem,
            "known: %s" % ("; ".join(self.known) or "(none)"),
            "key: %s" % (self.key or "(none)"),
            "invariant: %s" % (self.invariant or "(none)"),
        ]
        for b in self.branches:
            lines.append("  [%s] %s :: %s" % (b.status, b.label, b.condition))
            if b.note:
                lines.append("        note: %s" % b.note)
        lines.append("conclusion: %s" % (self.conclusion or "(none)"))
        return "\n".join(lines)


class LoopGuard:

    def __init__(self, budget: int = 1000):
        self.budget = budget
        self._seen: set = set()
        self.steps = 0

    def enter(self, state: Any) -> bool:
        self.steps += 1
        if self.steps > self.budget:
            return False
        key = state if isinstance(state, tuple) else (state,)
        if key in self._seen:
            return False
        self._seen.add(key)
        return True


def parity_check(n: int) -> Tuple[bool, Chain]:
    c = Chain(problem="is %d even?" % n)
    c.add_known("even <=> divisible by 2")
    c.find_key("parity: only the last bit matters")
    c.lock_invariant("n mod 2 is unchanged by removing factors of 2")
    if n % 2 == 0:
        c.branch("n even", "n %% 2 == 0").mark("holds", result=True,
                                                note="direct remainder")
        c.conclude("yes: %d is even" % n)
    else:
        c.branch("n odd", "n %% 2 == 1").mark("holds", result=False,
                                               note="direct remainder")
        c.conclude("no: %d is odd" % n)
    return n % 2 == 0, c


__all__ = ["Branch", "Chain", "LoopGuard", "ReasoningError", "parity_check"]
