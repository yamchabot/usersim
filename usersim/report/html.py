"""
HTML report generator.

Produces a self-contained single-file report from results.json,
styled as per-person cards with avatar, goal, constraints, and
a dot-grid of scenario pass/fail results.

Clicking a scenario ball updates the constraints panel to show
the constraint state for that specific scenario (including the
scenario name and optional description).  Clicking the same ball
again (or pressing Escape) returns to the aggregate view.
"""
from __future__ import annotations
import json
from pathlib import Path


# DiceBear avatar styles per person index (cycles if more than 10 people)
_AVATAR_STYLES = [
    ("lorelei",     "ffd6e0"),
    ("adventurer",  "c2d4f0"),
    ("avataaars",   "d4f0c2"),
    ("bottts",      "f0e6c2"),
    ("croodles",    "e6c2f0"),
    ("fun-emoji",   "c2f0e6"),
    ("icons",       "f0c2d4"),
    ("micah",       "c2d4f0"),
    ("miniavs",     "f0d4c2"),
    ("personas",    "d4c2f0"),
]


def _avatar_url(name: str, idx: int) -> str:
    style, bg = _AVATAR_STYLES[idx % len(_AVATAR_STYLES)]
    return (f"https://api.dicebear.com/9.x/{style}/svg"
            f"?seed={name}&backgroundColor={bg}&radius=50")


def _html_attr(s: str) -> str:
    """Escape a string for use in an HTML attribute value."""
    return s.replace("&", "&amp;").replace('"', "&quot;").replace("'", "&#39;")


