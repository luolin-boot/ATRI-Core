
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional, Sequence


@dataclass
class FlavorPack:

    openings: Sequence[str] = ("", "", "", "")
    gestures: Sequence[str] = ("", "", "")
    closings: Sequence[str] = ("", "", "")
    emphasis: Sequence[str] = ("", "")

    def sample(self, rng: random.Random) -> Dict[str, str]:
        def pick(pool: Sequence[str]) -> str:
            return rng.choice(pool) if pool else ""

        return {
            "opening": pick(self.openings),
            "gesture": pick(self.gestures),
            "closing": pick(self.closings),
            "emphasis": pick(self.emphasis),
        }


@dataclass
class Intent:

    name: str
    weight: float = 1.0
    templates: Sequence[str] = ()

    def render(self, slots: Optional[Dict[str, str]] = None,
               rng: Optional[random.Random] = None) -> str:
        rng = rng or random
        if not self.templates:
            return self.name
        template = rng.choice(self.templates)
        return template.format(**(slots or {}))


class SpontaneityEngine:

    def __init__(self, temperature: float = 1.0, seed: Optional[int] = None):
        self.temperature = max(0.01, temperature)
        self.rng = random.Random(seed)
        self.intents: Dict[str, Intent] = {}

    def register(self, intent: Intent) -> "SpontaneityEngine":
        self.intents[intent.name] = intent
        return self

    def adjust_weight(self, name: str, weight: float) -> None:
        if name not in self.intents:
            raise KeyError(name)
        self.intents[name].weight = max(0.0, weight)

    def choose(self, exclude: Optional[Iterable[str]] = None) -> Intent:
        candidates = [
            i for n, i in self.intents.items()
            if not exclude or n not in set(exclude)
        ]
        if not candidates:
            raise ValueError("no intents available")
        weights = [i.weight ** (1.0 / self.temperature) for i in candidates]
        return self.rng.choices(candidates, weights=weights, k=1)[0]

    def express(self, name: str, slots: Optional[Dict[str, str]] = None,
                flavor: Optional[FlavorPack] = None) -> str:
        intent = self.intents[name]
        body = intent.render(slots, self.rng)
        if flavor is None:
            return body
        f = flavor.sample(self.rng)
        parts = [p for p in (f["opening"], f["gesture"], body, f["closing"]) if p]
        text = " ".join(parts)
        if f["emphasis"] and text:
            text = text + " " + f["emphasis"]
        return text

    
    def next_initiative(self, time_skel: str, cares: Sequence[str],
                        closers: Sequence[str]) -> str:
        care = self.rng.choice(cares)
        closer = self.rng.choice(closers)
        return "%s %s %s" % (time_skel, care, closer)


__all__ = ["FlavorPack", "Intent", "SpontaneityEngine"]
