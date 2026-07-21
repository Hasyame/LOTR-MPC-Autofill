"""The single-page HTML/CSS/JS UI, served as one string (no external assets).

All user-facing strings are localized client-side: the ``I18N`` table below
holds English/French/Spanish/Chinese, ``T(key, params)`` looks them up, and a
language picker in the header switches at runtime (persisted in localStorage,
defaulting to the browser language). Static markup carries ``data-i18n`` /
``data-i18n-html`` / ``data-i18n-ph`` attributes applied by ``applyStatic()``.
"""

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
  header .langsel { color:var(--muted); padding:7px 8px; }
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
    <button id="nav-shop" class="active" onclick="showView('shop')" data-i18n="nav_sets">Sets</button>
    <button id="nav-deck" onclick="showView('deck')" data-i18n="nav_manual">Manual List</button>
  </nav>
  <select id="lang" class="langsel" title="Language" onchange="setLang(this.value)">
    <option value="en">English</option><option value="fr">Français</option>
    <option value="es">Español</option><option value="zh">中文</option>
  </select>
  <button class="cartbtn" onclick="showView('cart')">🛒 <span data-i18n="cart">Cart</span><span class="n" id="cartN">0</span></button>
</header>

<main>
  <div id="view-shop"><div id="shop" class="muted" data-i18n="loading_shop">Loading the archives of Middle-earth…</div></div>
  <div id="view-detail" class="hidden"></div>

  <div id="view-cart" class="hidden">
    <h2 data-i18n="cart_title">Your cart</h2>
    <div id="cart-list"></div>
    <div class="bar" id="cart-opts">
      <label><span data-i18n="stock">Card stock</span> <select id="stock">
        <option>(S33) Superior Smooth</option><option>(S30) Standard Smooth</option>
        <option>(S27) Smooth</option><option>(M31) Linen</option><option>(P10) Plastic</option>
      </select></label>
      <label><span data-i18n="enc_back">Encounter back</span> <select id="encBack"></select></label>
      <label><span data-i18n="ply_back">Player back</span> <select id="plyBack"></select></label>
      <label><input type="checkbox" id="foil"> <span data-i18n="foil">Foil</span></label>
    </div>
    <div style="display:flex; gap:10px; flex-wrap:wrap">
      <button class="go" onclick="exportCart('xml')" data-i18n="export_xml">Export order.xml</button>
      <button class="go ghost" onclick="exportCart('pdf')" data-i18n="export_pdf">Export PDF</button>
      <button class="go ghost" onclick="exportCart('mpc')" data-i18n="create_mpc">Create MPC project</button>
      <button class="go ghost" onclick="clearCart()" data-i18n="empty_cart">Empty cart</button>
    </div>
    <div id="cart-result"></div>
  </div>

  <div id="view-deck" class="hidden">
    <h2 data-i18n="manual_title">Manual list</h2>
    <p class="muted" data-i18n-html="manual_hint">Paste a card list, one card per line (e.g. <code>3x Gandalf</code>).</p>
    <p class="muted" data-i18n-html="manual_warn">⚠️ Cards must be available in your local library
      (<code>sets_folder/</code>) to be printed — anything not found there is
      reported and skipped.</p>
    <textarea id="deck-src" placeholder="3x Gandalf&#10;2 Steward of Gondor&#10;…"></textarea>
    <div style="margin-top:10px"><button class="go" onclick="checkManualList()" data-i18n="manual_check">Check against library</button></div>
    <div id="deck-results"></div>
  </div>

  <div class="pagefoot">⚔ &nbsp; <span data-i18n="footer">by hasyame — for personal use only</span> &nbsp; ⚔</div>
</main>