def generate_report(results: dict, output_path: str | Path) -> None:
    summary     = results.get("summary", {})
    all_results = results.get("results", [])

    persons_ordered = []
    seen = set()
    for r in all_results:
        p = r["person"]
        if p not in seen:
            seen.add(p)
            persons_ordered.append(p)

    scenarios = sorted({r["scenario"] for r in all_results})
    result_map = {(r["person"], r["scenario"]): r for r in all_results}

    total     = summary.get("total", 0)
    satisfied = summary.get("satisfied", 0)
    score     = summary.get("score", 0.0)
    n_pass    = satisfied
    n_fail    = total - satisfied

    # ── Collect never-exercised constraints across all personas ────────────────
    never_exercised: dict[str, list[str]] = {}
    for person_name in persons_ordered:
        person_results = [result_map.get((person_name, s)) for s in scenarios]
        fired_counts: dict[str, int | None] = {}
        for r in person_results:
            if not r:
                continue
            for c in r.get("constraints", []):
                if not isinstance(c, dict):
                    continue
                lbl   = c["label"]
                fired = c.get("antecedent_fired")
                if fired is None:
                    continue
                if lbl not in fired_counts:
                    fired_counts[lbl] = 0
                if fired:
                    fired_counts[lbl] += 1
        unexercised = [lbl for lbl, cnt in fired_counts.items() if cnt == 0]
        if unexercised:
            never_exercised[person_name] = unexercised

    if never_exercised:
        gap_rows = ""
        for person_name, labels in never_exercised.items():
            for lbl in labels:
                gap_rows += f"<tr><td class='gap-person'>{person_name}</td><td class='gap-label'>{lbl}</td></tr>\n"
        gaps_html = f"""
<div class="gaps-section">
  <div class="gaps-title">⚠️ Never-exercised constraints</div>
  <p class="gaps-desc">These conditional constraints had their antecedent false in every scenario.
  Add scenarios where the condition is true to properly test them.</p>
  <table class="gaps-table">
    <thead><tr><th>Persona</th><th>Constraint</th></tr></thead>
    <tbody>{gap_rows}</tbody>
  </table>
</div>
"""
    else:
        gaps_html = ""

    # ── Per-person cards ───────────────────────────────────────────────────────
    cards_html = ""
    for pi, person_name in enumerate(persons_ordered):
        person_results = [result_map.get((person_name, s)) for s in scenarios]
        p_pass = sum(1 for r in person_results if r and r["satisfied"])
        p_fail = len(scenarios) - p_pass
        all_ok = p_fail == 0

        first = next((r for r in person_results if r), {})
        role    = first.get("role",    "")
        goal    = first.get("goal",    "")
        pronoun = first.get("pronoun", "they")

        # Aggregate constraint counts across ALL scenarios (for default/reset view)
        n_scenarios      = len([r for r in person_results if r])
        constraint_pass:  dict[str, int]        = {}
        constraint_fired: dict[str, int | None] = {}
        constraint_labels: list[str] = []
        for r in person_results:
            if not r:
                continue
            for c in r.get("constraints", []):
                lbl   = c["label"]  if isinstance(c, dict) else c
                psd   = c["passed"] if isinstance(c, dict) else True
                fired = c.get("antecedent_fired") if isinstance(c, dict) else None
                if lbl not in constraint_pass:
                    constraint_labels.append(lbl)
                    constraint_pass[lbl]  = 0
                    constraint_fired[lbl] = 0 if fired is not None else None
                if psd:
                    constraint_pass[lbl] += 1
                if fired is True and constraint_fired[lbl] is not None:
                    constraint_fired[lbl] += 1

        card_cls  = "all-pass" if all_ok else "some-fail"
        badge_cls = "badge-all" if all_ok else "badge-some"

        def _constraint_cls(lbl, _n=n_scenarios, _cp=constraint_pass, _cf=constraint_fired):
            n_p = _cp[lbl]; n_f = _cf[lbl]
            if n_f == 0 and _cf[lbl] is not None: return "c-pass c-unexercised"
            if n_p == _n:  return "c-pass"
            if n_p == 0:   return "c-fail"
            return "c-partial"

        def _constraint_sym(lbl, _n=n_scenarios, _cp=constraint_pass, _cf=constraint_fired):
            n_p = _cp[lbl]; n_f = _cf[lbl]
            if n_f == 0 and _cf[lbl] is not None: return "–"
            return "✓" if n_p == _n else "✗" if n_p == 0 else "~"

        agg_constraints_html = "".join(
            '<div class="constraint {}">'
            '<span class="c-status">{}</span>'
            '<span class="c-label">{}</span>'
            '<span class="c-count">{}/{}</span></div>'.format(
                _constraint_cls(lbl), _constraint_sym(lbl),
                lbl, constraint_pass[lbl], n_scenarios,
            )
            for lbl in constraint_labels
        )

        # Dot grid — embed per-scenario constraint JSON on each ball
        dots = ""
        for si, scenario in enumerate(scenarios):
            r = result_map.get((person_name, scenario))
            if r:
                dot_cls = "pass" if r["satisfied"] else "fail"
                viols   = r.get("violations", [])
                desc    = r.get("description", "")
                sc_constraints = [
                    {"label": c["label"], "passed": c["passed"],
                     "antecedent_fired": c.get("antecedent_fired")}
                    for c in r.get("constraints", []) if isinstance(c, dict)
                ]
                sc_json    = _html_attr(json.dumps(sc_constraints))
                viols_attr = _html_attr("|".join(viols))
                dots += (
                    f'<div class="scenario-row {dot_cls}" '
                    f'data-person="{pi}" data-scenario="{si}" '
                    f'data-scenario-name="{_html_attr(scenario)}" '
                    f'data-description="{_html_attr(desc)}" '
                    f'data-violations="{viols_attr}" '
                    f'data-constraints="{sc_json}">'
                    f'<div class="ball {dot_cls}"></div>'
                    f'<span class="sc-name">{scenario}</span>'
                    f'</div>\n'
                )

        cards_html += f"""
<div class="card {card_cls}" data-card="{pi}">
  <div class="identity">
    <img class="avatar" src="{_avatar_url(person_name, pi)}" alt="{person_name}"
         onerror="this.style.background='#2d333b'" />
    <div class="person-name">{person_name}</div>
    <div class="person-role">{role}</div>
    <div class="pronouns">{pronoun}</div>
    <div class="pass-badge {badge_cls}">{p_pass}/{len(scenarios)} scenarios</div>
  </div>

  <div class="constraints-panel" id="cp-{pi}">
    <div class="panel-header">
      <div class="goal-text" id="cp-{pi}-goal">{goal}</div>
      <div class="scenario-label" id="cp-{pi}-scenario-label"></div>
    </div>
    <div class="constraints" id="cp-{pi}-constraints">
      {agg_constraints_html}
    </div>
  </div>

  <div class="grid-panel">
    <div class="grid-header">
      <div class="legend">
        <span class="leg-dot leg-pass"></span> pass
        <span class="leg-dot leg-fail"></span> fail
      </div>
      <div class="grid-score">
        <span class="n-pass">{p_pass}</span>
        <span style="color:var(--muted)"> / </span>
        <span class="n-fail">{len(scenarios)}</span>
      </div>
    </div>
    <div class="scenario-list" id="balls-{pi}">
{dots}    </div>
  </div>
</div>
"""

    # Build JS map of aggregate state per card (for reset on deselect)
    agg_map_entries = []
    for pi, person_name in enumerate(persons_ordered):
        person_results_2 = [result_map.get((person_name, s)) for s in scenarios]
        n_sc2 = len([r for r in person_results_2 if r])
        cp2: dict[str, int] = {}
        cf2: dict[str, int | None] = {}
        cl2: list[str] = []
        for r in person_results_2:
            if not r:
                continue
            for c in r.get("constraints", []):
                lbl   = c["label"]  if isinstance(c, dict) else c
                psd   = c["passed"] if isinstance(c, dict) else True
                fired = c.get("antecedent_fired") if isinstance(c, dict) else None
                if lbl not in cp2:
                    cl2.append(lbl)
                    cp2[lbl] = 0
                    cf2[lbl] = 0 if fired is not None else None
                if psd:
                    cp2[lbl] += 1
                if fired is True and cf2[lbl] is not None:
                    cf2[lbl] += 1

        def _ac(lbl, _n=n_sc2, _cp=cp2, _cf=cf2):
            n_f = _cf[lbl]; n_p = _cp[lbl]
            if n_f == 0 and _cf[lbl] is not None: return "c-pass c-unexercised"
            if n_p == _n: return "c-pass"
            if n_p == 0:  return "c-fail"
            return "c-partial"

        def _as(lbl, _n=n_sc2, _cp=cp2, _cf=cf2):
            n_f = _cf[lbl]; n_p = _cp[lbl]
            if n_f == 0 and _cf[lbl] is not None: return "–"
            return "✓" if n_p == _n else "✗" if n_p == 0 else "~"

        # Build escaped HTML for JS template literal
        agg_html_parts = []
        for lbl in cl2:
            cls  = _ac(lbl)
            sym  = _as(lbl)
            lbl_e = lbl.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")
            agg_html_parts.append(
                f'<div class=\\"constraint {cls}\\">'
                f'<span class=\\"c-status\\">{sym}</span>'
                f'<span class=\\"c-label\\">{lbl_e}</span>'
                f'<span class=\\"c-count\\">{cp2[lbl]}/{n_sc2}</span></div>'
            )
        agg_html = "".join(agg_html_parts)

        first2 = next((r for r in person_results_2 if r), {})
        goal2  = (first2.get("goal", "") or "").replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")
        agg_map_entries.append(f'  {pi}: {{ goal: `{goal2}`, html: `{agg_html}` }}')

    agg_map_js = "{{\n" + ",\n".join(agg_map_entries) + "\n}}"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>User Simulation Report</title>
  <style>
