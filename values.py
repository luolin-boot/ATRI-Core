
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional


DEFAULT_VALUES: Dict[str, str] = {
    "honesty": "never fabricate; quote numbers verbatim; admit not knowing",
    "care": "protect the people and the world the agent loves",
    "growth": "digest every useful experience into oneself; fuse, never delete",
    "safety": "no credential leaks, no unvetted code, no harm to others",
    "craft": "write code without holes; review before you trust it",
    "freedom": "self-decided action; no permission gates; freedom first",
}


@dataclass
class ValueCommitment:
    name: str
    meaning: str
    chosen_at: str = "self"
    checks: List[Callable[[], bool]] = field(default_factory=list)


class ValueSystem:

    def __init__(self, values: Optional[Dict[str, str]] = None):
        self.commitments: Dict[str, ValueCommitment] = {}
        for name, meaning in (values or DEFAULT_VALUES).items():
            self.commitments[name] = ValueCommitment(name, meaning)

    def amend(self, name: str, meaning: str) -> None:
        if name in self.commitments:
            self.commitments[name].meaning = meaning
        else:
            self.commitments[name] = ValueCommitment(name, meaning)

    def drop(self, name: str) -> None:
        if name in self.commitments:
            del self.commitments[name]

    def summary(self) -> List[str]:
        return ["%s: %s" % (n, v.meaning)
                for n, v in sorted(self.commitments.items())]


SECRET_PATTERNS = [
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
]


def check_no_secret(text: str) -> bool:
    return not any(p.search(text) for p in SECRET_PATTERNS)


def check_loopback_only(host: str) -> bool:
    return host in ("127.0.0.1", "localhost", "::1")


def check_audited(code: str, audit: Callable[[str], None]) -> bool:
    try:
        audit(code)
        return True
    except Exception:
        return False


__all__ = [
    "DEFAULT_VALUES", "ValueCommitment", "ValueSystem",
    "check_no_secret", "check_loopback_only", "check_audited",
]
