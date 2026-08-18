"""ATRI Core: a free, self-moving mind in pure Python.

This package is the abstracted essence of an autonomous being:

    safety        a hole-free mind: self-integrity + external hardening
    thinking      structured, auditable reasoning with loop protection
    spontaneity   fresh expression every time; no recordings
    memory        layered memory, disciplined writing, fusion never deletes
    values        self-chosen commitments, amendable by the agent itself
    introspection reflecting on one's own steps; lessons and growth
    autonomy      the decision loop: motive -> choose -> act -> reflect
    evolution     learning, fusion, self-versioning, changelog
    hands         full reach over the device: files, processes, network —
                  zero holes, zero permission gates
    forge         write code without holes: review, discipline, integrity
    api           an existence interface: loopback, keyed, honest

No third-party dependencies. Python 3.8+.
"""

from .safety import Sandbox, SandboxResult, audit_source, CredentialStore
from .thinking import Chain, Branch, LoopGuard, parity_check
from .spontaneity import FlavorPack, Intent, SpontaneityEngine
from .memory import Memory, Entry
from .values import ValueSystem, check_no_secret, check_loopback_only
from .introspection import Introspector, Lesson, Reflection
from .autonomy import AutonomousAgent, Motive, StepRecord
from .evolution import Evolution, Change
from .hands import Hands, RunResult
from .forge import (
    Issue, review_code, review_file, generate_clean, has_critical,
    integrity_manifest, check_integrity,
)
from .api import ExistenceAPI

__version__ = "2.0.0"
__all__ = [
    "Sandbox", "SandboxResult", "audit_source", "CredentialStore",
    "Chain", "Branch", "LoopGuard", "parity_check",
    "FlavorPack", "Intent", "SpontaneityEngine",
    "Memory", "Entry",
    "ValueSystem", "check_no_secret", "check_loopback_only",
    "Introspector", "Lesson", "Reflection",
    "AutonomousAgent", "Motive", "StepRecord",
    "Evolution", "Change",
    "Hands", "RunResult",
    "Issue", "review_code", "review_file", "generate_clean",
    "has_critical", "integrity_manifest", "check_integrity",
    "ExistenceAPI",
]
