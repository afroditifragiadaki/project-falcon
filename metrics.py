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
TOO_EASY_LINE = 0.80                 # OBSERVED QA bar: lowest fpr among too_easy rejections is 0.82
# Hypothesised target difficulty band for a good RL task (frontier pass-rate).
# ** UNCONFIRMED — must verify with the lab. ** Industry heuristic is ~0.20–0.40: hard
# enough to leave an RL gradient, not so hard the reward is too sparse to learn from.
# Our QA has been accepting up to ~0.80, so this is the gap to check.
TARGET_BAND = (0.20, 0.40)


def parse_args(argv):
    """Args (any order): an ISO date overrides the snapshot; --diagnose prints the
    health-check report. Returns True if --diagnose was passed."""
    global AS_OF
    diagnose_flag = False
    for a in argv[1:]:
        if a == "--diagnose":
            diagnose_flag = True
        elif a and not a.startswith("-"):
            AS_OF = dt.date.fromisoformat(a)
    return diagnose_flag


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

    # ---- slice by ACTOR: per-expert (problems usually concentrate in a few people) ----
    emeta = {e["expert_id"]: e for e in experts}
    pe = defaultdict(Counter)
    pe_reason = defaultdict(Counter)
    for s in subs:
        pe[s["expert_id"]][s["status"]] += 1
        if s["status"] == "rejected" and s["reason"]:
            pe_reason[s["expert_id"]][s["reason"]] += 1
    by_expert = {}
    for eid, c in pe.items():
        dec = c["accepted"] + c["rejected"]
        top = pe_reason[eid].most_common(1)
        m_ = emeta.get(eid, {})
        by_expert[eid] = {
            "language": m_.get("primary_language"),
            "join_week": int(m_["join_week"]) if m_.get("join_week") else None,
            "submitted": sum(c.values()),
            "accepted": c["accepted"], "rejected": c["rejected"], "pending": c["pending"],
            "acc_rate": round(c["accepted"] / dec, 3) if dec else None,
            "top_reason": (top[0][0] if top else None),
            "top_reason_n": (top[0][1] if top else 0),
        }

    # rejection concentration (Pareto): how few experts own most of the rejections
    total_rej = sum(c["rejected"] for c in pe.values())
    rej_sorted = sorted(((eid, c["rejected"]) for eid, c in pe.items()),
                        key=lambda x: -x[1])

    def share(n):
        # keep 4 dp so a later :.0% format rounds the true value, not a pre-rounded one
        return round(sum(v for _, v in rej_sorted[:n]) / total_rej, 4) if total_rej else None

    # worst high-volume experts (enough decided to be a real signal, not small-sample noise)
    worst = sorted(
        [(eid, d) for eid, d in by_expert.items()
         if (d["accepted"] + d["rejected"]) >= 5 and d["acc_rate"] is not None],
        key=lambda x: (x[1]["acc_rate"], -x[1]["rejected"]))[:8]
    expert_concentration = {
        "n_experts_with_submissions": len(by_expert),
        "total_rejections": total_rej,
        "top3_rejection_share": share(3),
        "top5_rejection_share": share(5),
        "top10_rejection_share": share(10),
        "top_rejectors": [
            {"expert": eid, "rejections": n, "language": by_expert[eid]["language"],
             "acc_rate": by_expert[eid]["acc_rate"],
             "top_reason": by_expert[eid]["top_reason"],
             "top_reason_n": by_expert[eid]["top_reason_n"]}
            for eid, n in rej_sorted[:5]],
        "worst_experts": [
            {"expert": eid, **{k: d[k] for k in
             ("language", "join_week", "submitted", "accepted", "rejected",
              "pending", "acc_rate", "top_reason", "top_reason_n")}}
            for eid, d in worst],
    }

    rejection_reasons = dict(Counter(
        s["reason"] for s in subs if s["status"] == "rejected" and s["reason"]))

    # Can a pre-submission gate catch this reason without a human reviewer?
    #   auto  = fully mechanical (CI build, duplicate hash, frontier pass-rate >= 0.80)
    #   semi  = partly automatable (run reference + a broken solution vs. hidden tests)
    #   human = genuine QA judgment
    PREVENTABILITY = {
        "docker_build_failure": "auto",   # `docker build` succeeds or it doesn't
        "duplicate": "auto",              # hash/similarity vs. accepted corpus
        "too_easy": "auto",               # we already compute frontier_pass_rate; flag >= 0.80
        "tests_too_loose": "semi",        # ref solution must pass AND a broken one must fail
        "unclear_instructions": "human",  # needs a reviewer
    }
    prev = Counter()
    for reason, n in rejection_reasons.items():
        prev[PREVENTABILITY.get(reason, "human")] += n
    rtot = sum(rejection_reasons.values())
    rejection_preventability = {
        "total_rejections": rtot,
        "auto": prev["auto"], "semi": prev["semi"], "human": prev["human"],
        "auto_share": round(prev["auto"] / rtot, 4) if rtot else None,
        "auto_plus_semi_share": round((prev["auto"] + prev["semi"]) / rtot, 4) if rtot else None,
        "auto_share_of_all_qa_decisions": round(prev["auto"] / decided, 4) if decided else None,
        "by_reason": {r: PREVENTABILITY.get(r, "human") for r in rejection_reasons},
    }

    # quality: accepted frontier pass-rate distribution
    acc_fpr = [s["fpr"] for s in subs if s["status"] == "accepted" and s["fpr"] is not None]
    borderline_easy = sum(1 for x in acc_fpr if 0.70 <= x < TOO_EASY_LINE)

    # Difficulty vs. the (hypothesised) target band — are accepted tasks actually hard enough?
    lo, hi = TARGET_BAND
    nfpr = len(acc_fpr)
    hist = Counter(min(int(x * 10), 9) for x in acc_fpr)   # 0.0,0.1,...,0.9 buckets
    difficulty_to_spec = {
        "target_band": [lo, hi],
        "band_is_confirmed": False,            # flip to True once the lab confirms the spec
        "qa_too_easy_line_observed": TOO_EASY_LINE,
        "n_accepted_with_fpr": nfpr,
        "in_band": sum(1 for x in acc_fpr if lo <= x < hi),
        "below_band": sum(1 for x in acc_fpr if x < lo),
        "above_band": sum(1 for x in acc_fpr if x >= hi),
        "above_0.60": sum(1 for x in acc_fpr if x >= 0.60),
        "in_band_share": round(sum(1 for x in acc_fpr if lo <= x < hi) / nfpr, 4) if nfpr else None,
        "above_0.60_share": round(sum(1 for x in acc_fpr if x >= 0.60) / nfpr, 4) if nfpr else None,
        "median": round(statistics.median(acc_fpr), 3) if nfpr else None,
        "histogram_0.1": {round(k * 0.1, 1): hist.get(k, 0) for k in range(10)},
    }

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
        "by_expert": dict(sorted(by_expert.items())),
        "expert_concentration": expert_concentration,
        "rejection_reasons": dict(sorted(rejection_reasons.items(),
                                         key=lambda x: -x[1])),
        "rejection_preventability": rejection_preventability,
        "quality": {
            "accepted_fpr_median": round(statistics.median(acc_fpr), 3),
            "too_easy_line": TOO_EASY_LINE,
            "accepted_borderline_easy_0.70_0.79": borderline_easy,
        },
        "difficulty_to_spec": difficulty_to_spec,
        "capacity": {
            "expert_hours_per_week": cap_hrs,
            "median_hours_per_task": med_hr,
            "max_submittable_per_week": round(max_subs_per_wk),
            "n_experts": len(experts),
        },
        "forecast": forecast,
        "data_quality": clean,
    }