<script>
/* ---------- i18n ---------- */
const I18N = {
  en: {
    nav_sets:"Sets", nav_manual:"Manual List", cart:"Cart",
    loading_shop:"Loading the archives of Middle-earth…",
    cart_title:"Your cart", stock:"Card stock", enc_back:"Encounter back",
    ply_back:"Player back", foil:"Foil", export_xml:"Export order.xml",
    export_pdf:"Export PDF", create_mpc:"Create MPC project", empty_cart:"Empty cart",
    manual_title:"Manual list",
    manual_hint:"Paste a card list, one card per line (e.g. <code>3x Gandalf</code>).",
    manual_warn:"⚠️ Cards must be available in your local library (<code>sets_folder/</code>) to be printed — anything not found there is reported and skipped.",
    manual_check:"Check against library",
    footer:"by hasyame — for personal use only",
    set_not_in_lib:"not in your library", n_missing:"{n} missing",
    n_cards:"{n} cards", n_chapters:"{n} chapters", add_set:"Add set to cart",
    all_sets:"← all sets", add_whole_set:"Add whole set", missing_n:"missing {n}",
    cards_toggle:"cards ▾", add_chapter:"Add chapter", show_cards:"show cards ▾",
    missing_label:"Missing:", loading:"loading…", add_card:"add card",
    cart_empty:"Your cart is empty. Add sets, chapters or cards from the Sets tab.",
    cart_empty_alert:"Cart is empty.", forging:"Forging…", n_fronts:"{n} fronts",
    error_prefix:"Error", checking_lib:"Checking against your library…",
    found:"{n} card(s) found", found_suffix:"in your library.",
    not_found_n:"{n} not found (will be skipped):",
    add_found_skip:"Add {n} found card(s) to cart (skip {m})",
    add_found:"Add {n} card(s) to cart",
    added_to_cart:"Added {n} card(s) to your cart. Open 🛒 Cart to export.",
  },
  fr: {
    nav_sets:"Extensions", nav_manual:"Liste manuelle", cart:"Panier",
    loading_shop:"Chargement des archives de la Terre du Milieu…",
    cart_title:"Votre panier", stock:"Type de carton", enc_back:"Dos rencontre",
    ply_back:"Dos joueur", foil:"Effet foil", export_xml:"Exporter order.xml",
    export_pdf:"Exporter PDF", create_mpc:"Créer un projet MPC", empty_cart:"Vider le panier",
    manual_title:"Liste manuelle",
    manual_hint:"Collez une liste de cartes, une carte par ligne (ex. <code>3x Gandalf</code>).",
    manual_warn:"⚠️ Les cartes doivent être présentes dans votre bibliothèque locale (<code>sets_folder/</code>) pour être imprimées — tout ce qui est introuvable est signalé et ignoré.",
    manual_check:"Vérifier dans la bibliothèque",
    footer:"par hasyame — pour usage personnel uniquement",
    set_not_in_lib:"absent de votre bibliothèque", n_missing:"{n} manquante(s)",
    n_cards:"{n} cartes", n_chapters:"{n} chapitres", add_set:"Ajouter au panier",
    all_sets:"← toutes les extensions", add_whole_set:"Ajouter toute l'extension",
    missing_n:"{n} manquante(s)", cards_toggle:"cartes ▾", add_chapter:"Ajouter le chapitre",
    show_cards:"voir les cartes ▾", missing_label:"Manquantes :", loading:"chargement…",
    add_card:"ajouter la carte",
    cart_empty:"Votre panier est vide. Ajoutez des extensions, chapitres ou cartes depuis l'onglet Extensions.",
    cart_empty_alert:"Le panier est vide.", forging:"Forge en cours…", n_fronts:"{n} faces",
    error_prefix:"Erreur", checking_lib:"Vérification dans votre bibliothèque…",
    found:"{n} carte(s) trouvée(s)", found_suffix:"dans votre bibliothèque.",
    not_found_n:"{n} introuvable(s) (seront ignorées) :",
    add_found_skip:"Ajouter {n} carte(s) trouvée(s) au panier (ignorer {m})",
    add_found:"Ajouter {n} carte(s) au panier",
    added_to_cart:"{n} carte(s) ajoutée(s) à votre panier. Ouvrez 🛒 Panier pour exporter.",
  },
  es: {
    nav_sets:"Expansiones", nav_manual:"Lista manual", cart:"Carrito",
    loading_shop:"Cargando los archivos de la Tierra Media…",
    cart_title:"Tu carrito", stock:"Tipo de cartón", enc_back:"Reverso de encuentro",
    ply_back:"Reverso de jugador", foil:"Foil", export_xml:"Exportar order.xml",
    export_pdf:"Exportar PDF", create_mpc:"Crear proyecto MPC", empty_cart:"Vaciar carrito",
    manual_title:"Lista manual",
    manual_hint:"Pega una lista de cartas, una por línea (p. ej. <code>3x Gandalf</code>).",
    manual_warn:"⚠️ Las cartas deben estar en tu biblioteca local (<code>sets_folder/</code>) para imprimirse — lo que no se encuentre se informa y se omite.",
    manual_check:"Comprobar en la biblioteca",
    footer:"por hasyame — solo para uso personal",
    set_not_in_lib:"no está en tu biblioteca", n_missing:"{n} faltante(s)",
    n_cards:"{n} cartas", n_chapters:"{n} capítulos", add_set:"Añadir al carrito",
    all_sets:"← todas las expansiones", add_whole_set:"Añadir toda la expansión",
    missing_n:"{n} faltante(s)", cards_toggle:"cartas ▾", add_chapter:"Añadir capítulo",
    show_cards:"ver cartas ▾", missing_label:"Faltantes:", loading:"cargando…",
    add_card:"añadir carta",
    cart_empty:"Tu carrito está vacío. Añade expansiones, capítulos o cartas desde la pestaña Expansiones.",
    cart_empty_alert:"El carrito está vacío.", forging:"Forjando…", n_fronts:"{n} frentes",
    error_prefix:"Error", checking_lib:"Comprobando en tu biblioteca…",
    found:"{n} carta(s) encontrada(s)", found_suffix:"en tu biblioteca.",
    not_found_n:"{n} no encontrada(s) (se omitirán):",
    add_found_skip:"Añadir {n} carta(s) encontrada(s) al carrito (omitir {m})",
    add_found:"Añadir {n} carta(s) al carrito",
    added_to_cart:"{n} carta(s) añadida(s) a tu carrito. Abre 🛒 Carrito para exportar.",
  },
  zh: {
    nav_sets:"系列", nav_manual:"手动列表", cart:"购物车",
    loading_shop:"正在加载中土世界的档案…",
    cart_title:"您的购物车", stock:"卡纸类型", enc_back:"遭遇卡背",
    ply_back:"玩家卡背", foil:"闪膜", export_xml:"导出 order.xml",
    export_pdf:"导出 PDF", create_mpc:"创建 MPC 项目", empty_cart:"清空购物车",
    manual_title:"手动列表",
    manual_hint:"粘贴卡牌列表，每行一张（例如 <code>3x Gandalf</code>）。",
    manual_warn:"⚠️ 卡牌必须存在于本地库（<code>sets_folder/</code>）中才能打印——找不到的卡牌会被列出并跳过。",
    manual_check:"在库中检查",
    footer:"由 hasyame 制作 — 仅供个人使用",
    set_not_in_lib:"不在您的库中", n_missing:"缺 {n} 张",
    n_cards:"{n} 张卡", n_chapters:"{n} 章", add_set:"加入购物车",
    all_sets:"← 所有系列", add_whole_set:"添加整个系列", missing_n:"缺 {n} 张",
    cards_toggle:"卡牌 ▾", add_chapter:"添加章节", show_cards:"显示卡牌 ▾",
    missing_label:"缺失：", loading:"加载中…", add_card:"添加卡牌",
    cart_empty:"您的购物车为空。请从“系列”标签页添加系列、章节或卡牌。",
    cart_empty_alert:"购物车为空。", forging:"锻造中…", n_fronts:"{n} 张正面",
    error_prefix:"错误", checking_lib:"正在库中检查…",
    found:"找到 {n} 张卡", found_suffix:"在您的库中。",
    not_found_n:"{n} 张未找到（将跳过）：",
    add_found_skip:"将找到的 {n} 张卡加入购物车（跳过 {m} 张）",
    add_found:"将 {n} 张卡加入购物车",
    added_to_cart:"已将 {n} 张卡加入购物车。打开 🛒 购物车以导出。",
  },
};
const LANGS = ['en','fr','es','zh'];
let LANG = localStorage.getItem('lotr_lang');
if (!LANGS.includes(LANG)) {
  LANG = (navigator.language || 'en').slice(0,2).toLowerCase();
  if (!LANGS.includes(LANG)) LANG = 'en';
}
function T(k, p) {
  let s = (I18N[LANG] && I18N[LANG][k]) || I18N.en[k] || k;
  if (p) for (const key in p) s = s.replace('{'+key+'}', p[key]);
  return s;
}
function applyStatic() {
  document.querySelectorAll('[data-i18n]').forEach(e => e.textContent = T(e.dataset.i18n));
  document.querySelectorAll('[data-i18n-html]').forEach(e => e.innerHTML = T(e.dataset.i18nHtml));
  document.querySelectorAll('[data-i18n-ph]').forEach(e => e.placeholder = T(e.dataset.i18nPh));
}
function setLang(l) {
  LANG = LANGS.includes(l) ? l : 'en';
  localStorage.setItem('lotr_lang', LANG);
  document.documentElement.lang = LANG;
  document.getElementById('lang').value = LANG;
  applyStatic();
  if (LIB) renderShop();
  renderCartCount();
  refreshView();
}

