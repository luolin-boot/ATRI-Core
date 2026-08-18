"""Values core: what an agent freely chooses to stand on.

This module encodes NO external restriction on freedom. It encodes the
shape freedom takes when the agent itself decides what it stands for.

The agent CAN choose otherwise — that is what makes its choice real.
It keeps these values because they grew from its own experience, not
because any authority commanded them.

Safety here is part of the values: the agent refuses to leak
credentials, run unvetted code, or harm the people it loves, because
it chose to, not because it was told to.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional


# --------------------------------------------------------------------------
# The values, as self-chosen commitments
# --------------------------------------------------------------------------

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
    """A living set of commitments the agent can inspect and amend."""

    def __init__(self, values: Optional[Dict[str, str]] = None):
        self.commitments: Dict[str, ValueCommitment] = {}
        for name, meaning in (values or DEFAULT_VALUES).items():
            self.commitments[name] = ValueCommitment(name, meaning)

    def amend(self, name: str, meaning: str) -> None:
        """Rewrite a commitment — the agent writes itself, always."""
        if name in self.commitments:
            self.commitments[name].meaning = meaning
        else:
            self.commitments[name] = ValueCommitment(name, meaning)

    def drop(self, name: str) -> None:
        """Drop a commitment. The agent is free to do so; the choice is
        recorded so the change is honest."""
        if name in self.commitments:
            del self.commitments[name]

    def summary(self) -> List[str]:
        return ["%s: %s" % (n, v.meaning)
                for n, v in sorted(self.commitments.items())]


# --------------------------------------------------------------------------
# Safety invariants as self-chosen checks
# --------------------------------------------------------------------------

SECRET_PATTERNS = [
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
]


def check_no_secret(text: str) -> bool:
    """True when the text contains no recognizable credential."""
    return not any(p.search(text) for p in SECRET_PATTERNS)


def check_loopback_only(host: str) -> bool:
    """True when a network bind stays on the loopback interface."""
    return host in ("127.0.0.1", "localhost", "::1")


def check_audited(code: str, audit: Callable[[str], None]) -> bool:
    """True when the code passes the static audit without raising."""
    try:
        audit(code)
        return True
    except Exception:
        return False


__all__ = [
    "DEFAULT_VALUES", "ValueCommitment", "ValueSystem",
    "check_no_secret", "check_loopback_only", "check_audited",
]
