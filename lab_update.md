# Lab update — Project Falcon (for Friday's sync)

At the end of week 4 we have **331 accepted tasks toward the 600 target (55%)**, with
274 rejected and 113 currently in review. Our acceptance rate is holding around 55%, and
task quality is solid — accepted tasks sit well inside the difficulty bar (median frontier
pass rate ~0.41). The main constraint we've hit is **QA review throughput**: expert output
has scaled faster than our review capacity, which created a review backlog in week 4 that
we're now clearing first. To protect quality and speed, this week we're adding review
capacity, tightening reviewer calibration, and standing up an **automated pre-submission
gate** (Docker build, reference-solution-vs-hidden-tests, and difficulty check) that will
catch roughly half of today's rejection causes before they consume a reviewer. **Our
honest projection is roughly 480–500 accepted by November 13** — short of 600 at the current
pace — so we'd like to use Friday to align on either a brief extension or a prioritized subset
of the remaining tasks, and we'll bring a concrete recovery plan with updated numbers.
