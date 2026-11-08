# Internal note — Project Falcon status (end of week 4, Nov 2)

**TL;DR: we're off track for 600 by Nov 13.** Honest forecast ~495 accepted
(~17% short). The binding constraint is **QA review throughput**, not expert supply.
**One thing to resolve before Friday:** if the lab's difficulty spec is ~20–40% frontier
pass-rate, only ~30% of our accepted tasks qualify — a bigger risk than the count itself.
Below is where we stand, why, and what I'd do this week.

- **Where we stand:** **331 accepted / 600 (55%)**, 274 rejected, **113 pending (unreviewed)**.
  Overall acceptance rate **~55%** — and falling. Weekly accepted held ~93–94 in weeks 1–3,
  then **dropped to 50 in week 4** even though submissions rose (159 → 206). *Evidence:
  `metrics.json` → `weekly_by_submission`, `accepted_by_review_week`.*

- **The real bottleneck is QA, not experts.** Experts can produce ~**200 tasks/week**
  (772 expert-hrs ÷ 3.8 hrs/task); QA has **never cleared more than 102 accepts in a week**
  and only 60 in week 4. That's why the pending pile grew to 113. To hit 600 we'd need
  **~135 accepts/week** (~246 reviews/wk) for two weeks — more than double our best week ever.
  *Evidence: `capacity` + `forecast` in `metrics.json`.*

- **Rejections are concentrated and fixable.** Of 274 rejections, **tests_too_loose (104)
  and too_easy (75) are 65%**, then docker_build_failure (47) and unclear_instructions (36).
  The top two are process problems — experts aren't making tests tight/hard enough — not
  talent problems.

- **The problem concentrates in a few people — slice by actor, not just category.** The top
  3 experts own **29%** of all rejections; the top 10 own **49%**. Two high-volume experts
  are the single biggest drag: **E19** (TypeScript) submitted 56 tasks at **19% accept** —
  **38 of them rejected `tests_too_loose`, which is 37% of that entire failure mode by itself** —
  and **E07** (Python) is 49 tasks at **33%**, 24 of them `tests_too_loose`. **E19 + E07 alone =
  69 rejections (25% of all).** Targeted coaching of 2 people has more leverage than any
  broad memo. *Evidence: `metrics.json` → `expert_concentration`, `by_expert`.*

- **Go is an infrastructure problem, not a talent problem: 26% acceptance** (vs Python 61%,
  TypeScript 53%). The Go cohort joined in **week 3**, but their rejections are dominated by
  **`docker_build_failure`** (e.g. E32 6/6, E33 4/6) — three Go experts are at **0% accept**.
  That's a broken Go Docker template/toolchain, fixable once for the whole cohort, not 10
  people who can't code.

- **We have no pre-submission gate — and ~half of rejections don't need a human.** Classifying
  rejections by *who can catch them*: **49% are fully machine-checkable** before a reviewer ever
  looks (docker_build_failure 47 — a `docker build` that just doesn't compile; too_easy 75 — we
  already compute frontier_pass_rate, so flag ≥0.80; duplicate 12). Those 134 tasks are **22% of
  all 605 QA decisions** — reviewer time spent rejecting things a CI check would bounce instantly.
  A pre-submission harness (build + run reference solution vs. hidden tests + frontier pass-rate +
  dup check) would keep them out of the queue, **directly relieving the QA bottleneck** and giving
  experts feedback in minutes instead of days. This is the single highest-leverage fix because it
  hits the binding constraint. *Evidence: `metrics.json` → `rejection_preventability`.*

- **Slice the reviewers too:** acceptance ranges from **R3 68% to R4 32%** on similar volumes
  (168 vs 102 decided). That spread may partly reflect task mix (who gets Go/feature tasks), but
  it's wide enough to warrant a 30-min calibration sync and spot-checking each reviewer's calls —
  a mis-calibrated reviewer silently inflates or deflates our accepted count. (Category is a
  weaker lens here: features 41% / refactors 50% vs dependency_upgrades 68%, but the people cut
  above explains far more of the variance.)

- **⚠️ Possible difficulty-spec mismatch — our biggest hidden risk.** A good RL task needs a
  frontier pass-rate in a target band (industry heuristic ~**20–40%**: hard enough to leave a
  learning gradient, not so hard the reward is too sparse). **Our QA has been accepting up to
  ~0.80** (the lowest fpr among `too_easy` rejections is 0.82), and **never rejects for being too
  easy below that or too hard at all.** Result: only **98 of 331 accepted tasks (30%) fall in
  20–40%**, and **87 (26%) are above 0.60** — likely too easy under a strict spec. If the lab
  applies a 20–40% bar on their side, a large slice of our "accepted" count is at risk of
  re-rejection, so true progress may be well below 331. **This could matter more than throughput.**
  *I have not confirmed the target band — see open questions. Evidence: `difficulty_to_spec`.*

- **What I'd do this week (in priority order):**
  1. **Stand up a pre-submission CI gate** — `docker build` + run the reference solution against
     the hidden tests + frontier pass-rate check (flag ≥0.80) + duplicate check. Bounces ~49% of
     today's rejection causes before they reach a reviewer, freeing ~22% of QA capacity (the
     bottleneck), and fixes the Go `docker_build_failure` problem as a side effect.
  2. **Confirm the difficulty spec with the lab (today).** If it's ~20–40% pass-rate, re-score the
     331 accepted against it, re-tune the QA bar, and stop shipping ≥0.60 tasks — this could reset
     our real number and must not wait until Friday.
  3. **Triage the 113 pending now** — clearing the backlog at ~55% yields ~62 accepts immediately.
  4. **Coach E19 and E07 directly** on tightening tests (a 30-min session + 2 exemplars). Lifting
     these two toward the ~55% average reclaims ~35–40 tasks — more than any blanket memo.
  5. **Run a reviewer calibration sync** (R3 68% vs R4 32%) and ship a "tests tight + hard enough"
     checklist to everyone to stop the loose-tests bleed the gate can't fully catch.

- **Forecast:** at current pace **~495 accepted by Nov 13** — base case 496, range **451
  (hold week-4's slow pace) → 535 (match our best week)**. **We will likely miss 600 by ~100**
  unless QA throughput roughly doubles and holds. Recommend we go into Friday's sync with a
  realistic number and a concrete recovery plan rather than a promise we can't keep.

*Assumptions / open questions: **the 20–40% difficulty band is unconfirmed — confirm with the lab
first** (it drives the quality risk above); goal is 600 total (no per-language quota); ~2 weeks
remain (W5 + W6 to Fri Nov 13).
This is a point-in-time snapshot through **end of week 4 (Nov 1)**: 21 tasks the export shows as
reviewed on Nov 2–3 are counted as still pending as of the snapshot, and 2 QA rows with no
submission (T9001/T9002) are excluded as synthetic. Rebuild all numbers: `python3 metrics.py`.*
