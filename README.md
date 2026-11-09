# Rapid Rep Board (V1)

Richie's private board: reps across the top, metrics down the side.

Rows, in order: close rate, sales this week, sales this month, sales this quarter,
sales this year, gross profit (with GP%), sits.

Reps: Mike Dietrich, Francesco Ambrosio, Joe Young, Franco Querlim,
Daniel Leverich, Leomar Santana.

## Files
- `index.html` – the board, styled to Rapid Roofing Design System V2 (same header, chips, black bars and footer as the Scoreboard and Thermometer). Reads `data/reps.json`.
- `assets/` – white Rapid logo, R mark, and the brand fonts (Barlow Condensed, Inter), bundled so nothing loads from outside.
- `data/reps.json` – the numbers. Right now it holds SAMPLE numbers (`"sample": true`
  shows a banner on the board).
- `.github/workflows/refresh.yml` – runs every morning and rebuilds `data/reps.json`.

## What's left: wire the live numbers
Every number must come from `rules/rr_metrics.py` in `rapidhsg/rr-metrics-data`,
following `rules/RULES.md`, so the board matches the certified reports.
Do not write new counting logic. Joe owns the rules repo.

Hand this to Claude Code (or Joe) with read access to both repos:

> In this repo, write `build_reps.py`. It clones `rapidhsg/rr-metrics-data` (main and
> the `data` branch), reads `rules/RULES.md`, and uses `rules/rr_metrics.py` on
> `data/job_export_raw_latest.csv` to produce `data/reps.json` in exactly the shape
> of the sample file. Reps (in this column order): Mike Dietrich, Francesco Ambrosio,
> Joe Young, Franco Querlim, Daniel Leverich, Leomar Santana. Close rate and
> sits are quarter-to-date; gross profit is year-to-date (amount and GP%). Week is
> Monday–Sunday. Set `"sample": false`. Exclude Marco and Josh. Then make sure
> `.github/workflows/refresh.yml` runs it and commits the result.

## Privacy
This board is for Richie only. Keep this repo private and limit Pages access
(GitHub Pages on a private repo needs a paid org plan with access control).
Don't put it on the shop TV.
