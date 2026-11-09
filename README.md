# Project Falcon — project health check

A small analytics pipeline that reads three messy data exports, computes delivery
metrics for a coding-RL-task project, and renders a one-page HTML dashboard plus
written status notes.

## Run

```bash
python3 metrics.py
```

That one command:
1. reads everything in `data/` (`experts.csv`, `submissions.csv`, `qa_results.json`),
2. cleans the messy bits (mixed-case IDs, duplicate rows, blank fields),
3. writes `metrics.json`, and
4. renders `dashboard.html`.

Then open `dashboard.html` in a browser. This is a **point-in-time status report**, so
the snapshot date is pinned (`AS_OF = 2026-11-02`, end of week 4) rather than floating
with the wall clock — that keeps the numbers reproducible and identical across every
deliverable. To produce a later cut, pass a date:

```bash
python3 metrics.py 2026-11-09
```

`GOAL` (600 accepted), the `DUE` (Nov 13, 2026) deadline, and `AS_OF` are constants at
the top of `metrics.py`.

### Diagnostics

```bash
python3 metrics.py --diagnose
```

Runs a set of health-check rules over the metrics and prints ranked flags
(CRITICAL / WARN / INFO), each with its evidence and a recommended action — e.g.
forecast-short, difficulty-spec mismatch, QA bottleneck, rejection concentration,
reviewer-calibration spread, auto-preventable load. The same flags are saved in
`metrics.json` under `diagnostics` and shown as a banner at the top of the dashboard.
Rules are threshold-driven off the data, so they re-fire correctly on fresh exports.

## What's here

| File | What it is |
|---|---|
| `metrics.py` | Loads + cleans the data, computes all metrics, writes `metrics.json`, renders the dashboard |
| `dashboard.py` | Pure HTML renderer used by `metrics.py` (one standalone file, no deps) |
| `dashboard.html` | Generated — the one-page dashboard |
| `metrics.json` | Generated — all computed numbers |
| `internal_note.md` | Status note for the project lead |
| `lab_update.md` | Short client-facing update |
| `NOTES.md` | Working notes: goal, approach, assumptions, progress log |
| `TASK.md` | The original brief |
| `data/` | The source exports |

No third-party dependencies — standard-library Python 3 only.

## Headline findings

- **343 / 600 accepted** at end of week 4; acceptance rate ~55% and falling.
- The binding constraint is **QA review throughput**, not expert supply.
- Top rejection reasons — loose tests + too easy — are 64% of all rejections and fixable.
- Go lags badly (28% acceptance); those experts joined in week 3.
- Forecast misses 600 at current pace without roughly doubling QA throughput.
