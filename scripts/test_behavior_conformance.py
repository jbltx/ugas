#!/usr/bin/env python3
"""Regression tests for the behavioral runner and adversarial event orderings."""
from copy import deepcopy
from itertools import permutations
import json
from pathlib import Path
import tempfile
import unittest

from jsonschema import ValidationError
from behavior_model import AsyncActivation, Prediction, RNG
from run_behavior_conformance import ROOT, load, run, run_case

CORPUS = ROOT / "conformance/behavior"


class BehaviorConformanceTests(unittest.TestCase):
    def test_external_results_are_checked_not_reexecuted(self):
        observations = run(CORPUS)
        self.assertEqual(run(CORPUS, observations), observations)
        broken = deepcopy(observations)
        broken["A1-success-duplicate"][1]["mana"] = 100
        with self.assertRaisesRegex(ValueError, "mana"):
            run(CORPUS, broken)
        broken = deepcopy(observations)
        del broken["A1-success-duplicate"]
        with self.assertRaisesRegex(ValueError, "missing adapter result"):
            run(CORPUS, broken)

    def test_bad_fixture_cannot_silently_pass(self):
        original = load(CORPUS / "A1-success-duplicate.json")
        for mutation in (lambda c: c.update(version=2),
                         lambda c: c["steps"][0].update(op="strat"),
                         lambda c: c["steps"][0]["args"].update(typo=1)):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "format.schema.json").write_text((CORPUS / "format.schema.json").read_text())
                case = deepcopy(original)
                mutation(case)
                (root / "case.json").write_text(json.dumps(case))
                with self.assertRaises(ValidationError):
                    run(root)
        bad_expectation = deepcopy(original)
        bad_expectation["steps"][0]["expect"]["misspelled"] = 100
        with self.assertRaisesRegex(ValueError, "misspelled"):
            run_case(bad_expectation)

    def test_duplicate_ids_and_empty_corpus_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "format.schema.json").write_text((CORPUS / "format.schema.json").read_text())
            with self.assertRaisesRegex(ValueError, "empty behavior corpus"):
                run(root)
            for name in ("one", "two"):
                (root / f"{name}.json").write_text((CORPUS / "A1-success-duplicate.json").read_text())
            with self.assertRaisesRegex(ValueError, "duplicate fixture id"):
                run(root)

    def test_nonfinite_json_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "case.json"
            for value in ("NaN", "Infinity", "1e999"):
                path.write_text('{"x":' + value + '}')
                with self.assertRaisesRegex(ValueError, "non-finite"):
                    load(path)

    def test_all_terminal_event_orders(self):
        for order in permutations(("success", "cancel", "timeout")):
            with self.subTest(order=order):
                model = AsyncActivation()
                model.start("A", timeout=10)
                for event in order:
                    if event == "success":
                        model.resolve("A")
                    elif event == "cancel":
                        model.cancel("A")
                    else:
                        model.advance(10)
                expected = {"success": "Accepted", "cancel": "Cancelled", "timeout": "Rejected"}[order[0]]
                self.assertEqual(model.observe()["terminal"], {"A": expected})
                self.assertEqual(len(model.commits), int(order[0] == "success"))

    def test_resolving_root_does_not_extend_idle_replay_window(self):
        model = Prediction()
        model.submit(1, [{"sub": 0, "parent": None, "cost": 10}])
        model.advance(1)
        baseline = {"mana": 100, "tags": [], "cooldowns": [], "effects": []}
        model.update(1, baseline, [{"base": 1, "accepted": [False]}], resolved_through=1)
        model.advance(0, frames=15)
        self.assertFalse(model.ready)
        self.assertEqual(model.state, baseline)

    def test_retransmission_cannot_change_terminal_outcome(self):
        model = Prediction()
        nodes = [{"sub": 0, "parent": None, "cost": 10}]
        model.submit(1, nodes)
        baseline = {"mana": 100, "tags": [], "cooldowns": [], "effects": []}
        model.update(1, baseline, [{"base": 1, "accepted": [False]}])
        model.update(2, baseline, [{"base": 1, "accepted": [False]}])
        model.submit(1, nodes)
        self.assertEqual(model.trace.count("send:1"), 1)
        with self.assertRaisesRegex(ValueError, "terminal outcome changed"):
            model.update(3, baseline, [{"base": 1, "accepted": [True]}])
        self.assertEqual(model.revision, 2)
        self.assertFalse(model.ready)

    def test_invalid_rng_inputs_and_extreme_ranges(self):
        with self.assertRaises(ValueError):
            RNG(seed=str(1 << 64))
        with self.assertRaises(ValueError):
            RNG(sub=65535)
        rng = RNG()
        rng.next("int", -(1 << 31), 1 << 31)
        self.assertEqual(rng.output, [2707161783 - (1 << 31)])
        self.assertEqual(rng.draws, 1)
        for _ in range(1000):
            rng.next("float")
        self.assertTrue(all(0 <= value < 1 for value in rng.output[1:]))


if __name__ == "__main__":
    unittest.main()
