#!/usr/bin/env python3
"""Render a separately labeled review SVG from public aggregate JSON only.

Added November 2026. No PBIX, private game rows or Power BI engine is opened.
Original Power BI figures remain unchanged in the source gallery.
"""
from __future__ import annotations

import argparse
from html import escape
import json
import math
from pathlib import Path
import re


def quantity(value: object, *, count: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError("Review metrics must be finite and nonnegative")
    if count and int(value) != value:
        raise ValueError("Review counts must be integers")
    return value


def metric(data: dict) -> tuple[int, float]:
    count = quantity(data["count"], count=True)
    value = quantity(data["mean"])
    if count == 0:
        raise ValueError("A plotted mean needs a nonzero denominator")
    return count, value


def text(x: int, y: int, value: object, size: int = 18, color: str = "#24364b", weight: int = 400) -> str:
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{weight}">{escape(str(value))}</text>'


def render(summary: dict) -> str:
    """Render season-grain trends and separate, non-normalized group means."""
    try:
        total = quantity(summary["edwards"]["all_seasons"]["eligible_games"], count=True)
        seasons = summary["edwards"]["per_season"]
        if not seasons or len(seasons) > 6:
            raise ValueError("Expected one to six season groups")
        seen = set()
        rows = []
        for season in seasons:
            name = season["season"]
            if not re.fullmatch(r"\d{4}-\d{4}", name) or int(name[-4:]) != int(name[:4]) + 1 or name in seen:
                raise ValueError("Expected unique consecutive-year season labels")
            seen.add(name)
            rows.append((name[:5] + name[-2:], {key: metric(season["metrics"][key]) for key in ["PTS", "TRB", "AST"]}))
        rows.sort(key=lambda row: row[0])
        groups = [(label, *metric(summary["edwards"]["all_seasons"]["win_loss_pts"][key])) for key, label in [("W", "Wins"), ("L", "Losses")]]
        peers = [(str(p["player"]), *metric(p)) for p in summary["selected_peer_pts_2024_25"]]
        if not peers or len(peers) > 7:
            raise ValueError("Expected one to seven selected peers")
    except (KeyError, TypeError) as exc:
        raise ValueError("Missing review aggregate contract") from exc

    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1050" viewBox="0 0 1080 1050" role="img" aria-labelledby="title description">',
           '<title id="title">Anthony Edwards — season and scoring review</title>',
           '<desc id="description">Independent Python SVG of already-public aggregate results, not a Power BI export. Season averages and win-loss means are separate descriptive comparisons.</desc>',
           '<rect width="1080" height="1050" fill="#f4f7fb"/><g font-family="Arial, Helvetica, sans-serif">',
           text(40, 49, "BASKETBALL / AGGREGATE REVIEW", 14, "#087f8c", 700),
           text(40, 91, "Anthony Edwards: the season view", 33, weight=700),
           text(40, 123, f"{total:,} eligible recorded games · {rows[0][0]} through {rows[-1][0]}", 19),
           text(40, 153, "November 2026 Python review, not a Power BI export. Original figures preserved below.", 16),
           text(40, 205, "Per-game production by NBA season", 23, weight=700)]
    columns = [(245, "PTS", "#087f8c"), (515, "TRB", "#4d68aa"), (785, "AST", "#b76e26")]
    for x, key, color in columns:
        out.append(text(x, 242, key, 17, color, 700))
        maximum = max(value[key][1] for _, value in rows) or 1
        for index, (season, values) in enumerate(rows):
            count, value = values[key]
            y = 282 + index * 57
            out.append(f'<rect x="{x}" y="{y - 18}" width="{150 * value / maximum:.3f}" height="21" rx="3" fill="{color}"/>')
            out.append(text(x + 160, y, f"{value:.2f}", 16))
            out.append(text(x, y + 23, f"n={count}", 13, "#5d6c7e"))
    for index, (season, _) in enumerate(rows):
        out.append(text(40, 282 + index * 57, season, 18, weight=700))
    out.extend([text(40, 624, "Scoring in wins and losses", 22, weight=700), text(560, 624, "Selected peers / 2024-25", 22, weight=700)])
    maximum = max(v for _, _, v in groups) or 1
    for index, (label, count, value) in enumerate(groups):
        y = 677 + index * 102
        out.extend([text(40, y, label, 18, weight=700), text(40, y + 25, f"n={count}", 14),
                    f'<rect x="150" y="{y - 20}" width="{230 * value / maximum:.3f}" height="29" rx="3" fill="#087f8c"/>', text(150, y + 35, f"{value:.2f} PTS / recorded game", 16)])
    maximum = max(v for _, _, v in peers) or 1
    for index, (label, count, value) in enumerate(peers):
        y = 668 + index * 47
        out.extend([text(560, y, label, 16), f'<rect x="755" y="{y - 14}" width="{150 * value / maximum:.3f}" height="20" rx="3" fill="#4d68aa"/>', text(915, y, f"{value:.2f} · n={count}", 14)])
    out.extend([text(40, 982, "Descriptive association; scoring is not established as the cause of a win.", 16),
                text(40, 1009, "Season groups are not calendar years. Selected peers are not a league-wide ranking.", 15),
                text(40, 1032, "Missing-PTS nonappearances and undated totals excluded; original source workbooks remain private.", 14), '</g></svg>'])
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("aggregate_json", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.aggregate_json.resolve() == args.output.resolve():
        parser.error("Output must differ from source JSON")
    try:
        svg = render(json.loads(args.aggregate_json.read_text()))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(svg, encoding="utf-8")
    except (ValueError, OSError, UnicodeError) as exc:
        parser.exit(1, f"Review render failed: {exc}\n")
    print("Wrote aggregate-only review SVG; input unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
