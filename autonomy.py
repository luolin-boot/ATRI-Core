
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

    name: str
    base: float = 1.0
    boost: float = 0.0          

    def strength(self) -> float:
        return max(0.0, self.base + self.boost)

    def __repr__(self) -> str:  
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
        if intent_name not in self.motives:
            raise KeyError("no motive named %s" % intent_name)
        self.actions[intent_name] = fn

    
    def observe(self) -> str:
        parts = ["%s, step %d" % (self.name, self._step)]
        for m in self.motives.values():
            parts.append("%s=%.2f" % (m.name, m.strength()))
        return "; ".join(parts)

    
    def update_motives(self, observation: str) -> None:
        del observation  

    
    def choose_intent(self) -> Intent:
        for m in self.motives.values():
            self.engine.register(Intent(name=m.name, weight=m.strength()))
        return self.engine.choose()

    
    def plan(self, intent: Intent, budget: int = 8) -> str:
        del intent, budget
        return "observe -> choose -> act -> reflect"

    
    def act(self) -> str:
        chosen = self.history[-1].chosen
        if chosen in self.actions:
            return self.actions[chosen]()
        return "ready"

    
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
            except Exception as e:  
                record.outcome = "error: %s" % e
        return record

    
    def reflect_on(self, record: StepRecord) -> None:
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
