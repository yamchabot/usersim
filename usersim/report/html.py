"""
HTML report generator.

Produces a self-contained single-file report from results.json,
styled as per-person cards with avatar, goal, constraints, and
a dot-grid of scenario pass/fail results.
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

    # ── Per-person cards ───────────────────────────────────────────────────────
    cards_html = ""
    for pi, person_name in enumerate(persons_ordered):
        person_results = [result_map.get((person_name, s)) for s in scenarios]
        p_pass = sum(1 for r in person_results if r and r["satisfied"])
        p_fail = len(scenarios) - p_pass
        all_ok = p_fail == 0

        # Pull metadata from first result that has it
        first = next((r for r in person_results if r), {})
        role        = first.get("role",        "")
        goal        = first.get("goal",        "")
        pronoun     = first.get("pronoun",     "they")
        constraints = first.get("constraints", [])

        card_cls = "all-pass" if all_ok else "some-fail"
        badge_cls = "badge-all" if all_ok else "badge-some"

        constraints_html = "".join(
            '<div class="constraint{} {}">'
            '<span class="c-status">{}</span>{}</div>'.format(
                " implies" if c["label"].lower().startswith("if ") else "",
                "c-pass" if c["passed"] else "c-fail",
                "✓" if c["passed"] else "✗",
                c["label"],
            )
            for c in constraints
        )

        # Dot grid
        dots = ""
        for si, scenario in enumerate(scenarios):
            r = result_map.get((person_name, scenario))
            if r:
                dot_cls = "pass" if r["satisfied"] else "fail"
                viols   = r.get("violations", [])
                tip     = " | ".join(viols) if viols else scenario
                dots += (f'<div class="ball {dot_cls}" '
                         f'data-person="{pi}" data-scenario="{si}" '
                         f'data-scenario-name="{scenario}" '
                         f'data-violations="{"|".join(viols)}" '
                         f'title="{scenario}"></div>\n')

        cards_html += f"""
<div class="card {card_cls}">
  <div class="identity">
    <img class="avatar" src="{_avatar_url(person_name, pi)}" alt="{person_name}"
         onerror="this.style.background='#2d333b'" />
    <div class="person-name">{person_name}</div>
    <div class="person-role">{role}</div>
    <div class="pronouns">{pronoun}</div>
    <div class="pass-badge {badge_cls}">{p_pass}/{len(scenarios)} scenarios</div>
  </div>

  <div class="constraints-panel">
    <div class="goal-text">{goal}</div>
    <div class="constraints">
      {constraints_html}
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
    <div class="balls">
{dots}    </div>
  </div>
