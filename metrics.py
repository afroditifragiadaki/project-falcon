#!/usr/bin/env python3
"""Project Falcon health metrics.

Reads data/{experts.csv, submissions.csv, qa_results.json}, cleans the messy bits,
computes project metrics, and writes metrics.json. It also renders dashboard.html.

Run:  python3 metrics.py
"""
import csv, json, statistics, sys, datetime as dt
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "data"

GOAL = 600
DUE = dt.date(2026, 11, 13)          # Friday — the fixed project deadline
WEEK1_MON = dt.date(2026, 10, 5)     # project week 1 starts here
# A status report is a point-in-time artifact: pin the snapshot so the numbers are
# reproducible and identical across every deliverable. Override for a later cut with
#   python3 metrics.py 2026-11-09
AS_OF = dt.date(2026, 11, 2)         # end of week 4 (the brief's reporting date)
TOO_EASY_LINE = 0.80                 # inferred from too_easy rejections (min fpr 0.82)


def parse_args(argv):
    """Optional first arg overrides the snapshot date (ISO, e.g. 2026-11-09)."""
    global AS_OF
    if len(argv) > 1 and argv[1]:
        AS_OF = dt.date.fromisoformat(argv[1])


def snapshot():
    """Return (as_of_week, cutoff_date).

    A status report is a point-in-time artifact: it reflects everything through the
    end of the last fully-completed project week as of AS_OF, and *nothing after*.
    For AS_OF = Mon Nov 2 the last complete week is week 4, which ends Sun Nov 1, so
    the cutoff is Nov 1 — week-5 submissions/reviews in the export are excluded.
    """
    as_of_week = week_of((AS_OF - dt.timedelta(days=1)).isoformat())
    cutoff = WEEK1_MON + dt.timedelta(days=as_of_week * 7 - 1)
    return as_of_week, cutoff


def week_of(d: str):
    if not d:
        return None
    return (dt.date.fromisoformat(d) - WEEK1_MON).days // 7 + 1


# ---------------------------------------------------------------- load + clean
def load():
    experts = list(csv.DictReader(open(DATA / "experts.csv")))
    expert_ids = {e["expert_id"].upper() for e in experts}

    raw = list(csv.DictReader(open(DATA / "submissions.csv")))
    _, cutoff = snapshot()
    cutoff_iso = cutoff.isoformat()

    seen, subs = set(), []
    dup = subs_after_cutoff = 0
    for s in raw:
        s["expert_id"] = s["expert_id"].strip().upper()   # fix mixed-case ids
        tid = s["task_id"]
        if tid in seen:                                    # drop duplicate task rows
            dup += 1
            continue
        if s["submitted_at"] > cutoff_iso:                 # not yet submitted at snapshot
            subs_after_cutoff += 1
            continue
        seen.add(tid)
        try:
            s["hours_spent"] = float(s["hours_spent"]) if s["hours_spent"] else None
        except ValueError:
            s["hours_spent"] = None
        s["week"] = week_of(s["submitted_at"])
        subs.append(s)

    qa_list = json.load(open(DATA / "qa_results.json"))
    qa = {r["task_id"]: r for r in qa_list}

    reviews_after_cutoff = 0
    for s in subs:                                         # join QA onto submissions
        r = qa.get(s["task_id"], {})
        rdate = r.get("reviewed_at")
        if rdate and rdate > cutoff_iso:
            # Reviewed only after the snapshot → as of the report it is still pending.
            reviews_after_cutoff += 1
            s["status"] = "pending"
            s["fpr"] = s["reason"] = s["reviewer"] = s["reviewed_at"] = None
        else:
            s["status"] = r.get("status", "no_qa")
            s["fpr"] = r.get("frontier_pass_rate")
            s["reason"] = r.get("rejection_reason")
            s["reviewer"] = r.get("reviewer_id")
            s["reviewed_at"] = rdate

    # Effective QA view for throughput/reviewer stats: only decisions made by the
    # cutoff, and only for tasks that actually exist in the submission set (drops
    # the two synthetic orphan rows T9001/T9002), so every view agrees with the headline.
    sub_ids = {s["task_id"] for s in subs}
    qa_eff = [r for r in qa_list
              if r["task_id"] in sub_ids
              and not (r.get("reviewed_at") and r["reviewed_at"] > cutoff_iso)]

    clean = {
        "dup_submission_rows_dropped": dup,
        "expert_ids_case_fixed": sum(1 for s in raw if s["expert_id"] != s["expert_id"].upper()),
        "empty_hours_rows": sum(1 for s in subs if s["hours_spent"] is None),
        "unique_submissions": len(subs),
        "submissions_without_qa": sum(1 for s in subs if s["status"] == "no_qa"),
        "expert_ids_not_in_roster": sorted(
            {s["expert_id"] for s in subs} - expert_ids),
        "cutoff_date": cutoff_iso,
        "submissions_after_cutoff_excluded": subs_after_cutoff,
        "reviews_after_cutoff_deferred_to_pending": reviews_after_cutoff,
        "orphan_qa_rows_excluded": sorted(
            {r["task_id"] for r in qa_list} - sub_ids),
    }
    return experts, subs, qa_eff, clean


