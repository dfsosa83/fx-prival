"""Tests for the A1 orders-disabled observation-only runtime.

Synthetic event dictionaries and system temporary directories ONLY.
No market prices, fixtures, broker, MT5, network or repository runtime files.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import A1_OBSERVATION_ONLY_RUNTIME as rt  # noqa: E402


def valid_event(**overrides):
    ev = {f: None for f in rt.REQUIRED_EVENT_FIELDS}
    ev["event_id"] = "e1"
    ev["mode"] = "OBSERVATION_ONLY"
    ev.update(overrides)
    return ev


class TestObservationOnlyRuntime(unittest.TestCase):
    def test_01_static_safety_guard_passes_for_runtime(self):
        hits = rt.static_safety_check([Path(rt.__file__)])
        self.assertEqual(hits, [], f"guard hits: {hits}")

    def test_02_invalid_mode_rejected(self):
        with self.assertRaises(ValueError):
            rt.validate_configuration({"mode": "DEMO_ORDER"})
        rt.validate_configuration({"mode": "OBSERVATION_ONLY"})  # must not raise

    def test_03_prohibited_config_token_rejected(self):
        with self.assertRaises(ValueError):
            rt.validate_configuration({"mode": "OBSERVATION_ONLY", "note": "BROKER"})

    def test_04_reserved_execution_states_rejected(self):
        for s in rt.FUTURE_STATES:
            self.assertFalse(rt.validate_lifecycle_transition("ENTRY_PENDING", s))
            self.assertFalse(rt.validate_lifecycle_transition(s, "NO_SETUP"))

    def test_05_legal_observation_transitions_pass(self):
        self.assertTrue(rt.validate_lifecycle_transition("NO_SETUP", "SETUP_DETECTED"))
        self.assertTrue(rt.validate_lifecycle_transition("SETUP_DETECTED", "SIGNAL_ACCEPTED"))
        self.assertTrue(rt.validate_lifecycle_transition("SIGNAL_ACCEPTED", "ENTRY_PENDING"))
        self.assertTrue(rt.validate_lifecycle_transition("ENTRY_PENDING", "EXPIRED_UNFILLED"))

    def test_06_illegal_transition_fails(self):
        self.assertFalse(rt.validate_lifecycle_transition("NO_SETUP", "ENTRY_PENDING"))
        self.assertFalse(rt.validate_lifecycle_transition("EXPIRED_UNFILLED", "SIGNAL_ACCEPTED"))

    def test_07_required_event_fields_enforced(self):
        ev = valid_event()
        rt.validate_event_schema(ev)  # must not raise
        incomplete = dict(ev)
        del incomplete["error_status"]
        with self.assertRaises(ValueError):
            rt.validate_event_schema(incomplete)

    def test_08_prohibited_event_fields_rejected(self):
        for f in rt.PROHIBITED_EVENT_FIELDS:
            ev = valid_event()
            ev[f] = 1
            with self.assertRaises(ValueError):
                rt.validate_event_schema(ev)

    def test_09_append_only_sequence_monotonic(self):
        with tempfile.TemporaryDirectory() as td:
            p1 = rt.append_event_record(td, "sess1", valid_event(event_id="a"))
            rt.append_event_record(td, "sess1", valid_event(event_id="b"))
            lines = Path(p1).read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 2)
            import json
            self.assertEqual(json.loads(lines[0])["sequence_id"], 1)
            self.assertEqual(json.loads(lines[1])["sequence_id"], 2)
            with self.assertRaises(ValueError):
                rt.append_event_record(td, "sess1", valid_event(event_id="c"), sequence_id=1)

    def test_10_write_outside_root_refused(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):
                rt.append_event_record(td, "../escape", valid_event(event_id="x"))

    def test_11_existing_record_never_overwritten(self):
        with tempfile.TemporaryDirectory() as td:
            p1 = rt.append_event_record(td, "sess2", valid_event(event_id="first"))
            first_line = Path(p1).read_text(encoding="utf-8").splitlines()[0]
            rt.append_event_record(td, "sess2", valid_event(event_id="second"))
            after = Path(p1).read_text(encoding="utf-8").splitlines()
            self.assertEqual(after[0], first_line)
            self.assertEqual(len(after), 2)

    def test_12_session_metadata_attests_orders_disabled(self):
        meta = rt.make_session_metadata("sess3", "enginehash")
        self.assertEqual(meta["mode"], "OBSERVATION_ONLY")
        self.assertTrue(meta["orders_disabled"])
        self.assertFalse(meta["contains_broker_or_source_price_data"])
        self.assertEqual(meta["observation_window_target"]["min_calendar_days"], 30)
        self.assertEqual(meta["observation_window_target"]["min_completed_cycles"], 50)

    def test_13_observation_window_requires_both_conditions(self):
        base = rt.make_session_metadata("sess4", "h")
        m = dict(base); m["calendar_days_elapsed"] = 29; m["completed_cycles"] = 50
        self.assertEqual(rt.track_observation_window(m), rt.WINDOW_INCOMPLETE)
        m2 = dict(base); m2["calendar_days_elapsed"] = 30; m2["completed_cycles"] = 49
        self.assertEqual(rt.track_observation_window(m2), rt.WINDOW_INCOMPLETE)
        m3 = dict(base); m3["calendar_days_elapsed"] = 30; m3["completed_cycles"] = 50
        self.assertEqual(rt.track_observation_window(m3), rt.WINDOW_COMPLETE)

    def test_14_all_test_paths_temporary_and_cleaned(self):
        with tempfile.TemporaryDirectory() as td:
            p = rt.append_event_record(td, "sess5", valid_event(event_id="t14"))
            self.assertTrue(str(p).startswith(str(Path(td))))
        self.assertFalse(Path(td).exists())

    def test_15_no_fixture_price_or_repo_runtime_file_used(self):
        # only the runtime module and synthetic dicts are used in these tests
        self.assertTrue(str(Path(rt.__file__)).endswith("A1_OBSERVATION_ONLY_RUNTIME.py"))
        self.assertTrue(hasattr(rt, "REQUIRED_EVENT_FIELDS"))
        # no market/fixture module imported by the runtime
        hits = rt.static_safety_check([Path(rt.__file__)])
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