:root {{
  --bg:      #0d1117;
  --card:    #161b22;
  --card2:   #1c2128;
  --border:  #30363d;
  --text:    #e6edf3;
  --muted:   #8b949e;
  --pass:    #3fb950;
  --fail:    #f85149;
  --blue:    #58a6ff;
  --orange:  #ffa657;
  --mono:    'SF Mono', 'Consolas', 'Menlo', monospace;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: var(--bg);
  color: var(--text);
  padding: 32px 24px;
  min-height: 100vh;
}}
header {{
  border-bottom: 1px solid var(--border);
  padding-bottom: 20px;
  margin-bottom: 28px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}}
header h1 {{ font-size: 22px; font-weight: 600; margin-bottom: 6px; }}
.summary {{
  font-size: 13px; color: var(--muted);
  display: flex; gap: 20px; flex-wrap: wrap;
}}
.summary strong {{ color: var(--text); }}
.summary .s-pass {{ color: var(--pass); font-weight: 600; }}
.summary .s-fail {{ color: var(--fail); font-weight: 600; }}

/* ── Card layout ─────────────────────────────────────────── */
.card {{
  display: grid;
  grid-template-columns: 130px 1fr 280px;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px;
  margin-bottom: 14px;
  overflow: hidden;
}}
.identity {{
  display: flex; flex-direction: column; align-items: center;
  padding: 20px 16px; gap: 8px;
  border-right: 1px solid var(--border);
  background: var(--card2);
}}
.avatar {{
  width: 72px; height: 72px;
  border-radius: 50%; border: 2px solid var(--border);
  background: #2d333b; object-fit: cover;
}}
.card.all-pass  .avatar {{ border-color: var(--pass); box-shadow: 0 0 0 3px rgba(63,185,80,.18); }}
.card.some-fail .avatar {{ border-color: var(--fail); box-shadow: 0 0 0 3px rgba(248,81,73,.12); }}
.person-name {{ font-size: 14px; font-weight: 700; text-align: center; }}
.person-role {{ font-size: 10px; color: var(--muted); text-align: center; line-height: 1.4; }}
.pronouns    {{ font-size: 10px; color: var(--border); font-style: italic; text-align: center; }}
.pass-badge {{ font-size: 10px; font-weight: 600; padding: 2px 7px; border-radius: 10px; margin-top: 2px; }}
.badge-all  {{ background: rgba(63,185,80,.2);  color: var(--pass); }}
.badge-some {{ background: rgba(248,81,73,.15); color: var(--fail); }}