# ---------------------------------------------------------------- metrics
def compute(experts, subs, qa_list, clean):
    status = Counter(s["status"] for s in subs)
    accepted = status["accepted"]
    rejected = status["rejected"]
    pending = status["pending"]
    decided = accepted + rejected
    acc_rate = accepted / decided if decided else 0

    # weekly trend by SUBMISSION week
    byweek = defaultdict(Counter)
    for s in subs:
        byweek[s["week"]][s["status"]] += 1
    weekly = []
    for w in sorted(k for k in byweek if k):
        c = byweek[w]
        tot = sum(c.values())
        weekly.append({"week": w, "submitted": tot, "accepted": c["accepted"],
                       "rejected": c["rejected"], "pending": c["pending"]})

    # accepted by REVIEW week (throughput)
    acc_by_review_wk = Counter()
    dec_by_review_wk = Counter()
    for r in qa_list:
        if r["status"] in ("accepted", "rejected") and r.get("reviewed_at"):
            dec_by_review_wk[week_of(r["reviewed_at"])] += 1
            if r["status"] == "accepted":
                acc_by_review_wk[week_of(r["reviewed_at"])] += 1

    def rate_table(key):
        d = defaultdict(Counter)
        for s in subs:
            d[s[key]][s["status"]] += 1
        out = {}
        for k, c in d.items():
            dec = c["accepted"] + c["rejected"]
            out[k] = {"accepted": c["accepted"], "rejected": c["rejected"],
                      "pending": c["pending"],
                      "acc_rate": round(c["accepted"] / dec, 3) if dec else None}
        return out

    by_language = rate_table("language")
    by_category = rate_table("category")

    # reviewer leniency
    by_reviewer = {}
    revd = defaultdict(Counter)
    for r in qa_list:
        if r["status"] in ("accepted", "rejected"):
            revd[r["reviewer_id"]][r["status"]] += 1
    for rv, c in revd.items():
        dec = c["accepted"] + c["rejected"]
        by_reviewer[rv] = {"accepted": c["accepted"], "decided": dec,
                           "acc_rate": round(c["accepted"] / dec, 3)}

    rejection_reasons = dict(Counter(
        s["reason"] for s in subs if s["status"] == "rejected" and s["reason"]))

    # quality: accepted frontier pass-rate distribution
    acc_fpr = [s["fpr"] for s in subs if s["status"] == "accepted" and s["fpr"] is not None]
    borderline_easy = sum(1 for x in acc_fpr if 0.70 <= x < TOO_EASY_LINE)

    # capacity
    cap_hrs = sum(int(e["hours_per_week"]) for e in experts)
    hrs = [s["hours_spent"] for s in subs if s["hours_spent"] is not None]
    med_hr = statistics.median(hrs)
    max_subs_per_wk = cap_hrs / med_hr

    # ---- snapshot: a FIXED point in time (AS_OF), not the wall clock ----
    # "as-of week" = the last fully-completed project week as of the snapshot
    # (the day before AS_OF), so a Monday report reflects through the prior week.
    as_of_week = week_of((AS_OF - dt.timedelta(days=1)).isoformat())
    all_dates = ([s["submitted_at"] for s in subs if s["submitted_at"]]
                 + [r["reviewed_at"] for r in qa_list if r.get("reviewed_at")])
    data_through = max(all_dates) if all_dates else AS_OF.isoformat()
    due_week = week_of(DUE.isoformat())
    weeks_left = max(due_week - as_of_week, 0)   # remaining project weeks (e.g. W5–W6 = 2)
    days_left = (DUE - AS_OF).days
    wl = weeks_left
    past_due = weeks_left <= 0

    # ---- forecast ----
    # Run-rate from COMPLETE review weeks only (exclude the partial current week).
    review_weeks = sorted(acc_by_review_wk)
    complete = [w for w in review_weeks if w <= as_of_week] or review_weeks
    rates = [acc_by_review_wk[w] for w in complete]
    base_rate = statistics.mean(rates)
    last_rate = rates[-1]                   # most recent complete week
    best_rate = max(rates)
    forecast = {
        "accepted_now": accepted,
        "gap_to_goal": GOAL - accepted,
        "weeks_left": weeks_left,
        "past_due": past_due,
        "needed_accepts_per_week":
            None if past_due else round((GOAL - accepted) / weeks_left, 1),
        "needed_decided_per_week":
            None if past_due or not acc_rate
            else round((GOAL - accepted) / weeks_left / acc_rate, 1),
        "pace_basis_weeks": complete,
        "pessimistic": round(accepted + last_rate * wl),    # most recent week's pace
        "base": round(accepted + base_rate * wl),           # average pace
        "optimistic": round(accepted + best_rate * wl),     # best week's pace
        "peak_decided_week": max(dec_by_review_wk.values()),
    }

    return {
        "as_of": AS_OF.isoformat(),           # fixed snapshot date this report reflects
        "as_of_week": as_of_week,             # last completed project week at the snapshot
        "data_through": data_through,         # latest date present in the data
        "weeks_left": weeks_left,
        "goal": GOAL,
        "due": DUE.isoformat(),
        "headline": {
            "accepted": accepted, "rejected": rejected, "pending": pending,
            "decided": decided, "acc_rate": round(acc_rate, 3),
            "pct_to_goal": round(accepted / GOAL, 3),
        },
        "weekly_by_submission": weekly,
        "accepted_by_review_week": dict(sorted(acc_by_review_wk.items())),
        "decided_by_review_week": dict(sorted(dec_by_review_wk.items())),
        "by_language": by_language,
        "by_category": by_category,
        "by_reviewer": dict(sorted(by_reviewer.items())),
        "rejection_reasons": dict(sorted(rejection_reasons.items(),
                                         key=lambda x: -x[1])),
        "quality": {
            "accepted_fpr_median": round(statistics.median(acc_fpr), 3),
            "too_easy_line": TOO_EASY_LINE,
            "accepted_borderline_easy_0.70_0.79": borderline_easy,
        },
        "capacity": {
            "expert_hours_per_week": cap_hrs,
            "median_hours_per_task": med_hr,
            "max_submittable_per_week": round(max_subs_per_wk),
            "n_experts": len(experts),
        },
        "forecast": forecast,
        "data_quality": clean,
    }


