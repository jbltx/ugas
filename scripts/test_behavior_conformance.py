#!/usr/bin/env python3
"""Regression tests for the behavioral runner and adversarial event orderings."""
from copy import deepcopy
from itertools import permutations
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from jsonschema import ValidationError
from behavior_model import AsyncActivation, Prediction, RNG
from run_behavior_conformance import ROOT, json_equal, load, run, run_case

CORPUS = ROOT / "conformance/behavior"


class BehaviorConformanceTests(unittest.TestCase):
    def test_fixture_integer_inputs_accept_equivalent_numeric_forms(self):
        observations = run(CORPUS)
        with tempfile.TemporaryDirectory() as directory:
            corpus = Path(directory)
            (corpus / "format.schema.json").write_text((CORPUS / "format.schema.json").read_text())
            for path in sorted(CORPUS.glob("*.json")):
                if path.name == "format.schema.json":
                    continue
                case = load(path)
                # Change input representation only; keep golden observations fixed.
                if "initial" in case:
                    case["initial"] = json.loads(json.dumps(case["initial"]), parse_int=float)
                for step in case["steps"]:
                    if "args" in step:
                        step["args"] = json.loads(json.dumps(step["args"]), parse_int=float)
                encoded = json.dumps(case)
                with self.subTest(id=case["id"]):
                    self.assertTrue(json_equal(run_case(case), observations[case["id"]]))
                    self.assertEqual(json.dumps(case), encoded)
                (corpus / path.name).write_text(encoded)
            self.assertTrue(json_equal(run(corpus), observations))
            self.assertEqual(run(corpus, observations), observations)

    def test_integer_input_normalization_does_not_admit_invalid_types(self):
        with tempfile.TemporaryDirectory() as directory:
            corpus = Path(directory)
            (corpus / "format.schema.json").write_text((CORPUS / "format.schema.json").read_text())
            for value in (True, 55.5, "55"):
                case = load(CORPUS / "R3-child-stream.json")
                case["initial"]["sub"] = value
                (corpus / "case.json").write_text(json.dumps(case))
                with self.subTest(value=value), self.assertRaises(ValidationError):
                    run(corpus)

    def test_corpus_rejects_ignoring_included_attempts(self):
        case = load(CORPUS / "N2-included-before-outcome.json")
        run_case(case)
        update = Prediction.update

        def ignore_included(model, **args):
            return update(model, **{**args, "included": []})

        with patch.object(Prediction, "update", ignore_included):
            with self.assertRaisesRegex(ValueError, r"step 3 \(update\), state"):
                run_case(case)

    def test_corpus_rejects_replaying_the_wrong_timer_suffix(self):
        case = load(CORPUS / "N7-checkpoint-timer-suffix.json")
        run_case(case)
        update = Prediction.update
        # Both replaying every tick and suppressing every tick must fail.
        for checkpoint_frame in (0, 2):
            def wrong_boundary(model, **args):
                return update(model, **{**args, "checkpoint_frame": checkpoint_frame})

            with self.subTest(checkpoint_frame=checkpoint_frame):
                with patch.object(Prediction, "update", wrong_boundary):
                    with self.assertRaisesRegex(ValueError, r"step 4 \(update\), state"):
                        run_case(case)

    def test_clock_only_checks_cannot_grow_replay_work(self):
        model = Prediction(max_actions=1, max_frames=2)
        model.submit(1, [{"sub": 0, "parent": None, "cost": 10}])
        model.advance(0, frames=1, simulation_ms=0)
        journal = deepcopy(model.journal)
        for _ in range(10000):
            model.advance(0, frames=0, simulation_ms=0)
        self.assertEqual(model.journal, journal)
        self.assertEqual(sum(len(record["actions"]) for record in model.journal), 2)
        model.update(1, deepcopy(model.baseline), [], checkpoint_frame=0)
        self.assertEqual(model.trace.count("replay-step:1"), 1)
        self.assertTrue(model.ready)

    def test_clock_only_checks_expire_without_ticking_gameplay(self):
        model = Prediction(period_ms=10, tick_mana=5)
        model.submit(1, [{"sub": 0, "parent": None, "cost": 10}])
        state = deepcopy(model.state)
        journal = deepcopy(model.journal)
        model.advance(249, frames=0)
        self.assertEqual(model.state, state)
        self.assertEqual(model.journal, journal)
        self.assertEqual(model.frame, 0)
        self.assertEqual(model.now, 249)
        model.advance(1, frames=0)
        self.assertFalse(model.ready)
        self.assertEqual(model.state, model.baseline)
        self.assertEqual(model.journal, [])

    def test_clock_only_checks_do_not_reset_action_capacity(self):
        model = Prediction(max_actions=1)
        nodes = [{"sub": 0, "parent": None, "cost": 10}]
        model.submit(1, nodes)
        model.advance(1, frames=0)
        model.submit(2, nodes)
        self.assertEqual(model.state["mana"], 90)
        self.assertEqual(model.observe()["journal"], [1])
        self.assertIn("authority:2", model.trace)

    def test_simulation_delta_requires_frame_progress_before_mutation(self):
        model = Prediction(period_ms=10, tick_mana=5)
        model.submit(1, [{"sub": 0, "parent": None, "cost": 10}])
        before = deepcopy(vars(model))
        with self.assertRaisesRegex(ValueError, "simulation time requires frame progress"):
            model.advance(1, frames=0, simulation_ms=10)
        self.assertEqual(vars(model), before)

    def test_adapter_comparison_distinguishes_booleans_recursively(self):
        observations = run(CORPUS)
        cases = [
            ("R1-float-and-integer", 0, "draws", True),
            ("N2-replay-unaffordable-root", 1, "pending", [True]),
            ("N9-future-watermark", 1, "ready", 0),
            ("N9-future-watermark", 3, "ready", 1),
            ("N9-future-watermark", 1, "watermark", False),
            ("N7-idle-periodic-replay", 1, "state", {
                **observations["N7-idle-periodic-replay"][1]["state"],
                "period": {"elapsed": False, "count": True},
            }),
        ]
        for id, index, field, value in cases:
            with self.subTest(id=id, field=field):
                broken = deepcopy(observations)
                broken[id][index][field] = value
                with self.assertRaisesRegex(ValueError, field):
                    run(CORPUS, broken)

    def test_adapter_number_representation_and_object_order_are_equivalent(self):
        def numeric_json(value):
            if type(value) is int:
                return float(value)
            if isinstance(value, list):
                return [numeric_json(item) for item in value]
            if isinstance(value, dict):
                return {key: numeric_json(item) for key, item in reversed(list(value.items()))}
            return value
        converted = numeric_json(run(CORPUS))
        self.assertEqual(run(CORPUS, converted), converted)

    def test_null_adapter_observations_never_run_reference_models(self):
        observations = run(CORPUS)
        one_null = deepcopy(observations)
        one_null["A1-success-duplicate"] = None
        all_null = dict.fromkeys(observations)
        case = load(CORPUS / "A1-success-duplicate.json")
        # Removing the models makes an accidental reference execution fail this test.
        with patch("run_behavior_conformance.MODELS", {}):
            for name, results in (("one null", one_null), ("all null", all_null)):
                with self.subTest(name=name), self.assertRaisesRegex(ValueError, "observations must be a list"):
                    run(CORPUS, results)
            with self.assertRaisesRegex(ValueError, "observations must be a list"):
                run_case(case, None)
            with self.assertRaisesRegex(ValueError, "results must be an object"):
                run(CORPUS, None)

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

    def test_replay_drops_unaffordable_root_without_losing_request(self):
        model = Prediction()
        nodes = [{"sub": 0, "parent": None, "cost": 10, "target": "enemy"}]
        model.submit(1, nodes)
        baseline = {"mana": 5, "tags": [], "cooldowns": [], "effects": []}
        model.update(1, baseline, [])
        self.assertEqual(model.state, baseline)
        self.assertEqual(model.overlays, set())
        self.assertEqual(model.observe()["journal"], [])
        self.assertEqual(model.observe()["pending"], [1])
        model.submit(1, nodes)
        self.assertEqual(model.trace.count("send:1"), 1)
        model.update(2, {**baseline, "mana": 100}, [])
        self.assertEqual(model.state["mana"], 100)

    def test_replay_drops_ineligible_descendants_but_keeps_siblings(self):
        model = Prediction()
        nodes = [
            {"sub": 0, "parent": None, "cost": 10},
            {"sub": 1, "parent": 0, "cost": 20, "target": "enemy"},
            {"sub": 2, "parent": 1, "cost": 0, "target": "enemy"},
            {"sub": 3, "parent": 0, "cost": 5},
        ]
        model.submit(1, nodes)
        baseline = {"mana": 20, "tags": [], "cooldowns": [], "effects": []}
        model.update(1, baseline, [])
        self.assertEqual(model.state, {**baseline, "mana": 5, "tags": ["1:0", "1:3"], "cooldowns": ["1:0", "1:3"]})
        self.assertEqual(model.overlays, set())
        self.assertEqual(model.requests[1]["nodes"], nodes)
        model.update(2, {**baseline, "mana": 100}, [])
        self.assertEqual(model.state["mana"], 85)
        self.assertEqual(model.state["tags"], ["1:0", "1:3"])

    def test_initial_prediction_also_checks_affordability(self):
        model = Prediction(mana=5)
        model.submit(1, [{"sub": 0, "parent": None, "cost": 10}])
        self.assertEqual(model.state["mana"], 5)
        self.assertEqual(model.state["tags"], [])
        self.assertEqual(model.observe()["journal"], [])
        self.assertEqual(model.observe()["pending"], [1])

    def test_presentation_retirement_is_bounded_across_resolved_cycles(self):
        model = Prediction(max_requests=1)
        baseline = deepcopy(model.baseline)
        for base in range(1, 101):
            model.submit(base, [{"sub": 0, "parent": None, "cost": 10, "target": "enemy"}])
            model.cancel(base)
            self.assertEqual(model.presentation_retired, {f"{base}:0"})
            # A terminal outcome alone is not yet a safe retirement watermark.
            model.update(2 * base - 1, baseline, [{"base": base, "accepted": [False]}],
                         resolved_through=base - 1)
            self.assertEqual(model.presentation_retired, {f"{base}:0"})
            model.update(2 * base, baseline, [], resolved_through=base)
            self.assertEqual(model.presentation_retired, set())
            self.assertEqual(model.requests, {})
            self.assertEqual(model.journal, [])
            # A retransmission below the watermark must not revive presentation.
            model.submit(base, [{"sub": 0, "parent": None, "cost": 10, "target": "enemy"}])
            self.assertEqual(model.overlays, set())
        self.assertEqual(sum(item.startswith("send:") for item in model.trace), 100)

    def test_future_watermark_resyncs_without_losing_next_input(self):
        model = Prediction()
        nodes = [{"sub": 0, "parent": None, "cost": 10}]
        model.submit(1, nodes)
        with self.assertRaisesRegex(ValueError, "watermark exceeds allocated inputs"):
            model.update(1, deepcopy(model.baseline), [{"base": 1, "accepted": [False]}],
                         resolved_through=99)
        self.assertEqual((model.revision, model.watermark, model.next_base), (0, 0, 2))
        self.assertFalse(model.ready)
        model.submit(2, nodes)
        self.assertEqual(model.observe()["pending"], [1, 2])
        self.assertIn("send:2", model.trace)
        self.assertIn("authority:2", model.trace)
        model.update(1, deepcopy(model.baseline), [
            {"base": 1, "accepted": [False]}, {"base": 2, "accepted": [False]},
        ], resolved_through=2)
        self.assertEqual(model.watermark, 2)
        with self.assertRaisesRegex(ValueError, "watermark exceeds allocated inputs"):
            model.update(2, deepcopy(model.baseline), [], resolved_through=3)

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
