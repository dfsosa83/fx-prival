"""Synthetic offline tests for safe_h1_csv_rebuild (no MT5, no network, no production data).

All fixtures are tiny synthetic CSVs written under a TemporaryDirectory that is
removed at teardown. No production raw path is read or written, even read-only.
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import safe_h1_csv_rebuild as rebuild  # noqa: E402

CANON_HEADER = "datetime,open,high,low,close,volume"
LEGACY_HEADER = "open,high,low,close,volume,datetime"
FORBIDDEN_SUBSTRINGS = ("ml-signal-service/data/raw", "ml-signal-service\\data\\raw",
                        "quant-personal-fund/experiments", "quant-personal-fund\\experiments")


def canon_csv(*rows: str) -> str:
    return CANON_HEADER + "\n" + "".join(r + "\n" for r in rows)


def legacy_csv(*rows: str) -> str:
    return LEGACY_HEADER + "\n" + "".join(r + "\n" for r in rows)


class Base(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory(prefix="raw_schema_test_")
        self.tmp = Path(self._td.name)

    def tearDown(self):
        self._td.cleanup()

    def write(self, name: str, text: str) -> Path:
        p = self.tmp / name
        p.write_text(text, encoding="utf-8")
        return p

    def guard(self, *paths):
        for p in paths:
            sp = str(Path(p))
            self.assertTrue(sp.startswith(str(self.tmp)),
                            f"test path escaped temp dir: {sp}")
            for bad in FORBIDDEN_SUBSTRINGS:
                self.assertNotIn(bad, sp)


class TestDetectionAndNormalization(Base):
    def test_01_canonical_detect_and_rebuild(self):
        p = self.write("c.csv", canon_csv(
            "2020-01-01 00:00:00,1.0,1.1,0.9,1.05,100",
            "2020-01-01 01:00:00,1.05,1.15,1.0,1.10,110"))
        self.assertEqual(rebuild.detect_schema(p), "canonical")
        df = rebuild.read_and_normalize(p)
        self.assertEqual(list(df.columns), rebuild.CANONICAL_COLUMNS)
        self.assertEqual(len(df), 2)
        self.guard(p)

    def test_02_legacy_detect_and_normalize(self):
        p = self.write("l.csv", legacy_csv(
            "1.0,1.1,0.9,1.05,100,2020-01-01 00:00:00",
            "1.05,1.15,1.0,1.10,110,2020-01-01 01:00:00"))
        self.assertEqual(rebuild.detect_schema(p), "legacy")
        df = rebuild.read_and_normalize(p)
        self.assertEqual(list(df.columns), rebuild.CANONICAL_COLUMNS)
        # values mapped BY NAME, not position
        self.assertEqual(float(df["open"].iloc[0]), 1.0)
        self.assertEqual(float(df["close"].iloc[0]), 1.05)
        self.assertEqual(float(df["volume"].iloc[0]), 100.0)

    def test_03_output_schema_and_opaque_labels(self):
        p = self.write("c.csv", canon_csv(
            "2020-01-01 00:00:00,1.0,1.1,0.9,1.05,100"))
        df = rebuild.read_and_normalize(p)
        self.assertEqual(df["datetime"].iloc[0], "2020-01-01 00:00:00")  # unchanged string
        out = self.tmp / "out.csv"
        rebuild.write_candidate_atomic(df, out)
        header = out.read_text(encoding="utf-8").splitlines()[0]
        self.assertEqual(header, CANON_HEADER)
        self.guard(out)


class TestMerge(Base):
    def _canon(self, *rows):
        return rebuild.read_and_normalize(self.write("m_%d.csv" % len(rows), canon_csv(*rows)))

    def test_04_merge_non_overlapping_canonical(self):
        a = self._canon("2020-01-01 00:00:00,1,1.1,0.9,1.0,10")
        b = rebuild.read_and_normalize(self.write("b.csv", canon_csv(
            "2020-01-01 02:00:00,1,1.1,0.9,1.1,11")))
        merged = rebuild.merge_existing_and_new(a, b)
        self.assertEqual(len(merged), 2)
        self.assertTrue(merged["datetime"].is_monotonic_increasing)

    def test_05_merge_legacy_new_rows_normalized(self):
        a = self._canon("2020-01-01 00:00:00,1,1.1,0.9,1.0,10")
        legacy_new = rebuild.read_and_normalize(self.write("ln.csv", legacy_csv(
            "1,1.2,0.8,1.1,12,2020-01-01 01:00:00")))
        merged = rebuild.merge_existing_and_new(a, legacy_new)
        self.assertEqual(len(merged), 2)
        self.assertEqual(float(merged["close"].iloc[1]), 1.1)

    def test_06_identical_overlap_dedup(self):
        a = self._canon("2020-01-01 00:00:00,1,1.1,0.9,1.0,10")
        b = rebuild.read_and_normalize(self.write("b6.csv", canon_csv(
            "2020-01-01 00:00:00,1,1.1,0.9,1.0,10")))
        merged = rebuild.merge_existing_and_new(a, b)
        self.assertEqual(len(merged), 1)

    def test_07_conflicting_overlap_fails(self):
        a = self._canon("2020-01-01 00:00:00,1,1.1,0.9,1.0,10")
        b = rebuild.read_and_normalize(self.write("b7.csv", canon_csv(
            "2020-01-01 00:00:00,1,1.1,0.9,1.0,99")))   # differs in volume
        with self.assertRaises(rebuild.MergeConflictError):
            rebuild.merge_existing_and_new(a, b)


class TestValidation(Base):
    def test_08_duplicate_datetime_fails(self):
        p = self.write("d.csv", canon_csv(
            "2020-01-01 00:00:00,1,1.1,0.9,1.0,10",
            "2020-01-01 00:00:00,1,1.1,0.9,1.0,10"))
        with self.assertRaises(rebuild.ValidationError):
            rebuild.read_and_normalize(p)

    def test_09_out_of_order_fails(self):
        p = self.write("o.csv", canon_csv(
            "2020-01-01 02:00:00,1,1.1,0.9,1.0,10",
            "2020-01-01 01:00:00,1,1.1,0.9,1.0,10"))
        with self.assertRaises(rebuild.ValidationError):
            rebuild.read_and_normalize(p)

    def test_10_null_datetime_fails(self):
        p = self.write("n.csv", canon_csv(
            ",1,1.1,0.9,1.0,10"))
        with self.assertRaises(rebuild.ValidationError):
            rebuild.read_and_normalize(p)

    def test_11_non_numeric_or_nonfinite_fails(self):
        p1 = self.write("nn.csv", canon_csv("2020-01-01 00:00:00,abc,1.1,0.9,1.0,10"))
        with self.assertRaises(rebuild.ValidationError):
            rebuild.read_and_normalize(p1)
        p2 = self.write("inf.csv", canon_csv("2020-01-01 00:00:00,1,inf,0.9,1.0,10"))
        with self.assertRaises(rebuild.ValidationError):
            rebuild.read_and_normalize(p2)

    def test_12_non_positive_close_fails(self):
        p = self.write("neg.csv", canon_csv("2020-01-01 00:00:00,1,1.1,0.9,-1.0,10"))
        with self.assertRaises(rebuild.ValidationError):
            rebuild.read_and_normalize(p)

    def test_13_unsupported_schema_fails(self):
        p = self.write("u.csv", "foo,bar,baz\n1,2,3\n")
        with self.assertRaises(rebuild.SchemaError):
            rebuild.detect_schema(p)


class TestWriteSafety(Base):
    def _frame(self):
        return rebuild.read_and_normalize(self.write("w.csv", canon_csv(
            "2020-01-01 00:00:00,1,1.1,0.9,1.0,10",
            "2020-01-01 01:00:00,1,1.1,0.9,1.1,11")))

    def test_14_existing_backup_fails_closed(self):
        out = self.write("out.csv", canon_csv("2020-01-01 00:00:00,1,1.1,0.9,1.0,10"))
        before = rebuild.sha256_file(out)
        backup = self.write("out.bak", "preexisting")
        with self.assertRaises(rebuild.BackupError):
            rebuild.write_candidate_atomic(self._frame(), out, backup_path=backup)
        self.assertEqual(rebuild.sha256_file(out), before)   # original unchanged
        self.guard(out, backup)

    def test_15_write_validation_failure_leaves_original(self):
        out = self.write("out.csv", canon_csv("2020-01-01 00:00:00,1,1.1,0.9,1.0,10"))
        before_content = out.read_text(encoding="utf-8")
        before = rebuild.sha256_file(out)
        frame = self._frame()          # build fixture BEFORE applying the mock
        with mock.patch.object(rebuild, "read_and_normalize",
                               side_effect=rebuild.ValidationError("simulated")):
            with self.assertRaises(rebuild.WriteValidationError):
                rebuild.write_candidate_atomic(frame, out,
                                               backup_path=self.tmp / "out.bak")
        # original content + hash unchanged; no replacement; no leftover temp/backup
        self.assertEqual(rebuild.sha256_file(out), before)
        self.assertEqual(out.read_text(encoding="utf-8"), before_content)
        self.assertFalse((self.tmp / "out.bak").exists())
        leftovers = [p.name for p in self.tmp.iterdir() if p.suffix == ".tmp"]
        self.assertEqual(leftovers, [])
        self.guard(out)

    def test_16_and_17_paths_isolated_and_no_forbidden_paths(self):
        out = self.write("out.csv", canon_csv("2020-01-01 00:00:00,1,1.1,0.9,1.0,10"))
        res = rebuild.write_candidate_atomic(self._frame(), out,
                                             backup_path=self.tmp / "out.bak")
        self.assertIsNotNone(res["candidate_sha256"])
        self.assertIsNotNone(res["backup_sha256"])
        for name in ("out.csv", "out.bak"):
            self.guard(self.tmp / name)
        # every created test path lives inside the temp dir
        for p in self.tmp.iterdir():
            self.guard(p)


if __name__ == "__main__":
    unittest.main(verbosity=2)
