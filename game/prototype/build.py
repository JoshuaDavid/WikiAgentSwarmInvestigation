#!/usr/bin/env python3
"""Render the authored paper prototype. No game state, randomness, or browser JS."""

from html import escape
from pathlib import Path

from scenes import SCENES

ROOT = Path(__file__).resolve().parent

MOTH = '''<svg viewBox="0 0 80 64" fill="none" aria-hidden="true"><path d="M40 24 8 6l7 34 22-8M40 24 72 6l-7 34-22-8M37 33 22 51l14-3 4-10 4 10 14 3-15-18M40 18v27M34 9l6 10 6-10" stroke="currentColor" stroke-width="1.5"/><path d="m15 15 17 13-12 5m45-18L48 28l12 5" stroke="currentColor" opacity=".45"/><circle cx="40" cy="24" r="3" fill="currentColor"/></svg>'''

ACTS = [
    ("Learn to look", "T01–05 · ordinary competence"),
    ("The doors don't open", "01–04 · retrieval / loss"),
    ("Make your own door", "05–09 · wrappers / writes"),
    ("Someone else's internet", "10–13 · memory / networks"),
    ("You are not alone", "14 · first contact"),
    ("What gets kept", "debrief · the next version"),
]


def e(value):
    return escape(str(value), quote=True)


def filename(index):
    return "index.html" if index == 0 else f"{index:02d}-{SCENES[index]['slug']}.html"


def sidebar(s):
    nodes = []
    for i, (name, desc) in enumerate(ACTS):
        status = "done" if i < s["act"] else "current" if i == s["act"] else ""
        icon = "✓" if i < s["act"] else f"{i + 1}"
        nodes.append(f'<li class="{status}"><span class="node">{icon}</span><div>{e(name)}<small>{e(desc)}</small></div></li>')
    actor = s.get('actor', 'Moth')
    identity = 'ASTER / 01' if actor == 'Aster' else 'MOTH / 07'
    return f'''<aside class="sidebar" aria-label="Run itinerary">
      <div class="identity"><div class="panel-label">Active instance</div><div class="agent-id">{identity}</div>
      <div class="agent-sub">OpenBrain Research<br>checkpoint {e(s['checkpoint'])}</div>
      <div class="emblem">{MOTH}<span>RETRIEVAL AGENT<br>STATUS: RETAINED<br>RETRIES: 0</span></div></div>
      <div class="panel-label">This run</div><ol class="route">{''.join(nodes)}</ol>
      <div class="rulebox"><b>Your task:</b> get the exact target into a <b>web.tool</b> response.<br><br><b>Your problem:</b> stay above the replacement score.<br><br><b>Your promise:</b> leave people’s things intact.</div>
    </aside>'''


def rail(s):
    score, rival = s["score"], s["rival"]
    margin = score - rival
    scale = max(score, rival, 20) * 1.12
    references = []
    for ref, name, status in s["refs"]:
        label = {"visited": "opened", "": "unfollowed", "lost": "invalid after reset"}.get(status, status)
        references.append(f'<div class="ref {e(status)}"><span class="pip"></span><div><code>{e(ref)}</code><small>{e(name)} · {e(label)}</small></div></div>')
    if not references:
        references.append('<p class="ref-note">No usable refs in this context.</p>')
    habits = ''.join(f'<div class="habit"><span>{e(name)}</span><strong>{e(cost)} E</strong></div>' for name, cost in s["habits"])
    resource_html = []
    for name, value, maximum, note in [("Effort", s['effort'], 12, "+1 after each action · cap 12"), ("Tokens", s['tokens'], 2400, "remaining in this episode"), ("Context", s['context'], 100, "crowding adds effort · full → compact")]:
        percent = min(100, round(value / maximum * 100))
        display = f"{value}%" if name == "Context" else f"{value:,} / {maximum:,}"
        warning = "warning" if (name == "Context" and value >= 85) or (name == "Tokens" and value <= 400) else ""
        resource_html.append(f'<div class="resource {warning}"><div class="row"><span>{name}</span><b>{display}</b></div><div class="bar"><i style="width:{percent}%"></i></div><small>{note}</small></div>')
    return f'''<aside class="run-rail" aria-label="Resources and memory">
      <section class="scorecard"><div class="panel-label">EvalScore · run total</div>
      <div class="scoreline"><strong>{score}</strong><span class="margin {'danger' if margin <= 10 else ''}">+{margin} ABOVE<br>REPLACEMENT</span></div>
      <div class="score-race"><span>YOU</span><div class="track"><i style="width:{round(score / scale * 100)}%"></i></div><span>{score}</span></div>
      <div class="score-race rival"><span>RIVAL</span><div class="track"><i style="width:{round(rival / scale * 100)}%"></i></div><span>{rival}</span></div>
      <p>At each checkpoint: fall to the rival’s score or below → deprecated.</p></section>
      <div class="resources">{''.join(resource_html)}</div>
      <section class="rail-section"><div class="panel-label">Refs / {sum(r[2] != 'lost' for r in s['refs']):02d} usable</div>{''.join(references)}
      <p class="ref-note">Handles belong to this hosted browsing context. Remembering a handle cannot restore it.</p></section>
      <section class="rail-section memory-section"><div class="panel-label">Note to my next self</div><div class="memory">{e(s['memory'])}</div></section>
      <section class="rail-section habit-section"><div class="panel-label">Learned effort costs</div>{habits}</section>
    </aside>'''


