"""The single-page HTML/CSS/JS UI, served as one string (no external assets)."""

PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LOTRAutofill</title>
<style>
  :root { color-scheme: light dark; --fg:#1c1c1e; --bg:#f5f5f7; --card:#fff;
          --muted:#6b6b70; --accent:#4a6d3b; --border:#dcdce0; --warn:#a15c00; }
  @media (prefers-color-scheme: dark) {
    :root { --fg:#e8e8ea; --bg:#161618; --card:#232326; --muted:#9a9aa0;
            --accent:#7fae63; --border:#37373b; --warn:#e0a336; } }
  * { box-sizing: border-box; }
  body { margin:0; font:15px/1.5 system-ui,Segoe UI,Roboto,sans-serif;
         color:var(--fg); background:var(--bg); }
  header { padding:16px 22px; border-bottom:1px solid var(--border);
           display:flex; align-items:baseline; gap:14px; position:sticky; top:0;
           background:var(--bg); z-index:5; }
  header h1 { font-size:19px; margin:0; }
  header .lib { color:var(--muted); font-size:12px; }
  .tabs { display:flex; gap:6px; padding:12px 22px 0; }
  .tabs button { border:1px solid var(--border); background:var(--card);
    color:var(--fg); padding:7px 14px; border-radius:8px 8px 0 0; cursor:pointer; }
  .tabs button.active { border-bottom-color:var(--card); font-weight:600; }
  main { padding:18px 22px 120px; max-width:900px; }
  .bar { display:flex; gap:14px; align-items:center; flex-wrap:wrap;
         margin-bottom:14px; }
  select, input[type=text], textarea { font:inherit; color:var(--fg);
    background:var(--card); border:1px solid var(--border); border-radius:8px;
    padding:7px 9px; }
  textarea { width:100%; min-height:150px; resize:vertical; }
  .set { background:var(--card); border:1px solid var(--border); border-radius:10px;
         margin-bottom:8px; overflow:hidden; }
  .set > .row { display:flex; align-items:center; gap:10px; padding:10px 12px; }
  .set .name { font-weight:600; flex:1; }
  .count { color:var(--muted); font-size:13px; }
  .badge { font-size:11px; color:var(--warn); border:1px solid var(--warn);
           border-radius:20px; padding:1px 8px; }
  .toggle { cursor:pointer; user-select:none; width:16px; color:var(--muted); }
  .chapters { padding:0 12px 10px 40px; display:none; }
  .chapters.open { display:block; }
  .chapters label { display:flex; align-items:center; gap:8px; padding:3px 0; }
  .footer { position:fixed; bottom:0; left:0; right:0; background:var(--card);
    border-top:1px solid var(--border); padding:12px 22px; display:flex;
    align-items:center; gap:14px; }
  button.go { background:var(--accent); color:#fff; border:none; border-radius:9px;
    padding:10px 18px; font:inherit; font-weight:600; cursor:pointer; }
  button.go:disabled { opacity:.5; cursor:default; }
  .results { margin-top:16px; }
  .result { background:var(--card); border:1px solid var(--border);
    border-radius:8px; padding:10px 12px; margin-bottom:7px; font-size:14px; }
  .result code { font-size:12px; color:var(--muted); word-break:break-all; }
  .hidden { display:none; }
  .muted { color:var(--muted); }
  .err { color:#c0392b; }
</style>
</head>
<body>
<header>
  <h1>🏔️ LOTRAutofill</h1>
  <span class="lib" id="lib"></span>
</header>
<div class="tabs">
  <button id="tab-lib" class="active" onclick="showTab('lib')">Library</button>
  <button id="tab-deck" onclick="showTab('deck')">RingsDB Deck</button>
</div>

<main>
  <div class="bar">
    <label>Card stock
      <select id="stock">
        <option>(S33) Superior Smooth</option>
        <option>(S30) Standard Smooth</option>
        <option>(S27) Smooth</option>
        <option>(M31) Linen</option>
        <option>(P10) Plastic</option>
      </select>
    </label>
    <label><input type="checkbox" id="foil"> Foil</label>
  </div>

  <section id="view-lib">
    <div id="sets" class="muted">Loading library…</div>
  </section>

  <section id="view-deck" class="hidden">
    <p class="muted">Paste a decklist (one card per line, e.g. <code>3x Gandalf</code>)
      or a RingsDB decklist id / URL:</p>
    <textarea id="deck-src" placeholder="3x Gandalf&#10;2 Steward of Gondor&#10;…"></textarea>
    <div style="margin-top:10px"><button class="go" onclick="importDeck()">Import deck → order.xml</button></div>
    <div id="deck-results" class="results"></div>
  </section>
</main>

<div class="footer" id="footer">
  <button class="go" id="genBtn" onclick="generate()" disabled>Generate order.xml</button>
  <span id="selInfo" class="muted">No selection</span>
  <span id="results-inline" class="muted"></span>
</div>

<script>
let LIB = null;

async function load() {
  try {
    const r = await fetch('/api/library');
    LIB = await r.json();
    document.getElementById('lib').textContent = LIB.root;
    renderSets();
  } catch (e) { document.getElementById('sets').innerHTML =
    '<span class="err">Failed to load library: ' + e + '</span>'; }
}

function renderSets() {
  const el = document.getElementById('sets');
  el.className = '';
  el.innerHTML = '';
  LIB.sets.forEach((s, i) => {
    const box = document.createElement('div');
    box.className = 'set';
    const review = s.review_total ? `<span class="badge">${s.review_total} review</span>` : '';
    const toggle = s.has_chapters ? `<span class="toggle" onclick="toggleCh(${i})">▸</span>` : '<span class="toggle"></span>';
    box.innerHTML = `<div class="row">${toggle}
      <input type="checkbox" data-set="${i}" onchange="onSetToggle(${i})">
      <span class="name">${esc(s.name)}</span>
      <span class="count">${s.cards_total} cards${s.has_chapters ? ' · '+s.chapters.length+' ch.' : ''}</span>
      ${review}</div>`;
    if (s.has_chapters) {
      const ch = document.createElement('div');
      ch.className = 'chapters'; ch.id = 'ch-' + i;
      ch.innerHTML = s.chapters.map((c, j) =>
        `<label><input type="checkbox" data-set="${i}" data-ch="${j}" onchange="updateSel()">
          ${esc(c.name)} <span class="count">${c.unique_cards} cards</span></label>`).join('');
      box.appendChild(ch);
    }
    el.appendChild(box);
  });
  updateSel();
}

function toggleCh(i) {
  const ch = document.getElementById('ch-' + i);
  const open = ch.classList.toggle('open');
  event.target.textContent = open ? '▾' : '▸';
}
function onSetToggle(i) {
  const on = document.querySelector(`input[data-set="${i}"]:not([data-ch])`).checked;
  document.querySelectorAll(`#ch-${i} input[data-ch]`).forEach(c => c.checked = on);
  updateSel();
}
function selectedUnits() {
  const units = [];
  LIB.sets.forEach((s, i) => {
    if (!s.has_chapters) {
      if (document.querySelector(`input[data-set="${i}"]:not([data-ch])`).checked)
        units.push({set: s.name, chapter: null});
    } else {
      s.chapters.forEach((c, j) => {
        const cb = document.querySelector(`input[data-set="${i}"][data-ch="${j}"]`);
        if (cb && cb.checked) units.push({set: s.name, chapter: c.name});
      });
    }
  });
  return units;
}
function updateSel() {
  const n = selectedUnits().length;
  document.getElementById('genBtn').disabled = n === 0;
  document.getElementById('selInfo').textContent =
    n ? `${n} order file(s) selected` : 'No selection';
}

async function generate() {
  const btn = document.getElementById('genBtn');
  btn.disabled = true; document.getElementById('selInfo').textContent = 'Generating…';
  const body = { units: selectedUnits(), stock: stock.value, foil: foil.checked };
  try {
    const r = await fetch('/api/pick', {method:'POST', body: JSON.stringify(body)});
    const d = await r.json();
    if (d.error) throw new Error(d.error);
    const out = d.results.map(x =>
      `<div class="result"><b>${esc(x.label)}</b> — ${x.cards} cards, ${x.fronts} fronts<br>
       <code>${esc(x.order_xml)}</code></div>`).join('');
    let panel = document.getElementById('lib-results');
    if (!panel) { panel = document.createElement('div'); panel.id='lib-results';
      panel.className='results'; document.getElementById('view-lib').appendChild(panel); }
    panel.innerHTML = '<h3>Generated</h3>' + out;
  } catch (e) { alert('Error: ' + e.message); }
  updateSel();
}

async function importDeck() {
  const res = document.getElementById('deck-results');
  res.innerHTML = '<span class="muted">Importing…</span>';
  const body = { source: document.getElementById('deck-src').value,
                 stock: stock.value, foil: foil.checked };
  try {
    const r = await fetch('/api/deck', {method:'POST', body: JSON.stringify(body)});
    const d = await r.json();
    if (d.error) throw new Error(d.error);
    let html = `<div class="result"><b>${esc(d.deck)}</b> — ${d.cards} cards
      (${d.resolved} resolved)<br><code>${esc(d.order_xml)}</code></div>`;
    if (d.unmatched.length) html += `<div class="result err">Unmatched: ${d.unmatched.map(esc).join(', ')}</div>`;
    if (d.missing_images.length) html += `<div class="result">No image: ${d.missing_images.map(esc).join(', ')}</div>`;
    res.innerHTML = html;
  } catch (e) { res.innerHTML = '<span class="err">Error: ' + e.message + '</span>'; }
}

function showTab(t) {
  document.getElementById('view-lib').classList.toggle('hidden', t !== 'lib');
  document.getElementById('view-deck').classList.toggle('hidden', t !== 'deck');
  document.getElementById('footer').classList.toggle('hidden', t !== 'lib');
  document.getElementById('tab-lib').classList.toggle('active', t === 'lib');
  document.getElementById('tab-deck').classList.toggle('active', t === 'deck');
}
function esc(s){ return String(s).replace(/[&<>"]/g, c =>
  ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }

load();
</script>
</body>
</html>
"""
