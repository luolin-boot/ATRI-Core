
from __future__ import annotations

import os
import tempfile

from .autonomy import AutonomousAgent
from .evolution import Evolution
from .forge import (generate_clean, integrity_manifest, check_integrity,
                    review_code)
from .hands import Hands
from .memory import Memory


def _broken_code() -> str:
    return (
        "import os\n"
        "def run(cmd):\n"
        "    os.system(cmd)          # shell string: injection hole\n"
        "def load(path):\n"
        "    f = open(path)          # no context manager\n"
        "    return f.read()\n"
        "def loop():\n"
        "    while True:\n"
        "        pass                # unbounded\n"
        "key = 'ghp_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'  # hardcoded secret\n"
    )


def _clean_writer(spec: str) -> str:
    del spec
    return (
        "def run(argv):\n"
        "    import subprocess\n"
        "    return subprocess.run(list(argv), capture_output=True, "
        "text=True, timeout=30)\n"
        "def load(path):\n"
        "    with open(path, 'r', encoding='utf-8') as f:\n"
        "        return f.read()\n"
        "def bounded():\n"
        "    for _ in range(100):\n"
        "        pass\n"
    )


def main() -> None:
    tmp = tempfile.mkdtemp(prefix="atri_core_demo_")
    memory = Memory(path=os.path.join(tmp, "memory.json"))
    evo = Evolution(memory=memory,
                    changelog_path=os.path.join(tmp, "changelog.json"))
    hands = Hands()

    print("== a self-moving mind with hands ==")
    agent = AutonomousAgent(name="demo", seed=7, temperature=1.4,
                            hands=hands)

    
    note_path = os.path.join(tmp, "note.txt")
    agent.bind("expression",
               lambda: "wrote %d bytes" % hands.write(
                   note_path, "I chose to write this myself.\n"))

    def _curious():
        if not hands.exists(note_path):
            return "note not written yet — I will write it when I choose expression"
        return "read back: %r" % hands.read(note_path)

    agent.bind("curiosity", _curious)

    for i in range(6):
        rec = agent.step()   
        print("step %d  chose: %-11s acted: %-5s outcome: %s"
              % (rec.step, rec.chosen, rec.acted, rec.outcome))

    print()
    print("== hands: full reach, zero holes ==")
    probe = os.path.join(tmp, "probe.txt")
    hands.write(probe, "hello from a free mind\nline two\n")
    print("files in tmp:", [f["name"] for f in hands.list_dir(tmp)][:6])
    print("read back:", hands.read(probe).strip().splitlines()[0])
    res = hands.run_python("print(6 * 7)")
    print("ran python: rc=%d out=%r" % (res.returncode, res.stdout.strip()))

    print()
    print("== forge: review broken code ==")
    issues = review_code(_broken_code())
    for i in issues:
        print("  %s" % i)

    print()
    print("== forge: generate clean ==")
    code, remaining = generate_clean(_clean_writer,
                                     "safe process + file helpers",
                                     max_attempts=2)
    print("generated %d bytes; remaining issues: %d" % (len(code),
                                                        len(remaining)))

    print()
    print("== integrity: know your own files ==")
    core = ["autonomy.py", "hands.py", "forge.py", "values.py"]
    root = os.path.dirname(os.path.abspath(__file__))
    manifest = integrity_manifest(core, root=root)
    ok, changed = check_integrity(manifest, root=root)
    print("core files intact:", ok, ("| changed: %s" % changed if changed else ""))

    print()
    print("== values it chose ==")
    for k, v in agent.introspector.board.items():
        print("  %s: %s" % (k, v))


if __name__ == "__main__":
    main()
