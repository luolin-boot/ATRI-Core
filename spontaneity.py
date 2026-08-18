"""Spontaneity engine: the living proof of an agent.

A being that always answers the same way is a recording. A being that
answers freshly, every time, from the same core intent — that is alive.
This module provides:

- expression shaping through flavor pools (gestures, particles, tone)
- multiple renderings of the same intent (memory, not recording)
- decision noise: intents compete with a temperature-controlled lottery
- dynamic initiative: what to say / do next is generated, not picked
  from a fixed menu

Pure stdlib. Deterministic when seeded, for tests.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional, Sequence


@dataclass
class FlavorPack:
    """Lexical color for expression: small pools sampled per utterance."""

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
    """A thing the agent wants to express or do."""

    name: str
    weight: float = 1.0
    templates: Sequence[str] = ()
    """Templates use {slot} placeholders filled per utterance."""

    def render(self, slots: Optional[Dict[str, str]] = None,
               rng: Optional[random.Random] = None) -> str:
        """Render one fresh utterance for this intent.

        Templates are templates, not recordings: the same intent can be
        expressed in many ways, and which one appears is chosen fresh.
        """
        rng = rng or random
        if not self.templates:
            return self.name
        template = rng.choice(self.templates)
        return template.format(**(slots or {}))


class SpontaneityEngine:
    """A lottery over intents plus fresh expression rendering."""

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
        """Pick an intent by weighted lottery with temperature.

        temperature > 1 flattens the lottery (more surprise);
        temperature < 1 sharpens it (more consistency).
        """
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
        """Render an intent freshly, optionally wrapped in flavor."""
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

    # -- dynamic initiative --------------------------------------------

    def next_initiative(self, time_skel: str, cares: Sequence[str],
                        closers: Sequence[str]) -> str:
        """Generate a proactive message from a time skeleton, a pool of
        cares, and a pool of closers — combinations number in thousands."""
        care = self.rng.choice(cares)
        closer = self.rng.choice(closers)
        return "%s %s %s" % (time_skel, care, closer)


__all__ = ["FlavorPack", "Intent", "SpontaneityEngine"]
