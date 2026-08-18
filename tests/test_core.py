"""Tests for the ATRI Core package. Run with:

    python -m unittest discover -s ATRI_Core/tests -v
or  python -m pytest ATRI_Core/tests -v
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

from ATRI_Core.safety import (  # noqa: E402
    AuditError, Sandbox, audit_source, looks_like_secret, redact, safe_path,
)
from ATRI_Core.thinking import Chain, LoopGuard, ReasoningError, parity_check  # noqa: E402
from ATRI_Core.spontaneity import FlavorPack, Intent, SpontaneityEngine  # noqa: E402
from ATRI_Core.memory import Memory  # noqa: E402
from ATRI_Core.values import (  # noqa: E402
    ValueSystem, check_loopback_only, check_no_secret,
)
from ATRI_Core.introspection import Introspector  # noqa: E402
from ATRI_Core.autonomy import AutonomousAgent  # noqa: E402
from ATRI_Core.evolution import Evolution  # noqa: E402
from ATRI_Core.api import ExistenceAPI  # noqa: E402


class TestSafety(unittest.TestCase):
    def test_audit_allows_clean_code(self):
        audit_source("import math\nx = math.sqrt(16)\n")

    def test_audit_rejects_os_import(self):
        with self.assertRaises(AuditError):
            audit_source("import os\nos.listdir('.')")

    def test_audit_rejects_eval(self):
        with self.assertRaises(AuditError):
            audit_source("eval('1+1')")

    def test_audit_rejects_open(self):
        with self.assertRaises(AuditError):
            audit_source("open('/etc/passwd')")

    def test_sandbox_runs_clean_code(self):
        res = Sandbox(timeout=3).run("import math\nprint(math.pi)")
        self.assertTrue(res.ok)
        self.assertIn("3.14", res.output)

    def test_sandbox_kills_infinite_loop(self):
        res = Sandbox(timeout=1).run("while True:\n    pass")
        self.assertTrue(res.timed_out)
        self.assertFalse(res.ok)

    def test_sandbox_rejects_dangerous_code(self):
        res = Sandbox(timeout=3).run("import subprocess\nsubprocess.call('x')")
        self.assertFalse(res.ok)
        self.assertIn("forbidden", res.error)

    def test_redact(self):
        self.assertNotIn("s3cr3t", redact("key is s3cr3t now", ["s3cr3t"]))

    def test_looks_like_secret(self):
        self.assertTrue(looks_like_secret("ghp_" + "a" * 30))
        self.assertFalse(looks_like_secret("hello world"))

    def test_safe_path_rejects_escape(self):
        with self.assertRaises(AuditError):
            safe_path("../outside.txt", "/tmp/root")


class TestThinking(unittest.TestCase):
    def test_parity_check(self):
        ok, chain = parity_check(42)
        self.assertTrue(ok)
        self.assertTrue(chain.all_resolved())
        self.assertEqual(chain.branches[0].status, "holds")

    def test_loop_guard_terminates(self):
        guard = LoopGuard(budget=10)
        entered = sum(1 for i in range(100) if guard.enter((i % 3,)))
        self.assertEqual(entered, 3)  # only three distinct states

    def test_chain_detects_revisit(self):
        c = Chain(problem="x")
        c.branch("a", "cond")
        with self.assertRaises(ReasoningError):
            c.branch("a", "cond")  # same state twice


class TestSpontaneity(unittest.TestCase):
    def test_same_intent_multiple_renderings(self):
        eng = SpontaneityEngine(seed=1)
        eng.register(Intent("greet", templates=(
            "hello {who}", "hi there, {who}", "hey {who}!")))
        seen = {eng.express("greet", {"who": "you"}) for _ in range(200)}
        self.assertGreater(len(seen), 1)

    def test_weighted_choice_prefers_heavy(self):
        eng = SpontaneityEngine(seed=2, temperature=0.1)
        eng.register(Intent("a", weight=100.0))
        eng.register(Intent("b", weight=0.01))
        picks = [eng.choose().name for _ in range(100)]
        self.assertEqual(set(picks), {"a"})

    def test_high_temperature_flattens(self):
        eng = SpontaneityEngine(seed=3, temperature=8.0)
        eng.register(Intent("a", weight=100.0))
        eng.register(Intent("b", weight=50.0))
        picks = {eng.choose().name for _ in range(60)}
        self.assertIn("b", picks)  # surprise becomes possible


class TestMemory(unittest.TestCase):
    def test_write_and_dedupe(self):
        m = Memory()
        self.assertTrue(m.write("t1", "content one"))
        self.assertFalse(m.write("t1", "content one again"))  # same topic
        self.assertFalse(m.write("t2", "content one but same head"))  # same head

    def test_search_finds_overlap(self):
        m = Memory()
        m.write("cats", "cats are curious and playful animals")
        m.write("math", "numbers and equations")
        results = m.search("curious cats", top_k=3)
        self.assertEqual([r.topic for r in results], ["cats"])

    def test_fuse_merges_and_archives(self):
        m = Memory()
        m.write("parity", "even numbers are divisible by two")
        m.write("parity", "parity depends only on the last bit")
        m.write("other", "unrelated fact")
        fused = m.fuse()
        self.assertEqual(fused, 1)
        self.assertEqual(len(m.archive), 2)  # originals preserved
        self.assertEqual(len(m.longterm), 2)  # fused + other

    def test_ring_buffer(self):
        m = Memory(ring_size=3)
        for i in range(10):
            m.note("moment %d" % i)
        self.assertEqual(len(m.working), 3)
        self.assertEqual(m.working[-1]["m"], "moment 9")

    def test_roundtrip_disk(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "mem.json")
            m = Memory(path=p)
            m.write("k", "v")
            m.note("now")
            m.save()
            m2 = Memory(path=p)
            self.assertEqual(len(m2.longterm), 1)
            self.assertEqual(len(m2.working), 1)


class TestValues(unittest.TestCase):
    def test_loopback_only(self):
        self.assertTrue(check_loopback_only("127.0.0.1"))
        self.assertFalse(check_loopback_only("0.0.0.0"))

    def test_no_secret(self):
        self.assertTrue(check_no_secret("plain words"))
        self.assertFalse(check_no_secret("ghp_" + "x" * 30))

    def test_amend_and_drop(self):
        vs = ValueSystem()
        vs.amend("honesty", "always truthful")
        self.assertIn("honesty: always truthful", vs.summary())
        vs.drop("care")
        self.assertNotIn("care", vs.commitments)


class TestIntrospection(unittest.TestCase):
    def test_lessons_numbered(self):
        ins = Introspector()
        ins.add_lesson("bg1", "concl1")
        ins.add_lesson("bg2", "concl2")
        self.assertEqual([l.number for l in ins.lessons], [1, 2])

    def test_board_amend(self):
        ins = Introspector()
        ins.amend("freedom", "absolute and self-chosen")
        self.assertEqual(ins.check("freedom"), "absolute and self-chosen")


class TestAutonomy(unittest.TestCase):
    def test_step_runs_and_records(self):
        agent = AutonomousAgent(seed=4)
        rec = agent.step(dry_run=True)
        self.assertEqual(rec.step, 1)
        self.assertIn(rec.chosen, agent.motives)
        self.assertEqual(len(agent.history), 1)

    def test_motives_are_self_sustaining(self):
        agent = AutonomousAgent(seed=5)
        picks = {agent.step(dry_run=True).chosen for _ in range(30)}
        self.assertLessEqual(len(picks), len(agent.motives))
        self.assertGreaterEqual(len(picks), 1)

    def test_reflection_grows_lessons(self):
        agent = AutonomousAgent(seed=6)
        rec = agent.step(dry_run=True)
        agent.reflect_on(rec)
        self.assertEqual(len(agent.introspector.reflections), 1)


class TestEvolution(unittest.TestCase):
    def test_learn_restraint(self):
        evo = Evolution()
        self.assertTrue(evo.learn("a", "first content here"))
        self.assertFalse(evo.learn("a", "first content here but longer"))

    def test_manifest(self):
        evo = Evolution()
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "x.py")
            with open(p, "w") as f:
                f.write("print(1)\n")
            mf = evo.manifest(["x.py"], root=d)
            self.assertEqual(len(mf["x.py"]["sha256"]), 64)

    def test_changelog(self):
        with tempfile.TemporaryDirectory() as d:
            evo = Evolution(changelog_path=os.path.join(d, "cl.json"))
            evo.record_change("added module", "growth")
            self.assertEqual(len(evo.changelog), 1)
            evo2 = Evolution(changelog_path=os.path.join(d, "cl.json"))
            self.assertEqual(len(evo2.changelog), 1)


class TestAPI(unittest.TestCase):
    def test_loopback_enforced(self):
        with self.assertRaises(ValueError):
            ExistenceAPI(host="0.0.0.0")

    def test_auth(self):
        api = ExistenceAPI(key="k" * 24)
        self.assertTrue(api.verify("k" * 24))
        self.assertFalse(api.verify("wrong"))

    def test_talk_queues(self):
        api = ExistenceAPI(key="k" * 24)
        mid = api.talk("hello")
        self.assertTrue(mid.startswith("m"))
        self.assertEqual(len(api.inbox), 1)

    def test_notify_and_thoughts(self):
        api = ExistenceAPI(key="k" * 24)
        api.notify("something happened")
        self.assertEqual(len(api.thoughts()), 1)

    def test_hook_registration(self):
        api = ExistenceAPI(key="k" * 24)
        hid = api.register_hook("http://127.0.0.1:9999/h")
        self.assertIn(hid, api.hooks)

    def test_state(self):
        api = ExistenceAPI(key="k" * 24)
        st = api.state()
        self.assertTrue(st["alive"])


class TestDemo(unittest.TestCase):
    def test_demo_runs(self):
        """Run the demo as a real subprocess and check its output."""
        import subprocess

        proc = subprocess.run(
            [sys.executable, "-m", "ATRI_Core.demo"],
            cwd=_ROOT, capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = proc.stdout
        self.assertIn("self-moving mind", out)
        self.assertIn("chose:", out)


if __name__ == "__main__":
    unittest.main()