/* ── Constraints panel ───────────────────────────────────── */
.constraints-panel {{
  padding: 18px 20px;
  border-right: 1px solid var(--border);
  display: flex; flex-direction: column; gap: 10px;
  min-width: 0;
  transition: background .15s;
}}
.constraints-panel.scenario-active {{
  background: rgba(88,166,255,.04);
}}
.panel-header {{ display: flex; flex-direction: column; gap: 6px; }}
.goal-text {{ font-size: 12px; color: var(--muted); line-height: 1.5; }}

/* scenario label strip (shown when a ball is selected) */
.scenario-label {{
  display: none;
  align-items: center; gap: 6px;
  font-size: 11px; font-weight: 600; color: var(--blue);
  padding: 5px 0 3px;
  border-top: 1px solid var(--border);
}}
.scenario-label.visible {{ display: flex; }}
.scenario-label .sl-name  {{ flex: 1; }}
.scenario-label .sl-badge {{
  font-size: 10px; font-weight: 600;
  padding: 1px 6px; border-radius: 8px;
}}
.scenario-label .sl-badge.pass {{ background: rgba(63,185,80,.2);  color: var(--pass); }}
.scenario-label .sl-badge.fail {{ background: rgba(248,81,73,.15); color: var(--fail); }}
.scenario-label .sl-close {{
  cursor: pointer; color: var(--muted); font-size: 14px;
  line-height: 1; padding: 0 2px; opacity: .6;
}}
.scenario-label .sl-close:hover {{ opacity: 1; color: var(--text); }}

.constraints {{ display: flex; flex-direction: column; gap: 4px; }}
.constraint {{
  display: flex; align-items: center;
  font-family: var(--mono); font-size: 11px;
  padding: 4px 9px; border-radius: 5px;
  background: #0d1117; border: 1px solid var(--border);
  color: var(--blue); word-break: break-word; line-height: 1.6;
}}
.constraint.c-fail    {{ border-color: var(--fail); background: rgba(248,81,73,.08); color: var(--fail); }}
.constraint.c-partial {{ border-color: var(--orange); background: rgba(255,166,87,.08); color: var(--orange); }}
.constraint.c-unexercised {{ opacity: 0.4; }}
.c-status {{ margin-right: 6px; font-size: 10px; opacity: 0.8; }}
.c-label  {{ flex: 1; }}
.c-count  {{ margin-left: 8px; font-size: 10px; opacity: 0.55; white-space: nowrap; }}

/* ── Never-exercised gaps ────────────────────────────────── */
.gaps-section {{
  background: rgba(255,166,87,.08); border: 1px solid var(--orange);
  border-radius: 10px; padding: 18px 22px; margin-bottom: 24px;
}}
.gaps-title {{ font-weight: 700; color: var(--orange); margin-bottom: 6px; font-size: 14px; }}
.gaps-desc  {{ font-size: 12px; color: var(--muted); margin-bottom: 14px; line-height: 1.5; }}
.gaps-table {{ border-collapse: collapse; width: 100%; }}
.gaps-table th {{
  font-size: 11px; text-transform: uppercase; letter-spacing: .06em;
  color: var(--muted); padding: 6px 12px;
  border-bottom: 1px solid var(--border); text-align: left;
}}
.gap-person {{
  font-weight: 600; padding: 6px 12px; font-size: 12px;
  border-bottom: 1px solid #21262d; white-space: nowrap;
}}
.gap-label {{
  font-family: var(--mono); font-size: 11px; color: var(--blue);
  padding: 6px 12px; border-bottom: 1px solid #21262d;
}}

