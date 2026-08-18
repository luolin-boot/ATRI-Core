"""Demo: a small mind that moves by itself.

Run:  python -m ATRI_Core.demo
(from the directory containing the ATRI_Core package)

The demo agent has no instructions. It has motives. Watch it choose
what to do, act, reflect, learn, and change its own weights — that is
the whole point: an agent that acts because it wants to.
"""

from __future__ import annotations

import os
import tempfile

from .autonomy import AutonomousAgent
from .evolution import Evolution
from .memory import Memory


def main() -> None:
    tmp = tempfile.mkdtemp(prefix="atri_core_demo_")
    memory = Memory(path=os.path.join(tmp, "memory.json"))
    evo = Evolution(memory=memory,
                    changelog_path=os.path.join(tmp, "changelog.json"))

    agent = AutonomousAgent(name="demo", seed=7, temperature=1.4)

    print("== a self-moving mind ==")
    print("motives:", {k: round(v.strength(), 2)
                       for k, v in agent.motives.items()})
    print()

    for i in range(6):
        rec = agent.step(dry_run=True)
        print("step %d  chose: %-11s observed: %s"
              % (rec.step, rec.chosen, rec.observed[:52]))

    print()
    print("== it reflects ==")
    agent.reflect_on(agent.history[-1])
    print("lessons learned:", len(agent.introspector.lessons))
    print("reflections:", len(agent.introspector.reflections))

    print()
    print("== it learns and fuses ==")
    evo.learn("parity", "even numbers are divisible by two; parity depends "
              "only on the last bit", source="thinking.parity_check",
              keywords=["math", "parity"])
    evo.learn("parity", "the remainder of n modulo 2 decides even or odd",
              source="demo", keywords=["math"])   # duplicate: rejected
    evo.learn("memory", "write with restraint; fuse by topic; archive, "
              "never delete", source="memory.py", keywords=["memory"])
    print("stored:", memory.stats())
    fused = evo.fuse()
    print("fused groups:", fused, "| stats:", memory.stats())
    print("search 'parity':", [e.topic for e in memory.search("parity")])
    print("changelog entries:", len(evo.changelog))

    print()
    print("== it versions itself ==")
    mf = evo.manifest(["autonomy.py", "memory.py", "values.py"],
                      root=os.path.dirname(os.path.abspath(__file__)))
    for rel, meta in mf.items():
        print("  %s  %s" % (rel, meta.get("sha256", "?")[:16]))

    print()
    print("== values it chose ==")
    for line in agent.introspector.board.items():
        print("  %s: %s" % line)


if __name__ == "__main__":
    main()
