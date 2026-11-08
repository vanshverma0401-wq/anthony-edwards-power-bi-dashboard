#!/usr/bin/env python3
"""New portfolio audit tooling introduced 2026-11-08, not original Power Query.

Read the privately retained, values-only XLSX exports without changing them,
refreshing connections, evaluating formulas or emitting individual game rows.
The JSON output contains workbook structure, hashes and aggregate statistics.
Requires openpyxl. It does not validate Power BI's own execution or measures.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import date, datetime
import hashlib
import json
import math
from numbers import Real
from pathlib import Path
import re
from typing import Iterable, Sequence

from openpyxl import load_workbook


SOURCE_FILES = (
    "AnthonyEdwards_AllSeasons.xlsx",
    "NBA Comparisons.xlsx",
    "Timberwolves Seasons.xlsx",
)
SEASONS = tuple(f"{year}-{year + 1}" for year in range(2020, 2025))
PEER_SHEETS = (
    ("Tyler Herro", "Tyler Herro 2024-2025"),
    ("Jaylen Brown", "Jaylen Brown 2024-2025"),
    ("Jalen Green", "Jalen Green 2024-2025"),
    # Preserve the source sheet's spelling while labeling the player correctly.
    ("Donovan Mitchell", "Donovon Mitchell 2024-2025"),
    ("Devin Booker", "Devin Booker 2024-2025"),
)
REQUIRED_HEADERS = ("DATE", "RESULT", "PTS", "TRB", "AST")


def numeric(value: object) -> bool:
    """Accept finite Excel numbers, including zero, but not bools or strings."""
    return isinstance(value, Real) and not isinstance(value, bool) and math.isfinite(value)


def real_date(value: object) -> bool:
    """Accept native Excel dates or valid ISO date strings, not serial guesses."""
    if isinstance(value, (datetime, date)):
        return True
    if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value.strip()):
        try:
            date.fromisoformat(value.strip())
            return True
        except ValueError:
            pass
    return False


def column_map(headers: Sequence[object]) -> dict[str, int]:
    """Match required whole headers regardless of case or surrounding spaces."""
    columns: dict[str, int] = {}
    for index, value in enumerate(headers):
        label = value.strip().upper() if isinstance(value, str) else ""
        if label in REQUIRED_HEADERS:
            if label in columns:
                raise ValueError(f"Ambiguous duplicate required column: {label}")
            columns[label] = index
    missing = set(REQUIRED_HEADERS) - columns.keys()
    if missing:
        raise ValueError("Missing required player columns: " + ", ".join(sorted(missing)))
    return columns


@dataclass
class Metric:
    count: int = 0
    total: float = 0.0

    def add(self, value: object) -> None:
        if numeric(value):
            self.count += 1
            self.total += float(value)

    def merge(self, other: "Metric") -> None:
        self.count += other.count
        self.total += other.total

    def as_dict(self) -> dict[str, object]:
        return {"count": self.count, "mean": round(self.total / self.count, 6) if self.count else None}


@dataclass
class PlayerSummary:
    rows_after_header: int = 0
    excluded_without_valid_date: int = 0
    excluded_without_numeric_pts: int = 0
    eligible_games: int = 0
    eligible_games_without_known_result: int = 0
    metrics: dict[str, Metric] = field(default_factory=lambda: {key: Metric() for key in ("PTS", "TRB", "AST")})
    win_loss: dict[str, Metric] = field(default_factory=lambda: {key: Metric() for key in ("W", "L")})

    def merge(self, other: "PlayerSummary") -> None:
        for key in ("rows_after_header", "excluded_without_valid_date", "excluded_without_numeric_pts",
                    "eligible_games", "eligible_games_without_known_result"):
            setattr(self, key, getattr(self, key) + getattr(other, key))
        for key, metric in self.metrics.items():
            metric.merge(other.metrics[key])
        for key, metric in self.win_loss.items():
            metric.merge(other.win_loss[key])

    def as_dict(self) -> dict[str, object]:
        return {
            "rows_after_header": self.rows_after_header,
            "excluded_without_valid_date": self.excluded_without_valid_date,
            "excluded_without_numeric_pts": self.excluded_without_numeric_pts,
            "eligible_games": self.eligible_games,
            "eligible_games_without_known_result": self.eligible_games_without_known_result,
            "metrics": {key: value.as_dict() for key, value in self.metrics.items()},
            "win_loss_pts": {key: value.as_dict() for key, value in self.win_loss.items()},
        }


def summarize_rows(headers: Sequence[object], rows: Iterable[Sequence[object]]) -> PlayerSummary:
    columns = column_map(headers)
    summary = PlayerSummary()
    for row in rows:
        summary.rows_after_header += 1
        def cell(label: str) -> object:
            index = columns[label]
            return row[index] if index < len(row) else None

        if not real_date(cell("DATE")):
            summary.excluded_without_valid_date += 1
            continue
        points = cell("PTS")
        if not numeric(points):
            summary.excluded_without_numeric_pts += 1
            continue
        summary.eligible_games += 1
        for key, metric in summary.metrics.items():
            metric.add(cell(key))
        result = cell("RESULT")
        match = re.match(r"^\s*([WL])(?:\s|,|$)", result, flags=re.I) if isinstance(result, str) else None
        if match:
            summary.win_loss[match.group(1).upper()].add(points)
        else:
            summary.eligible_games_without_known_result += 1
    return summary


def inspect_workbook(path: Path, analyze_players: bool) -> tuple[dict[str, object], dict[str, PlayerSummary]]:
    """Inspect structures/formula markup, then read cached values only.

    Player exports must be values-only. Formula cells are rejected before any
    metric is calculated, avoiding silent use of absent or stale formula caches.
    External workbook links are not retained or refreshed.
    """
    formula_count = 0
    formula_book = load_workbook(path, read_only=True, data_only=False, keep_links=False)
    try:
        for sheet in formula_book:
            formula_count += sum(cell.data_type == "f" for row in sheet.iter_rows() for cell in row)
    finally:
        formula_book.close()
    if analyze_players and formula_count:
        raise ValueError(f"Player workbook must be a values-only export: {path.name}")

    book = load_workbook(path, read_only=True, data_only=True, keep_links=False)
    inventory: list[dict[str, object]] = []
    summaries: dict[str, PlayerSummary] = {}
    try:
        for sheet in book:
            rows = sheet.iter_rows(values_only=True)
            headers = next(rows, ())
            inventory.append({
                "name": sheet.title,
                "declared_rows_including_header": sheet.max_row,
                "declared_columns": sheet.max_column,
                "headers": [value if isinstance(value, (str, int, float, bool)) else None for value in headers],
            })
            if analyze_players:
                summaries[sheet.title] = summarize_rows(headers, rows)
    finally:
        book.close()
    source = {
        "filename": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "sheet_count": len(inventory),
        "formula_cells_present": formula_count,
        "sheets": inventory,
    }
    return source, summaries


def validate_source_dir(source_dir: Path) -> dict[str, object]:
    sources: list[dict[str, object]] = []
    analyses: dict[str, dict[str, PlayerSummary]] = {}
    for name in SOURCE_FILES:
        source, summaries = inspect_workbook(source_dir / name, analyze_players=name != SOURCE_FILES[2])
        sources.append(source)
        analyses[name] = summaries
    edwards = analyses[SOURCE_FILES[0]]
    comparison = analyses[SOURCE_FILES[1]]
    missing = set(SEASONS) - edwards.keys()
    if missing:
        raise ValueError("Missing Edwards season sheets: " + ", ".join(sorted(missing)))
    missing_peers = {sheet for _, sheet in PEER_SHEETS} - comparison.keys()
    if missing_peers:
        raise ValueError("Missing comparison sheets: " + ", ".join(sorted(missing_peers)))

    combined = PlayerSummary()
    per_season: list[dict[str, object]] = []
    for season in SEASONS:
        combined.merge(edwards[season])
        per_season.append({"season": season, **edwards[season].as_dict()})
    peers = [{"player": "Anthony Edwards", "source_sheet": "2024-2025",
              **edwards["2024-2025"].metrics["PTS"].as_dict()}]
    peers.extend({"player": player, "source_sheet": sheet, **comparison[sheet].metrics["PTS"].as_dict()}
                 for player, sheet in PEER_SHEETS)
    return {
        "schema_version": 1,
        "tooling_introduced": "2026-11-08",
        "tooling_scope": "New portfolio audit helper; not recovered Power Query, DAX or original project code.",
        "method": {
            "read_only": True,
            "formula_evaluation_or_refresh": False,
            "player_formula_policy": "Refuse player workbooks containing formula cells; original exports are values-only.",
            "eligible_game": "Valid native date or ISO date string plus finite numeric PTS; zero PTS is included.",
            "summary_exclusion": "Rows without a valid date are excluded, including season totals.",
            "nonappearance_exclusion": "Dated rows with blank or nonnumeric PTS are excluded.",
            "other_metrics": "TRB and AST each use numeric values among eligible PTS games; their counts are reported separately.",
            "result_groups": "W or L prefix in Result, among eligible PTS games; unknown results are counted separately.",
            "mean_precision_decimal_places": 6,
            "data_output": "Hashes, sheet/header inventories and aggregates only; no game rows, local paths or workbook-author metadata.",
            "power_bi_runtime_validated": False,
        },
        "sources": sources,
        "edwards": {"per_season": per_season, "all_seasons": combined.as_dict()},
        "selected_peer_pts_2024_25": peers,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_dir", type=Path, help="Directory containing the three private original XLSX files.")
    parser.add_argument("--output", type=Path, required=True, help="Aggregate-only JSON destination.")
    args = parser.parse_args(argv)
    protected_sources = {(args.source_dir / name).resolve() for name in SOURCE_FILES}
    if args.output.resolve() in protected_sources:
        parser.error("Output must not overwrite an input workbook.")
    result = validate_source_dir(args.source_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print("Wrote aggregate-only workbook validation JSON.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