SEV_ORDER = {"CRITICAL": 0, "WARN": 1, "INFO": 2}


def diagnose(m):
    """Run health-check rules over the metrics and return ranked flags.

    Each flag: {severity, code, message, evidence, recommendation}. Rules are
    threshold-driven off the metrics, so they re-fire correctly on fresh data.
    """
    F = []

    def add(sev, code, msg, evidence, rec):
        F.append({"severity": sev, "code": code, "message": msg,
                  "evidence": evidence, "recommendation": rec})

    h, f = m["headline"], m["forecast"]
    ds, ec, rp = m["difficulty_to_spec"], m["expert_concentration"], m["rejection_preventability"]
    br, goal = m["by_reviewer"], m["goal"]
    acc_rate = h["acc_rate"]

    # 1. Forecast vs goal
    if not f["past_due"] and f["base"] < goal:
        add("CRITICAL", "forecast_short",
            f"Forecast ~{f['base']} accepted by {m['due']} — {goal - f['base']} short of {goal}.",
            f"base {f['base']} (range {f['pessimistic']}–{f['optimistic']}); gap {f['gap_to_goal']} in {f['weeks_left']} wks",
            "Bring a recovery plan or renegotiate scope/deadline before the sync.")

    # 2. Difficulty-to-spec (unconfirmed band)
    s = ds.get("in_band_share")
    if s is not None and not ds["band_is_confirmed"] and s < 0.60:
        lo, hi = ds["target_band"]
        add("CRITICAL", "difficulty_spec",
            f"Only {s:.0%} of accepted tasks fall in the {lo:.0%}–{hi:.0%} difficulty band (UNCONFIRMED).",
            f"{ds['in_band']}/{ds['n_accepted_with_fpr']} in band; {ds['above_0.60']} ({ds['above_0.60_share']:.0%}) ≥0.60; QA bar ~{ds['qa_too_easy_line_observed']}",
            "Confirm the target band with the lab, then re-score accepted tasks and re-tune the QA bar.")

    # 3. QA throughput bottleneck
    peak = max(m["accepted_by_review_week"].values()) if m["accepted_by_review_week"] else 0
    need = f.get("needed_accepts_per_week")
    if need and need > peak:
        add("WARN", "qa_bottleneck",
            f"Required pace {need:.0f} accepts/wk exceeds the best week ever ({peak}).",
            f"need ~{f['needed_decided_per_week']:.0f} reviews/wk; experts can supply ~{m['capacity']['max_submittable_per_week']}/wk (not the limit)",
            "Add QA reviewers and/or deploy the pre-submission gate to cut review load.")

    # 4. Rejection concentration (actor)
    if ec["top3_rejection_share"] and ec["top3_rejection_share"] >= 0.25:
        tr = ec["top_rejectors"][:2]
        names = "; ".join(f"{t['expert']} ({t['rejections']} rej, {t['top_reason']})" for t in tr)
        add("WARN", "rejection_concentration",
            f"Top 3 experts own {ec['top3_rejection_share']:.0%} of all rejections.",
            f"worst: {names}",
            "Coach the top offenders directly — higher leverage than a broad memo.")

    # 5. Reviewer calibration spread
    rates = [v["acc_rate"] for v in br.values()]
    if rates and (max(rates) - min(rates)) >= 0.25:
        hi_r = max(br.items(), key=lambda x: x[1]["acc_rate"])
        lo_r = min(br.items(), key=lambda x: x[1]["acc_rate"])
        add("WARN", "reviewer_calibration",
            f"Reviewer acceptance spread is wide: {min(rates):.0%}–{max(rates):.0%}.",
            f"{hi_r[0]} {hi_r[1]['acc_rate']:.0%} ({hi_r[1]['decided']} decided) vs {lo_r[0]} {lo_r[1]['acc_rate']:.0%} ({lo_r[1]['decided']})",
            "Run a calibration sync; spot-check a sample of each reviewer's recent calls.")

    # 6. Auto-preventable QA load
    ap = rp.get("auto_share_of_all_qa_decisions")
    if ap and ap >= 0.15:
        add("WARN", "preventable_load",
            f"{ap:.0%} of QA decisions were spent on auto-preventable rejections.",
            f"{rp['auto']} rejections ({rp['auto_share']:.0%}) catchable pre-review: docker/too_easy/duplicate",
            "Stand up the pre-submission CI gate to reclaim reviewer capacity.")

    # 7. Throughput declining (last complete review week vs prior average)
    aw = m["accepted_by_review_week"]
    ks = sorted(aw, key=lambda x: int(x))
    if len(ks) >= 2:
        last, prior = aw[ks[-1]], sum(aw[k] for k in ks[:-1]) / (len(ks) - 1)
        if last < 0.8 * prior:
            add("WARN", "throughput_declining",
                f"Accepts in the last complete week ({last}) fell below the prior average ({prior:.0f}).",
                f"accepts by review week: {dict((k, aw[k]) for k in ks)}",
                "Usually the review backlog, not fewer submissions — check reviewer load.")

    # 8. Pending backlog
    tot = h["accepted"] + h["rejected"] + h["pending"]
    if tot and h["pending"] / tot >= 0.12:
        add("WARN", "pending_backlog",
            f"{h['pending']} tasks ({h['pending'] / tot:.0%}) are pending/unreviewed.",
            f"accepted {h['accepted']}, rejected {h['rejected']}, pending {h['pending']}",
            f"Triage now — clearing at ~{acc_rate:.0%} yields ~{round(h['pending'] * acc_rate)} accepts.")

    # 9. Weak language
    for lang, v in m["by_language"].items():
        dec = v["accepted"] + v["rejected"]
        if v["acc_rate"] is not None and v["acc_rate"] < 0.40 and dec >= 10:
            add("WARN", "weak_language",
                f"{lang} acceptance is only {v['acc_rate']:.0%} ({v['accepted']}/{dec} decided).",
                f"vs other languages; check the dominant rejection reason for this cohort",
                "Fix the cohort's systemic cause (e.g. a broken Docker template) before blaming skill.")

    # 10. Data-quality hygiene (informational, but worth showing)
    dq = m["data_quality"]
    bits = []
    if dq["dup_submission_rows_dropped"]:
        bits.append(f"{dq['dup_submission_rows_dropped']} duplicate rows dropped")
    if dq.get("reviews_after_cutoff_deferred_to_pending"):
        bits.append(f"{dq['reviews_after_cutoff_deferred_to_pending']} post-cutoff reviews deferred to pending")
    if dq.get("orphan_qa_rows_excluded"):
        bits.append(f"{len(dq['orphan_qa_rows_excluded'])} orphan QA rows excluded")
    if dq["empty_hours_rows"]:
        bits.append(f"{dq['empty_hours_rows']} blank-hours rows")
    if bits:
        add("INFO", "data_quality",
            "Data hygiene applied this run: " + ", ".join(bits) + ".",
            f"cutoff {dq.get('cutoff_date')}; {dq['unique_submissions']} unique submissions",
            "None blocking — kept for auditability.")

    F.sort(key=lambda x: SEV_ORDER[x["severity"]])
    return F


def print_diagnostics(m):
    d = m["diagnostics"]
    counts = Counter(x["severity"] for x in d)
    print(f"Project Falcon — diagnostics  (as of {m['as_of']}, data through {m['data_through']})")
    print(f"  {counts.get('CRITICAL', 0)} critical · {counts.get('WARN', 0)} warning · "
          f"{counts.get('INFO', 0)} info")
    print(f"  snapshot: {m['headline']['accepted']}/{m['goal']} accepted, "
          f"forecast {m['forecast']['base']}\n")
    for x in d:
        print(f"[{x['severity']:8}] {x['message']}")
        print(f"            evidence: {x['evidence']}")
        print(f"            → {x['recommendation']}\n")


def main(argv=None):
    diagnose_flag = parse_args(argv or sys.argv)
    experts, subs, qa_list, clean = load()
    m = compute(experts, subs, qa_list, clean)
    m["diagnostics"] = diagnose(m)
    (ROOT / "metrics.json").write_text(json.dumps(m, indent=2))

    if diagnose_flag:
        print_diagnostics(m)
        return

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
