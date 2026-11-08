"""Synthetic-data checks for the new November 2026 workbook audit helper."""

from datetime import date, datetime
from contextlib import redirect_stderr
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

from openpyxl import Workbook


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_workbooks.py"
SPEC = importlib.util.spec_from_file_location("validate_workbooks", SCRIPT)
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


HEADERS = ("Date", "PTS", "Result", "TRB", "AST")


class RowEligibilityTests(unittest.TestCase):
    def test_excludes_totals_and_nonappearances_but_keeps_zero(self):
        summary = audit.summarize_rows(HEADERS, [
            (date(2024, 1, 1), 0, "W, 90-80", 0, 2),
            (datetime(2024, 1, 2), 20, "L, 95-100", 6, 4),
            (date(2024, 1, 3), None, "W, 91-80", None, None),
            (None, 2000, "60-22", 100, 200),
            ("Totals", 2000, None, 100, 200),
        ]).as_dict()
        self.assertEqual(summary["eligible_games"], 2)
        self.assertEqual(summary["excluded_without_valid_date"], 2)
        self.assertEqual(summary["excluded_without_numeric_pts"], 1)
        self.assertEqual(summary["metrics"]["PTS"], {"count": 2, "mean": 10.0})
        self.assertEqual(summary["win_loss_pts"]["W"], {"count": 1, "mean": 0.0})
        self.assertEqual(summary["win_loss_pts"]["L"], {"count": 1, "mean": 20.0})

    def test_numeric_strings_booleans_and_nonfinite_values_are_not_numbers(self):
        rows = [(date(2024, 1, 1), value, "W", 1, 1)
                for value in ("20", True, False, float("nan"), float("inf"), None, "Inactive")]
        summary = audit.summarize_rows(HEADERS, rows).as_dict()
        self.assertEqual(summary["eligible_games"], 0)
        self.assertEqual(summary["excluded_without_numeric_pts"], 7)
        self.assertEqual(summary["metrics"]["PTS"], {"count": 0, "mean": None})

    def test_iso_dates_are_validated_and_missing_other_metrics_have_separate_counts(self):
        summary = audit.summarize_rows(HEADERS, [
            ("2024-02-29", 10, " unknown", None, 0),
            ("2024-02-30", 500, "W", 50, 50),
            (45351, 500, "W", 50, 50),
        ]).as_dict()
        self.assertEqual(summary["eligible_games"], 1)
        self.assertEqual(summary["eligible_games_without_known_result"], 1)
        self.assertEqual(summary["metrics"]["TRB"], {"count": 0, "mean": None})
        self.assertEqual(summary["metrics"]["AST"], {"count": 1, "mean": 0.0})

    def test_headers_are_matched_by_whole_name_and_position(self):
        headers = ("Some PTS total", " ast ", "Result", " DATE ", " trb ", "pts")
        summary = audit.summarize_rows(headers, [(9999, 3, " W, 10-9", date(2024, 1, 1), 4, 5)]).as_dict()
        self.assertEqual(summary["metrics"]["PTS"]["mean"], 5.0)
        self.assertEqual(summary["metrics"]["AST"]["mean"], 3.0)
        with self.assertRaisesRegex(ValueError, "Missing required"):
            audit.column_map(("Date", "Result", "PTS total", "TRB", "AST"))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            audit.column_map((*HEADERS, " pts "))

    def test_combining_summaries_weights_by_game_count(self):
        first = audit.summarize_rows(HEADERS, [(date(2024, 1, 1), 0, "W", 0, 0)])
        second = audit.summarize_rows(HEADERS, [
            (date(2024, 1, 2), 30, "L", 3, 3),
            (date(2024, 1, 3), 30, "L", 3, 3),
        ])
        first.merge(second)
        self.assertEqual(first.as_dict()["metrics"]["PTS"], {"count": 3, "mean": 20.0})


class WorkbookTests(unittest.TestCase):
    def write_book(self, path, sheets, formula=False):
        book = Workbook()
        book.remove(book.active)
        for name in sheets:
            sheet = book.create_sheet(name)
            sheet.append(HEADERS)
            sheet.append((date(2024, 1, 1), "=1+1" if formula else 0, "W", 0, 1))
            sheet.append((date(2024, 1, 2), 10, "L", 2, 3))
            sheet.append((None, 1000, "Totals", 200, 300))
            sheet.append((date(2024, 1, 3), None, "W", None, None))
        book.save(path)
        book.close()

    def test_formula_cells_are_rejected_without_evaluation(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "synthetic.xlsx"
            self.write_book(path, ["2024-2025"], formula=True)
            with self.assertRaisesRegex(ValueError, "values-only"):
                audit.inspect_workbook(path, analyze_players=True)

    def test_cli_refuses_output_to_source_before_reading_or_writing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / audit.SOURCE_FILES[0]
            self.write_book(source, ["2024-2025"])
            before = source.read_bytes()
            alias = root / "output-alias.json"
            alias.symlink_to(source)
            # Other required source files are deliberately absent: the guard
            # must fail before validation, including through a symlink alias.
            for output in (source, alias):
                with self.subTest(output=output.name):
                    error = io.StringIO()
                    with redirect_stderr(error), self.assertRaises(SystemExit) as raised:
                        audit.main([str(root), "--output", str(output)])
                    self.assertEqual(raised.exception.code, 2)
                    self.assertIn("must not overwrite", error.getvalue())
                    self.assertEqual(source.read_bytes(), before)

    def test_cli_emits_aggregates_and_hashes_without_paths_or_game_rows(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_book(root / audit.SOURCE_FILES[0], audit.SEASONS)
            self.write_book(root / audit.SOURCE_FILES[1], [sheet for _, sheet in audit.PEER_SHEETS])
            self.write_book(root / audit.SOURCE_FILES[2], ["Synthetic team source"])
            output = root / "result.json"
            audit.main([str(root), "--output", str(output)])
            content = output.read_text()
            result = json.loads(content)
            self.assertNotIn(str(root), content)
            self.assertNotIn("2024-01-01", content)
            self.assertEqual(result["edwards"]["all_seasons"]["eligible_games"], 10)
            self.assertEqual(result["edwards"]["all_seasons"]["metrics"]["PTS"], {"count": 10, "mean": 5.0})
            self.assertEqual(result["edwards"]["all_seasons"]["win_loss_pts"]["W"], {"count": 5, "mean": 0.0})
            self.assertEqual(len(result["selected_peer_pts_2024_25"]), 6)
            self.assertEqual(len(result["sources"]), 3)
            self.assertTrue(all(len(source["sha256"]) == 64 for source in result["sources"]))
            self.assertTrue(all(source["formula_cells_present"] == 0 for source in result["sources"]))


if __name__ == "__main__":
    unittest.main()
