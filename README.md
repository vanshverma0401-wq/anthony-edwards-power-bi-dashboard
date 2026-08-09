# Anthony Edwards Power BI Performance Dashboard

Collaborative Power BI case study by **Vansh Verma and Denny Hoang**.

## At a glance

- **Question:** How did Anthony Edwards' box-score production change across his first five NBA seasons, how did it differ between wins and losses, and how did his 2024-25 performance compare with five selected shooting guards?
- **Coverage:** 2020-21 through 2024-25 Anthony Edwards game logs, Minnesota Timberwolves game context, and 2024-25 comparison-player game logs.
- **Deliverable:** Two Power BI report pages with 20 visual containers, including slicers, KPI cards, line and bar charts, tables, a donut chart, and a custom radar visual.
- **Tools:** Power BI, Power Query, Excel, report modeling, calculated fields and aggregations, interactive filtering, and analytical storytelling.

## Analytical questions

1. How did points, rebounds, assists, and shooting efficiency vary across Edwards' first five seasons?
2. How did scoring differ between games the Timberwolves won and lost?
3. How did Edwards compare with Devin Booker, Donovan Mitchell, Tyler Herro, Jaylen Brown, and Jalen Green during 2024-25?
4. Which opponent and home/away filters help reveal matchup patterns?

## Workflow

1. Collected player and team game-log data identified in the original report as coming primarily from Basketball-Reference, with NBA.com used for team context.
2. Prepared and standardized season-level Excel tables for player, opponent, date, result, box-score, and shooting fields.
3. Consolidated the season and comparison tables in the shared Power BI workflow.
4. Built two interactive report pages with slicers for season, opponent, home/away status, player, and game result.
5. Cross-checked the featured values against the private source workbooks during the portfolio audit.

## Dashboard evidence

### Five-season production trend

![Anthony Edwards points, rebounds, and assists trend](assets/performance-trends.png)

The source workbooks show Edwards' scoring average rising from **19.33 points per game in 2020-21** to **27.56 in 2024-25**. Rebounds and assists varied rather than increasing every season, so the public interpretation is deliberately descriptive.

### 2024-25 peer scoring comparison

![Anthony Edwards and five selected guards scoring and plus-minus table](assets/peer-scoring-table.png)

Within this six-player comparison set, Edwards recorded the highest 2024-25 scoring average at **27.56 points per game**. This is a selected-peer comparison, not a league-wide ranking.

### 2024-25 shooting-efficiency comparison

![Selected guards field goal, free throw, and three-point percentage comparison](assets/peer-shooting-efficiency.png)

The report compares three shooting percentages side by side to show that scoring volume and shooting efficiency answer different questions.

## Additional verified observation

Across **381 games with recorded Edwards point totals**, the private source workbooks produced averages of **24.83 points in wins** and **22.77 points in losses**. This is an association in the selected data; it does not establish that scoring caused the game outcome.

## Contribution and attribution

Vansh Verma and Denny Hoang worked jointly across source collection and preparation, Power Query, report modeling, Power BI calculations, visual design, documentation, and presentation. This project must always be presented as collaborative work.

## Validation

- Final PBIX structure verified: two report pages, 20 visual containers, 18 model tables, and one custom radar visual.
- Three source workbooks inspected and featured values recalculated from private evidence.
- Source report and proposal both name Denny Hoang and Vansh Verma.
- No unsupported percentage-improvement, causal-impact, or predictive-performance claim is used here.

## Limitations

- The analysis is descriptive and based on the data snapshot assembled for the original project.
- Game-level shooting percentages are averaged in some visuals; attempt-weighted season percentages may differ.
- The five comparison players are a selected peer group, not an exhaustive position ranking.
- Plus/minus is contextual and should not be interpreted as an individual causal-impact measure.
- The original forecast visual is not featured because its model assumptions were not documented well enough for a defensible public claim.
- Exact Power Query and DAX definitions are not distributed in this public case study.

## Data and viewing boundary

This repository is designed as a **screenshot-based, non-commercial portfolio case study**. The PBIX and raw Excel workbooks are intentionally excluded because they contain third-party statistical data and shared project work.

The original report identifies [Basketball-Reference](https://www.basketball-reference.com/) as the primary data provider and [NBA.com](https://www.nba.com/) as a team-context source. See [DATA_AND_USAGE.md](DATA_AND_USAGE.md) for attribution, source terms, and reuse boundaries.

## Status

Published as a screenshot-based portfolio case study with Denny Hoang credited and the raw data, PBIX, course documents, and unsupported claims kept private.
