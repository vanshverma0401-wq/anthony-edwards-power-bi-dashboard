# Methods and limitations

## Original report structure

The final PBIX has two 1280 x 720 report pages:

1. **Anthony Edwards Performance:** 13 visual containers: three slicers, two line charts, a clustered bar chart, a donut chart, four cards, an image and a text box.
2. **Comparison to Top Shooting Guards:** seven containers: two slicers, a bundled radar visual, two pivot tables, a clustered bar chart and a clustered column chart.

The diagram lists **18 tables**: five Edwards season tables, five Timberwolves
season tables, five peer-player tables (including Devin Booker) and three
consolidated analysis tables. This is a table-name inventory, not verification of
relationships, cardinalities, table contents or a star schema.

## Private source and aggregation checks

The three workbooks contain 15 worksheets. The audit excludes summary rows and
requires a real date plus numeric PTS for the Edwards and peer scoring checks.
Dated nonappearance rows with blank PTS are excluded; numeric zero is retained.

- Edwards numeric-PTS counts by season: 72, 72, 79, 79 and 79, totaling 381.
- Wins: 204 games, mean PTS 24.8333; losses: 177 games, mean PTS 22.7740.
- Edwards 2024-25 scoring mean: 27.55696 PTS across 79 recorded games.
- The comparison includes five selected peer guards plus Edwards.

These aggregate checks validate the project snapshot, not the completeness or
current accuracy of the providers' entire databases. Source workbook sheet ranges
may include summary or blank rows and are not equivalent to appearance counts.

## Calendar years and NBA seasons

The original line charts bind to `AE Data.Date` and its Year/Quarter/Month/Day
hierarchy. Calendar-year chart values are not the same as NBA-season averages
from the worksheets, because a season spans two calendar years. The season
endpoints in the README come from workbook checks, not a relabeling of the chart.

## Aggregation interpretation

Readable visual queries contain implicit aggregation operators and display names.
Projection aliases can retain a `Sum(...)` name even when the actual query uses
an average operator and an `Average ...` display label. The technical inventory
therefore preserves operator evidence rather than treating aliases as formulas.

Some visuals average game-level FG%, FT% and 3P%. Those averages are not
attempt-weighted season rates. An attempt-weighted rate would require dividing
total makes by total attempts at the intended grain. Empty percentage values,
zero-attempt games and the visual's filter context affect the result.

Win/loss average scoring is descriptive. The original donut's percentage labels
normalize two group averages and should not be read as percentages of games or
of total points. The gallery preserves that original donut with this limitation beside it; the
checked analytical claim is restricted to the two group means.

## Original-report interpretation corrections

The original write-up uses stronger causal, growth and forecast language than
the evidence supports. This case study therefore:

- describes win/loss associations without claiming scoring caused victories;
- distinguishes calendar-year charts from season aggregates;
- avoids claiming every statistic improved every season;
- limits rankings to the six selected players;
- treats plus/minus as contextual;
- includes the original forecast only as a labeled, unvalidated historical visual, without treating its projected line as an established prediction.

## What the source inspection establishes

The inspector reads only the ZIP members `Report/Layout` and `DiagramLayout`.
It derives selected page, visual, field-binding, query-operator and table-name
metadata. It does not execute embedded JavaScript, report expressions, DAX, M,
workbook formulas or a Power BI engine. The workbook validator reads cell values
and computes a limited set of descriptive aggregates.

## What remains unavailable or unverified

- The PBIX's compressed `DataModel` and protected `SecurityBindings` were not decoded.
- No exact Power Query transformation definitions or explicit DAX measures were recovered.
- Relationship definitions, direction, cardinality and row-filter propagation are not established by diagram nodes alone.
- No fresh Power BI Desktop load, refresh, gateway configuration or interactive test was performed on the Air.
- Forecast settings, validation and accuracy remain unverified.
- A full privacy scan of opaque model contents is not claimed.

The public utilities were written for the November 2026 portfolio audit. They are
separate from the original 2025 team implementation and do not reconstruct a
loadable PBIX, PBIP or semantic model.

## Reproducibility boundary

Readers can inspect the screenshots, static evidence and synthetic-fixture tests.
Those with authorized copies of the same private originals can rerun the audit
commands and compare hashes and derived output. The raw sports data and original
course documents are not redistributed. A complete public end-to-end refresh is
therefore not supplied.

## Complete source-figure gallery

The README now displays all nine analytical figures from the final write-up in
report order. Their image bytes are preserved exactly. The joint project logo is
omitted. The [figure manifest](technical/figure_manifest.json) maps the original
media names to public assets and hashes. Original visual weaknesses are stated
beside the relevant image rather than silently presented as validated findings.