def main(argv=None):
    parse_args(argv or sys.argv)
    experts, subs, qa_list, clean = load()
    m = compute(experts, subs, qa_list, clean)
    (ROOT / "metrics.json").write_text(json.dumps(m, indent=2))

    h, f = m["headline"], m["forecast"]
    need = ("DEADLINE PASSED" if f["past_due"]
            else f"Need {f['needed_accepts_per_week']:.0f} accepts/wk for "
                 f"{f['weeks_left']} wks")
    print("Project Falcon — metrics rebuilt  (metrics.json written)")
    print(f"  As of {m['as_of']} (end of week {m['as_of_week']}, data through "
          f"{m['data_through']}) · due {m['due']}")
    print(f"  Accepted {h['accepted']}/{m['goal']}  ({h['pct_to_goal']:.0%})   "
          f"rejected {h['rejected']}  pending {h['pending']}")
    print(f"  Acceptance rate: {h['acc_rate']:.0%}")
    print(f"  {need}; best week ever was "
          f"{max(m['accepted_by_review_week'].values())}.")
    print(f"  Forecast by {m['due']}: {f['pessimistic']}-{f['optimistic']} "
          f"accepted  (base {f['base']}) vs goal {m['goal']}")

    render_dashboard(m)
    print("  dashboard.html written")


# ---------------------------------------------------------------- dashboard
def render_dashboard(m):
    from dashboard import build_html   # local module
    (ROOT / "dashboard.html").write_text(build_html(m))


if __name__ == "__main__":
    main()
