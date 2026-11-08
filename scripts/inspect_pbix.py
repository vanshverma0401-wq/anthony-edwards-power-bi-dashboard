#!/usr/bin/env python3
"""Read-only PBIX layout inventory, added for the November 2026 portfolio review.

The original report is 2025 academic work. This tool does not load Power BI,
execute embedded code, decompress its data model, or reconstruct M/DAX.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from zipfile import BadZipFile, ZipFile

MAX_JSON_BYTES = 8 * 1024 * 1024
MAX_ARCHIVE_ENTRIES = 2000
MAX_VISUALS = 1000
_SENSITIVE = re.compile(
    r"(?:[A-Za-z]:\\|/(?:Users|home|Volumes)/|https?://|\\\\|"
    r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b|"
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b|"
    r"\b[0-9a-f]{16,}\b)", re.I
)


class InspectionError(ValueError):
    """The selected source is malformed or exceeds a read boundary."""


def safe_name(value: object) -> str:
    """Copy only bounded human-readable labels, redacting sensitive patterns."""
    if not isinstance(value, str):
        return ""
    if _SENSITIVE.search(value):
        return "[redacted]"
    return "".join(c for c in value if c.isprintable())[:200]


def _json(value: object, context: str) -> dict:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        raise InspectionError(f"Expected a JSON object in {context}")
    try:
        parsed = json.loads(value)
    except (ValueError, RecursionError) as exc:
        raise InspectionError(f"Invalid JSON in {context}") from exc
    if not isinstance(parsed, dict):
        raise InspectionError(f"Expected a JSON object in {context}")
    return parsed


def _read_json(archive: ZipFile, name: str) -> dict:
    if sum(i.filename == name for i in archive.infolist()) != 1:
        raise InspectionError(f"Expected one {name} entry")
    info = archive.getinfo(name)
    if info.file_size > MAX_JSON_BYTES:
        raise InspectionError(f"{name} exceeds the JSON size limit")
    with archive.open(info) as source:
        raw = source.read(MAX_JSON_BYTES + 1)
    if len(raw) > MAX_JSON_BYTES:
        raise InspectionError(f"{name} exceeds the JSON size limit")
    # PBIX uses UTF-16LE; synthetic/other exports may use UTF-8 or a BOM.
    encoding = "utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else (
        "utf-16-le" if b"\x00" in raw[:40] else "utf-8-sig")
    try:
        return _json(raw.decode(encoding), name)
    except UnicodeError as exc:
        raise InspectionError(f"Cannot decode {name}") from exc


def _table(expression: object, aliases: dict[str, str], depth: int = 0) -> str:
    if not isinstance(expression, dict) or depth > 12:
        return ""
    source = expression.get("SourceRef")
    if isinstance(source, dict):
        return safe_name(source.get("Entity") or aliases.get(source.get("Source"), ""))
    for value in expression.values():
        found = _table(value, aliases, depth + 1)
        if found:
            return found
    return ""


def _expression(value: object, aliases: dict[str, str], depth: int = 0) -> dict:
    if not isinstance(value, dict) or depth > 12:
        return {"kind": "unexpanded"}
    for key in ("Column", "Measure"):
        if isinstance(value.get(key), dict):
            item = value[key]
            return {"kind": "column" if key == "Column" else "measure_reference",
                    "table": _table(item, aliases),
                    "property": safe_name(item.get("Property"))}
    if isinstance(value.get("Aggregation"), dict):
        item = value["Aggregation"]
        code = item.get("Function")
        return {"kind": "aggregation", "function_code": code if type(code) is int else None,
                "operand": _expression(item.get("Expression"), aliases, depth + 1)}
    if isinstance(value.get("HierarchyLevel"), dict):
        item = value["HierarchyLevel"]
        hierarchy = item.get("Expression", {}).get("Hierarchy", {})
        variation = hierarchy.get("Expression", {}).get("PropertyVariationSource", {})
        return {"kind": "hierarchy_level", "table": _table(item, aliases),
                "source_property": safe_name(variation.get("Property")),
                "hierarchy": safe_name(hierarchy.get("Hierarchy")),
                "level": safe_name(item.get("Level"))}
    return {"kind": "literal_or_unexpanded_expression_omitted"}


def _query(visual: dict, single: dict) -> tuple[dict, str]:
    if visual.get("query"):
        query = _json(visual["query"], "visual query")
        for command in query.get("Commands", []):
            semantic = command.get("SemanticQueryDataShapeCommand", {})
            if isinstance(semantic.get("Query"), dict):
                return semantic["Query"], "visual_semantic_query"
    return _json(single.get("prototypeQuery", {}), "prototype query"), "prototype_query"


def _selection(item: dict, aliases: dict[str, str]) -> dict:
    expression = _expression(item, aliases)
    native = safe_name(item.get("NativeReferenceName"))
    result = {"query_alias": safe_name(item.get("Name")),
              "native_display_name": native, "expression": expression}
    # Aliases such as Sum(...) can survive a later aggregation change.
    # Only label these codes when the saved display text corroborates them.
    if expression.get("kind") == "aggregation":
        code = expression["function_code"]
        if code == 0 and native.lower().startswith("sum of "):
            result["display_corroborated_operation"] = "sum"
        elif code == 1 and native.lower().startswith("average of "):
            result["display_corroborated_operation"] = "average"
    return result


def inspect_pbix(path: Path) -> dict:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    try:
        with ZipFile(path) as archive:
            if len(archive.infolist()) > MAX_ARCHIVE_ENTRIES:
                raise InspectionError("Archive exceeds the entry-count limit")
            layout = _read_json(archive, "Report/Layout")
            diagram = _read_json(archive, "DiagramLayout")
    except (BadZipFile, RuntimeError, NotImplementedError) as exc:
        raise InspectionError("Cannot read the selected ZIP entries") from exc
    pages = []
    sections = layout.get("sections", [])
    if not isinstance(sections, list) or not all(isinstance(s, dict) for s in sections):
        raise InspectionError("Report sections must be a list of objects")
    for page_number, section in enumerate(sections, 1):
        visuals = []
        containers = section.get("visualContainers", [])
        if not isinstance(containers, list) or not all(isinstance(v, dict) for v in containers):
            raise InspectionError("Visual containers must be a list of objects")
        if len(containers) > MAX_VISUALS:
            raise InspectionError("Report page exceeds the visual-count limit")
        for index, visual in enumerate(containers, 1):
            config = _json(visual.get("config", {}), "visual config")
            single = config.get("singleVisual", {})
            query, origin = _query(visual, single)
            aliases = {str(item.get("Name")): str(item.get("Entity", ""))
                       for item in query.get("From", []) if isinstance(item, dict)}
            projections = {safe_name(role): [safe_name(p.get("queryRef")) for p in values
                                            if isinstance(p, dict)]
                           for role, values in single.get("projections", {}).items()
                           if isinstance(values, list)}
            visuals.append({"visual_number": index,
                            "visual_type": safe_name(single.get("visualType", "other")),
                            "projection_roles": projections,
                            "selection_source": origin,
                            "selections": [_selection(item, aliases) for item in query.get("Select", [])
                                           if isinstance(item, dict)],
                            "saved_query_has_filter": bool(query.get("Where"))})
        pages.append({"page_number": page_number, "name": safe_name(section.get("displayName")),
                      "width": section.get("width") if type(section.get("width")) is int else None,
                      "height": section.get("height") if type(section.get("height")) is int else None,
                      "visual_count": len(visuals),
                      "visual_types": dict(sorted(Counter(v["visual_type"] for v in visuals).items())),
                      "visuals": visuals})
    table_names = sorted({safe_name(node.get("nodeIndex"))
                          for item in diagram.get("diagrams", [])
                          for node in item.get("nodes", []) if isinstance(node, dict)})
    return {"inventory_format": 1, "tool_added": "November 2026 portfolio review",
            "original_report_year": 2025, "source_sha256": digest.hexdigest(),
            "scope": {"read_entries": ["Report/Layout", "DiagramLayout"],
                      "static_only": True, "literal_filter_values_excluded": True,
                      "excluded": ["model data", "full queries", "cached values", "resource blobs",
                                   "private identifiers", "source paths", "M and DAX definitions"],
                      "not_established": ["model relationships", "Power BI load or refresh",
                                          "query execution", "Power Query transformations"]},
            "page_count": len(pages), "visual_count": sum(p["visual_count"] for p in pages),
            "diagram_table_count": len(table_names), "diagram_table_names": table_names,
            "pages": pages}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pbix", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.pbix.resolve() == args.output.resolve():
        parser.error("Output must differ from the PBIX source")
    try:
        inventory = inspect_pbix(args.pbix)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(inventory, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    except (InspectionError, OSError) as exc:
        parser.exit(1, f"Inspection failed: {exc}\n")
    print(f"Inspected {inventory['page_count']} pages and {inventory['visual_count']} visual containers.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
