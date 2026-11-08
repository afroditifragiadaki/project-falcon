# Internal note — Project Falcon status (end of week 4, Nov 2)

**TL;DR: we're off track for 600 by Nov 13.** Honest forecast ~500–520 accepted
(~15% short). The binding constraint is **QA review throughput**, not expert supply.
Below is where we stand, why, and what I'd do this week.

- **Where we stand:** **343 accepted / 600 (57%)**, 283 rejected, **92 pending (unreviewed)**.
  Overall acceptance rate **55%** — and falling. Weekly accepted held ~93–94 in weeks 1–3,
  then **dropped to 62 in week 4** even though submissions rose (159 → 206). *Evidence:
  `metrics.json` → `weekly_by_submission`, `accepted_by_review_week`.*

- **The real bottleneck is QA, not experts.** Experts can produce ~**200 tasks/week**
  (772 expert-hrs ÷ 3.8 hrs/task); QA has **never cleared more than 103 accepts in a week**
  and only 60 in week 4. That's why the pending pile jumped to 92. To hit 600 we'd need
  **128 accepts/week** (~233 reviews/wk) for two weeks — more than double our best week ever.
  *Evidence: `capacity` + `forecast` in `metrics.json`.*

- **Rejections are concentrated and fixable.** Of 283 rejections, **tests_too_loose (105)
  and too_easy (77) are 64%**, then docker_build_failure (51) and unclear_instructions (37).
  The top two are process problems — experts aren't making tests tight/hard enough — not
  talent problems. A pre-submission checklist + 2–3 worked examples should lift acceptance.

- **Go is the weakest language: 28% acceptance** (vs Python 61%, TypeScript 53%). The Go
  experts only joined in **week 3**, so they're still climbing the curve on our bar. If the
  lab expects language balance, Go is the risk; if not, it's a drag on overall rate.

- **Category signal:** features (43%) and refactors (49%) reject far more than
  dependency_upgrades (68%) and bug_fixes (58%). We can steer capacity toward categories that
  pass more reliably without hurting task quality.

- **QA calibration gap:** reviewer acceptance ranges from **R3 68% to R4 33%**. That spread
  may partly reflect task mix (e.g., who gets the Go/feature tasks), but it's wide enough to
  warrant a 30-min calibration sync and spot-checking a sample of each reviewer's decisions.

- **A quality caveat to watch:** 42 accepted tasks sit in the 0.70–0.79 frontier-pass band
  (borderline-easy; the "too easy" rejection line is ~0.80). They're inside our current bar,
  but if the lab re-QAs on their side, that's the band most at risk of re-rejection.

- **What I'd do this week (in priority order):**
  1. **Add QA capacity / triage the 92 pending first** — throughput is the gate. Clearing the
     backlog at 55% yields ~50 accepts almost immediately.
  2. **Ship a "tests tight + hard enough" checklist** and 2–3 exemplar tasks to all experts;
     target the two reasons that cause 64% of rejections.
  3. **Run a reviewer calibration sync** and standardize the too-easy/loose-tests thresholds.
  4. **Reallocate effort** toward higher-yield categories and pair-support the Go cohort.

- **Forecast:** at current pace **~500–520 accepted by Nov 13** (range 463 pessimistic →
  524 optimistic). **We will likely miss 600 by ~80–100** unless QA throughput roughly doubles
  and holds. Recommend we go into Friday's sync with a realistic number and a concrete recovery
  plan rather than a promise we can't keep.

*Assumptions: goal is 600 total (no per-language quota); ~2 weeks remain (W5 + W6 to Fri Nov 13);
2 QA rows with no submission (T9001/T9002) excluded as synthetic. Rebuild all numbers:
`python3 metrics.py`.*