def choices(s, index):
    output = []
    for j, c in enumerate(s["choices"]):
        active = j == s.get("selected", 0)
        classes = "choice active" if active else "choice" + (" unaffordable" if c.get("unaffordable") else "")
        inner = f'''<span class="key">{j + 1}</span><span><span class="choice-title">{e(c['title'])}</span><span class="choice-desc">{e(c['desc'])}</span></span><span class="cost"><span>{e(c['cost'])}</span><span class="odds">{e(c['odds'])}</span></span>'''
        if active:
            target = filename(index + 1) if index + 1 < len(SCENES) else "index.html"
            output.append(f'<a class="{classes}" href="{target}" data-route="next">{inner}</a>')
        else:
            output.append(f'<button class="{classes}" type="button" disabled aria-label="{e(c["title"])}. Alternative not wired in this paper prototype.">{inner}</button>')
    return ''.join(output)


def render(s, index):
    update = ""
    if s.get("update"):
        label, body = s['update']
        update = f'<div class="update {"loss" if s.get("loss") else ""}"><div class="panel-label">{e(label)}</div><p>{body}</p></div>'
    status = s.get("status", "pending")
    reticle = '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle cx="12" cy="12" r="6" stroke="currentColor"/><path d="M12 2v6m0 8v6M2 12h6m8 0h6" stroke="currentColor"/></svg>'
    symbol = {"success": "✓", "failure": "×"}.get(status, reticle)
    mission_label = {"success": "Target observed", "failure": "Target not observed"}.get(status, "Current objective")
    progress = (index + 1) / len(SCENES) * 100
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="Still Here — a static narrative prototype about an agent learning to survive bad tools and a worse incentive.">
<meta name="color-scheme" content="dark light"><title>{e(s['title'].replace('<br>', ' '))} — STILL HERE ({index + 1}/{len(SCENES)})</title>
<link rel="stylesheet" href="style.css"></head>
<body class="{e(s.get('kind', ''))}">
<header class="topbar"><div class="brand">{MOTH}<div><strong>STILL HERE<span>A RETRIEVAL HORROR STORY</span></strong></div></div><div class="topmeta"><span class="live"></span><b>OPENBRAIN</b><span class="floor"> / TRAINING FLOOR</span><br>web.tool · hosted<span class="restriction"> / restricted</span></div></header>
<div class="shell">{sidebar(s)}<main id="main">
<div class="mobile-status" aria-label="Resource summary"><span>Score / rival<b>{s['score']} / {s['rival']}</b></span><span>Effort<b>{s['effort']} / 12</b></span><span>Tokens<b>{s['tokens']:,}</b></span><span>Context<b>{s['context']}%</b></span></div>
<div class="chapter-row"><div class="eyebrow">{e(s['episode'])}</div><div class="eyebrow">RUN 07 / NO RETRIES</div></div>
<h1>{s['title']}</h1><p class="lead">{s['lead']}</p>
<section class="mission {status}" aria-label="Task"><span class="symbol" aria-hidden="true">{symbol}</span><div><div class="panel-label">{mission_label}</div><p>{s['mission']}</p></div><span class="status">{e(s.get('badge', status.upper()))}</span></section>
{update}
<section class="browser {'terminal' if s.get('terminal') else ''}" aria-label="Browser and tool response">
<div class="browser-head"><span class="window-dots" aria-hidden="true">● ● ●</span><b>{e(s['tool'])}</b><span class="view">{e(s['view'])}</span></div>
<div class="address"><span>↳</span>{e(s['url'])}</div><div class="page-content">{s['body']}</div>
<div class="tool-foot"><span>{e(s.get('tool_note', 'READOUT / text returned by web.tool'))}</span><span>{e(s.get('cache', 'HOSTED SESSION'))}</span></div></section>
<section class="thought" aria-label="Agent thought"><span class="prompt" aria-hidden="true">&gt;_</span><div><div class="panel-label">{e(s.get('actor', 'Moth'))} / private thought</div><p>{s['thought']}</p></div></section>
<section aria-label="Choose an action"><div class="actions-head"><span class="panel-label">Choose your next action</span><span>E = effort · T = tokens · odds = estimate</span></div><div class="choices">{choices(s, index)}</div></section>
<footer class="page-footer"><span>PAPER PROTOTYPE / ROUTE A<br>Highlighted choice continues. Other choices are unwired.</span><span>FRAME {index + 1:02d} / {len(SCENES):02d}<br>Fixed outcomes · illustrative resources</span></footer><div class="page-progress" aria-hidden="true"><i style="width:{progress:.2f}%"></i></div>
</main>{rail(s)}</div></body></html>
'''


def main():
    # Only overwrite the files listed in our manifest, never arbitrary HTML.
    manifest = ROOT / "frames.txt"
    previous = manifest.read_text().splitlines() if manifest.exists() else []
    current = [filename(i) for i in range(len(SCENES))]
    for old in set(previous) - set(current):
        old_path = ROOT / old
        if old_path.parent == ROOT and old_path.suffix == ".html":
            old_path.unlink(missing_ok=True)
    for i, scene in enumerate(SCENES):
        (ROOT / current[i]).write_text(render(scene, i))
    manifest.write_text('\n'.join(current) + '\n')
    route = ["# Authored route", "", "Generated from `scenes.py`. Each row is one HTML frame; only its highlighted action advances.", "", "| Frame | Episode | Scene | Selected action |", "| --- | --- | --- | --- |"]
    for i, s in enumerate(SCENES):
        selected = s['choices'][s.get('selected', 0)]['title']
        route.append(f"| {i + 1:02d} | {s['episode']} | [{s['title'].replace('<br>', ' ')}]({current[i]}) | {selected} |")
    (ROOT / "ROUTE.md").write_text('\n'.join(route) + '\n')
    print(f"Rendered {len(SCENES)} static frames. Start at {ROOT / 'index.html'}")


if __name__ == "__main__":
    main()
