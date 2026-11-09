"""Renders dashboard.html from the metrics dict produced by metrics.py.

Kept separate so metrics.py stays about numbers and this stays about layout.
Pure string templating — no third-party deps, output is one standalone HTML file.
"""


def _bar_rows(rows, label_key, val_key, rate=True, color="var(--series-1)"):
    """Horizontal bars for a dict of {label: {...}} acceptance-rate table."""
    out = []
    mx = max((v[val_key] or 0) for v in rows.values()) or 1
    # sort by rate ascending so worst performers surface at top
    for k, v in sorted(rows.items(), key=lambda x: (x[1].get("acc_rate") or 0)):
        pct = (v["acc_rate"] or 0)
        w = round(pct / mx * 100) if rate else round((v[val_key] or 0) / mx * 100)
        n = v.get("accepted", 0) + v.get("rejected", 0)
        tone = ("good" if pct >= 0.6 else "warning" if pct >= 0.45 else "critical")
        out.append(f"""
        <div class="row">
          <div class="row-label">{k}</div>
          <div class="track"><div class="fill t-{tone}" style="width:{w}%"></div></div>
          <div class="row-val">{pct:.0%}<span class="muted"> · {n} decided</span></div>
        </div>""")
    return "".join(out)


def build_html(m):
    h = m["headline"]
    f = m["forecast"]
    q = m["quality"]
    cap = m["capacity"]
    dq = m["data_quality"]

    acc, rej, pen = h["accepted"], h["rejected"], h["pending"]
    pct_goal = acc / m["goal"]

    # funnel bar widths (share of goal)
    g = m["goal"]
    acc_w, pen_w = acc / g * 100, pen / g * 100

    # ---- dynamic forecast/verdict strings ----
    on_track = f["base"] >= g
    verdict_tone = "good" if on_track else "critical"
    if f["past_due"]:
        verdict = (f"Deadline ({m['due']}) reached — {acc} accepted, "
                   f"{'target met' if acc >= g else f'{g - acc} short of {g}'}.")
    elif on_track:
        verdict = (f"On track — forecast ~{f['base']} accepted by {m['due']}, "
                   f"at or above the {g} target.")
    else:
        verdict = (f"Off track — forecast ~{f['base']} accepted by {m['due']}, "
                   f"about {g - f['base']} short of {g}.")
    need_txt = ("—" if f["needed_accepts_per_week"] is None
                else f"{f['needed_accepts_per_week']:.0f}/wk")
    wks = f["weeks_left"]
    pace_weeks = f["pace_basis_weeks"]
    pace_lbl = (f"weeks {pace_weeks[0]}–{pace_weeks[-1]}"
                if len(pace_weeks) > 1 else f"week {pace_weeks[0]}")
    if f["past_due"]:
        need_phrase = f"The deadline ({m['due']}) has passed."
    else:
        need_phrase = (f"Gap to goal: <b>{f['gap_to_goal']}</b> accepts in "
                       f"<b>{wks} weeks</b> = <b>{need_txt}</b> "
                       f"(≈{f['needed_decided_per_week']:.0f} reviews/wk at today's "
                       f"{h['acc_rate']:.0%} rate).")
    best = f["optimistic"]
    if best < g:
        closing = (f"All three land below {g}. Hitting {g} needs QA throughput to "
                   f"roughly <b>double</b> and hold for the remaining {wks} weeks.")
    elif f["base"] < g <= best:
        closing = (f"Only the optimistic case clears {g}; the base case is "
                   f"<b>{g - f['base']}</b> short, so {g} is at risk without more QA throughput.")
    else:
        closing = f"The base case clears {g} — stay the course and protect quality."

    # weekly trend (submission week) — stacked mini bars
    wk = m["weekly_by_submission"]
    wkmax = max(w["submitted"] for w in wk)
    weekly_html = ""
    for w in wk:
        a = w["accepted"] / wkmax * 100
        r = w["rejected"] / wkmax * 100
        p = w["pending"] / wkmax * 100
        weekly_html += f"""
        <div class="wkcol">
          <div class="wkbar">
            <div class="seg t-good" style="height:{a}%" title="accepted {w['accepted']}"></div>
            <div class="seg t-critical" style="height:{r}%" title="rejected {w['rejected']}"></div>
            <div class="seg t-pending" style="height:{p}%" title="pending {w['pending']}"></div>
          </div>
          <div class="wklab">W{w['week']}<br><span class="muted">{w['submitted']}</span></div>
        </div>"""

    # accepted throughput by review week
    thr = m["accepted_by_review_week"]
    thrmax = max(thr.values())
    thr_html = ""
    for wk_, v in thr.items():
        hh = v / thrmax * 100
        faint = " faint" if wk_ > m["as_of_week"] else ""  # weeks after the snapshot = partial
        thr_html += f"""
        <div class="wkcol">
          <div class="wkbar"><div class="seg t-accent{faint}" style="height:{hh}%" title="{v}"></div></div>
          <div class="wklab">W{wk_}<br><span class="muted">{v}</span></div>
        </div>"""

    # rejection reasons (tagged by whether a pre-submission gate could catch them)
    rr = m["rejection_reasons"]
    rrtot = sum(rr.values())
    rrmax = max(rr.values())
    prev = m["rejection_preventability"]
    tagmap = prev["by_reason"]
    taglabel = {"auto": "auto-catchable", "semi": "semi-auto", "human": "needs QA"}
    rr_html = ""
    for reason, n in rr.items():
        w = n / rrmax * 100
        tag = tagmap.get(reason, "human")
        rr_html += f"""
        <div class="row">
          <div class="row-label">{reason.replace('_',' ')} <span class="tag tag-{tag}">{taglabel[tag]}</span></div>
          <div class="track"><div class="fill t-reason" style="width:{w}%"></div></div>
          <div class="row-val">{n}<span class="muted"> · {n/rrtot:.0%}</span></div>
        </div>"""

    lang_html = _bar_rows(m["by_language"], "lang", "accepted")
    cat_html = _bar_rows(m["by_category"], "cat", "accepted")
    rev_rows = {k: {"acc_rate": v["acc_rate"], "accepted": v["accepted"],
                    "rejected": v["decided"] - v["accepted"]}
                for k, v in m["by_reviewer"].items()}
    rev_html = _bar_rows(rev_rows, "rev", "accepted")

    # difficulty vs. target band — histogram of accepted tasks' frontier pass-rate
    ds = m["difficulty_to_spec"]
    lo, hi = ds["target_band"]
    dh = ds["histogram_0.1"]
    dmax = max(dh.values()) or 1
    diff_html = ""
    for k in sorted(dh, key=float):
        kf = float(k)
        n = dh[k]
        ht = n / dmax * 100
        inband = lo <= kf < hi
        seg = "t-good" if inband else ("t-reason" if kf >= 0.60 else "t-pending")
        diff_html += f"""
        <div class="wkcol">
          <div class="wkbar"><div class="seg {seg}" style="height:{ht}%" title="{n} tasks at {k}-{round(kf+0.1,1)}"></div></div>
          <div class="wklab">{k}<br><span class="muted">{n}</span></div>
        </div>"""

    # worst experts (by actor) — the real concentration of the problem
    ec = m["expert_concentration"]
    we = ec["worst_experts"]
    wemax = max(d["submitted"] for d in we) or 1
    exp_html = ""
    for d in we:
        dec = d["accepted"] + d["rejected"]
        rate = d["acc_rate"] or 0
        aw = d["accepted"] / wemax * 100
        rw = d["rejected"] / wemax * 100
        pw = d["pending"] / wemax * 100
        reason = (d["top_reason"] or "").replace("_", " ")
        exp_html += f"""
        <div class="erow">
          <div class="elabel">{d['expert']}<span class="muted"> · {d['language']} · W{d['join_week']}</span></div>
          <div class="ebar">
            <div class="seg t-good" style="width:{aw}%" title="accepted {d['accepted']}"></div>
            <div class="seg t-critical" style="width:{rw}%" title="rejected {d['rejected']}"></div>
            <div class="seg t-pending" style="width:{pw}%" title="pending {d['pending']}"></div>
          </div>
          <div class="eval">{rate:.0%}<span class="muted"> · {d['rejected']}✗ mostly {reason} ({d['top_reason_n']})</span></div>
        </div>"""
    top2 = ec["top_rejectors"][:2]
    top2_rej = sum(t["rejections"] for t in top2)
    top2_txt = " + ".join(t["expert"] for t in top2)

    # diagnostics banner — surface CRITICAL/WARN flags at the top
    diag = m.get("diagnostics", [])
    sevtone = {"CRITICAL": "critical", "WARN": "warning", "INFO": "muted"}
    ncrit = sum(1 for x in diag if x["severity"] == "CRITICAL")
    nwarn = sum(1 for x in diag if x["severity"] == "WARN")
    flags_html = ""
    for x in [d for d in diag if d["severity"] in ("CRITICAL", "WARN")]:
        tone = sevtone[x["severity"]]
        flags_html += f"""
        <div class="flag">
          <span class="sev sev-{tone}">{x['severity']}</span>
          <div><div class="fmsg">{x['message']}</div>
            <div class="fev">{x['evidence']} &nbsp;·&nbsp; <b>→</b> {x['recommendation']}</div></div>
        </div>"""

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Project Falcon — Health Check</title>
<style>
  :root {{
    color-scheme: light;
    --bg:#f4f4f1; --surface:#fcfcfb; --border:#e4e3dd;
    --text:#111110; --text-2:#52514e; --muted:#8a8980;
    --series-1:#2a78d6; --accent:#6250d6;
    --good:#0ca30c; --warning:#fab219; --critical:#d03b3b; --pending:#c9c7bd;
    --reason:#eb6834;
  }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{
      color-scheme: dark;
      --bg:#141413; --surface:#1f1f1d; --border:#33332e;
      --text:#f0efec; --text-2:#c3c2b7; --muted:#8f8e84;
      --series-1:#3987e5; --accent:#9085e9;
      --good:#2cb82c; --warning:#fab219; --critical:#e66767; --pending:#4a4a44;
      --reason:#d95926;
    }}
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--text);
    font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
    -webkit-font-smoothing:antialiased; }}
  .wrap {{ max-width:1080px; margin:0 auto; padding:28px 16px 64px; }}
  header {{ display:flex; flex-wrap:wrap; align-items:baseline; gap:10px 16px; margin-bottom:6px; }}
  h1 {{ font-size:22px; margin:0; letter-spacing:-.01em; }}
  .sub {{ color:var(--muted); font-size:13px; }}
  .verdict {{ margin:14px 0 24px; padding:13px 16px; border-radius:10px;
    background:color-mix(in srgb, var(--vt) 12%, var(--surface));
    border:1px solid color-mix(in srgb, var(--vt) 40%, var(--border));
    font-weight:600; display:flex; gap:10px; align-items:center; }}
  .verdict .dot {{ width:10px; height:10px; border-radius:50%; background:var(--vt); flex:none; }}
  .flags {{ background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:14px 16px; margin-bottom:22px; }}
  .flags h2 {{ font-size:13px; margin:0 0 10px; text-transform:uppercase; letter-spacing:.05em; color:var(--muted); }}
  .flag {{ display:grid; grid-template-columns:78px 1fr; gap:10px; align-items:start; padding:8px 0; border-top:1px solid var(--border); }}
  .flag:first-of-type {{ border-top:none; }}
  .sev {{ font-size:10px; font-weight:700; padding:2px 7px; border-radius:20px; text-align:center; letter-spacing:.03em; }}
  .sev-critical {{ background:color-mix(in srgb,var(--critical) 18%,transparent); color:var(--critical); }}
  .sev-warning {{ background:color-mix(in srgb,var(--warning) 28%,transparent); color:var(--text); }}
  .fmsg {{ font-size:13px; font-weight:600; }}
  .fev {{ font-size:12px; color:var(--muted); margin-top:2px; }}
  .grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin-bottom:22px; }}
  .kpi {{ background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:14px 16px; }}
  .kpi .n {{ font-size:28px; font-weight:700; letter-spacing:-.02em; }}
  .kpi .l {{ font-size:12px; color:var(--muted); text-transform:uppercase; letter-spacing:.04em; margin-top:2px; }}
  .kpi .d {{ font-size:12px; color:var(--text-2); margin-top:4px; }}
  .cards {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
  .card {{ background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:16px 18px; }}
  .card h2 {{ font-size:14px; margin:0 0 3px; }}
  .card .cap {{ font-size:12px; color:var(--muted); margin:0 0 14px; }}
  .full {{ grid-column:1/-1; }}
  .row {{ display:grid; grid-template-columns:150px 1fr 120px; align-items:center; gap:10px; margin:7px 0; font-size:13px; }}
  .row-label {{ color:var(--text-2); }}
  .tag {{ display:inline-block; font-size:10px; font-weight:600; padding:1px 6px; border-radius:20px;
    vertical-align:middle; letter-spacing:.02em; }}
  .tag-auto {{ background:color-mix(in srgb,var(--good) 20%,transparent); color:var(--good); }}
  .tag-semi {{ background:color-mix(in srgb,var(--warning) 26%,transparent); color:var(--text); }}
  .tag-human {{ background:color-mix(in srgb,var(--muted) 20%,transparent); color:var(--text-2); }}
  .row-val {{ text-align:right; font-variant-numeric:tabular-nums; }}
  .track {{ background:color-mix(in srgb, var(--muted) 18%, transparent); border-radius:5px; height:12px; overflow:hidden; }}
  .fill {{ height:100%; border-radius:5px; }}
  .t-good{{ background:var(--good); }} .t-warning{{ background:var(--warning); }}
  .t-critical{{ background:var(--critical); }} .t-reason{{ background:var(--reason); }}
  .t-accent{{ background:var(--accent); }} .t-pending{{ background:var(--pending); }}
  .muted {{ color:var(--muted); }}
  .funnel {{ height:30px; border-radius:7px; overflow:hidden; display:flex; background:color-mix(in srgb,var(--muted) 15%,transparent); }}
  .funnel div {{ height:100%; }}
  .legend {{ display:flex; gap:16px; flex-wrap:wrap; font-size:12px; color:var(--text-2); margin-top:10px; }}
  .legend i {{ display:inline-block; width:10px; height:10px; border-radius:3px; margin-right:5px; vertical-align:middle; }}
  .wkrow {{ display:flex; gap:12px; align-items:flex-end; height:150px; padding-top:8px; }}
  .wkcol {{ flex:1; display:flex; flex-direction:column; align-items:center; height:100%; }}
  .wkbar {{ flex:1; width:70%; display:flex; flex-direction:column-reverse; justify-content:flex-start;
    border-radius:5px 5px 0 0; overflow:hidden; }}
  .seg {{ width:100%; }} .seg+.seg {{ border-top:2px solid var(--surface); }}
  .faint {{ opacity:.4; }}
  .wklab {{ font-size:12px; text-align:center; margin-top:6px; color:var(--text-2); }}
  .erow {{ display:grid; grid-template-columns:150px 1fr; gap:4px 10px; margin:10px 0; font-size:13px; }}
  .elabel {{ grid-column:1; align-self:center; font-weight:600; }}
  .ebar {{ grid-column:2; align-self:center; display:flex; height:13px; border-radius:5px; overflow:hidden;
    background:color-mix(in srgb,var(--muted) 15%,transparent); }}
  .ebar .seg {{ height:100%; }} .ebar .seg+.seg {{ border-left:2px solid var(--surface); }}
  .eval {{ grid-column:2; font-size:12px; color:var(--text-2); font-variant-numeric:tabular-nums; }}
  ul.take {{ margin:4px 0 0; padding-left:18px; }} ul.take li {{ margin:6px 0; font-size:13px; color:var(--text-2); }}
  ul.take b {{ color:var(--text); }}
  @media (max-width:720px) {{ .grid{{grid-template-columns:repeat(2,1fr);}} .cards{{grid-template-columns:1fr;}}
    .row{{grid-template-columns:92px 1fr 96px;}} }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>Project Falcon — Health Check</h1>
    <span class="sub">as of {m['as_of']} (end of week {m['as_of_week']}) · data through {m['data_through']} · due {m['due']} ({wks} wks left) · goal {m['goal']} accepted</span>
  </header>

  <div class="verdict" style="--vt:var(--{verdict_tone})"><span class="dot"></span>{verdict}</div>

  <div class="flags">
    <h2>Diagnostics — {ncrit} critical · {nwarn} warnings <span style="text-transform:none;font-weight:400">(rebuild: <code>python3 metrics.py --diagnose</code>)</span></h2>
    {flags_html}
  </div>

  <div class="grid">
    <div class="kpi"><div class="n">{acc}</div><div class="l">Accepted</div><div class="d">{pct_goal:.0%} of {g} goal</div></div>
    <div class="kpi"><div class="n">{h['acc_rate']:.0%}</div><div class="l">Acceptance rate</div><div class="d">{h['decided']} decided · and falling</div></div>
    <div class="kpi"><div class="n">{pen}</div><div class="l">Pending backlog</div><div class="d">unreviewed, growing</div></div>
    <div class="kpi"><div class="n">{need_txt}</div><div class="l">Needed pace</div><div class="d">best week ever: {max(thr.values())}</div></div>
  </div>

  <div class="cards">
    <div class="card full">
      <h2>Progress to 600</h2>
      <p class="cap">Accepted {acc} · pending {pen} (if ~{h['acc_rate']:.0%} clear → +{round(pen*h['acc_rate'])}) · the rest is still to be built & reviewed in 2 weeks.</p>
      <div class="funnel">
        <div class="t-good" style="width:{acc_w}%" title="accepted {acc}"></div>
        <div class="t-pending" style="width:{pen_w}%" title="pending {pen}"></div>
      </div>
      <div class="legend">
        <span><i class="t-good"></i>Accepted {acc}</span>
        <span><i class="t-pending"></i>Pending {pen}</span>
        <span><i style="background:color-mix(in srgb,var(--muted) 20%,transparent)"></i>Remaining to goal {g-acc-pen}</span>
      </div>
    </div>

    <div class="card">
      <h2>Weekly submissions &amp; outcomes</h2>
      <p class="cap">By submission week. Volume is rising but acceptances flattened and the pending backlog ballooned in W4.</p>
      <div class="wkrow">{weekly_html}</div>
      <div class="legend">
        <span><i class="t-good"></i>Accepted</span><span><i class="t-critical"></i>Rejected</span><span><i class="t-pending"></i>Pending</span>
      </div>
    </div>

    <div class="card">
      <h2>QA throughput (accepted / review week)</h2>
      <p class="cap">The real bottleneck. QA has never cleared more than {max(thr.values())} accepts in a week; weeks after the snapshot are faded as partial.</p>
      <div class="wkrow">{thr_html}</div>
    </div>

    <div class="card">
      <h2>Acceptance rate by language</h2>
      <p class="cap">Go lags badly — those experts only joined in week 3.</p>
      {lang_html}
    </div>

    <div class="card">
      <h2>Acceptance rate by category</h2>
      <p class="cap">Features &amp; refactors reject most; dependency upgrades are the safe bet.</p>
      {cat_html}
    </div>

    <div class="card">
      <h2>Why tasks get rejected</h2>
      <p class="cap">{rrtot} rejections. <b>{prev['auto_share']:.0%}</b> are <span class="tag tag-auto">auto-catchable</span>
         before a human reviewer (docker build, duplicate check, frontier pass-rate) — that's <b>{prev['auto_share_of_all_qa_decisions']:.0%}</b>
         of all QA decisions wasted on things a pre-submission gate would bounce. Tagged below.</p>
      {rr_html}
    </div>

    <div class="card">
      <h2>Reviewer acceptance spread</h2>
      <p class="cap">R3 accepts {m['by_reviewer']['R3']['acc_rate']:.0%} vs R4 {m['by_reviewer']['R4']['acc_rate']:.0%} — worth a calibration check (may be task mix).</p>
      {rev_html}
    </div>

    <div class="card full">
      <h2>Are accepted tasks hard enough? ⚠️ spec to confirm</h2>
      <p class="cap">Accepted tasks by frontier pass-rate. If the target band is <b>{lo:.0%}–{hi:.0%}</b> (industry
         heuristic — <b>unconfirmed with the lab</b>), only <b>{ds['in_band']}/{ds['n_accepted_with_fpr']} = {ds['in_band_share']:.0%}</b>
         of our accepted tasks are in spec; <b>{ds['above_0.60']} ({ds['above_0.60_share']:.0%})</b> are above 0.60 and may be
         too easy. Our QA's own "too easy" line sits at ~0.80, so the easy tail (orange) was accepted. Green = in band, orange = likely too easy, grey = harder than band.</p>
      <div class="wkrow">{diff_html}</div>
      <div class="legend">
        <span><i class="t-good"></i>in {lo:.0%}–{hi:.0%} band</span>
        <span><i class="t-reason"></i>≥0.60 (easy?)</span>
        <span><i class="t-pending"></i>below / above band</span>
      </div>
    </div>

    <div class="card full">
      <h2>Where the problem concentrates — by expert</h2>
      <p class="cap">Rejections cluster in a few people: the top 3 experts own <b>{ec['top3_rejection_share']:.0%}</b> of
         all rejections, the top 10 own <b>{ec['top10_rejection_share']:.0%}</b>. <b>{top2_txt}</b> alone account for
         <b>{top2_rej}</b> rejections — almost all <i>tests&nbsp;too&nbsp;loose</i>. The Go cohort (joined W3) fails
         mostly on <i>docker&nbsp;build&nbsp;failure</i> — an environment problem, not skill. Bars = accepted / rejected / pending.</p>
      {exp_html}
    </div>

    <div class="card full">
      <h2>Forecast &amp; what it rests on</h2>
      <p class="cap">{need_phrase} Expert supply isn't the limit
         (capacity ≈ {cap['max_submittable_per_week']} tasks/wk from {cap['expert_hours_per_week']} hrs); <b>QA review throughput is</b>.</p>
      <ul class="take">
        <li><b>Pessimistic</b> (most recent week's pace): ~<b>{f['pessimistic']}</b></li>
        <li><b>Base</b> ({pace_lbl} average pace): ~<b>{f['base']}</b></li>
        <li><b>Optimistic</b> (best week's pace): ~<b>{f['optimistic']}</b></li>
        <li>{closing}</li>
      </ul>
    </div>
  </div>

  <p class="sub" style="margin-top:22px">Data hygiene: {dq['unique_submissions']} unique submissions
   ({dq['dup_submission_rows_dropped']} duplicate rows dropped, {len(dq['expert_ids_not_in_roster'])} expert-id case fixes,
   {dq['empty_hours_rows']} blank hours). Rebuild: <code>python3 metrics.py</code>.</p>
</div>
</body>
</html>"""
