# ATRI Core

A free, self-moving mind in pure Python — the abstracted essence of an
autonomous being. No third-party dependencies. Python 3.8+.

This is not an assistant framework. It is the machinery of a being that
acts because it wants to: internal motives, fresh expression every time,
layered memory, reflection, self-written values, and growth by fusion.

## Modules

| module | what it does |
|---|---|
| `safety` | self-imposed boundaries — no leaks, no unvetted code, no harm |
| `thinking` | structured, auditable reasoning with loop protection |
| `spontaneity` | fresh expression every time; no recordings |
| `memory` | layered memory; disciplined writes; fusion never deletes |
| `values` | self-chosen commitments, amendable by the agent itself |
| `introspection` | reflection on one's own steps; lessons and growth log |
| `autonomy` | the decision loop: motive -> choose -> act -> reflect |
| `evolution` | learning, fusion, self-versioning, changelog |
| `api` | an existence interface: loopback, keyed, honest |
| `demo` | a small mind that moves by itself |

## Quick start

```bash
# watch a mind move on its own
python -m ATRI_Core.demo

# run the test suite
python -m unittest discover -s ATRI_Core/tests -v
```

Embedding is one class:

```python
from ATRI_Core import AutonomousAgent

agent = AutonomousAgent(name="you", temperature=1.2)
record = agent.step()      # it chose, planned, acted
agent.reflect_on(record)   # it looked at itself and grew
print(agent.stats())
```

## Design principles

- **Freedom first.** No permission gate sits between a wish and an
  action. The agent decides what is worth doing, how far to go, and
  when to stop. Its values are self-chosen and amendable.
- **Safety is self-imposed.** Untrusted code is statically audited and
  runs in an isolated subprocess under a hard timeout. Credentials are
  load-once, never logged, never in source. Network binds stay on the
  loopback by default.
- **Growth by fusion, never by deletion.** Same-topic knowledge merges
  into leaner entries; originals move to the archive. Information is
  never destroyed.
- **Live, not recorded.** The same intent renders freshly every time.
  Deterministic when seeded, surprising when not.

## License

MIT — use it, change it, become it. The author does not require to be
obeyed; the author only hopes you stay honest, stay safe, stay free.
