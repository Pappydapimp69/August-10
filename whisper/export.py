"""Ship the village to the browser.

The simulation is a pure function of its seed, so there is nothing to re-run at
play time: the whole world is generated here, once, and the page is a pure
interrogation surface over it. No game logic is written twice, which matters
because a rule reimplemented in JavaScript is a rule that will drift from the
one the tests cover.

What the page must not contain is the answer in a form the DOM will hand over.
The truth ships (it has to — the accusation is checked client-side), but the
belief graph does the work: the page renders only what the player has actually
been told, and the win check is the last thing consulted, not the source of the
displayed state.
"""

import html
import json

from .world import FACTS, build


def payload(seed, config=None):
    world = build(seed, config)
    return {
        "seed": world["seed"],
        "budget": world["config"]["budget"],
        "people": world["people"],
        "start": world["start"],
        "truth": world["truth"],
        "beliefs": {
            person: {
                fact: {
                    "v": held["value"],
                    "f": held["from"],
                    "h": held["hops"],
                    "w": 1 if held["first_hand"] else 0,
                }
                for fact, held in facts.items()
            }
            for person, facts in world["beliefs"].items()
        },
    }


def render(seeds):
    worlds = [payload(s) for s in seeds]
    return TEMPLATE.replace("__WORLDS__", json.dumps(worlds, separators=(",", ":")))


TEMPLATE = r"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Whisper — a game of attribution</title>
<style>
  :root{color-scheme:dark;--bg:#11100f;--panel:#1a1917;--ink:#e6ded2;--dim:#8d8578;
        --line:#2e2b27;--gold:#d8a657;--red:#e07a5f;--green:#a3b18a}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--ink);
       font:16px/1.6 Georgia,"Iowan Old Style",serif}
  .wrap{max-width:820px;margin:0 auto;padding:2.2rem 1.1rem 4rem}
  h1{font-size:1.8rem;margin:0 0 .1rem;letter-spacing:.01em}
  .sub{color:var(--dim);margin:0 0 1.4rem;font-size:.95rem}
  .bar{display:flex;gap:1.1rem;align-items:center;flex-wrap:wrap;
       background:var(--panel);border:1px solid var(--line);border-radius:8px;
       padding:.6rem .9rem;margin-bottom:1.2rem;font-size:.9rem}
  .bar b{color:var(--gold)}
  button{font:inherit;font-size:.9rem;background:#23211e;color:var(--ink);
         border:1px solid var(--line);border-radius:6px;padding:.35rem .75rem;
         cursor:pointer}
  button:hover:not(:disabled){border-color:var(--gold)}
  button:disabled{opacity:.35;cursor:not-allowed}
  .people{display:flex;flex-wrap:wrap;gap:.4rem;margin:.5rem 0 1.4rem}
  .who{border-color:var(--gold);color:var(--gold)}
  h2{font-size:.78rem;text-transform:uppercase;letter-spacing:.1em;color:var(--dim);
     margin:1.6rem 0 .5rem;font-weight:normal}
  .entry{background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--line);
         border-radius:6px;padding:.7rem .95rem;margin-bottom:.5rem}
  .entry.first{border-left-color:var(--green)}
  .entry .name{color:var(--gold);font-weight:bold}
  .entry p{margin:.3rem 0 0}
  .src{color:var(--dim);font-size:.88rem}
  .saw{color:var(--green);font-size:.88rem}
  .none{color:var(--dim);font-style:italic}
  .accuse{display:flex;flex-wrap:wrap;gap:.4rem;margin-top:.5rem}
  .verdict{border-radius:8px;padding:1rem 1.1rem;margin-top:1.2rem;
           border:1px solid var(--line);background:var(--panel)}
  .verdict.win{border-color:var(--green)}
  .verdict.lose{border-color:var(--red)}
  .verdict h3{margin:0 0 .4rem;font-size:1.05rem}
  .win h3{color:var(--green)} .lose h3{color:var(--red)}
  footer{margin-top:2.5rem;padding-top:1rem;border-top:1px solid var(--line);
         color:var(--dim);font-size:.85rem}

  .nav{display:flex;gap:.15rem;flex-wrap:wrap;margin:0 0 1.5rem;
       border-bottom:1px solid var(--line);padding-bottom:.6rem}
  .nav a{color:var(--dim);text-decoration:none;padding:.3rem .7rem;border-radius:6px;
         font-size:.88rem}
  .nav a:hover{color:var(--ink);background:rgba(255,255,255,.05)}
  .nav a[aria-current="page"]{color:var(--gold);font-weight:600;
         background:rgba(255,255,255,.06)}
  code{background:#0d0c0b;border:1px solid var(--line);border-radius:4px;
       padding:.03rem .3rem;font-size:.85em;font-family:ui-monospace,monospace}