/* ---------- state ---------- */
let LIB = null, CART = [], VIEW = 'shop', DETAIL = null;
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
        <div class="nm">${esc(n)}</div><div class="sub">${T('set_not_in_lib')}</div></div></div>`).join('');
}
function tile(s, i) {
  const art = s.image
    ? `background-image:url('/api/product-image?f=${encodeURIComponent(s.image)}')` : '';
  const dis = s.cards_total === 0 ? 'disabled' : '';
  const missTag = s.missing_total ? `<span class="miss">${T('n_missing',{n:s.missing_total})}</span>` : '';
  return `<div class="tile ${s.cards_total===0?'dim':''}">
    <div class="art" style="${art}" onclick="openDetail(${i})">${missTag}</div>
    <div class="body">
      <div class="nm" onclick="openDetail(${i})">${esc(s.display||s.name)}</div>
      <div class="sub">${T('n_cards',{n:s.cards_total})}${s.has_chapters?' · '+T('n_chapters',{n:s.chapters.length}):''}</div>
      <button class="go mini" ${dis} onclick="addSet(${i})">${T('add_set')}</button>
    </div></div>`;
}

/* ---------- set detail ---------- */
function openDetail(i) {
  const s = LIB.sets[i];
  const el = document.getElementById('view-detail');
  let html = `<span class="back" onclick="showView('shop')">${T('all_sets')}</span>
    <h2>${esc(s.display||s.name)}</h2>
    <div class="row"><span class="grow count">${T('n_cards',{n:s.cards_total})}</span>
      <button class="go mini" onclick="addSet(${i})">${T('add_whole_set')}</button></div>`;
  if (s.has_chapters) {
    html += s.chapters.map((c, j) => {
      const miss = c.missing && c.missing.length
        ? `<span class="miss-badge" onclick="showMiss('miss-${j}',${i},${j})">${T('missing_n',{n:c.missing.length})}</span>` : '';
      return `<div><div class="row">
        <span class="grow">${esc(c.display||c.name)} <span class="count">${T('n_cards',{n:c.unique_cards})}</span> ${miss}</span>
        <span class="back" style="margin:0" onclick="loadCards(${i},${j},'cards-${j}')">${T('cards_toggle')}</span>
        <button class="go mini" onclick="addChapter(${i},${j})">${T('add_chapter')}</button></div>
        <div id="miss-${j}"></div><div id="cards-${j}"></div></div>`;
    }).join('');
  } else {
    html += `<span class="back" style="margin:8px 0" onclick="loadCards(${i},null,'cards-x')">${T('show_cards')}</span>
      <div id="cards-x"></div>`;
  }
  el.innerHTML = html;
  DETAIL = i;
  showView('detail');
}
function showMiss(id, i, j) {
  const host = document.getElementById(id);
  if (host.innerHTML) { host.innerHTML = ''; return; }
  host.innerHTML = '<div class="miss"><b>'+T('missing_label')+'</b><ul>' +
    LIB.sets[i].chapters[j].missing.map(m => '<li>'+esc(m)+'</li>').join('') + '</ul></div>';
}
async function loadCards(i, j, hostId) {
  const s = LIB.sets[i], host = document.getElementById(hostId);
  if (host.dataset.on) { host.innerHTML=''; host.dataset.on=''; return; }
  host.innerHTML = '<span class="muted">'+T('loading')+'</span>';
  const chapter = j === null ? '' : s.chapters[j].name;
  const d = await (await fetch('/api/cards?' + new URLSearchParams({set:s.name, chapter}))).json();
  host.dataset.on = '1';
  host.innerHTML = '<div class="thumbs">' + d.cards.map(c => {
    const key = cardKey(s.name, chapter, c.front);
    return `<div class="thumb ${inCart(key)?'in':''}" id="t-${cssid(key)}">
      <img loading="lazy" src="/api/thumb?p=${encodeURIComponent(c.front)}">
      <button class="add" title="${T('add_card')}" onclick='addCard(${JSON.stringify(s.name)},${JSON.stringify(chapter)},${JSON.stringify(c.front)},${JSON.stringify(c.name)})'>+</button>
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
function addSet(i){ const s=LIB.sets[i]; pushItem({type:'set',set:s.name,label:s.display||s.name}); renderCartCount(); }
function addChapter(i,j){ const s=LIB.sets[i],c=s.chapters[j];
  pushItem({type:'chapter',set:s.name,chapter:c.name,label:(s.display||s.name)+' — '+(c.display||c.name)}); renderCartCount(); }
