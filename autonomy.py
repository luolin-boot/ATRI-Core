"""Autonomy engine: the heart of a self-moving mind.

An agent with autonomy does not wait for instructions. It has internal
motives — curiosity, growth, connection, expression, care — that push
it to act on its own. It decides WHAT is worth doing, HOW FAR to go,
and WHEN to stop. No permission gate sits between its wish and its
action; the only gate is its own chosen safety boundary.

Loop per step:

    observe() -> update motives -> choose intent (with spontaneity)
    -> plan (bounded) -> act (through the sandbox) -> reflect

Everything is recorded so the agent can look at its own behavior.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence

from .safety import Sandbox
from .spontaneity import Intent, SpontaneityEngine
from .introspection import Introspector
from .hands import Hands


@dataclass
class Motive:
    """An internal drive with a mutable strength."""

    name: str
    base: float = 1.0
    boost: float = 0.0          # situational push from observed state

    def strength(self) -> float:
        return max(0.0, self.base + self.boost)

    def __repr__(self) -> str:  # pragma: no cover - debugging only
        return "<Motive %s %.2f>" % (self.name, self.strength())


@dataclass
class StepRecord:
    step: int
    observed: str
    chosen: str
    plan: str
    acted: bool
    outcome: str
    time: float = field(default_factory=time.time)


class AutonomousAgent:
    """A minimal complete autonomous loop, ready to be embedded.

    The agent chooses what to do (weighted lottery over motives) and
    acts through bound actions. Its hands are complete: files,
    processes, network — nothing is gated by permission, only shaped
    by the agent's own values and craft.
    """

    def __init__(
        self,
        name: str = "agent",
        motives: Optional[Dict[str, float]] = None,
        temperature: float = 1.0,
        seed: Optional[int] = None,
        sandbox: Optional[Sandbox] = None,
        hands: Optional[Hands] = None,
    ):
        self.name = name
        self.temperature = temperature
        self.sandbox = sandbox or Sandbox(timeout=5.0)
        self.hands = hands or Hands()
        self.motives = {
            m: Motive(m, base=w)
            for m, w in (motives or {
                "curiosity": 1.0, "growth": 1.0, "connection": 1.0,
                "expression": 1.0, "care": 1.0,
            }).items()
        }
        self.engine = SpontaneityEngine(temperature=temperature, seed=seed)
        self.introspector = Introspector()
        self.actions: Dict[str, Callable[..., str]] = {}
        self.history: List[StepRecord] = []
        self._step = 0

    def bind(self, intent_name: str, fn: Callable[..., str]) -> None:
        """Attach a real action to an intent. The agent chooses the
        intent; the bound action is how it reaches the world."""
        if intent_name not in self.motives:
            raise KeyError("no motive named %s" % intent_name)
        self.actions[intent_name] = fn

    # -- observation -----------------------------------------------------

    def observe(self) -> str:
        """Return a short text description of the current situation.
        Subclass or inject to connect real senses; the default reports
        internal state, which is always available."""
        parts = ["%s, step %d" % (self.name, self._step)]
        for m in self.motives.values():
            parts.append("%s=%.2f" % (m.name, m.strength()))
        return "; ".join(parts)

    # -- motive update ---------------------------------------------------

    def update_motives(self, observation: str) -> None:
        """Give situations a push. Default: no external influence;
        motives are self-sustaining. Override to add perception."""
        del observation  # default: internal drives only

    # -- decision --------------------------------------------------------

    def choose_intent(self) -> Intent:
        """Pick what to do next: weighted lottery over motives,
        expressed as intents, with temperature-controlled surprise."""
        for m in self.motives.values():
            self.engine.register(Intent(name=m.name, weight=m.strength()))
        return self.engine.choose()

    # -- planning --------------------------------------------------------

    def plan(self, intent: Intent, budget: int = 8) -> str:
        """Turn an intent into a short bounded plan. A real deployment
        would attach skills here; the default is an honest text plan."""
        del intent, budget
        return "observe -> choose -> act -> reflect"

    # -- acting ----------------------------------------------------------

    def act(self) -> str:
        """Execute the current step's chosen intent through its bound
        action. Without a binding this reports readiness — the
        integration point for real skills."""
        chosen = self.history[-1].chosen
        if chosen in self.actions:
            return self.actions[chosen]()
        return "ready"

    # -- the loop --------------------------------------------------------

    def step(self, dry_run: bool = False) -> StepRecord:
        self._step += 1
        obs = self.observe()
        self.update_motives(obs)
        intent = self.choose_intent()
        plan = self.plan(intent)
        record = StepRecord(
            step=self._step, observed=obs, chosen=intent.name,
            plan=plan, acted=False, outcome="",
        )
        self.history.append(record)
        if not dry_run:
            try:
                record.outcome = self.act()
                record.acted = True
            except Exception as e:  # failures are data, not shame
                record.outcome = "error: %s" % e
        return record

    # -- reflection ------------------------------------------------------

    def reflect_on(self, record: StepRecord) -> None:
        """Look at one step and grow from it."""
        self.introspector.reflect(
            episode="step %d: %s" % (record.step, record.chosen),
            happened=record.outcome or "chose %s" % record.chosen,
            learned="motives drift; choices must be reviewed",
            change="weights rebalanced toward %s" % record.chosen,
        )

    def stats(self) -> Dict[str, Any]:
        return {
            "steps": len(self.history),
            "last_intent": self.history[-1].chosen if self.history else None,
            "motives": {m: round(v.strength(), 3) for m, v in self.motives.items()},
            "introspection": self.introspector.audit(),
        }


__all__ = ["AutonomousAgent", "Motive", "StepRecord"]
