# Project Falcon — working notes

**Role:** Strategic Projects Associate. **Snapshot:** end of week 4 (Mon Nov 2, 2026).
**Goal:** 600 accepted coding RL tasks by Fri Nov 13 (end of week 6). ~2 weeks left.

## Goal (for today)
Give the lead, by EOD, an honest read on: where we stand vs 600, what's going wrong
(with evidence), what to do this week, and whether we'll make it. Plus a short, honest
update for the lab's Friday sync.

## Approach
1. One script (`metrics.py`) reads all 3 files, cleans them, computes metrics → `metrics.json`.
2. Single-file HTML dashboard the lead can scan in 2 min.
3. Internal note (bullets) + lab update (5-6 sentences).

## Data cleaning decisions (messy data handled)
- **Expert IDs:** submissions use mixed case (`e09` vs `E09`). Uppercased to match `experts.csv`.
- **Duplicate task_ids in submissions:** 4 duplicate rows → keep first occurrence (dedup to 718 unique).
- **Empty `hours_spent`:** 6 rows → excluded from hours stats only (task still counts).
- Join qa_results to submissions by `task_id`. Every unique submission has a QA record.
- Week numbering: week 1 = Oct 5–11, etc.
- **Point-in-time cutoff:** this is an end-of-week-4 report, so the snapshot cuts at **Nov 1**.
  The export includes 21 reviews dated Nov 2–3 (week 5, after the snapshot) — those tasks are
  counted as **still pending** as of Nov 2, not accepted/rejected. 2 orphan QA rows
  (T9001/T9002, no submission) are excluded as synthetic. This keeps every view at one instant.

## What "done" looks like
- `python3 metrics.py` rebuilds metrics.json + prints headline numbers.
- Dashboard opens standalone, shows: accepted vs 600, weekly trend, acceptance by
  language/category/reviewer, rejection reasons, pending backlog, forecast.
- Note + lab update are specific, evidence-backed, and honest.

## Headline findings (as of end of week 4, Nov 1 cutoff)
- **331 accepted / 600** (55%) at end of wk 4. 274 rejected, 113 pending (backlog).
- **Acceptance rate ~55%** overall and **falling**; weekly accepted was ~93–94/wk (W1–3)
  then **dropped to 50 in W4** while submissions rose (159→206) → growing pending backlog.
- **Bottleneck is QA throughput, not expert supply.** Experts can produce ~200 tasks/wk
  (772 hrs/wk ÷ 3.8 hr/task); QA has never cleared >102/wk.
- **Top rejection reasons:** tests_too_loose (104) + too_easy (75) = 65% of rejections — both fixable with guidance.
- **Go is weak:** 26% acceptance (vs Python 61%, TS 53%); Go experts only joined wk 3.
- **Slice by actor — problems concentrate in people:** top 3 experts = 29% of rejections,
  top 10 = 49%. E19 (56 subs, 19%) + E07 (49 subs, 33%) = 69 rejections, nearly all
  tests_too_loose (E19 alone = 38 of 104). Go cohort fails on docker_build_failure (infra, not skill).
- **Reviewer spread:** R3 accepts 68% vs R4 32% — calibration worth checking (may be task-mix).
- **Forecast: ~495 accepted by Nov 13 (range 451–535, base 496) — ~100 short of 600** at current pace.

## Open questions / assumptions
- Is there a per-language quota, or just 600 total? Assumed **600 total**, but flagged Go.
- Does the lab re-QA our accepted tasks? If so, the 41 accepted tasks in the 0.70–0.79
  "borderline-easy" band are a re-rejection risk.
- "Due Fri Nov 13" assumed hard. Weeks remaining counted as ~2 (W5 + W6-to-Fri).

## Progress log
- :00 — explored data, found cleaning issues + trend. Writing script.
- ~:20 — metrics.py + dashboard.py running; headline + forecast computed. Flagged that the
  submissions-join excludes 2 QA rows (T9001/T9002) with no submission record — synthetic, so
  dropped. (Superseded by the cutoff revision below; see Headline findings for final numbers.)
- ~:50 — dashboard, internal note, and lab update drafted. Cross-checked numbers against metrics.json.
- revision — pinned the snapshot to a fixed `AS_OF` (Nov 2) and applied an **end-of-week-4 cutoff
  (Nov 1)**: 21 Nov 2–3 reviews now count as pending, orphans dropped. Final point-in-time numbers:
  **331 accepted, 274 rejected, 113 pending; forecast ~495 (451–535).** All deliverables reconciled.
