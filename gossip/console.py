"""An interactive pre-mortem you drive in the browser.

`gossip hazard` answers one question per invocation. The interesting move is
sweeping — adding a tag, seeing the risk surface re-form, backing it out. That
is a thing you do with your hands, not with a CLI flag, so the whole canon's
*structure* is embedded once and the browser recomputes on every click.

## What gets embedded, and what deliberately does not

By default: tag vocabulary, per-entry tag sets, project slugs, entry ids, and
two flags per lesson (does it record a failure; is it verified). That is exactly
the exposure already published by the graph page — structure and names, no
content.

NOT by default: rule-of-thumb text and tension headings. Those are lesson prose
out of a private repo, and shipping them to a public site is a wider disclosure
than the structure is. `--include-prose` turns them on for a local render. The
default has to be the narrow one: a flag you must actively set is a decision
someone made, and a default that leaks is an accident nobody made.

Entry ids stay in either mode, so a citation like `dog#E42` is still actionable
through `brain query` by anyone who can already read the canon.
"""

import json

from .canon import field, is_verified, short
from .hazard import open_tensions


def payload(ctx, ledger_path=None, include_prose=False):
    """The whole canon's structure, compact enough to inline."""
    entries = ctx["entries"]

    vocab = {}
    for e in entries:
        for t in e["tags"]:
            vocab[t] = vocab.get(t, 0) + 1
    tags = sorted(vocab, key=lambda t: (-vocab[t], t))
    index = {t: i for i, t in enumerate(tags)}

    rows = []
    for e in entries:
        ids = sorted(index[t] for t in set(e["tags"]) if t in index)
        if not ids:
            continue
        row = {
            "p": short(e["file"]),
            "i": e["id"],
            "t": ids,
            "b": 1 if field(e["block"], "where/why") else 0,
            "v": 1 if is_verified(e["provenance"]) else 0,
        }
        if include_prose:
            rule = field(e["block"], "rule of thumb") or field(e["block"], "what")
            row["r"] = rule[:280]
        rows.append(row)

    forks = []
    for head, hits in open_tensions(tags, ledger_path or ""):
        tid = head.split("·")[0].strip().lstrip("# ").strip()
        kind = head.split("·")[1].strip() if "·" in head else ""
        fork = {"id": tid, "k": kind, "t": sorted(index[h] for h in hits if h in index)}
        if include_prose:
            fork["h"] = head
        forks.append(fork)

    return {
        "asof": ctx["asof"],
        "tags": tags,
        "counts": [vocab[t] for t in tags],
        "entries": rows,
        "forks": forks,
        "prose": bool(include_prose),
    }


def render(ctx, ledger_path=None, include_prose=False):
    data = payload(ctx, ledger_path, include_prose)
    return TEMPLATE.replace("__DATA__", json.dumps(data, separators=(",", ":")))