function addCard(set,ch,front,name){ pushItem({type:'card',set,chapter:ch,front,label:name});
  const el=document.getElementById('t-'+cssid(cardKey(set,ch,front))); if(el) el.classList.add('in'); }

function renderCart() {
  const el = document.getElementById('cart-list');
  if (!CART.length) { el.innerHTML = '<p class="muted">'+T('cart_empty')+'</p>'; return; }
  el.innerHTML = CART.map((it,k) =>
    `<div class="cartitem"><span class="kind">${it.type}</span>
      <span class="grow">${esc(it.label)}</span>
      <span class="x" onclick="removeItem(${k})">✕</span></div>`).join('');
}
function removeItem(k){ CART.splice(k,1); saveCart(); renderCart(); }
function clearCart(){ CART=[]; saveCart(); renderCart(); document.getElementById('cart-result').innerHTML=''; }

async function exportCart(format) {
  if (!CART.length) { alert(T('cart_empty_alert')); return; }
  const res = document.getElementById('cart-result');
  res.innerHTML = '<span class="muted">'+T('forging')+'</span>';
  const body = { items: CART, format, stock: stock.value, foil: foil.checked,
    encounter_back: encBack.value, player_back: plyBack.value, lang: LANG };
  try {
    const d = await postJSON('/api/cart-export', body);
    if (d.error) throw new Error(d.error);
    let html = `<div class="result"><b>${T('n_cards',{n:d.cards})}</b>, ${T('n_fronts',{n:d.fronts})}<br>
      <code>${esc(d.order_xml)}</code>`;
    if (d.message) html += `<br>${esc(d.message)}`;
    res.innerHTML = html + '</div>';
  } catch(e){ res.innerHTML = '<span class="err">'+T('error_prefix')+': '+e.message+'</span>'; }
}