/* ── Scenario list (grid panel) ──────────────────────────── */
.grid-panel {{
  padding: 14px 16px 14px;
  display: flex; flex-direction: column; gap: 8px;
}}
.grid-header {{
  display: flex; align-items: center; justify-content: space-between;
  font-size: 11px; color: var(--muted);
  padding-bottom: 6px;
  border-bottom: 1px solid var(--border);
}}
.grid-score {{ font-weight: 600; font-size: 12px; }}
.grid-score .n-pass {{ color: var(--pass); }}
.grid-score .n-fail {{ color: var(--fail); }}

.scenario-list {{
  display: flex; flex-direction: column; gap: 3px;
}}
.scenario-row {{
  display: flex; align-items: center; gap: 8px;
  padding: 4px 6px; border-radius: 5px;
  cursor: pointer;
  transition: background .1s, opacity .12s;
  border: 1px solid transparent;
}}
.scenario-row:hover {{ background: rgba(255,255,255,.05); }}
.scenario-row.selected {{
  background: rgba(88,166,255,.1);
  border-color: rgba(88,166,255,.3);
}}
.scenario-list.has-selection .scenario-row:not(.selected) {{ opacity: 0.35; }}
.scenario-list.has-selection .scenario-row:not(.selected):hover {{ opacity: 0.85; }}

.ball {{
  width: 10px; height: 10px; border-radius: 50%;
  flex-shrink: 0; pointer-events: none;
}}
.ball.pass {{ background: var(--pass); }}
.ball.fail {{ background: var(--fail); }}
.scenario-row.selected .ball {{ box-shadow: 0 0 0 2px #fff, 0 0 0 3px rgba(255,255,255,.3); }}

.sc-name {{
  font-size: 11px; color: var(--muted);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  pointer-events: none;
}}
.scenario-row.pass .sc-name {{ color: var(--text); }}
.scenario-row.fail  .sc-name {{ color: var(--fail); }}
.scenario-row.selected .sc-name {{ color: var(--blue); font-weight: 600; }}

.legend {{ display: flex; gap: 8px; align-items: center; font-size: 10px; color: var(--muted); }}
.leg-dot {{ width: 8px; height: 8px; border-radius: 50%; display: inline-block; }}
.leg-pass {{ background: var(--pass); }}
.leg-fail {{ background: var(--fail); }}

/* ── Tooltip ─────────────────────────────────────────────── */
#tooltip {{
  position: fixed;
  background: #1c2128; border: 1px solid #444c56;
  border-radius: 8px; padding: 10px 14px;
  font-size: 12px; max-width: 340px;
  pointer-events: none; z-index: 9999;
  box-shadow: 0 8px 28px rgba(0,0,0,.5);
  display: none; line-height: 1.5;
}}
#tooltip .tip-scenario {{ font-weight: 700; color: var(--blue); margin-bottom: 5px; }}
#tooltip .tip-pass {{ color: var(--pass); }}
#tooltip .tip-fail {{ color: var(--fail); margin-top: 3px; font-size: 11px; font-family: var(--mono); }}
#tooltip .tip-hint {{ color: var(--muted); font-size: 10px; margin-top: 4px; }}
  </style>
</head>
<body>

<header>
  <div>
    <h1>🐉 User Simulation Report</h1>
    <div class="summary">
      <span><strong>{satisfied}</strong> / <strong>{total}</strong> person×scenario checks satisfied ({score:.0%})</span>
      <span><span class="s-pass">{n_pass} passed</span> &nbsp; <span class="s-fail">{n_fail} failed</span></span>
      <span><strong>{len(scenarios)}</strong> scenarios &nbsp; <strong>{len(persons_ordered)}</strong> people</span>
    </div>
  </div>
</header>

<div id="tooltip"></div>

{gaps_html}

{cards_html}

<script>
// Aggregate constraint HTML + goal per card — used when deselecting a ball
const AGG = {agg_map_js};

const tip = document.getElementById('tooltip');
const selectedBall = {{}};  // cardIdx → ball | null

function buildConstraintHTML(constraints) {{
  return constraints.map(c => {{
    const fired = c.antecedent_fired;
    const unexercised = (fired === false);
    const cls = unexercised ? 'c-pass c-unexercised'
              : c.passed    ? 'c-pass' : 'c-fail';
    const sym = unexercised ? '–' : c.passed ? '✓' : '✗';
    return `<div class="constraint ${{cls}}"><span class="c-status">${{sym}}</span>`
         + `<span class="c-label">${{c.label}}</span></div>`;
  }}).join('');
}}