</div>
"""

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
  font-size: 13px;
  color: var(--muted);
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
}}
.summary strong {{ color: var(--text); }}
.summary .s-pass {{ color: var(--pass); font-weight: 600; }}
.summary .s-fail {{ color: var(--fail); font-weight: 600; }}

/* ── Person card ─────────────────────────────────────────── */
.card {{
  display: grid;
  grid-template-columns: 130px 1fr 280px;
  gap: 0;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px;
  margin-bottom: 14px;
  overflow: hidden;
}}

.identity {{
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px 16px;
  gap: 8px;
  border-right: 1px solid var(--border);
  background: var(--card2);
}}

.avatar {{
  width: 72px; height: 72px;
  border-radius: 50%;
  border: 2px solid var(--border);
  background: #2d333b;
  object-fit: cover;
}}
.card.all-pass  .avatar {{ border-color: var(--pass); box-shadow: 0 0 0 3px rgba(63,185,80,.18); }}
.card.some-fail .avatar {{ border-color: var(--fail); box-shadow: 0 0 0 3px rgba(248,81,73,.12); }}

.person-name {{ font-size: 14px; font-weight: 700; text-align: center; }}
.person-role {{ font-size: 10px; color: var(--muted); text-align: center; line-height: 1.4; }}
.pronouns    {{ font-size: 10px; color: var(--border); font-style: italic; text-align: center; }}

.pass-badge {{ font-size: 10px; font-weight: 600; padding: 2px 7px; border-radius: 10px; margin-top: 2px; }}
.badge-all  {{ background: rgba(63,185,80,.2);  color: var(--pass); }}
.badge-some {{ background: rgba(248,81,73,.15); color: var(--fail); }}

.constraints-panel {{
  padding: 18px 20px;
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
}}

.goal-text {{
  font-size: 12px;
  color: var(--muted);
  line-height: 1.5;
}}

.constraints {{
  display: flex;
  flex-direction: column;
  gap: 4px;
}}

.constraint {{
  font-family: var(--mono);
  font-size: 11px;
  padding: 4px 9px;
  border-radius: 5px;
  background: #0d1117;
  border: 1px solid var(--border);
  color: var(--blue);
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.6;
}}
.constraint.implies          {{ color: var(--orange); }}
.constraint.implies.c-pass  {{ color: var(--blue); opacity: 0.45; }}
.constraint.c-fail           {{ border-color: var(--fail); background: rgba(248,81,73,.08); color: var(--fail); }}
.c-status {{ margin-right: 6px; font-size: 10px; opacity: 0.8; }}

.grid-panel {{
  padding: 16px 16px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}}

.grid-header {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 11px;
  color: var(--muted);
}}
.grid-score {{ font-weight: 600; font-size: 12px; }}
.grid-score .n-pass {{ color: var(--pass); }}
.grid-score .n-fail {{ color: var(--fail); }}

.balls {{
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  align-content: flex-start;
}}

.ball {{
  width: 13px; height: 13px;
  border-radius: 50%;
  cursor: pointer;
  flex-shrink: 0;
  transition: transform .12s, filter .12s;
}}
.ball:hover {{ transform: scale(1.55); filter: brightness(1.2); z-index: 5; }}
.ball.pass  {{ background: var(--pass); }}
.ball.fail  {{ background: var(--fail); opacity: .75; }}
.ball.fail:hover {{ opacity: 1; }}

.legend {{ display: flex; gap: 8px; align-items: center; font-size: 10px; color: var(--muted); }}
.leg-dot {{ width: 8px; height: 8px; border-radius: 50%; display: inline-block; }}
.leg-pass {{ background: var(--pass); }}
.leg-fail {{ background: var(--fail); }}

/* ── Tooltip ─────────────────────────────────────────────── */
#tooltip {{
  position: fixed;
  background: #1c2128;
  border: 1px solid #444c56;
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 12px;
  max-width: 340px;
  pointer-events: none;
  z-index: 9999;
  box-shadow: 0 8px 28px rgba(0,0,0,.5);
  display: none;
  line-height: 1.5;
}}
#tooltip .tip-scenario {{ font-weight: 700; color: var(--blue); margin-bottom: 5px; }}
#tooltip .tip-pass     {{ color: var(--pass); }}
#tooltip .tip-fail     {{ color: var(--fail); margin-top: 3px; font-size: 11px; font-family: var(--mono); }}
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

{cards_html}

<script>
const tip = document.getElementById('tooltip');
document.querySelectorAll('.ball').forEach(ball => {{
  ball.addEventListener('mouseenter', e => {{
    const scenario  = ball.dataset.scenarioName || ball.title;
    const viols     = (ball.dataset.violations || '').split('|').filter(Boolean);
    const isPass    = ball.classList.contains('pass');
    let html = `<div class="tip-scenario">${{scenario}}</div>`;
    if (isPass) {{
      html += `<div class="tip-pass">✓ satisfied</div>`;
    }} else {{
      html += `<div class="tip-fail">${{viols.map(v => '✗ ' + v).join('<br>')}}</div>`;
    }}
    tip.innerHTML = html;
    tip.style.display = 'block';
  }});
  ball.addEventListener('mousemove', e => {{
    tip.style.left = (e.clientX + 14) + 'px';
    tip.style.top  = (e.clientY - 10) + 'px';
  }});
  ball.addEventListener('mouseleave', () => {{ tip.style.display = 'none'; }});
}});
</script>

</body>
</html>"""

    Path(output_path).write_text(html)
