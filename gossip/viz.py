"""A self-contained HTML page of what gossip found.

The layout is computed here, in python, and is **deterministic** — community
centres on a ring, members on a sub-ring, positions a pure function of the
canon. No physics simulation, no RNG, no layout that settles differently on
each load. Two runs over the same canon produce byte-identical HTML, so a diff
of the page is a diff of the knowledge rather than of a random seed. That is the
same discipline the canon it renders keeps about itself.

Hearsay edges are drawn dashed, following the convention `brain viz --film`
already uses for prose-mined edges: tension T26 is open on exactly whether they
are real, so the page shows the doubt instead of flattening it.
"""

import html
import math

from . import confidence, seams
from .canon import short

PALETTE = [
    "#7aa2f7", "#bb9af7", "#7dcfff", "#9ece6a", "#e0af68",
    "#f7768e", "#73daca", "#c0caf5", "#ff9e64", "#b4f9f8",
    "#a9b1d6", "#ff75a0", "#41a6b5",
]

W, H = 1200, 900
CX, CY = W / 2, H / 2


def _positions(partition, singleton_ring=True):
    """{node: (x, y)} — communities on a ring, members on a sub-ring."""
    sized = [(lb, m) for lb, m in partition if len(m) > 1]
    singles = [n for lb, m in partition if len(m) == 1 for n in m]

    pos, colour = {}, {}
    outer = min(W, H) * 0.36
    for i, (label, members) in enumerate(sized):
        angle = 2 * math.pi * i / max(1, len(sized)) - math.pi / 2
        cx = CX + outer * math.cos(angle)
        cy = CY + outer * math.sin(angle)
        radius = 26 + 5.5 * len(members)
        for j, node in enumerate(members):
            a = 2 * math.pi * j / len(members)
            pos[node] = (cx + radius * math.cos(a), cy + radius * math.sin(a))
            colour[node] = PALETTE[i % len(PALETTE)]

    if singleton_ring and singles:
        edge = min(W, H) * 0.47
        for k, node in enumerate(singles):
            a = 2 * math.pi * k / len(singles) - math.pi / 2
            pos[node] = (CX + edge * math.cos(a), CY + edge * math.sin(a))
            colour[node] = "#3b4261"
    return pos, colour


def _svg(ctx):
    edges, scores = ctx["kept"], ctx["scores"]
    pos, colour = _positions(ctx["partition"])
    reaches = seams.reach(edges)

    parts = [f'<svg viewBox="0 0 {W} {H}" role="img" '
             'aria-label="co-verification graph by community">']

    for (a, b), rec in sorted(edges.items()):
        if a not in pos or b not in pos:
            continue
        x1, y1 = pos[a]
        x2, y2 = pos[b]
        conf = scores[(a, b)]
        hearsay = rec["hearsay"] and not rec["witness"]
        same = colour.get(a) == colour.get(b) and colour.get(a) != "#3b4261"
        parts.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{colour[a] if same else "#565f89"}" '
            f'stroke-width="{0.5 + 2.6 * conf:.2f}" '
            f'stroke-opacity="{0.16 + 0.5 * conf:.2f}"'
            + (' stroke-dasharray="4 3"' if hearsay else "") + "/>")

    for node in sorted(pos):
        x, y = pos[node]
        r = 3.2 + 0.42 * min(reaches.get(node, 0), 26)
        parts.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{colour[node]}" '
            f'fill-opacity="0.9" stroke="#1a1b26" stroke-width="1.2">'
            f'<title>{html.escape(short(node))} · reach {reaches.get(node, 0)}</title>'
            "</circle>")

    for node in sorted(pos):
        if reaches.get(node, 0) < 7:
            continue
        x, y = pos[node]
        parts.append(
            f'<text x="{x:.1f}" y="{y - 9:.1f}" text-anchor="middle" '
            f'font-size="10.5" fill="#c0caf5">{html.escape(short(node))}</text>')

    parts.append("</svg>")
    return "\n".join(parts)


def _row(cells, tag="td"):
    return "<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in cells) + "</tr>"