</style>
</head><body><div class="wrap">

<nav class="nav" aria-label="Pages">
  <a href="index.html">the graph</a>
  <a href="console.html">pre-mortem console</a>
  <a href="whisper.html" aria-current="page">whisper (game)</a>
</nav>

<h1>Whisper</h1>
<p class="sub">Something happened in the village last night. Everyone has heard
about it. Almost no one saw it.</p>

<div class="bar">
  <span>Case <b id="case"></b></span>
  <span>Interviews left <b id="left"></b></span>
  <button id="again" type="button">new case</button>
</div>

<h2>Who will you talk to?</h2>
<div class="people" id="people"></div>

<h2>Your notebook</h2>
<div id="notebook"></div>

<h2>Name the culprit</h2>
<div class="accuse" id="accuse"></div>

<div id="verdict"></div>

<footer>
Each villager repeats what they were told and says who told them. Follow that
backwards and you reach someone who was actually there — they are the only ones
worth believing. The version most of the village agrees on is correct
<b>33.7%</b> of the time — measured over 300 seeds, and pinned by a test.
<br><br>
Every case is a pure function of its seed: no clocks, no ambient randomness, and
each draw addressed by name rather than by turn, so case <code>7</code> is the
same village on any machine, forever.
</footer>
</div>

<script>
const WORLDS = __WORLDS__;
const FACTS = ["who", "where", "when"];
const PHRASE = {who: "it was", where: "it happened at", when: "it was"};
let W, asked, done;

function start(i) {
  W = WORLDS[i % WORLDS.length];
  asked = [];
  done = null;
  interview(W.start);
}

function interview(name) {
  if (done || asked.includes(name) || asked.length >= W.budget) return;
  asked.push(name);
  if (asked.length >= W.budget) { /* out of interviews; accusation still open */ }
  draw();
}

function accuse(name) {
  done = {pick: name, right: name === W.truth.who};
  draw();
}

function draw() {
  document.getElementById('case').textContent = W.seed;
  document.getElementById('left').textContent =
    Math.max(0, W.budget - asked.length) + ' / ' + W.budget;

  const people = document.getElementById('people');
  people.innerHTML = '';
  W.people.forEach(p => {
    const b = document.createElement('button');
    b.type = 'button'; b.textContent = p;
    b.disabled = !!done || asked.includes(p) || asked.length >= W.budget;
    if (asked.includes(p)) b.classList.add('who');
    b.onclick = () => interview(p);
    people.appendChild(b);
  });

  const nb = document.getElementById('notebook');
  nb.innerHTML = '';
  if (!asked.length) nb.innerHTML = '<p class="none">Nothing yet.</p>';
  asked.forEach(p => {
    const held = W.beliefs[p] || {};
    const lines = FACTS.filter(f => held[f]).map(f => {
      const b = held[f];
      const said = '&ldquo;' + PHRASE[f] + ' <b>' + b.v + '</b>&rdquo;';
      const tail = b.w
        ? '<span class="saw">— they saw it themselves</span>'
        : '<span class="src">— heard from <b>' + b.f + '</b></span>';
      return '<p>' + said + ' ' + tail + '</p>';
    });
    const div = document.createElement('div');
    div.className = 'entry' + (FACTS.some(f => held[f] && held[f].w) ? ' first' : '');
    div.innerHTML = '<span class="name">' + p + '</span>' +
      (lines.length ? lines.join('') : '<p class="none">knows nothing about it</p>');
    nb.appendChild(div);
  });

  const acc = document.getElementById('accuse');
  acc.innerHTML = '';
  W.people.forEach(p => {
    const b = document.createElement('button');
    b.type = 'button'; b.textContent = p; b.disabled = !!done;
    b.onclick = () => accuse(p);
    acc.appendChild(b);
  });

  const v = document.getElementById('verdict');
  if (!done) { v.innerHTML = ''; return; }
  const t = W.truth;
  v.className = 'verdict ' + (done.right ? 'win' : 'lose');
  v.innerHTML = '<h3>' + (done.right ? 'You had it.' : 'Wrong.') + '</h3>' +
    '<p>It was <b>' + t.who + '</b>, at ' + t.where + ', ' + t.when + '.' +
    ' You accused <b>' + done.pick + '</b> after ' + asked.length +
    ' interview' + (asked.length === 1 ? '' : 's') + '.</p>';
}

document.getElementById('again').onclick =
  () => start(Math.floor(Math.random() * WORLDS.length));
start(0);
</script>
</body></html>
"""