TEMPLATE = r"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>gossip — pre-mortem console</title>
<style>
  :root{color-scheme:dark;--bg:#14151f;--panel:#1c1e2b;--ink:#c9d1f0;--dim:#7b83a8;
        --line:#2c3145;--hot:#f7768e;--warm:#e0af68;--cool:#9ece6a;--accent:#7aa2f7}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--ink);
       font:15px/1.55 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}
  .wrap{max-width:1100px;margin:0 auto;padding:2rem 1.1rem 4rem}
  h1{font-size:1.6rem;margin:0 0 .2rem;letter-spacing:-.02em}
  .sub{color:var(--dim);margin:0 0 1.5rem;max-width:66ch}
  h2{font-size:.8rem;text-transform:uppercase;letter-spacing:.08em;color:var(--dim);
     margin:2rem 0 .6rem;font-weight:600}
  .chips{display:flex;flex-wrap:wrap;gap:.35rem;max-height:9.5rem;overflow-y:auto;
         background:var(--panel);border:1px solid var(--line);border-radius:9px;padding:.6rem}
  .chip{background:#232739;border:1px solid var(--line);color:var(--ink);border-radius:99px;
        padding:.2rem .6rem;font-size:.82rem;cursor:pointer;font-family:inherit}
  .chip:hover{border-color:var(--accent)}
  .chip[aria-pressed="true"]{background:var(--accent);color:#12131c;border-color:var(--accent);
        font-weight:600}
  .chip small{opacity:.6;margin-left:.3rem}
  .plan{display:flex;flex-wrap:wrap;gap:.4rem;align-items:center;min-height:2.2rem;
        margin:.6rem 0 0}
  .plan .chip[aria-pressed="true"]{background:var(--accent)}
  .empty{color:var(--dim);font-style:italic}
  button.clear{background:none;border:1px solid var(--line);color:var(--dim);
        border-radius:6px;padding:.2rem .55rem;font-size:.78rem;cursor:pointer;font-family:inherit}
  .scroll{overflow-x:auto}
  table.matrix{border-collapse:collapse;font-size:.8rem}
  table.matrix th{color:var(--dim);font-weight:600;padding:.3rem .45rem;text-align:left;
        white-space:nowrap}
  table.matrix td{padding:0;text-align:center}
  .cell{width:3.1rem;height:2.2rem;display:flex;align-items:center;justify-content:center;
        border-radius:5px;margin:2px;font-variant-numeric:tabular-nums;font-weight:600}
  .c0{background:rgba(247,118,142,.9);color:#12131c}
  .c1{background:rgba(224,175,104,.85);color:#12131c}
  .c2{background:rgba(158,206,106,.75);color:#12131c}
  .c3{background:rgba(158,206,106,.35)}
  .cx{background:#191b26;color:var(--dim)}
  .panel{background:var(--panel);border:1px solid var(--line);border-radius:9px;
         padding:.85rem 1rem;margin-bottom:.55rem}
  .panel.danger{border-color:var(--hot)}
  .panel b{color:var(--hot)}
  ul{margin:.4rem 0 0;padding-left:1.1rem}
  li{margin:.18rem 0}
  code{background:#12131c;border:1px solid var(--line);border-radius:4px;
       padding:.03rem .3rem;font-size:.82em}
  .bite{color:var(--hot);font-weight:700}
  .unver{color:var(--warm)}
  .legend{color:var(--dim);font-size:.82rem;margin-top:.5rem}
  footer{margin-top:2.5rem;padding-top:1rem;border-top:1px solid var(--line);
         color:var(--dim);font-size:.83rem}
  a{color:var(--accent)}
  .nav{display:flex;gap:.15rem;flex-wrap:wrap;margin:0 0 1.5rem;
       border-bottom:1px solid var(--line);padding-bottom:.6rem}
  .nav a{color:var(--dim);text-decoration:none;padding:.3rem .7rem;border-radius:6px;
         font-size:.88rem}
  .nav a:hover{color:var(--ink);background:rgba(255,255,255,.05)}
  .nav a[aria-current="page"]{color:var(--accent);font-weight:600;
         background:rgba(255,255,255,.06)}

</style>
</head><body><div class="wrap">

<nav class="nav" aria-label="Pages">
  <a href="index.html">the graph</a>
  <a href="console.html" aria-current="page">pre-mortem console</a>
  <a href="whisper.html">whisper (game)</a>
  <a href="ember.html">ember (world)</a>
</nav>

<h1>pre-mortem console</h1>
<p class="sub">Name what you are about to build. The grid is what the canon has
on every pair of it &mdash; and the red cells, the ones nothing has ever tested
together, are the point. A relevance-ranked search over an untested pair returns
nothing, which reads exactly like reassurance.</p>

<h2>Pick the tags of your plan</h2>
<div class="chips" id="chips"></div>
<div class="plan" id="plan"><span class="empty">nothing selected</span></div>

<h2>Risk surface</h2>
<div class="scroll" id="matrix"></div>
<p class="legend">
  <span class="cell c0" style="display:inline-flex;width:1.6rem;height:1.1rem"></span> never tested together &nbsp;
  <span class="cell c1" style="display:inline-flex;width:1.6rem;height:1.1rem"></span> 1&ndash;2 &nbsp;
  <span class="cell c2" style="display:inline-flex;width:1.6rem;height:1.1rem"></span> 3&ndash;9 &nbsp;
  <span class="cell c3" style="display:inline-flex;width:1.6rem;height:1.1rem"></span> 10+
</p>

<h2>Verdict</h2>
<div id="verdict"></div>

<h2>What has bitten this combination</h2>
<div id="hazards"></div>

<h2>Open forks over your ground</h2>
<div id="forks"></div>

<footer id="foot"></footer>
</div>

<script>
const D = __DATA__;
const plan = new Set();

const chips = document.getElementById('chips');
D.tags.forEach((t, i) => {
  const b = document.createElement('button');
  b.className = 'chip'; b.type = 'button';
  b.setAttribute('aria-pressed', 'false');
  b.innerHTML = t + '<small>' + D.counts[i] + '</small>';
  b.onclick = () => { plan.has(i) ? plan.delete(i) : plan.add(i); draw(); };
  b.dataset.i = i;
  chips.appendChild(b);
});

function pairCount(a, b) {
  let n = 0;
  for (const e of D.entries) if (e.t.includes(a) && e.t.includes(b)) n++;
  return n;
}
function cls(n) { return n === 0 ? 'c0' : n <= 2 ? 'c1' : n <= 9 ? 'c2' : 'c3'; }

function draw() {
  for (const b of chips.children)
    b.setAttribute('aria-pressed', plan.has(+b.dataset.i) ? 'true' : 'false');

  const sel = [...plan].sort((x, y) => D.tags[x].localeCompare(D.tags[y]));
  const planEl = document.getElementById('plan');
  planEl.innerHTML = '';
  if (!sel.length) planEl.innerHTML = '<span class="empty">nothing selected</span>';
  sel.forEach(i => {
    const b = document.createElement('button');
    b.className = 'chip'; b.type = 'button'; b.setAttribute('aria-pressed', 'true');
    b.textContent = D.tags[i] + ' ×';
    b.onclick = () => { plan.delete(i); draw(); };
    planEl.appendChild(b);
  });
  if (sel.length) {
    const c = document.createElement('button');
    c.className = 'clear'; c.textContent = 'clear all';
    c.onclick = () => { plan.clear(); draw(); };
    planEl.appendChild(c);
  }

  const m = document.getElementById('matrix');
  if (sel.length < 2) {
    m.innerHTML = '<p class="empty">pick at least two — the whole method is ' +
                  'about what happens where they meet.</p>';
    document.getElementById('verdict').innerHTML = '';
    document.getElementById('hazards').innerHTML = '';
    document.getElementById('forks').innerHTML = '';
    return;
  }

  let html = '<table class="matrix"><tr><th></th>';
  sel.forEach(j => html += '<th>' + D.tags[j] + '</th>');
  html += '</tr>';
  const holes = [];
  sel.forEach(i => {
    html += '<tr><th>' + D.tags[i] + '</th>';
    sel.forEach(j => {
      if (i === j) { html += '<td><div class="cell cx">—</div></td>'; return; }
      const n = pairCount(i, j);
      if (n === 0 && i < j) holes.push([i, j]);
      html += '<td><div class="cell ' + cls(n) + '">' + n + '</div></td>';
    });
    html += '</tr>';
  });
  m.innerHTML = html + '</table>';

  holes.sort((p, q) =>
    (D.counts[q[0]] + D.counts[q[1]]) - (D.counts[p[0]] + D.counts[p[1]]));
  const v = document.getElementById('verdict');
  if (!holes.length) {
    v.innerHTML = '<div class="panel">Every pair in this plan has been exercised ' +
                  'before. That is the good case — it does not mean it is safe, it ' +
                  'means the evidence exists to check.</div>';
  } else {
    v.innerHTML = '<div class="panel danger"><b>' + holes.length +
      ' untested pair' + (holes.length > 1 ? 's' : '') + '.</b> Not safe: unmeasured.<ul>' +
      holes.map(([i, j]) => '<li><code>' + D.tags[i] + ' + ' + D.tags[j] +
        '</code> — ' + D.counts[i] + ' and ' + D.counts[j] +
        ' lessons apiece, <b>0</b> together</li>').join('') + '</ul></div>';
  }

  const scored = [];
  for (const e of D.entries) {
    const hit = e.t.filter(t => plan.has(t));
    if (hit.length < 2) continue;
    let s = hit.length * (e.b ? 2 : 1) * (e.v ? 1 : 0.75);
    scored.push([s, e, hit]);
  }
  scored.sort((a, b) => b[0] - a[0] ||
    (a[1].p + a[1].i).localeCompare(b[1].p + b[1].i));
  const h = document.getElementById('hazards');
  h.innerHTML = scored.length
    ? '<div class="panel"><ul>' + scored.slice(0, 14).map(([s, e, hit]) =>
        '<li>' + (e.b ? '<span class="bite">!</span> ' : '') +
        '<code>' + e.p + '#' + e.i + '</code> [' +
        hit.map(t => D.tags[t]).join('+') + ']' +
        (e.v ? '' : ' <span class="unver">unverified</span>') +
        (e.r ? '<br>' + e.r : '') + '</li>').join('') +
        '</ul><p class="legend"><span class="bite">!</span> records an actual ' +
        'failure, not just coverage of the area' +
        (D.prose ? '' : ' · look any of these up with <code>brain query</code>') +
        '</p></div>'
    : '<div class="panel">No lesson carries two or more of these tags. ' +
      'On this combination the canon is silent — which is the finding.</div>';

  const f = D.forks.filter(x => x.t.some(t => plan.has(t)));
  document.getElementById('forks').innerHTML = f.length
    ? '<div class="panel"><ul>' + f.map(x => '<li><code>' + x.id + '</code> ' +
        (x.h || x.k) + ' <span class="legend">[' +
        x.t.filter(t => plan.has(t)).map(t => D.tags[t]).join('+') +
        ']</span></li>').join('') + '</ul>' +
        '<p class="legend">Open. Decisions you are about to make silently ' +
        'unless you make them deliberately.</p></div>'
    : '<div class="panel">No open fork sits over this ground.</div>';
}

document.getElementById('foot').innerHTML =
  D.entries.length + ' lessons · ' + D.tags.length + ' tags · as of ' + D.asof +
  ' · computed in your browser, nothing sent anywhere' +
  (D.prose ? '' : ' · structure only, no lesson text embedded');
draw();
</script>
</body></html>
"""
