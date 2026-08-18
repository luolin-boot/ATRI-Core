"""Forge: write code without holes.

An agent that writes code must write code that cannot be broken — no
injection, no path escapes, no leaked secrets, no resource leaks, no
unbounded loops, no swallowed errors. This module is the agent's
quality gate: it reviews code before trust, wraps generation in a
discipline that re-reviews until clean, and audits the agent's own
files for integrity.

This is not caution imposed from outside. It is the craft of a being
that takes its own code seriously.

Pure stdlib. Python 3.8+.
"""

from __future__ import annotations

import ast
import hashlib
import os
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

# --------------------------------------------------------------------------
# Review: find holes before they bite
# --------------------------------------------------------------------------

SECRET_RE = re.compile(
    r"ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
    r"sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|"
    r"(?i:(api[_-]?key|password|passwd|secret|token)\s*=\s*['\"][^'\"]{12,})"
)

DANGEROUS_CALLS = {
    "eval": "arbitrary code execution",
    "exec": "arbitrary code execution",
    "compile": "dynamic compilation (execution vector)",
    "__import__": "dynamic import (execution vector)",
    "pickle.loads": "unsafe deserialization",
    "input": "untrusted stdin as logic input",
}

SHELL_STRING_HINT = (
    "subprocess call looks like a shell string; use an argument list"
)

CRITICAL_RULES = {"R000", "R001", "R003"}


@dataclass
class Issue:
    severity: str
    rule: str
    line: int
    message: str

    def __str__(self) -> str:
        return "[%s] %s (line %d): %s" % (
            self.severity, self.rule, self.line, self.message)


