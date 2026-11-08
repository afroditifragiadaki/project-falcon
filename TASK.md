# Project Falcon: project health check

**Today is Monday, November 2, 2026.** You are the Strategic Projects Associate on
Project Falcon. Your lead is out today and wants a clear picture by end of day.

## Context

A frontier AI lab ordered **600 accepted coding RL tasks** (real repos in Python,
TypeScript and Go; each task has a Docker environment, hidden tests and a reference
solution). Delivery is due **Friday, November 13** (end of week 6). We are at the end
of **week 4**.

Experts build and submit tasks. Our QA reviewers accept or reject each one. Only
accepted tasks count toward the 600. The lab has a sync with us on Friday and will
ask how the project is going.

## Data (in `data/`)

| File | What it holds |
|---|---|
| `experts.csv` | `expert_id`, `primary_language`, `join_week`, `hours_per_week` |
| `submissions.csv` | one row per submitted task: `task_id`, `expert_id`, `language`, `category`, `submitted_at`, `hours_spent` |
| `qa_results.json` | one record per reviewed task: `task_id`, `status` (accepted / rejected / pending), `rejection_reason`, `reviewer_id`, `frontier_pass_rate`, `reviewed_at` |

Week 1 started on Monday, October 5. The data is an export from our tools and may
not be perfectly clean.

## Deliverables (timebox: 75 minutes)

1. **A script** that reads all three files and computes the project's metrics.
   Running one command should rebuild everything.
2. **A one-page dashboard** (a single HTML file is fine) your lead can scan in
   two minutes: where we stand, what's going wrong, and whether we'll hit 600.
3. **An internal note to your lead** (5 to 8 bullets): status, the main problems
   with the evidence for each, what you'd do this week, and your forecast.
4. **A short update for the lab** (5 or 6 sentences) for Friday's sync.

## How you'll be judged

- **Visible structure:** before you start, write your goal, approach, what "done"
  looks like, and open questions in `NOTES.md`. Add a one-line progress update at
  roughly 20 and 50 minutes.
- **Correctness:** are the numbers right, and did you handle the messy data?
- **Insight:** did you find *why* things are going wrong, with evidence, not just
  *what* the numbers are?
- **Judgment:** are the actions specific, and is the client update honest and
  constructive?
- **Ownership:** you decide what matters most. Note any assumptions you made.
