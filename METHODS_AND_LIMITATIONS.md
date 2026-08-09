# Methods and limitations

## Verified report structure

The final PBIX contains two 1280 x 720 report pages:

1. **Anthony Edwards Performance** — 13 visual containers: three slicers, two line charts, one clustered bar chart, one donut chart, four cards, one image, and one text box.
2. **Comparison to Top Shooting Guards** — seven visual containers: two slicers, one custom radar visual, two pivot-style tables, one clustered bar chart, and one clustered column chart.

The model diagram contains 18 tables: five Anthony Edwards season tables, five Timberwolves season tables, five comparison-player tables, Devin Booker's comparison table, and three consolidated analysis tables.

## Private-data validation

The portfolio audit inspected all three Excel source workbooks and recalculated the featured values after excluding summary rows and games without recorded player statistics.

- Anthony Edwards source coverage: five seasons.
- Recorded Edwards point totals used in the win/loss check: 381 games.
- 2024-25 peer comparison: Edwards plus five selected guards.
- Report structure: two pages and 20 visual containers.

## Interpretation rules

- Use `associated with`, `differed between`, or `compared with` for win/loss observations.
- Do not claim that Edwards' scoring caused wins.
- Do not present the selected six-player comparison as a league-wide rank.
- Do not describe the forecast visual as a reliable future prediction.
- Do not use plus/minus as an isolated causal measure of individual impact.

## Technical evidence boundary

The PBIX layout verifies the visual queries, filters, implicit aggregations, report pages, and model-table names. The shared workflow included Power Query and Power BI calculations, but exact transformation and DAX definitions were not independently reconstructed during this Mac-based audit and are not included in the public package.

## Reproducibility boundary

The public case study is intentionally screenshot-based. A reproducible raw-data build is not supplied because the source terms and collaborative PBIX make raw redistribution inappropriate for this portfolio package.
