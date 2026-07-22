"""Tiny zero-dependency i18n for the CLI and the web server.

Supported languages: English (en), French (fr), Spanish (es), Chinese (zh).

The CLI sets a process-wide language once (``set_lang``) from ``--lang`` / the
environment; ``t(key)`` then reads it. The web server, which serves many
languages at once, passes ``lang=`` explicitly per request. The GUI page itself
carries its own JS string table (see ``web/page.py``); the keys here cover only
what Python code prints or returns.
"""

from __future__ import annotations

import os

LANGS = ("en", "fr", "es", "zh")
DEFAULT = "en"

_LANG = DEFAULT  # process-wide default, set once by the CLI


def set_lang(lang: str | None) -> None:
    """Set the process-wide language used by ``t`` when no ``lang`` is given."""
    global _LANG
    _LANG = lang if lang in LANGS else DEFAULT


def current_lang() -> str:
    return _LANG


def resolve_lang(explicit: str | None = None) -> str:
    """Pick a language: ``explicit`` > ``LOTR_LANG`` > ``LANGUAGE``/``LC_ALL``/
    ``LANG`` env > default (``en``). Only the 2-letter prefix is inspected."""
    for cand in (explicit, os.environ.get("LOTR_LANG"),
                 os.environ.get("LANGUAGE"), os.environ.get("LC_ALL"),
                 os.environ.get("LANG")):
        if not cand:
            continue
        code = cand.strip().lower().replace("_", "-")[:2]
        if code in LANGS:
            return code
    return DEFAULT


def t(key: str, lang: str | None = None, **kw) -> str:
    """Translate ``key`` into ``lang`` (or the process-wide language), then
    ``str.format(**kw)``. Falls back to English, then to the raw key."""
    use = lang if lang in LANGS else _LANG
    table = STRINGS.get(key, {})
    text = table.get(use) or table.get(DEFAULT) or key
    return text.format(**kw) if kw else text


