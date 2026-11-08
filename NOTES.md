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
- Week numbering: week 1 = Oct 5–11, etc. A few reviews dated Nov 3 (just past snapshot) kept as-is.

## What "done" looks like
- `python3 metrics.py` rebuilds metrics.json + prints headline numbers.
- Dashboard opens standalone, shows: accepted vs 600, weekly trend, acceptance by
  language/category/reviewer, rejection reasons, pending backlog, forecast.
- Note + lab update are specific, evidence-backed, and honest.

## Headline findings (from exploration)
- **344 accepted / 600** (57%) at end of wk 4. 284 rejected, 92 pending (backlog).
- **Acceptance rate ~55%** overall and **falling**; weekly accepted was ~93/wk (W1–3)
  then **dropped to 62 in W4** while submissions rose (159→206) → growing pending backlog.
- **Bottleneck is QA throughput, not expert supply.** Experts can produce ~200 tasks/wk
  (772 hrs/wk ÷ 3.8 hr/task); QA has never cleared >~100/wk.
- **Top rejection reasons:** tests_too_loose (105) + too_easy (77) = 64% of rejections — both fixable with guidance.
- **Go is weak:** 28% acceptance (vs Python 61%, TS 53%); Go experts only joined wk 3.
- **Reviewer spread:** R3 accepts 68% vs R4 33% — calibration worth checking (may be task-mix).
- **Forecast: ~500–520 accepted by Nov 13 — ~80–100 short of 600** at current pace.

## Open questions / assumptions
- Is there a per-language quota, or just 600 total? Assumed **600 total**, but flagged Go.
- Does the lab re-QA our accepted tasks? If so, the 42 accepted tasks in the 0.70–0.79
  "borderline-easy" band are a re-rejection risk.
- "Due Fri Nov 13" assumed hard. Weeks remaining counted as ~2 (W5 + W6-to-Fri).

## Progress log
- :00 — explored data, found cleaning issues + trend. Writing script.
- ~:20 — metrics.py + dashboard.py running; 343 accepted/600, forecast ~463–524. Note the
  submissions-join gives 343 accepted vs 344 raw in QA: 2 QA rows (T9001/T9002) have no
  submission record and look synthetic → excluded (a deliverable needs a real submitted task).
- ~:50 — dashboard, internal note, and lab update drafted. Cross-checked numbers against metrics.json.