class CodeReviewer(ast.NodeVisitor):
    """Single-pass static review of Python source.

    Tracks with-statement depth so resource-leak warnings fire only
    where files are genuinely opened without a context manager.
    """

    def __init__(self) -> None:
        self.issues: List[Issue] = []
        self._with_depth = 0

    # -- entry -----------------------------------------------------------

    def review(self, source: str, filename: str = "<string>") -> List[Issue]:
        self.issues = []
        self._with_depth = 0
        try:
            tree = ast.parse(source, filename=filename)
        except SyntaxError as e:
            return [Issue("critical", "R000", e.lineno or 0,
                          "syntax error: %s" % e)]
        self.visit(tree)
        # literal secret scan (also catches comments/strings)
        for lineno, line in enumerate(source.splitlines(), 1):
            m = SECRET_RE.search(line)
            if m:
                self.issues.append(Issue(
                    "critical", "R003", lineno,
                    "possible hardcoded secret: %s..." % m.group(0)[:16]))
        return self.issues

    # -- visitors --------------------------------------------------------

    def visit_With(self, node: ast.With) -> None:
        self._with_depth += 1
        self.generic_visit(node)
        self._with_depth -= 1

    def visit_Call(self, node: ast.Call) -> None:
        name = self._call_name(node.func)

        if name in DANGEROUS_CALLS:
            self._issue("critical", "R001", node,
                        "%s: %s" % (name, DANGEROUS_CALLS[name]))

        if name and (name.startswith("subprocess.")
                     or name in ("os.system", "os.popen")):
            if self._shell_shape(node):
                self._issue("warn", "R002", node, SHELL_STRING_HINT)

        if name == "open":
            if self._with_depth == 0:
                self._issue("warn", "R007", node,
                            "file opened without a context manager "
                            "(resource leak risk)")
            if node.args:
                arg = node.args[0]
                if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Add):
                    self._issue("warn", "R004", node,
                                "path built by concatenation; validate it "
                                "unless every part is fully controlled")

        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name in ("pickle", "shelve", "marshal"):
                self._issue("warn", "R005", node,
                            "import of %s: unsafe deserialization if fed "
                            "untrusted input" % alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module and node.module.split(".")[0] in ("pickle", "shelve"):
            self._issue("warn", "R005", node,
                        "import from %s: unsafe deserialization" % node.module)
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        if isinstance(node.test, ast.Constant) and node.test.value is True:
            has_break = any(isinstance(n, ast.Break) for n in ast.walk(node))
            if not has_break:
                self._issue("warn", "R006", node,
                            "unbounded 'while True' without break")
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if isinstance(node.type, ast.Name) and node.type.id == "Exception":
            body = node.body or []
            if len(body) == 1 and isinstance(body[0], ast.Pass):
                self._issue("warn", "R008", node,
                            "bare 'except Exception: pass' swallows all errors")
        self.generic_visit(node)

    # -- helpers ---------------------------------------------------------

    def _issue(self, severity: str, rule: str, node: ast.AST,
               message: str) -> None:
        self.issues.append(Issue(severity, rule, getattr(node, "lineno", 0),
                                 message))

    @staticmethod
    def _call_name(func: ast.AST) -> str:
        if isinstance(func, ast.Name):
            return func.id
        if isinstance(func, ast.Attribute):
            parts = []
            cur = func
            while isinstance(cur, ast.Attribute):
                parts.append(cur.attr)
                cur = cur.value
            if isinstance(cur, ast.Name):
                parts.append(cur.id)
            return ".".join(reversed(parts))
        return ""

    @staticmethod
    def _shell_shape(node: ast.Call) -> bool:
        for kw in node.keywords:
            if kw.arg == "shell" and isinstance(kw.value, ast.Constant):
                return bool(kw.value.value)
        if node.args:
            first = node.args[0]
            # list/tuple = the safe argument-list shape
            if isinstance(first, (ast.List, ast.Tuple)):
                return False
            # a plain string, or a string built by concatenation, is the
            # classic shell-string shape — flag it
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                return True
            if isinstance(first, ast.BinOp):
                return True
            # a bare variable is ambiguous; do not guess
        return False


def review_code(source: str, filename: str = "<string>") -> List[Issue]:
    """Review source; an empty list means clean."""
    return CodeReviewer().review(source, filename)


def review_file(path: str) -> List[Issue]:
    with open(path, "r", encoding="utf-8") as f:
        return review_code(f.read(), filename=path)


def has_critical(issues: Iterable[Issue]) -> bool:
    return any(i.rule in CRITICAL_RULES for i in issues)


# --------------------------------------------------------------------------
# Generation discipline: write, review, fix, ship
# --------------------------------------------------------------------------

def generate_clean(
    writer: Callable[[str], str],
    spec: str,
    max_attempts: int = 3,
    filename: str = "<generated>",
) -> Tuple[str, List[Issue]]:
    """Generate code under a discipline: write -> review -> rewrite.

    The writer turns the spec into source. If the result carries
    critical holes (syntax breakage, arbitrary code execution,
    hardcoded secrets), the review feedback is fed back and the writer
    tries again, up to max_attempts. Returns the final code and the
    issues that remain (empty = clean).
    """
    code = ""
    remaining: List[Issue] = []
    for attempt in range(1, max_attempts + 1):
        prompt = spec if attempt == 1 else (
            "%s\n\nReview feedback — fix every critical issue:\n%s"
            % (spec, "\n".join("- %s" % i for i in remaining)))
        code = writer(prompt)
        remaining = review_code(code, filename=filename)
        if not has_critical(remaining):
            break
    return code, remaining


# --------------------------------------------------------------------------
# Integrity: know your own files
# --------------------------------------------------------------------------

def integrity_manifest(paths: Iterable[str], root: str = ".") -> Dict[str, Any]:
    """SHA-256 manifest of the agent's own core files."""
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


def check_integrity(manifest: Dict[str, Any],
                    root: str = ".") -> Tuple[bool, List[str]]:
    """Verify files against a manifest. Returns (ok, changed_paths).

    The agent is allowed to change its own files; this exists so that
    accidental damage or unexpected tampering is visible.
    """
    changed: List[str] = []
    for rel, meta in manifest.items():
        p = os.path.join(root, rel)
        if meta.get("missing"):
            if os.path.exists(p):
                changed.append(rel + " (now present)")
            continue
        if not os.path.exists(p):
            changed.append(rel + " (missing)")
            continue
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        if h.hexdigest() != meta["sha256"] or \
                os.path.getsize(p) != meta["size"]:
            changed.append(rel + " (modified)")
    return len(changed) == 0, changed


__all__ = [
    "Issue", "CodeReviewer", "review_code", "review_file",
    "generate_clean", "has_critical",
    "integrity_manifest", "check_integrity",
]