# One dict per string. Keys are stable identifiers; values are per-language.
STRINGS: dict[str, dict[str, str]] = {
    # ---- web server (banner + GUI-facing messages) ---------------------- #
    "gui_running": {
        "en": "LOTRAutofill GUI running at {url}",
        "fr": "Interface LOTRAutofill disponible sur {url}",
        "es": "Interfaz de LOTRAutofill en {url}",
        "zh": "LOTRAutofill 图形界面运行于 {url}",
    },
    "gui_library": {
        "en": "Library: {path}",
        "fr": "Bibliothèque : {path}",
        "es": "Biblioteca: {path}",
        "zh": "卡牌库：{path}",
    },
    "gui_stop_hint": {
        "en": "Press Ctrl+C to stop.",
        "fr": "Appuyez sur Ctrl+C pour arrêter.",
        "es": "Pulsa Ctrl+C para detener.",
        "zh": "按 Ctrl+C 停止。",
    },
    "gui_stopping": {
        "en": "Stopping.",
        "fr": "Arrêt.",
        "es": "Deteniendo.",
        "zh": "正在停止。",
    },
    "srv_cart_empty": {
        "en": "Cart is empty (nothing resolved).",
        "fr": "Le panier est vide (rien à résoudre).",
        "es": "El carrito está vacío (nada resuelto).",
        "zh": "购物车为空（没有可解析的卡牌）。",
    },
    "srv_order_not_found": {
        "en": "order.xml not found",
        "fr": "order.xml introuvable",
        "es": "order.xml no encontrado",
        "zh": "未找到 order.xml",
    },

    # ---- CLI: generic ---------------------------------------------------- #
    "cli_manifest_not_found": {
        "en": "error: manifest not found: {path}",
        "fr": "erreur : manifeste introuvable : {path}",
        "es": "error: manifiesto no encontrado: {path}",
        "zh": "错误：未找到清单：{path}",
    },
    "cli_not_a_dir": {
        "en": "error: not a directory: {path}",
        "fr": "erreur : n'est pas un dossier : {path}",
        "es": "error: no es un directorio: {path}",
        "zh": "错误：不是目录：{path}",
    },
    "cli_manifest_written": {
        "en": "Manifest written to: {path}",
        "fr": "Manifeste écrit dans : {path}",
        "es": "Manifiesto escrito en: {path}",
        "zh": "清单已写入：{path}",
    },

    # ---- CLI: reference / db -------------------------------------------- #
    "cli_scrape_start": {
        "en": "Scraping Hall of Beorn scenarios (one-time; cached)...",
        "fr": "Récupération des scénarios Hall of Beorn (une seule fois ; mis en cache)...",
        "es": "Extrayendo escenarios de Hall of Beorn (una vez; en caché)...",
        "zh": "正在抓取 Hall of Beorn 剧本（一次性；已缓存）…",
    },
    "cli_scrape_done": {
        "en": "Cached {n} scenarios to {path}",
        "fr": "{n} scénarios mis en cache dans {path}",
        "es": "{n} escenarios en caché en {path}",
        "zh": "已将 {n} 个剧本缓存到 {path}",
    },
    "cli_indexing": {
        "en": "Indexing card library under {path} ...",
        "fr": "Indexation de la bibliothèque de cartes dans {path} ...",
        "es": "Indexando la biblioteca de cartas en {path} ...",
        "zh": "正在索引 {path} 下的卡牌库…",
    },
    "cli_ref_on": {
        "en": "Hall of Beorn cross-reference on",
        "fr": "recoupement Hall of Beorn activé",
        "es": "referencia cruzada de Hall of Beorn activada",
        "zh": "已启用 Hall of Beorn 交叉参照",
    },
    "cli_ref_off": {
        "en": "no Hall of Beorn reference (run `lotr-autofill reference` first)",
        "fr": "pas de référence Hall of Beorn (lancez d'abord `lotr-autofill reference`)",
        "es": "sin referencia de Hall of Beorn (ejecuta antes `lotr-autofill reference`)",
        "zh": "无 Hall of Beorn 参照（请先运行 `lotr-autofill reference`）",
    },
    "cli_db_summary": {
        "en": "{sets} sets, {cards} cards indexed ({ref}). {missing} missing card(s):",
        "fr": "{sets} sets, {cards} cartes indexées ({ref}). {missing} carte(s) manquante(s) :",
        "es": "{sets} sets, {cards} cartas indexadas ({ref}). {missing} carta(s) faltante(s):",
        "zh": "已索引 {sets} 个系列、{cards} 张卡（{ref}）。缺失 {missing} 张卡：",
    },
    "cli_missing_flag": {
        "en": "[{n} MISSING]",
        "fr": "[{n} MANQUANTE(S)]",
        "es": "[{n} FALTANTE(S)]",
        "zh": "[缺 {n} 张]",
    },
    "cli_missing_prefix": {
        "en": "missing —",
        "fr": "manquantes —",
        "es": "faltantes —",
        "zh": "缺失 —",
    },
    "cli_db_written": {
        "en": "Database written to: {path}",
        "fr": "Base de données écrite dans : {path}",
        "es": "Base de datos escrita en: {path}",
        "zh": "数据库已写入：{path}",
    },

    # ---- CLI: sets / pick (interactive) --------------------------------- #
    "cli_no_sets": {
        "en": "No printable set folders found under {path}",
        "fr": "Aucun dossier de set imprimable sous {path}",
        "es": "No se encontraron carpetas de sets imprimibles en {path}",
        "zh": "在 {path} 下未找到可打印的系列文件夹",
    },
    "cli_printable_sets": {
        "en": "Printable sets under {path}:",
        "fr": "Sets imprimables sous {path} :",
        "es": "Sets imprimibles en {path}:",
        "zh": "{path} 下的可打印系列：",
    },
    "cli_nothing_selected": {
        "en": "Nothing selected.",
        "fr": "Aucune sélection.",
        "es": "Nada seleccionado.",
        "zh": "未选择任何内容。",
    },
    "cli_set_has_chapters": {
        "en": "'{name}' has {n} chapters:",
        "fr": "« {name} » a {n} chapitres :",
        "es": "«{name}» tiene {n} capítulos:",
        "zh": "「{name}」有 {n} 个章节：",
    },
    "cli_all_chapters": {
        "en": "[a] all chapters (one order.xml each)",
        "fr": "[a] tous les chapitres (un order.xml chacun)",
        "es": "[a] todos los capítulos (un order.xml cada uno)",
        "zh": "[a] 所有章节（各生成一个 order.xml）",
    },
    "cli_prompt_chapters": {
        "en": "Chapters to print (comma-separated), 'a' for all: ",
        "fr": "Chapitres à imprimer (séparés par des virgules), « a » pour tous : ",
        "es": "Capítulos a imprimir (separados por comas), «a» para todos: ",
        "zh": "要打印的章节（用逗号分隔），输入 a 表示全部：",
    },
    "cli_which_sets": {
        "en": "Which set(s) do you want to print?",
        "fr": "Quel(s) set(s) voulez-vous imprimer ?",
        "es": "¿Qué set(s) quieres imprimir?",
        "zh": "您想打印哪些系列？",
    },
    "cli_all": {
        "en": "[a] all",
        "fr": "[a] tous",
        "es": "[a] todos",
        "zh": "[a] 全部",
    },
    "cli_prompt_sets": {
        "en": "Enter numbers (comma-separated), 'a' for all: ",
        "fr": "Entrez les numéros (séparés par des virgules), « a » pour tous : ",
        "es": "Introduce los números (separados por comas), «a» para todos: ",
        "zh": "输入编号（用逗号分隔），输入 a 表示全部：",
    },

    # ---- CLI: order.xml writing ----------------------------------------- #
    "cli_img_missing": {
        "en": "! {n} image(s) missing — order.xml may be incomplete.",
        "fr": "! {n} image(s) manquante(s) — order.xml peut être incomplet.",
        "es": "! {n} imagen(es) faltante(s) — order.xml puede estar incompleto.",
        "zh": "！缺少 {n} 张图片 —— order.xml 可能不完整。",
    },
    "cli_orderxml_written": {
        "en": "order.xml written to: {path}  ({cards} cards, {fronts} fronts)",
        "fr": "order.xml écrit dans : {path}  ({cards} cartes, {fronts} faces)",
        "es": "order.xml escrito en: {path}  ({cards} cartas, {fronts} frentes)",
        "zh": "order.xml 已写入：{path}（{cards} 张卡，{fronts} 张正面）",
    },

    # ---- CLI: build report ---------------------------------------------- #
    "rep_root": {
        "en": "Root: {path}",
        "fr": "Racine : {path}",
        "es": "Raíz: {path}",
        "zh": "根目录：{path}",
    },
    "rep_unique": {
        "en": "Unique cards : {n}",
        "fr": "Cartes uniques : {n}",
        "es": "Cartas únicas : {n}",
        "zh": "唯一卡牌：{n}",
    },
    "rep_slots": {
        "en": "Total slots  : {n}",
        "fr": "Emplacements : {n}",
        "es": "Espacios totales : {n}",
        "zh": "总卡位：{n}",
    },
    "sec_double": {
        "en": "Double-sided pairs (verify face/back)",
        "fr": "Paires recto-verso (vérifier face/dos)",
        "es": "Pares de doble cara (verifica cara/reverso)",
        "zh": "双面配对（请核对正/背面）",
    },
    "sec_fuzzy": {
        "en": "Fuzzy (typo) matches — please verify",
        "fr": "Correspondances approximatives (fautes de frappe) — à vérifier",
        "es": "Coincidencias aproximadas (erratas) — verifica por favor",
        "zh": "模糊（拼写）匹配 —— 请核对",
    },
    "sec_unmatched": {
        "en": "UNMATCHED cardlist entries",
        "fr": "Entrées de cardlist NON APPARIÉES",
        "es": "Entradas de cardlist SIN EMPAREJAR",
        "zh": "未匹配的 cardlist 条目",
    },
    "sec_orphan": {
        "en": "Orphan sides (need face/back — check these)",
        "fr": "Faces orphelines (face/dos manquant — à vérifier)",
        "es": "Caras huérfanas (faltan cara/reverso — revísalas)",
        "zh": "孤立卡面（缺正/背面 —— 请检查）",
    },
    "sec_auto": {
        "en": "Auto-included (not in cardlist, added at 1)",
        "fr": "Ajoutées automatiquement (absentes de la cardlist, quantité 1)",
        "es": "Incluidas automáticamente (no en cardlist, añadidas con 1)",
        "zh": "自动加入（不在 cardlist 中，数量为 1）",
    },
    "sec_warnings": {
        "en": "Warnings",
        "fr": "Avertissements",
        "es": "Advertencias",
        "zh": "警告",
    },
}