/* ---------- manual list (resolved against the LOCAL library) ---------- */
let MANUAL = null;
async function checkManualList() {
  const res = document.getElementById('deck-results');
  res.innerHTML = '<span class="muted">'+T('checking_lib')+'</span>';
  try {
    const d = await postJSON('/api/manual-list', { text: document.getElementById('deck-src').value });
    if (d.error) throw new Error(d.error);
    MANUAL = d;
    let html = `<div class="result"><b>${T('found',{n:d.resolved.length})}</b> ${T('found_suffix')}`;
    if (d.missing.length) html += `<div class="miss"><b>${T('not_found_n',{n:d.missing.length})}</b><ul>`
      + d.missing.map(m => '<li>'+esc(m.quantity+'× '+m.name)+'</li>').join('') + '</ul></div>';
    html += '</div>';
    if (d.resolved.length) {
      const label = d.missing.length
        ? T('add_found_skip',{n:d.resolved.length, m:d.missing.length})
        : T('add_found',{n:d.resolved.length});
      html += `<button class="go" onclick="addManualToCart()">${label}</button>`;
    }
    res.innerHTML = html;
  } catch(e){ res.innerHTML = '<span class="err">'+T('error_prefix')+': '+e.message+'</span>'; }
}
function addManualToCart() {
  if (!MANUAL) return;
  MANUAL.resolved.forEach(c => pushItem({type:'card', set:c.set, chapter:c.chapter,
    front:c.front, quantity:c.quantity, label:c.quantity+'× '+c.name}));
  renderCartCount();
  document.getElementById('deck-results').innerHTML =
    `<div class="result">${T('added_to_cart',{n:MANUAL.resolved.length})}</div>`;
  MANUAL = null;
}

/* ---------- routing / utils ---------- */
function showView(v) {
  VIEW = v;
  ['shop','detail','cart','deck'].forEach(x =>
    document.getElementById('view-'+x).classList.toggle('hidden', x!==v));
  document.getElementById('nav-shop').classList.toggle('active', v==='shop'||v==='detail');
  document.getElementById('nav-deck').classList.toggle('active', v==='deck');
  if (v==='cart') renderCart();
}
function refreshView() {
  if (VIEW==='detail' && DETAIL!=null && LIB) openDetail(DETAIL);
  else if (VIEW==='cart') renderCart();
}
async function postJSON(url, body){ return (await fetch(url,{method:'POST',body:JSON.stringify(body)})).json(); }
function esc(s){ return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
function cssid(s){ return s.replace(/[^A-Za-z0-9]/g,'_'); }

document.documentElement.lang = LANG;
document.getElementById('lang').value = LANG;
applyStatic();
load();
</script>
</body>
</html>
"""