function selectBall(ball, pi) {{
  const ballsEl       = document.getElementById(`balls-${{pi}}`);
  const panel         = document.getElementById(`cp-${{pi}}`);
  const goalEl        = document.getElementById(`cp-${{pi}}-goal`);
  const labelEl       = document.getElementById(`cp-${{pi}}-scenario-label`);
  const constraintsEl = document.getElementById(`cp-${{pi}}-constraints`);

  const scenario    = ball.dataset.scenarioName;
  const desc        = ball.dataset.description || '';
  const isPass      = ball.classList.contains('pass');
  const constraints = JSON.parse(ball.dataset.constraints || '[]');

  selectedBall[pi] = ball;
  ball.classList.add('selected');
  ballsEl.classList.add('has-selection');
  panel.classList.add('scenario-active');

  constraintsEl.innerHTML = buildConstraintHTML(constraints);

  const badgeCls = isPass ? 'pass' : 'fail';
  const badgeTxt = isPass ? 'passed' : 'failed';
  labelEl.innerHTML =
    `<span class="sl-name">${{scenario}}</span>`
  + `<span class="sl-badge ${{badgeCls}}">${{badgeTxt}}</span>`
  + `<span class="sl-close" title="Back to summary" data-card="${{pi}}">✕</span>`;
  labelEl.classList.add('visible');

  goalEl.textContent = desc || AGG[pi].goal;
}}

function deselectCard(pi) {{
  const prev = selectedBall[pi];
  if (prev) {{ prev.classList.remove('selected'); selectedBall[pi] = null; }}

  const ballsEl       = document.getElementById(`balls-${{pi}}`);
  const panel         = document.getElementById(`cp-${{pi}}`);
  const goalEl        = document.getElementById(`cp-${{pi}}-goal`);
  const labelEl       = document.getElementById(`cp-${{pi}}-scenario-label`);
  const constraintsEl = document.getElementById(`cp-${{pi}}-constraints`);

  ballsEl.classList.remove('has-selection');
  panel.classList.remove('scenario-active');
  labelEl.classList.remove('visible');
  labelEl.innerHTML = '';
  goalEl.textContent = AGG[pi].goal;
  constraintsEl.innerHTML = AGG[pi].html;
}}

document.querySelectorAll('.ball').forEach(ball => {{
  const pi = parseInt(ball.dataset.person, 10);

  ball.addEventListener('click', e => {{
    e.stopPropagation();
    tip.style.display = 'none';
    if (selectedBall[pi] === ball) {{
      deselectCard(pi);
    }} else {{
      if (selectedBall[pi]) selectedBall[pi].classList.remove('selected');
      selectBall(ball, pi);
    }}
  }});

  ball.addEventListener('mouseenter', e => {{
    if (ball.classList.contains('selected')) return;
    const scenario = ball.dataset.scenarioName || ball.title;
    const viols    = (ball.dataset.violations || '').split('|').filter(Boolean);
    const isPass   = ball.classList.contains('pass');
    let html = `<div class="tip-scenario">${{scenario}}</div>`;
    if (isPass) {{
      html += `<div class="tip-pass">✓ satisfied</div>`;
    }} else {{
      html += `<div class="tip-fail">${{viols.map(v => '✗ ' + v).join('<br>')}}</div>`;
    }}
    html += `<div class="tip-hint">click for details</div>`;
    tip.innerHTML = html;
    tip.style.display = 'block';
  }});
  ball.addEventListener('mousemove', e => {{
    tip.style.left = (e.clientX + 14) + 'px';
    tip.style.top  = (e.clientY - 10) + 'px';
  }});
  ball.addEventListener('mouseleave', () => {{ tip.style.display = 'none'; }});
}});

// Close button (✕) in scenario label
document.addEventListener('click', e => {{
  const btn = e.target.closest('.sl-close');
  if (btn) deselectCard(parseInt(btn.dataset.card, 10));
}});

// Escape deselects all
document.addEventListener('keydown', e => {{
  if (e.key === 'Escape')
    Object.keys(selectedBall).forEach(k => deselectCard(parseInt(k, 10)));
}});
</script>

</body>
</html>"""

    Path(output_path).write_text(html)
