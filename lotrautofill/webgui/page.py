"""The single-page HTML/CSS/JS UI, served as one string (no external assets)."""

PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LOTRAutofill</title>
<style>
  :root {
    --bg:#161009; --bg2:#1e160c; --card:#251c10; --fg:#ece0c4; --muted:#a08e6c;
    --gold:#c8a13a; --gold-soft:#8a6f28; --accent:#5c7a3f; --border:#4a3a1e;
    --warn:#d9a53a; --err:#d9694f;
  }
  * { box-sizing:border-box; }
  body { margin:0; background:
      radial-gradient(1200px 500px at 50% -220px, #2a2010 0%, var(--bg) 60%);
    color:var(--fg); font:15px/1.55 "Palatino Linotype","Book Antiqua",Georgia,serif; }
  h1,h2,h3 { font-family:"Trajan Pro","Palatino Linotype",Georgia,serif;
    letter-spacing:.5px; font-weight:600; }
  header { padding:18px 24px 14px; text-align:center;
    border-bottom:1px solid var(--border);
    background:linear-gradient(#1e1509,#160f07); }
  header h1 { margin:0; font-size:24px; color:var(--gold);
    text-shadow:0 1px 0 #000, 0 0 18px rgba(200,161,58,.25); }
  header .lib { color:var(--muted); font-size:12px; margin-top:2px; }
  .rule { height:2px; margin:0; border:0;
    background:linear-gradient(90deg,transparent,var(--gold-soft),transparent); }
  .tabs { display:flex; gap:6px; justify-content:center; padding:12px 0 0; }
  .tabs button { border:1px solid var(--border); background:var(--card);
    color:var(--muted); padding:7px 16px; border-radius:8px 8px 0 0; cursor:pointer;
    font-family:inherit; }
  .tabs button.active { color:var(--gold); border-bottom-color:var(--card);
    font-weight:600; }
  main { padding:16px 24px 150px; max-width:920px; margin:0 auto; }
  .bar { display:flex; gap:16px; align-items:center; flex-wrap:wrap;
    margin-bottom:16px; background:var(--card); border:1px solid var(--border);
    border-radius:10px; padding:12px 14px; }
  .bar label { font-size:13px; color:var(--muted); display:flex; gap:6px;
    align-items:center; }
  select, input[type=text], textarea { font:inherit; font-size:14px; color:var(--fg);
    background:var(--bg2); border:1px solid var(--border); border-radius:7px;
    padding:6px 8px; }
  textarea { width:100%; min-height:150px; resize:vertical; font-family:inherit; }
  .set { background:var(--card); border:1px solid var(--border); border-radius:10px;
    margin-bottom:8px; overflow:hidden; }
  .set.unavailable { opacity:.5; }
  .set > .row { display:flex; align-items:center; gap:10px; padding:10px 12px; }
  .set .name { font-weight:600; flex:1; color:var(--fg); }
  .count { color:var(--muted); font-size:13px; }
  .badge { font-size:11px; border-radius:20px; padding:1px 8px; cursor:pointer;
    color:var(--warn); border:1px solid var(--gold-soft); }
  .badge.grey { color:var(--muted); border-color:var(--border); cursor:default; }
  .toggle { cursor:pointer; user-select:none; width:16px; color:var(--gold); }
  .panel { padding:0 12px 10px 42px; display:none; }
  .panel.open { display:block; }
  .panel label.ch { display:flex; align-items:center; gap:8px; padding:3px 0; }
  input[type=checkbox] { accent-color:var(--accent); width:15px; height:15px; }
  .miss { color:var(--warn); font-size:12px; margin:4px 0 6px; }
  .miss ul { margin:4px 0 4px 16px; padding:0; columns:2; }
  .prev { font-size:12px; color:var(--gold); cursor:pointer; user-select:none; }
  .thumbs { display:flex; flex-wrap:wrap; gap:6px; margin:6px 0; max-height:360px;
    overflow:auto; padding:4px; background:var(--bg2); border-radius:8px; }
  .thumb { width:84px; text-align:center; }
  .thumb img { width:84px; height:auto; border-radius:4px; border:1px solid var(--border);
    background:#0d0906; }
  .thumb .cap { font-size:10px; color:var(--muted); line-height:1.2;
    overflow:hidden; max-height:24px; }
  .footer { position:fixed; bottom:0; left:0; right:0; background:#140e06;
    border-top:1px solid var(--gold-soft); padding:12px 24px; display:flex;
    align-items:center; gap:12px; flex-wrap:wrap; }
  button.go { background:linear-gradient(#c8a13a,#9c7c26); color:#20180a;
    border:1px solid #6f5716; border-radius:9px; padding:10px 16px; font:inherit;
    font-weight:700; cursor:pointer; }
  button.go.ghost { background:transparent; color:var(--gold);
    border:1px solid var(--gold-soft); font-weight:600; }
  button.go:disabled { opacity:.45; cursor:default; }
  button.mini { font-size:12px; padding:5px 10px; }
  .results { margin-top:18px; }
  .result { background:var(--card); border:1px solid var(--border);
    border-radius:8px; padding:10px 12px; margin-bottom:8px; font-size:14px;
    display:flex; align-items:center; gap:12px; justify-content:space-between; }
  .result code { font-size:12px; color:var(--muted); word-break:break-all; }
  .hidden { display:none; }
  .muted { color:var(--muted); }
  .err { color:var(--err); }
  .pagefoot { text-align:center; color:var(--gold-soft); font-size:12px;
    padding:22px 0 6px; letter-spacing:1px; }
</style>
</head>
<body>
<header>
  <h1>The One Deck · LOTRAutofill</h1>
  <div class="lib" id="lib"></div>
</header>
<hr class="rule">
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
    <label>Encounter back <select id="encBack"></select></label>
    <label>Player back <select id="plyBack"></select></label>
    <label><input type="checkbox" id="foil"> Foil</label>
  </div>

  <section id="view-lib">
    <div id="sets" class="muted">Loading the archives of Middle-earth…</div>
    <div id="lib-results" class="results"></div>
  </section>

  <section id="view-deck" class="hidden">
    <p class="muted">Paste a decklist (one card per line, e.g. <code>3x Gandalf</code>)
      or a RingsDB decklist id / URL:</p>
    <textarea id="deck-src" placeholder="3x Gandalf&#10;2 Steward of Gondor&#10;…"></textarea>
    <div style="margin-top:10px">
      <button class="go" onclick="importDeck()">Import deck → order.xml</button>
    </div>
    <div id="deck-results" class="results"></div>
  </section>

  <div class="pagefoot">⚔ &nbsp; by hasyame — for personal use only &nbsp; ⚔</div>
</main>

<div class="footer" id="footer">
  <button class="go" id="genBtn" onclick="generate(false)" disabled>Generate order.xml</button>
  <button class="go ghost" id="genGoBtn" onclick="generate(true)" disabled>
    Generate + create MPC project</button>
  <span id="selInfo" class="muted">No selection</span>
</div>

<script>
let LIB = null;

async function load() {
  try {
    const [lib, backs] = await Promise.all([
      fetch('/api/library').then(r => r.json()),
      fetch('/api/backs').then(r => r.json()),
    ]);
    LIB = lib;
    document.getElementById('lib').textContent = LIB.root;
    fillBacks(backs);
    renderSets();
  } catch (e) { document.getElementById('sets').innerHTML =
    '<span class="err">Failed to load: ' + e + '</span>'; }
}

function fillBacks(b) {
  const fill = (sel, opts, def) => { sel.innerHTML = opts.map(o =>
    `<option ${o === def ? 'selected' : ''}>${esc(o)}</option>`).join(''); };
  fill(document.getElementById('encBack'), b.encounter, b.default_encounter);
  fill(document.getElementById('plyBack'), b.player, b.default_player);
}

function renderSets() {
  const el = document.getElementById('sets');
  el.className = ''; el.innerHTML = '';
  LIB.sets.forEach((s, i) => el.appendChild(setRow(s, i)));
  (LIB.unavailable_sets || []).forEach(name => {
    const box = document.createElement('div');
    box.className = 'set unavailable';
    box.innerHTML = `<div class="row"><span class="toggle"></span>
      <input type="checkbox" disabled>
      <span class="name">${esc(name)}</span>
      <span class="count">not in your library</span></div>`;
    el.appendChild(box);
  });
  updateSel();
}

function setRow(s, i) {
  const box = document.createElement('div');
  box.className = 'set' + (s.cards_total === 0 ? ' unavailable' : '');
  const dis = s.cards_total === 0 ? 'disabled' : '';
  const miss = s.missing_total
    ? `<span class="badge" onclick="openMiss(${i},event)">Cards missing (${s.missing_total})</span>` : '';
  box.innerHTML = `<div class="row">
    <span class="toggle" onclick="togglePanel(${i})">▸</span>
    <input type="checkbox" data-set="${i}" ${dis} onchange="onSetToggle(${i})">
    <span class="name">${esc(s.name)}</span>
    <span class="count">${s.cards_total} cards${s.has_chapters ? ' · '+s.chapters.length+' ch.' : ''}</span>
    ${miss}</div>
    <div class="panel" id="panel-${i}"></div>`;
  return box;
}

function togglePanel(i) {
  const p = document.getElementById('panel-' + i);
  const open = p.classList.toggle('open');
  event.target.textContent = open ? '▾' : '▸';
  if (open && !p.dataset.built) { p.dataset.built = '1'; buildPanel(i, p); }
}

function buildPanel(i, p) {
  const s = LIB.sets[i];
  if (s.has_chapters) {
    p.innerHTML = s.chapters.map((c, j) => {
      const miss = c.missing && c.missing.length
        ? `<span class="badge" onclick="showMiss(document.getElementById('miss-${i}-${j}'),LIB.sets[${i}].chapters[${j}].missing);event.stopPropagation()">missing ${c.missing.length}</span>` : '';
      return `<div>
        <label class="ch"><input type="checkbox" data-set="${i}" data-ch="${j}" onchange="updateSel()">
          ${esc(c.name)} <span class="count">${c.unique_cards} cards</span> ${miss}
          <span class="prev" onclick="loadCards(${i},${j})">preview ▾</span></label>
        <div id="miss-${i}-${j}"></div>
        <div id="thumbs-${i}-${j}"></div></div>`;
    }).join('');
  } else {
    p.innerHTML = `<div id="miss-${i}-x"></div>
      <span class="prev" onclick="loadCards(${i},null)">preview cards ▾</span>
      <div id="thumbs-${i}-x"></div>`;
  }
}

function openMiss(i, ev) {
  ev.stopPropagation();
  const p = document.getElementById('panel-' + i);
  if (!p.dataset.built) { p.dataset.built = '1'; buildPanel(i, p); }
  if (!p.classList.contains('open')) { p.classList.add('open');
    const t = p.parentElement.querySelector('.toggle'); if (t) t.textContent = '▾'; }
  const s = LIB.sets[i];
  if (!s.has_chapters)
    showMiss(document.getElementById(`miss-${i}-x`), s.chapters[0].missing);
}
function showMiss(host, list) {
  if (!host) return;
  if (host.dataset.shown) { host.innerHTML = ''; host.dataset.shown = ''; return; }
  host.dataset.shown = '1';
  host.innerHTML = '<div class="miss"><b>Missing cards:</b><ul>' +
    (list || []).map(m => '<li>' + esc(m) + '</li>').join('') + '</ul></div>';
}

async function loadCards(i, j) {
  const s = LIB.sets[i];
  const host = document.getElementById(`thumbs-${i}-${j === null ? 'x' : j}`);
  if (host.dataset.loaded) { host.innerHTML = ''; host.dataset.loaded = ''; return; }
  host.innerHTML = '<span class="muted">loading previews…</span>';
  const chapter = j === null ? '' : s.chapters[j].name;
  const q = new URLSearchParams({ set: s.name, chapter });
  try {
    const d = await (await fetch('/api/cards?' + q)).json();
    host.dataset.loaded = '1';
    host.innerHTML = '<div class="thumbs">' + d.cards.map(c =>
      `<div class="thumb"><img loading="lazy" src="/api/thumb?p=${encodeURIComponent(c.front)}" alt="">
        <div class="cap">${esc(c.name)}</div></div>`).join('') + '</div>';
  } catch (e) { host.innerHTML = '<span class="err">Preview failed: ' + e + '</span>'; }
}

function onSetToggle(i) {
  const on = document.querySelector(`input[data-set="${i}"]:not([data-ch])`).checked;
  document.querySelectorAll(`#panel-${i} input[data-ch]`).forEach(c => c.checked = on);
  updateSel();
}
function selectedUnits() {
  const units = [];
  LIB.sets.forEach((s, i) => {
    if (s.cards_total === 0) return;
    if (!s.has_chapters) {
      const cb = document.querySelector(`input[data-set="${i}"]:not([data-ch])`);
      if (cb && cb.checked) units.push({set: s.name, chapter: null});
    } else {
      const anyCh = document.querySelectorAll(`#panel-${i} input[data-ch]:checked`);
      if (anyCh.length) anyCh.forEach(cb =>
        units.push({set: s.name, chapter: s.chapters[+cb.dataset.ch].name}));
      else if (document.querySelector(`input[data-set="${i}"]:not([data-ch])`).checked)
        s.chapters.forEach(c => units.push({set: s.name, chapter: c.name}));
    }
  });
  return units;
}
function updateSel() {
  const n = selectedUnits().length;
  document.getElementById('genBtn').disabled = n === 0;
  document.getElementById('genGoBtn').disabled = n === 0;
  document.getElementById('selInfo').textContent =
    n ? `${n} order file(s) selected` : 'No selection';
}

function orderBody() {
  return { units: selectedUnits(), stock: stock.value, foil: foil.checked,
           encounter_back: encBack.value, player_back: plyBack.value };
}
async function generate(alsoCreate) {
  document.getElementById('genBtn').disabled = true;
  document.getElementById('genGoBtn').disabled = true;
  document.getElementById('selInfo').textContent = 'Forging order files…';
  try {
    const d = await postJSON('/api/pick', orderBody());
    if (d.error) throw new Error(d.error);
    renderResults(d.results);
    if (alsoCreate) for (const x of d.results) await createProject(x.order_xml, null);
  } catch (e) { alert('Error: ' + e.message); }
  updateSel();
}
function renderResults(results) {
  const panel = document.getElementById('lib-results');
  panel.innerHTML = '<h3>Forged</h3>' + results.map(x =>
    `<div class="result"><div><b>${esc(x.label)}</b> — ${x.cards} cards, ${x.fronts} fronts
      <br><code>${esc(x.order_xml)}</code></div>
      <button class="go ghost mini" data-xml="${esc(x.order_xml)}">Create MPC project</button>
     </div>`).join('');
  wireCreateButtons(panel);
}
function wireCreateButtons(panel) {
  panel.querySelectorAll('button[data-xml]').forEach(b =>
    b.onclick = () => createProject(b.dataset.xml, b));
}
async function createProject(orderXml, btn) {
  if (btn) { btn.disabled = true; btn.textContent = 'Launching…'; }
  try {
    const d = await postJSON('/api/autofill', { order_xml: orderXml });
    if (d.error) throw new Error(d.error);
    if (btn) btn.textContent = 'MPC tool launched ✓';
  } catch (e) { alert('Error: ' + e.message); if (btn) { btn.disabled = false; btn.textContent = 'Create MPC project'; } }
}
async function importDeck() {
  const res = document.getElementById('deck-results');
  res.innerHTML = '<span class="muted">Summoning cards from RingsDB…</span>';
  try {
    const d = await postJSON('/api/deck', { source: document.getElementById('deck-src').value,
      stock: stock.value, foil: foil.checked });
    if (d.error) throw new Error(d.error);
    let html = `<div class="result"><div><b>${esc(d.deck)}</b> — ${d.cards} cards
      (${d.resolved} resolved)<br><code>${esc(d.order_xml)}</code></div>
      <button class="go ghost mini" data-xml="${esc(d.order_xml)}">Create MPC project</button></div>`;
    if (d.unmatched.length) html += `<div class="result err">Unmatched: ${d.unmatched.map(esc).join(', ')}</div>`;
    if (d.missing_images.length) html += `<div class="result">No image: ${d.missing_images.map(esc).join(', ')}</div>`;
    res.innerHTML = html; wireCreateButtons(res);
  } catch (e) { res.innerHTML = '<span class="err">Error: ' + e.message + '</span>'; }
}
async function postJSON(url, body) {
  const r = await fetch(url, {method:'POST', body: JSON.stringify(body)});
  return r.json();
}
function showTab(t) {
  document.getElementById('view-lib').classList.toggle('hidden', t !== 'lib');
  document.getElementById('view-deck').classList.toggle('hidden', t !== 'deck');
  document.getElementById('footer').classList.toggle('hidden', t !== 'lib');
  document.getElementById('tab-lib').classList.toggle('active', t === 'lib');
  document.getElementById('tab-deck').classList.toggle('active', t === 'deck');
}
function esc(s){ return String(s).replace(/[&<>"']/g, c =>
  ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

load();
</script>
</body>
</html>
"""
