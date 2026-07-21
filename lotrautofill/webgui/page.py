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
  a { color:var(--gold); }
  header { padding:14px 24px; display:flex; align-items:center; gap:16px;
    border-bottom:1px solid var(--border); background:linear-gradient(#1e1509,#160f07);
    position:sticky; top:0; z-index:10; }
  header h1 { margin:0; font-size:20px; color:var(--gold); flex:1;
    text-shadow:0 1px 0 #000, 0 0 18px rgba(200,161,58,.25); cursor:pointer; }
  header nav button, .cartbtn { border:1px solid var(--border); background:var(--card);
    color:var(--muted); padding:7px 14px; border-radius:8px; cursor:pointer;
    font-family:inherit; font-size:14px; }
  header nav button.active { color:var(--gold); border-color:var(--gold-soft); }
  .cartbtn { color:var(--gold); border-color:var(--gold-soft); font-weight:600; }
  .cartbtn .n { background:var(--gold); color:#20180a; border-radius:20px;
    padding:0 7px; margin-left:6px; font-weight:700; }
  main { padding:20px 24px 60px; max-width:1000px; margin:0 auto; }
  .grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(180px,1fr));
    gap:16px; }
  .tile { background:var(--card); border:1px solid var(--border); border-radius:12px;
    overflow:hidden; display:flex; flex-direction:column; }
  .tile.dim { opacity:.45; }
  .tile .art { height:170px; background:#0d0906 center/contain no-repeat;
    cursor:pointer; display:flex; align-items:flex-end; }
  .tile .art .miss { margin:6px; font-size:11px; color:#20180a; background:var(--warn);
    border-radius:20px; padding:1px 8px; }
  .tile .body { padding:10px 12px; display:flex; flex-direction:column; gap:8px; flex:1; }
  .tile .nm { font-weight:600; cursor:pointer; }
  .tile .sub { color:var(--muted); font-size:12px; flex:1; }
  button.go { background:linear-gradient(#c8a13a,#9c7c26); color:#20180a;
    border:1px solid #6f5716; border-radius:9px; padding:8px 12px; font:inherit;
    font-weight:700; cursor:pointer; }
  button.go.ghost { background:transparent; color:var(--gold);
    border:1px solid var(--gold-soft); font-weight:600; }
  button.go:disabled { opacity:.45; cursor:default; }
  button.mini { font-size:12px; padding:5px 9px; }
  .back { color:var(--gold); cursor:pointer; user-select:none; margin-bottom:12px;
    display:inline-block; }
  .row { display:flex; align-items:center; gap:10px; padding:9px 0;
    border-bottom:1px solid var(--border); }
  .row .grow { flex:1; }
  .count { color:var(--muted); font-size:13px; }
  .miss-badge { font-size:11px; color:var(--warn); border:1px solid var(--gold-soft);
    border-radius:20px; padding:1px 8px; cursor:pointer; }
  .miss { color:var(--warn); font-size:12px; margin:4px 0; }
  .miss ul { margin:4px 0 4px 16px; columns:2; }
  .thumbs { display:flex; flex-wrap:wrap; gap:8px; margin:8px 0; max-height:420px;
    overflow:auto; padding:6px; background:var(--bg2); border-radius:8px; }
  .thumb { width:96px; text-align:center; position:relative; }
  .thumb img { width:96px; border-radius:4px; border:1px solid var(--border);
    background:#0d0906; }
  .thumb .cap { font-size:10px; color:var(--muted); max-height:24px; overflow:hidden; }
  .thumb .add { position:absolute; top:2px; right:2px; background:var(--gold);
    color:#20180a; border:none; border-radius:6px; width:22px; height:22px;
    font-weight:800; cursor:pointer; }
  .thumb.in .add { background:var(--accent); color:#fff; }
  .bar { display:flex; gap:16px; align-items:center; flex-wrap:wrap; margin:14px 0;
    background:var(--card); border:1px solid var(--border); border-radius:10px;
    padding:12px 14px; }
  .bar label { font-size:13px; color:var(--muted); display:flex; gap:6px; align-items:center; }
  select, input[type=text], textarea { font:inherit; font-size:14px; color:var(--fg);
    background:var(--bg2); border:1px solid var(--border); border-radius:7px; padding:6px 8px; }
  textarea { width:100%; min-height:150px; resize:vertical; font-family:inherit; }
  .cartitem { display:flex; align-items:center; gap:10px; padding:9px 12px;
    background:var(--card); border:1px solid var(--border); border-radius:8px; margin-bottom:6px; }
  .cartitem .x { color:var(--err); cursor:pointer; font-weight:700; }
  .kind { font-size:11px; color:var(--muted); border:1px solid var(--border);
    border-radius:20px; padding:0 8px; }
  .result { background:var(--card); border:1px solid var(--border); border-radius:8px;
    padding:10px 12px; margin-top:10px; font-size:14px; }
  .result code { font-size:12px; color:var(--muted); word-break:break-all; }
  .muted { color:var(--muted); } .err { color:var(--err); } .hidden { display:none; }
  .pagefoot { text-align:center; color:var(--gold-soft); font-size:12px;
    padding:26px 0 6px; letter-spacing:1px; }
</style>
</head>
<body>
<header>
  <h1 onclick="showView('shop')">⛰️ LOTRAutofill</h1>
  <nav>
    <button id="nav-shop" class="active" onclick="showView('shop')">Sets</button>
    <button id="nav-deck" onclick="showView('deck')">Manual List</button>
  </nav>
  <button class="cartbtn" onclick="showView('cart')">🛒 Cart<span class="n" id="cartN">0</span></button>
</header>

<main>
  <div id="view-shop"><div id="shop" class="muted">Loading the archives of Middle-earth…</div></div>
  <div id="view-detail" class="hidden"></div>

  <div id="view-cart" class="hidden">
    <h2>Your cart</h2>
    <div id="cart-list"></div>
    <div class="bar" id="cart-opts">
      <label>Card stock <select id="stock">
        <option>(S33) Superior Smooth</option><option>(S30) Standard Smooth</option>
        <option>(S27) Smooth</option><option>(M31) Linen</option><option>(P10) Plastic</option>
      </select></label>
      <label>Encounter back <select id="encBack"></select></label>
      <label>Player back <select id="plyBack"></select></label>
      <label><input type="checkbox" id="foil"> Foil</label>
    </div>
    <div style="display:flex; gap:10px; flex-wrap:wrap">
      <button class="go" onclick="exportCart('xml')">Export order.xml</button>
      <button class="go ghost" onclick="exportCart('pdf')">Export PDF</button>
      <button class="go ghost" onclick="exportCart('mpc')">Create MPC project</button>
      <button class="go ghost" onclick="clearCart()">Empty cart</button>
    </div>
    <div id="cart-result"></div>
  </div>

  <div id="view-deck" class="hidden">
    <h2>Manual list</h2>
    <p class="muted">Paste a decklist (one card per line, e.g. <code>3x Gandalf</code>)
      or a RingsDB decklist id / URL:</p>
    <textarea id="deck-src" placeholder="3x Gandalf&#10;2 Steward of Gondor&#10;…"></textarea>
    <div style="margin-top:10px"><button class="go" onclick="importDeck()">Import → order.xml</button></div>
    <div id="deck-results"></div>
  </div>

  <div class="pagefoot">⚔ &nbsp; by hasyame — for personal use only &nbsp; ⚔</div>
</main>

<script>
let LIB = null, CART = [];
try { CART = JSON.parse(localStorage.getItem('lotr_cart') || '[]'); } catch(e) {}

async function load() {
  const [lib, backs] = await Promise.all([
    fetch('/api/library').then(r => r.json()),
    fetch('/api/backs').then(r => r.json()),
  ]);
  LIB = lib;
  fillBacks(backs);
  renderShop(); renderCartCount();
}
function fillBacks(b) {
  const fill = (id, opts, def) => { document.getElementById(id).innerHTML =
    opts.map(o => `<option ${o===def?'selected':''}>${esc(o)}</option>`).join(''); };
  fill('encBack', b.encounter, b.default_encounter);
  fill('plyBack', b.player, b.default_player);
}

/* ---------- shop ---------- */
function renderShop() {
  const el = document.getElementById('shop');
  el.className = 'grid';
  el.innerHTML = LIB.sets.map((s, i) => tile(s, i)).join('') +
    (LIB.unavailable_sets || []).map(n =>
      `<div class="tile dim"><div class="art"></div><div class="body">
        <div class="nm">${esc(n)}</div><div class="sub">not in your library</div></div></div>`).join('');
}
function tile(s, i) {
  const art = s.image
    ? `background-image:url('/api/product-image?f=${encodeURIComponent(s.image)}')` : '';
  const dis = s.cards_total === 0 ? 'disabled' : '';
  const missTag = s.missing_total ? `<span class="miss">${s.missing_total} missing</span>` : '';
  return `<div class="tile ${s.cards_total===0?'dim':''}">
    <div class="art" style="${art}" onclick="openDetail(${i})">${missTag}</div>
    <div class="body">
      <div class="nm" onclick="openDetail(${i})">${esc(s.display||s.name)}</div>
      <div class="sub">${s.cards_total} cards${s.has_chapters?' · '+s.chapters.length+' chapters':''}</div>
      <button class="go mini" ${dis} onclick="addSet(${i})">Add set to cart</button>
    </div></div>`;
}

/* ---------- set detail ---------- */
function openDetail(i) {
  const s = LIB.sets[i];
  const el = document.getElementById('view-detail');
  let html = `<span class="back" onclick="showView('shop')">← all sets</span>
    <h2>${esc(s.display||s.name)}</h2>
    <div class="row"><span class="grow count">${s.cards_total} cards</span>
      <button class="go mini" onclick="addSet(${i})">Add whole set</button></div>`;
  if (s.has_chapters) {
    html += s.chapters.map((c, j) => {
      const miss = c.missing && c.missing.length
        ? `<span class="miss-badge" onclick="showMiss('miss-${j}',${i},${j})">missing ${c.missing.length}</span>` : '';
      return `<div><div class="row">
        <span class="grow">${esc(c.display||c.name)} <span class="count">${c.unique_cards} cards</span> ${miss}</span>
        <span class="back" style="margin:0" onclick="loadCards(${i},${j},'cards-${j}')">cards ▾</span>
        <button class="go mini" onclick="addChapter(${i},${j})">Add chapter</button></div>
        <div id="miss-${j}"></div><div id="cards-${j}"></div></div>`;
    }).join('');
  } else {
    html += `<span class="back" style="margin:8px 0" onclick="loadCards(${i},null,'cards-x')">show cards ▾</span>
      <div id="cards-x"></div>`;
  }
  el.innerHTML = html;
  showView('detail');
}
function showMiss(id, i, j) {
  const host = document.getElementById(id);
  if (host.innerHTML) { host.innerHTML = ''; return; }
  host.innerHTML = '<div class="miss"><b>Missing:</b><ul>' +
    LIB.sets[i].chapters[j].missing.map(m => '<li>'+esc(m)+'</li>').join('') + '</ul></div>';
}
async function loadCards(i, j, hostId) {
  const s = LIB.sets[i], host = document.getElementById(hostId);
  if (host.dataset.on) { host.innerHTML=''; host.dataset.on=''; return; }
  host.innerHTML = '<span class="muted">loading…</span>';
  const chapter = j === null ? '' : s.chapters[j].name;
  const d = await (await fetch('/api/cards?' + new URLSearchParams({set:s.name, chapter}))).json();
  host.dataset.on = '1';
  host.innerHTML = '<div class="thumbs">' + d.cards.map(c => {
    const key = cardKey(s.name, chapter, c.front);
    return `<div class="thumb ${inCart(key)?'in':''}" id="t-${cssid(key)}">
      <img loading="lazy" src="/api/thumb?p=${encodeURIComponent(c.front)}">
      <button class="add" title="add card" onclick='addCard(${JSON.stringify(s.name)},${JSON.stringify(chapter)},${JSON.stringify(c.front)},${JSON.stringify(c.name)})'>+</button>
      <div class="cap">${esc(c.name)}</div></div>`;
  }).join('') + '</div>';
}

/* ---------- cart ---------- */
function cartKey(it){ return it.type+'|'+(it.set||'')+'|'+(it.chapter||'')+'|'+(it.front||''); }
function cardKey(set,ch,front){ return 'card|'+set+'|'+ch+'|'+front; }
function inCart(key){ return CART.some(it => cartKey(it) === key); }
function saveCart(){ localStorage.setItem('lotr_cart', JSON.stringify(CART)); renderCartCount(); }
function renderCartCount(){ document.getElementById('cartN').textContent = CART.length; }
function pushItem(it){ if(!inCart(cartKey(it))){ CART.push(it); saveCart(); } }
function addSet(i){ const s=LIB.sets[i]; pushItem({type:'set',set:s.name,label:s.display||s.name}); flash('Added set'); }
function addChapter(i,j){ const s=LIB.sets[i],c=s.chapters[j];
  pushItem({type:'chapter',set:s.name,chapter:c.name,label:(s.display||s.name)+' — '+(c.display||c.name)}); flash('Added chapter'); }
function addCard(set,ch,front,name){ pushItem({type:'card',set,chapter:ch,front,label:name});
  const el=document.getElementById('t-'+cssid(cardKey(set,ch,front))); if(el) el.classList.add('in'); }
function flash(msg){ const b=document.getElementById('cartN'); b.textContent=CART.length; }

function renderCart() {
  const el = document.getElementById('cart-list');
  if (!CART.length) { el.innerHTML = '<p class="muted">Your cart is empty. Add sets, chapters or cards from the Sets tab.</p>'; return; }
  el.innerHTML = CART.map((it,k) =>
    `<div class="cartitem"><span class="kind">${it.type}</span>
      <span class="grow">${esc(it.label)}</span>
      <span class="x" onclick="removeItem(${k})">✕</span></div>`).join('');
}
function removeItem(k){ CART.splice(k,1); saveCart(); renderCart(); }
function clearCart(){ CART=[]; saveCart(); renderCart(); document.getElementById('cart-result').innerHTML=''; }

async function exportCart(format) {
  if (!CART.length) { alert('Cart is empty.'); return; }
  const res = document.getElementById('cart-result');
  res.innerHTML = '<span class="muted">Forging…</span>';
  const body = { items: CART, format, stock: stock.value, foil: foil.checked,
    encounter_back: encBack.value, player_back: plyBack.value };
  try {
    const d = await postJSON('/api/cart-export', body);
    if (d.error) throw new Error(d.error);
    let html = `<div class="result"><b>${d.cards} cards</b>, ${d.fronts} fronts<br>
      <code>${esc(d.order_xml)}</code>`;
    if (d.message) html += `<br>${esc(d.message)}`;
    res.innerHTML = html + '</div>';
  } catch(e){ res.innerHTML = '<span class="err">Error: '+e.message+'</span>'; }
}

/* ---------- manual list (RingsDB import for now) ---------- */
async function importDeck() {
  const res = document.getElementById('deck-results');
  res.innerHTML = '<span class="muted">Summoning cards…</span>';
  try {
    const d = await postJSON('/api/deck', { source: document.getElementById('deck-src').value,
      stock: stock ? stock.value : '(S33) Superior Smooth', foil: false });
    if (d.error) throw new Error(d.error);
    let html = `<div class="result"><b>${esc(d.deck)}</b> — ${d.cards} cards (${d.resolved} resolved)<br>
      <code>${esc(d.order_xml)}</code></div>`;
    if (d.unmatched.length) html += `<div class="result err">Missing from database: ${d.unmatched.map(esc).join(', ')}</div>`;
    res.innerHTML = html;
  } catch(e){ res.innerHTML = '<span class="err">Error: '+e.message+'</span>'; }
}

/* ---------- routing / utils ---------- */
function showView(v) {
  ['shop','detail','cart','deck'].forEach(x =>
    document.getElementById('view-'+x).classList.toggle('hidden', x!==v));
  document.getElementById('nav-shop').classList.toggle('active', v==='shop'||v==='detail');
  document.getElementById('nav-deck').classList.toggle('active', v==='deck');
  if (v==='cart') renderCart();
}
async function postJSON(url, body){ return (await fetch(url,{method:'POST',body:JSON.stringify(body)})).json(); }
function esc(s){ return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
function cssid(s){ return s.replace(/[^A-Za-z0-9]/g,'_'); }
load();
</script>
</body>
</html>
"""