def render(ctx):
    edges, scores, kept = ctx["edges"], ctx["scores"], ctx["kept"]
    from .graph import components

    comps = components(edges)
    sized = [g for g in ctx["partition"] if len(g[1]) > 1]
    wit = sum(1 for e in edges.values() if e["witness"] and not e["hearsay"])
    hear = sum(1 for e in edges.values() if e["hearsay"] and not e["witness"])
    mixed = len(edges) - wit - hear
    veto = sum(1 for e in edges.values() if confidence.vetoed(e))

    stats = [
        (len(ctx["entries"]), "lessons"),
        (len(ctx["node_tags"]), "systems"),
        (len(kept), "confident edges"),
        (veto, "vetoed (T26)"),
        (len(sized), "communities"),
        (f"{ctx['modularity']:.3f}", "modularity Q"),
    ]
    stat_html = "".join(
        f'<div class="stat"><b>{v}</b><span>{html.escape(str(k))}</span></div>'
        for v, k in stats)

    top_edges = sorted(kept, key=lambda k: (-scores[k], k))[:12]
    edge_rows = "".join(_row([
        f"{scores[k]:.3f}",
        html.escape(short(k[0])),
        html.escape(short(k[1])),
        "witness" if edges[k]["witness"] and not edges[k]["hearsay"]
        else ("hearsay" if edges[k]["hearsay"] and not edges[k]["witness"] else "mixed"),
        str(len(edges[k]["sources"])),
        "safe" if edges[k]["safe"] else "",
    ]) for k in top_edges)

    seam_rows = "".join(_row([
        f"{s:.2f}",
        html.escape(short(a)),
        html.escape(short(b)),
        str(len(sh)),
        f"{d['reach'][0]}/{d['reach'][1]}",
        f"{d['drama']:.2f}",
    ]) for s, a, b, sh, d in seams.rank(kept, ctx["node_tags"], ctx["node_entries"], limit=12))

    community_html = "".join(
        f'<details><summary><i style="background:{PALETTE[i % len(PALETTE)]}"></i>'
        f"community {i + 1} · {len(m)} systems · anchor "
        f"<code>{html.escape(short(lb))}</code></summary><p>"
        + " ".join(f"<code>{html.escape(short(n))}</code>" for n in m)
        + "</p></details>"
        for i, (lb, m) in enumerate(sized))

    return TEMPLATE.format(
        asof=html.escape(ctx["asof"]),
        stats=stat_html,
        svg=_svg(ctx),
        components=len(comps),
        largest=len(comps[0]) if comps else 0,
        n_comm=len(sized),
        largest_comm=len(sized[0][1]) if sized else 0,
        agreement=f"{ctx['agreement']:.2f}",
        witness=wit, hearsay=hear, mixed=mixed, vetoed=veto,
        wit_pct=100 * wit / max(1, len(edges)),
        mix_pct=100 * mixed / max(1, len(edges)),
        hear_pct=100 * hear / max(1, len(edges)),
        edge_rows=edge_rows,
        seam_rows=seam_rows,
        communities=community_html,
    )


TEMPLATE = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>gossip — the co-verification graph as a social network</title>
<style>
  :root {{ color-scheme: dark; --bg:#1a1b26; --panel:#1f2335; --ink:#c0caf5;
           --dim:#7f88b0; --line:#2f3549; --accent:#7aa2f7; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--ink);
         font:15px/1.6 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif; }}
  .wrap {{ max-width:1180px; margin:0 auto; padding:2.5rem 1.25rem 4rem; }}
  h1 {{ font-size:1.9rem; margin:0 0 .3rem; letter-spacing:-.02em; }}
  h2 {{ font-size:1.1rem; margin:2.5rem 0 .75rem; color:var(--accent);
        font-weight:600; }}
  .sub {{ color:var(--dim); margin:0 0 2rem; }}
  .stats {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(140px,1fr));
            gap:.75rem; margin-bottom:2rem; }}
  .stat {{ background:var(--panel); border:1px solid var(--line); border-radius:9px;
           padding:.85rem 1rem; }}
  .stat b {{ display:block; font-size:1.5rem; line-height:1.2; }}
  .stat span {{ color:var(--dim); font-size:.82rem; }}
  figure {{ margin:0; background:var(--panel); border:1px solid var(--line);
            border-radius:11px; padding:.5rem; }}
  svg {{ width:100%; height:auto; display:block; }}
  figcaption {{ color:var(--dim); font-size:.85rem; padding:.6rem .9rem 0; }}
  .scroll {{ overflow-x:auto; }}
  table {{ width:100%; border-collapse:collapse; font-size:.88rem;
           min-width:520px; }}
  th,td {{ text-align:left; padding:.45rem .7rem; border-bottom:1px solid var(--line); }}
  th {{ color:var(--dim); font-weight:600; font-size:.78rem;
        text-transform:uppercase; letter-spacing:.05em; }}
  td:first-child {{ font-variant-numeric:tabular-nums; color:var(--accent); }}
  .bar {{ display:flex; height:26px; border-radius:6px; overflow:hidden;
          margin:.5rem 0 .4rem; }}
  .bar i {{ display:block; }}
  .key {{ color:var(--dim); font-size:.85rem; }}
  details {{ background:var(--panel); border:1px solid var(--line);
             border-radius:8px; padding:.6rem .9rem; margin-bottom:.5rem; }}
  summary {{ cursor:pointer; }}
  summary i {{ display:inline-block; width:10px; height:10px; border-radius:3px;
               margin-right:.5rem; }}
  code {{ background:#171822; border:1px solid var(--line); border-radius:4px;
          padding:.05rem .35rem; font-size:.83em; }}
  p {{ max-width:70ch; }}
  footer {{ margin-top:3rem; padding-top:1.25rem; border-top:1px solid var(--line);
            color:var(--dim); font-size:.85rem; }}
  a {{ color:var(--accent); }}
