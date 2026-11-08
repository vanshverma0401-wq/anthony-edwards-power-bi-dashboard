"""Focused synthetic fixtures; no Power BI installation or sports data needed."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("inspect_pbix", ROOT / "scripts" / "inspect_pbix.py")
inspector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inspector)


def fixture(path: Path, *, code: int = 1, alias: str = "Sum(Example.PTS)",
            native: str = "Average of Points", encoding: str = "utf-16-le") -> None:
    selection = {"Aggregation": {"Expression": {"Column": {
        "Expression": {"SourceRef": {"Source": "a"}}, "Property": "PTS"}},
        "Function": code}, "Name": alias, "NativeReferenceName": native}
    hierarchy = {"HierarchyLevel": {"Expression": {"Hierarchy": {
        "Expression": {"PropertyVariationSource": {"Expression": {"SourceRef": {"Source": "a"}},
                       "Name": "Variation", "Property": "Date"}}, "Hierarchy": "Date Hierarchy"}},
        "Level": "Year"}, "Name": "Example.Date.Year"}
    query = {"From": [{"Name": "a", "Entity": "Example"}], "Select": [selection, hierarchy],
             "Where": [{"Condition": {"Literal": {"Value": "PRIVATE_FILTER_VALUE"}}}]}
    visual = {"config": json.dumps({"name": "PRIVATE_VISUAL_ID", "singleVisual": {
        "visualType": "card", "projections": {"Values": [{"queryRef": alias}]},
        "prototypeQuery": {"Select": [{"Literal": {"Value": "prototype must not replace actual query"}}]}}}),
        "query": json.dumps({"Commands": [{"SemanticQueryDataShapeCommand": {"Query": query}}]}),
        "dataTransforms": "PRIVATE_CACHE"}
    layout = {"sections": [{"name": "PRIVATE_SECTION_ID", "displayName": "Example page", "width": 1280,
                            "height": 720, "visualContainers": [visual]}]}
    diagram = {"diagrams": [{"nodes": [{"nodeIndex": "Example", "nodeLineageTag": "PRIVATE_GUID"}]}]}
    with ZipFile(path, "w") as archive:
        archive.writestr("Report/Layout", json.dumps(layout).encode(encoding))
        archive.writestr("DiagramLayout", json.dumps(diagram).encode(encoding))
        archive.writestr("DataModel", b"DO_NOT_READ_MODEL")
        archive.writestr("Report/CustomVisuals/code.js", b"DO_NOT_EXECUTE")


class InspectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / "example.pbix"

    def test_actual_function_overrides_stale_alias_and_prototype(self) -> None:
        fixture(self.source)
        result = inspector.inspect_pbix(self.source)
        visual = result["pages"][0]["visuals"][0]
        selection = visual["selections"][0]
        self.assertEqual(visual["selection_source"], "visual_semantic_query")
        self.assertEqual(selection["query_alias"], "Sum(Example.PTS)")
        self.assertEqual(selection["expression"]["function_code"], 1)
        self.assertEqual(selection["display_corroborated_operation"], "average")
        self.assertEqual(selection["expression"]["operand"],
                         {"kind": "column", "table": "Example", "property": "PTS"})

    def test_unknown_function_is_not_guessed_from_alias(self) -> None:
        fixture(self.source, code=999, native="Average of Points")
        selection = inspector.inspect_pbix(self.source)["pages"][0]["visuals"][0]["selections"][0]
        self.assertEqual(selection["expression"]["function_code"], 999)
        self.assertNotIn("display_corroborated_operation", selection)

    def test_counts_hierarchy_dimensions_and_private_values(self) -> None:
        fixture(self.source)
        result = inspector.inspect_pbix(self.source)
        self.assertEqual((result["page_count"], result["visual_count"], result["diagram_table_count"]), (1, 1, 1))
        self.assertEqual(result["pages"][0]["width"], 1280)
        h = result["pages"][0]["visuals"][0]["selections"][1]["expression"]
        self.assertEqual(h["kind"], "hierarchy_level")
        self.assertEqual((h["table"], h["source_property"], h["level"]), ("Example", "Date", "Year"))
        text = json.dumps(result)
        for forbidden in ["PRIVATE_FILTER_VALUE", "PRIVATE_VISUAL_ID", "PRIVATE_SECTION_ID", "PRIVATE_GUID",
                          "PRIVATE_CACHE", "DO_NOT_READ_MODEL", "DO_NOT_EXECUTE", str(self.source)]:
            self.assertNotIn(forbidden, text)

    def test_utf8_input_and_read_only_source(self) -> None:
        fixture(self.source, encoding="utf-8", code=0, native="Sum of Points")
        before = self.source.read_bytes()
        result = inspector.inspect_pbix(self.source)
        self.assertEqual(self.source.read_bytes(), before)
        self.assertEqual(result["pages"][0]["visuals"][0]["selections"][0]["display_corroborated_operation"], "sum")

    def test_size_limit_rejects_selected_entry(self) -> None:
        fixture(self.source)
        with patch.object(inspector, "MAX_JSON_BYTES", 10):
            with self.assertRaises(inspector.InspectionError):
                inspector.inspect_pbix(self.source)

    def test_malformed_selected_json_is_rejected(self) -> None:
        with ZipFile(self.source, "w") as archive:
            archive.writestr("Report/Layout", "{broken")
            archive.writestr("DiagramLayout", "{}")
        with self.assertRaises(inspector.InspectionError):
            inspector.inspect_pbix(self.source)

    def test_duplicate_selected_entries_are_rejected(self) -> None:
        with ZipFile(self.source, "w") as archive:
            archive.writestr("Report/Layout", "{}")
            with self.assertWarns(UserWarning):
                archive.writestr("Report/Layout", "{}")
            archive.writestr("DiagramLayout", "{}")
        with self.assertRaises(inspector.InspectionError):
            inspector.inspect_pbix(self.source)

    def test_name_redaction(self) -> None:
        for value in ["/Users/example/source.xlsx", "C:\\Users\\example\\source.xlsx",
                      "person@example.com", "aa87e608-6e66-4240-a8d0-2b4fbb3d28a1",
                      "https://example.sharepoint.com/private", "\\\\server\\user\\data.xlsx"]:
            self.assertEqual(inspector.safe_name(value), "[redacted]")
        self.assertEqual(inspector.safe_name("Average of Points"), "Average of Points")


if __name__ == "__main__":
    unittest.main()
