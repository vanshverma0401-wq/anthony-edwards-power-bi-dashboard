"""Synthetic and aggregate-only contracts for the new review SVG."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "render_review.py"


class ReviewVisualTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SCRIPT.exists(), "Missing review renderer")
        spec = importlib.util.spec_from_file_location("render_review", SCRIPT)
        self.renderer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.renderer)
        self.summary = json.loads((ROOT / "technical/data_validation.json").read_text())

    def test_uses_season_labels_counts_and_group_means_without_percentages(self):
        svg = self.renderer.render(self.summary)
        ET.fromstring(svg)
        for label in ["2020-21", "2024-25", "381", "204", "177", "24.83", "22.77"]:
            self.assertIn(label, svg)
        self.assertIn("not a Power BI export", svg)
        self.assertIn("Descriptive association", svg)
        self.assertNotIn("52.16%", svg)

    def test_output_is_deterministic_and_labels_are_escaped(self):
        self.summary["selected_peer_pts_2024_25"][0]["player"] = "Example & <player>"
        first = self.renderer.render(self.summary)
        self.assertEqual(first, self.renderer.render(self.summary))
        self.assertIn("Example &amp; &lt;player&gt;", first)
        ET.fromstring(first)

    def test_seasons_are_ordered_chronologically_even_if_input_changes_order(self):
        expected = self.renderer.render(self.summary)
        self.summary["edwards"]["per_season"].reverse()
        self.assertEqual(self.renderer.render(self.summary), expected)

    def test_missing_and_invalid_metrics_are_rejected(self):
        del self.summary["edwards"]["per_season"][0]["metrics"]["PTS"]
        with self.assertRaises(ValueError):
            self.renderer.render(self.summary)
        self.summary = json.loads((ROOT / "technical/data_validation.json").read_text())
        for value in [float("nan"), float("inf"), -1]:
            self.summary["selected_peer_pts_2024_25"][0]["mean"] = value
            with self.assertRaises(ValueError):
                self.renderer.render(self.summary)

    def test_cli_emits_no_private_paths_or_game_rows_and_leaves_input_unchanged(self):
        source = ROOT / "technical/data_validation.json"
        before = source.read_bytes()
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "overview.svg"
            self.assertEqual(self.renderer.main([str(source), "--output", str(output)]), 0)
            self.assertEqual(source.read_bytes(), before)
            self.assertNotIn(str(source), output.read_text())
            self.assertNotIn("2024-01-01", output.read_text())
            ET.fromstring(output.read_text())

    def test_cli_refuses_to_overwrite_input(self):
        source = ROOT / "technical/data_validation.json"
        before = source.read_bytes()
        with self.assertRaises(SystemExit):
            self.renderer.main([str(source), "--output", str(source)])
        self.assertEqual(source.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