</style>
</head><body><div class="wrap">

<h1>gossip</h1>
<p class="sub">Brain&rsquo;s co-verification graph, read as a social network.
Every figure recomputed from canon &middot; as of {asof}.<br>
&rarr; <a href="console.html"><b>Open the pre-mortem console</b></a> &mdash; name
what you are about to build, see what the canon says will bite it.</p>

<div class="stats">{stats}</div>

<figure>
{svg}
<figcaption>Nodes sized by reach, coloured by community; grey ring = systems in
no confident community. Edge width and opacity are confidence.
<b>Dashed edges are hearsay</b> &mdash; mined from prose, never declared, and
possibly just a name-drop (tension T26 is open on exactly that).</figcaption>
</figure>

<h2>Communities, where brain sees one blob</h2>
<p>Connected components put {largest} of these systems in a single cluster
({components} component in total), which is true and tells you nothing. gossip
clusters on confidence and keeps only what <b>five independent traversals all
agree on</b>: {n_comm} communities, largest {largest_comm}. The traversals
agreed with each other {agreement} of the time underneath that consensus &mdash;
printed rather than hidden, because it is the real uncertainty here.</p>
{communities}

<h2>Who saw it happen</h2>
<div class="bar">
  <i style="width:{wit_pct:.1f}%;background:#9ece6a"></i>
  <i style="width:{mix_pct:.1f}%;background:#e0af68"></i>
  <i style="width:{hear_pct:.1f}%;background:#f7768e"></i>
</div>
<p class="key">{witness} witness-only (declared in a <code>Composed:</code>
field) &middot; {mixed} mixed &middot; {hearsay} hearsay-only (mined from prose).
{vetoed} edges are asserted exactly once, by prose alone &mdash; scored zero,
listed rather than silently dropped.</p>

<h2>Edges by confidence</h2>
<p>witness &times; independence &times; corroboration &times; recency, with a
single zero collapsing the product. An edge whose <code>Got right</code> names
both systems is a pair confirmed <em>compatible</em>, not merely co-tested, and
never decays.</p>
<div class="scroll"><table>
<tr><th>conf</th><th>system</th><th>system</th><th>provenance</th><th>sources</th><th></th></tr>
{edge_rows}
</table></div>

<h2>What to test next</h2>
<p>context &times; novelty &times; drama. Novelty favours the recluse over the
hub &mdash; pairing the two best-connected systems is the least surprising
experiment available &mdash; and drama is the share of the pair&rsquo;s lessons
still unverified, so a good seam retires provenance debt while it adds an edge.</p>
<div class="scroll"><table>
<tr><th>score</th><th>system</th><th>system</th><th>tags</th><th>reach</th><th>drama</th></tr>
{seam_rows}
</table></div>

<footer>Generated by <code>gossip viz</code> &mdash; read-only over
<code>memory/projects</code>. Layout is a pure function of the canon: no RNG, no
physics, no wall-clock, so two runs over the same knowledge produce identical
pages and a visual diff is a diff of what is known.</footer>

</div></body></html>
"""
