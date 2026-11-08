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
        faint = " faint" if wk_ >= m["current_week"] else ""  # current/future = partial
        thr_html += f"""
        <div class="wkcol">
          <div class="wkbar"><div class="seg t-accent{faint}" style="height:{hh}%" title="{v}"></div></div>
          <div class="wklab">W{wk_}<br><span class="muted">{v}</span></div>
        </div>"""

    # rejection reasons
    rr = m["rejection_reasons"]
    rrtot = sum(rr.values())
    rrmax = max(rr.values())
    rr_html = ""
    for reason, n in rr.items():
        w = n / rrmax * 100
        rr_html += f"""
        <div class="row">
          <div class="row-label">{reason.replace('_',' ')}</div>
          <div class="track"><div class="fill t-reason" style="width:{w}%"></div></div>
          <div class="row-val">{n}<span class="muted"> · {n/rrtot:.0%}</span></div>
        </div>"""

    lang_html = _bar_rows(m["by_language"], "lang", "accepted")
    cat_html = _bar_rows(m["by_category"], "cat", "accepted")
    rev_rows = {k: {"acc_rate": v["acc_rate"], "accepted": v["accepted"],
                    "rejected": v["decided"] - v["accepted"]}
                for k, v in m["by_reviewer"].items()}
    rev_html = _bar_rows(rev_rows, "rev", "accepted")

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
  .row {{ display:grid; grid-template-columns:120px 1fr 120px; align-items:center; gap:10px; margin:7px 0; font-size:13px; }}
  .row-label {{ color:var(--text-2); }}
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
    <span class="sub">as of {m['as_of']} (week {m['current_week']}) · data through {m['data_through']} · due {m['due']} ({wks} wks left) · goal {m['goal']} accepted</span>
  </header>

  <div class="verdict" style="--vt:var(--{verdict_tone})"><span class="dot"></span>{verdict}</div>

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
      <p class="cap">The real bottleneck. QA has never cleared more than {max(thr.values())} accepts in a week; the current week (W{m['current_week']}) is faded as partial.</p>
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
      <p class="cap">{rrtot} rejections. The top two — loose tests &amp; too easy — are {round((rr.get('tests_too_loose',0)+rr.get('too_easy',0))/rrtot*100)}% and both fixable with guidance.</p>
      {rr_html}
    </div>

    <div class="card">
      <h2>Reviewer acceptance spread</h2>
      <p class="cap">R3 accepts {m['by_reviewer']['R3']['acc_rate']:.0%} vs R4 {m['by_reviewer']['R4']['acc_rate']:.0%} — worth a calibration check (may be task mix).</p>
      {rev_html}
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
