"""Dati del listino e resa in HTML (anteprima, PDF e stampa usano lo stesso documento)."""
import base64
import copy
import html
import json
import os
import re
import shutil

DEFAULT_ACCENT = "#f2b8c4"
DEFAULT_TEXT = "#3b4350"
DEFAULT_NAME = "#ffffff"
DEFAULT_COLS = ["", "", "", ""]
SAMPLE_COLS = ["MODELLO", "KW", "CASH", "IVATO"]


def new_section(title="NUOVA SEZIONE"):
    return {"title": title, "cols": list(DEFAULT_COLS), "rows": [["", "", "", ""]]}


def new_block(name="Marchio"):
    return {"name": name, "logo": "", "sections": [new_section()]}


def new_document():
    return {"version": 1, "title": "", "accent": DEFAULT_ACCENT, "blocks": [new_block("Marchio 1")]}


def sample_document():
    def sec(title, rows, cols=None):
        return {"title": title, "cols": cols or list(SAMPLE_COLS), "rows": [list(r) for r in rows]}
    doc = new_document()
    doc["title"] = "Listino caldaie e climatizzatori"
    doc["blocks"] = [{
        "name": "ARISTON", "logo": "",
        "sections": [
            sec("CAMERA APERTA", [["CARES X MTN", "24", "370,00\n395,00", "430,00"],
                                  ["CARES X GPL", "24", "370,00\n425,00", "430,00"]]),
            sec("CONDENSAZIONE", [["CARES S", "24", "490,00\n500,00", "550,00"],
                                  ["CARES S", "30", "750,00", "825,00"],
                                  ["HS PREMIUM", "24", "460,00\n465,00", "495,00"],
                                  ["HS PREMIUM", "30", "600,00\n535,00", "650,00"]]),
            sec("CLIMATIZZATORI", [["ALYS", "9.000", "0,00", "220,00"]],
                ["MODELLO", "BTU/h", "CASH", "IVATO"]),
        ]}]
    return doc


def load(path):
    with open(path, "r", encoding="utf-8-sig") as fh:
        doc = json.load(fh)
    if not isinstance(doc, dict) or not isinstance(doc.get("blocks"), list):
        raise ValueError("il file non è un listino tk-listino")
    base = new_document()
    base.update(doc)
    base["blocks"] = [b for b in base["blocks"] if isinstance(b, dict)]
    _clean_style(base)
    for b in base["blocks"]:
        b.setdefault("name", "Marchio")
        b.setdefault("logo", "")
        if not isinstance(b.get("sections"), list):
            b["sections"] = []
        b["sections"] = [s for s in b["sections"] if isinstance(s, dict)]
        migrate_block_colors(b)
        _clean_style(b)
        for s in b["sections"]:
            s.setdefault("title", "")
            if not isinstance(s.get("cols"), list):
                s["cols"] = list(DEFAULT_COLS)
            s["cols"] = [str(c) for c in s["cols"]]
            if not isinstance(s.get("rows"), list):
                s["rows"] = []
            n = len(s["cols"])
            s["rows"] = [([str(c) for c in r] + [""] * n)[:n] for r in s["rows"] if isinstance(r, list)]
            _clean_style(s)
            row_images(s)
            row_marks(s)
    return base


COLOR_RE = re.compile(r"#[0-9a-fA-F]{6}")
COLOR_KEYS = ("accent", "color", "head_color", "name_color", "text_color", "doc_title_color", "sec_title_color",
              "title_color")


def _clean_style(obj):
    """Colori e caratteri letti dal file: finiscono dentro l'HTML del foglio, quindi si tiene solo ciò che è valido
    (colori #rrggbb, caratteri tra quelli inclusi, grandezze ragionevoli); il resto torna al valore predefinito."""
    for key in COLOR_KEYS:
        if key in obj and not (isinstance(obj[key], str) and COLOR_RE.fullmatch(obj[key])):
            if key == "accent":
                obj[key] = DEFAULT_ACCENT
            else:
                obj.pop(key)
    fonts = obj.get("fonts")
    if fonts is None:
        return
    if not isinstance(fonts, dict):
        obj.pop("fonts")
        return
    clean = {}
    for key, f in fonts.items():
        if key not in FONT_DEFAULTS or not isinstance(f, dict):
            continue
        g = {}
        if f.get("family", "") in FONT_FAMILIES:
            g["family"] = f.get("family", "")
        size = f.get("size")
        if isinstance(size, (int, float)) and not isinstance(size, bool) and 4 <= size <= 96:
            g["size"] = size
        for flag in ("bold", "italic"):
            if isinstance(f.get(flag), bool):
                g[flag] = f[flag]
        clean[key] = g
    obj["fonts"] = clean


def _write_atomic(path, text):
    """Scrive su «.tmp» accanto, lo forza sul disco e solo allora lo mette al posto del file vero: se il programma
    si chiude (o la pennetta si stacca) a metà, il listino di prima resta intero."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def save(path, doc, backup=True):
    """Salva il listino; la versione precedente resta in «<nome>.listino.bak»."""
    text = json.dumps(doc, ensure_ascii=False, indent=1)
    if backup and os.path.isfile(path):
        try:
            shutil.copy2(path, path + ".bak")
        except OSError:
            pass
    _write_atomic(path, text)


def clone(doc):
    return copy.deepcopy(doc)


def logo_name(i):
    return f"logo{i}"


def row_images(s):
    """Foto della prima colonna, una per riga ("" = nessuna): la lista resta lunga quanto le righe."""
    imgs = list(s.get("imgs") or [])
    imgs = (imgs + [""] * len(s["rows"]))[:len(s["rows"])]
    if any(imgs):
        s["imgs"] = imgs
    else:
        s.pop("imgs", None)
    return imgs


def row_marks(s):
    """Celle da controllare dopo un'importazione: per ogni riga, l'elenco delle colonne evidenziate (vedi importer).
    Come le foto riga, la lista resta lunga quanto le righe; vuota del tutto = la chiave sparisce."""
    n = len(s.get("cols") or [])
    raw = s.get("dubbi") if isinstance(s.get("dubbi"), list) else []
    marks = [sorted({c for c in (m if isinstance(m, list) else []) if isinstance(c, int) and 0 <= c < n})
             for m in raw]
    marks = (marks + [[] for _ in s["rows"]])[:len(s["rows"])]
    if any(marks):
        s["dubbi"] = marks
    else:
        s.pop("dubbi", None)
    return marks


def count_marks(doc):
    return sum(len(m) for b in doc["blocks"] for s in b["sections"] for m in row_marks(s))


def clear_marks(doc):
    """«Ho controllato»: via i colori delle celle e la richiesta di conferma."""
    doc.pop("da_controllare", None)
    for b in doc["blocks"]:
        for s in b["sections"]:
            s.pop("dubbi", None)


def row_img_name(bi, si, ri):
    return f"rimg{bi}_{si}_{ri}"


def _png_size(data):
    """Larghezza e altezza di un PNG leggendo l'intestazione (le foto riga sono salvate come PNG)."""
    if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) >= 24:
        return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
    return 1, 1


def _fit(data, box_w=60, box_h=42):
    w, h = _png_size(data)
    k = min(box_w / max(1, w), box_h / max(1, h))
    return max(1, round(w * k)), max(1, round(h * k))


def _esc(text):
    return html.escape(str(text)).replace("\n", "<br>")


def _darker(color):
    c = color.lstrip("#")
    r, g, b = (int(c[i:i + 2], 16) for i in (0, 2, 4))
    return "#%02x%02x%02x" % (int(r * 0.78), int(g * 0.78), int(b * 0.78))


def block_colors(doc, b):
    """(sfondo, intestazioni/secondo prezzo, nome del marchio, titolo sezione) del marchio: il riquadro del marchio
    e le fasce delle sue sezioni hanno lo stesso colore e lo stesso colore del testo; se non scelti, quelli del foglio."""
    bg = (b or {}).get("color") or doc.get("accent") or DEFAULT_ACCENT
    head = doc.get("head_color") or _darker(bg)
    tc = (b or {}).get("text_color") or doc.get("name_color") or DEFAULT_NAME
    return bg, head, tc, tc  # il titolo della sezione è legato al testo del marchio


def section_colors(doc, b, s):
    """(intestazioni/secondo prezzo, modelli e prezzi) della sezione: i suoi, se no quelli del foglio."""
    head = (s or {}).get("head_color") or block_colors(doc, b)[1]
    text = (s or {}).get("text_color") or doc.get("text_color") or DEFAULT_TEXT
    return head, text


def migrate_block_colors(b):
    """Listini fino alla 1.8.2: colore e testo erano per sezione; ora sono del marchio (vince la prima sezione)."""
    for key, skey in (("color", "color"), ("text_color", "title_color")):
        for s in b.get("sections", []):
            c = s.pop(skey, None)
            if c and not b.get(key):
                b[key] = c


# testo → (chiave del colore nel listino, sta sul colore del foglio?)
TEXT_COLOR_KEYS = {
    "title": ("doc_title_color", False),
    "name": ("name_color", True),
    "sec": ("sec_title_color", True),
    "head": ("head_color", False),
    "text": ("text_color", False),
}


def text_color(doc, key):
    """Colore in uso per quel testo: quello scelto, se no quello predefinito."""
    if key == "sec":
        key = "name"  # stesso colore del nome del marchio
    ck = TEXT_COLOR_KEYS[key][0]
    if doc.get(ck):
        return doc[ck]
    accent = doc.get("accent") or DEFAULT_ACCENT
    if key == "title":
        return doc.get("text_color") or DEFAULT_TEXT
    if key == "name":
        return DEFAULT_NAME
    if key == "sec":
        return doc.get("head_color") or _darker(accent)
    if key == "head":
        return _darker(accent)
    return DEFAULT_TEXT


# grandezza (pt), grassetto, corsivo di ogni testo del foglio
FONT_DEFAULTS = {
    "title": (17, True, False),   # titolo in cima al foglio
    "name": (19, True, False),    # nome del marchio
    "sec": (11, True, False),     # titolo della sezione
    "head": (10, False, False),   # intestazioni delle colonne
    "text": (11, False, False),   # modelli e prezzi
}


BLOCK_FONT_KEYS = ("name", "sec")    # nome del marchio e titolo della sezione: regolati per marchio
SECTION_FONT_KEYS = ("head", "text")  # intestazioni e prezzi: regolati per sezione


# caratteri inclusi nel programma (Google Fonts, cartella tklistino/fonts); "" = quello di sempre (Cambria)
FONT_FAMILIES = ["", "Roboto", "Open Sans", "Lato", "Montserrat", "Poppins", "Oswald", "Raleway", "Nunito",
                 "Playfair Display", "Merriweather"]


def font_style(doc, key, b=None, s=None):
    """Carattere, grandezza, grassetto, corsivo: quello del marchio o della sezione, se scelto, se no del foglio."""
    size, bold, italic = FONT_DEFAULTS[key]
    f = dict((doc.get("fonts") or {}).get(key) or {})
    own = b if key in BLOCK_FONT_KEYS else s if key in SECTION_FONT_KEYS else None
    if own:
        f.update((own.get("fonts") or {}).get(key) or {})
    return {"size": f.get("size", size), "bold": f.get("bold", bold), "italic": f.get("italic", italic),
            "family": f.get("family", "")}


def font_css(doc, key, b=None, s=None):
    f = font_style(doc, key, b, s)
    # virgolette doppie: gli attributi style='…' del foglio usano quelle semplici
    family = f'font-family:"{f["family"]}",Cambria,Georgia,serif; ' if f["family"] else ""
    return (f"{family}font-size:{f['size']}pt; font-weight:{'bold' if f['bold'] else 'normal'}; "
            f"font-style:{'italic' if f['italic'] else 'normal'}")


def _cell(text, accent_text, color, css, align, img=None, width=""):
    """Prima riga del testo in scuro, le successive (prezzo alternativo) nel colore d'accento.
    css = grandezza e stile del testo; img = (nome risorsa, larghezza, altezza): la foto va a sinistra del testo."""
    lines = str(text).split("\n")
    out = []
    for i, line in enumerate(lines):
        col = color if i == 0 else accent_text
        out.append(f"<span style='color:{col}'>{html.escape(line)}</span>")
    body = "<br>".join(out)
    if img:
        name, w, h = img
        pic = f"<img src='{name}' width='{w}' height='{h}'>"
        body = (f"<table border='0' cellspacing='0' cellpadding='0'><tr><td valign='middle'>{pic}</td>"
                f"<td valign='middle' style='padding-left:6px; {css}'>{body}</td></tr></table>"
                if str(text).strip() else pic)
    w = f" width='{width}%'" if width else ""
    return f"<td{w} align='{align}' valign='middle' style='padding:5px; {css}'>{body}</td>"


LINE_COLOR = "#8b97a5"  # righe della tabella: più marcate (prima #b9c2cc, troppo chiare)


def _title_html(doc):
    text = doc.get("text_color") or DEFAULT_TEXT
    title_color = doc.get("doc_title_color") or text
    css = font_css(doc, "title")
    if doc.get("title") and doc.get("title_bg"):  # titolo su una fascia del colore del foglio
        accent = doc.get("accent") or DEFAULT_ACCENT
        return (f"<table width='100%' border='0' cellspacing='0' cellpadding='0'><tr>"
                f"<td align='center' bgcolor='{accent}' style='padding:6px'>"
                f"<span style='{css}; color:{title_color}'>{_esc(doc['title'])}</span></td></tr></table>"
                f"<div style='font-size:6pt'>&nbsp;</div>")
    if doc.get("title"):
        return (f"<p align='center' style='{css}; color:{title_color}; margin:0 0 8px 0'>"
                f"{_esc(doc['title'])}</p>")
    return ""


def _section_html(doc, bi, block, si, a, b, with_images):
    """Tabella della sezione con le sole righe a..b-1: fascia e intestazioni ci sono sempre
    (una sezione che continua sulla pagina dopo le ripete)."""
    s = block["sections"][si]
    sec_bg, _head, _name, sec_title_color = block_colors(doc, block)
    css_sec = font_css(doc, "sec", block)
    imgs = row_images(s) if with_images else [""] * len(s["rows"])
    n = max(1, len(s["cols"]))
    first_w = 34
    rest_w = (66 // max(1, n - 1)) if n > 1 else 66
    widths = [first_w] + [rest_w] * (n - 1)
    t = [f"<table width='100%' border='1' cellspacing='0' cellpadding='0' "
         f"style='border-collapse:collapse; border-style:solid; border-color:{LINE_COLOR}'>"]
    t.append(f"<tr><td colspan='{n}' align='center' bgcolor='{sec_bg}' style='padding:4px'>"
             f"<span style='{css_sec}; color:{sec_title_color}; letter-spacing:1px'>"
             f"{_esc(s['title'])}</span></td></tr>")
    head_c, text_c = section_colors(doc, block, s)
    css_head, css_text = font_css(doc, "head", s=s), font_css(doc, "text", s=s)
    # intestazioni tutte vuote: niente riga vuota sotto la fascia (le larghezze passano alla prima riga)
    has_head = any(str(c).strip() for c in s["cols"])
    if has_head:
        t.append("<tr>" + "".join(
            f"<td width='{widths[i]}%' align='{'left' if i == 0 else 'center'}' style='padding:5px'>"
            f"<span style='{css_head}; color:{head_c}'>{_esc(c)}</span></td>"
            for i, c in enumerate(s["cols"])) + "</tr>")
    for ri in range(a, b):
        r = s["rows"][ri]
        img = None
        if imgs[ri]:
            img = (row_img_name(bi, si, ri), *_fit(base64.b64decode(imgs[ri])))
        t.append("<tr>" + "".join(
            _cell(r[i] if i < len(r) else "", head_c, text_c, css_text, "left" if i == 0 else "center",
                  img if i == 0 else None, widths[i] if ri == a and not has_head else "")
            for i in range(n)) + "</tr>")
    t.append("</table><div style='font-size:3pt'>&nbsp;</div>")
    return "".join(t)


def _block_html(doc, bi, chunks, with_images, page_break=False):
    """Riquadro del marchio + le sue sezioni (chunks = [(si, da_riga, a_riga)]): su ogni pagina il marchio si ripete."""
    block = doc["blocks"][bi]
    sec_bg, _head, name_color, _sec_c = block_colors(doc, block)
    # foto senza sfondo: il riquadro resta bianco (solo se c'è la foto, se no il nome sparirebbe)
    brand_bg = "" if block.get("no_bg") and block.get("logo") else f" bgcolor='{sec_bg}'"
    if with_images and block.get("logo"):
        logo = f"<img src='{logo_name(bi)}' width='150'>"
    else:
        logo = (f"<span style='{font_css(doc, 'name', block)}; color:{name_color}'>"
                f"{_esc(block.get('name', ''))}</span>")
    inner = "".join(_section_html(doc, bi, block, si, a, b, with_images) for si, a, b in chunks)
    brk = " style='page-break-before:always'" if page_break else ""
    return (f"<table width='100%' border='0' cellspacing='0' cellpadding='0'{brk}><tr>"
            f"<td width='24%' align='center' valign='middle'{brand_bg}>{logo}</td>"
            f"<td width='1%'></td>"
            f"<td width='75%' valign='top'>{inner}</td></tr></table>"
            f"<div style='font-size:6pt'>&nbsp;</div>")


def all_in_one_page(doc):
    """Tutto il listino come se fosse una pagina sola: [(marchio, [(sezione, da_riga, a_riga)])]."""
    return [[(bi, [(si, 0, len(s["rows"])) for si, s in enumerate(b["sections"])])
             for bi, b in enumerate(doc["blocks"])]]


def render_html(doc, with_images=True, pages=None, title=True):
    """pages = [pagina, …], pagina = [(marchio, [(sezione, da_riga, a_riga)])]: ogni pagina dalla seconda in poi
    inizia con un salto pagina, così le righe non vengono mai tagliate a metà (vedi MainWindow.paginate)."""
    text = doc.get("text_color") or DEFAULT_TEXT
    parts = [f"<html><body style=\"font-family:'Cambria','Georgia','Times New Roman',serif; color:{text}\">"]
    if pages is None:
        pages = all_in_one_page(doc)
    for p, page in enumerate(pages):
        if p == 0 and title:
            parts.append(_title_html(doc))
        for k, (bi, chunks) in enumerate(page):
            parts.append(_block_html(doc, bi, chunks, with_images, page_break=(p > 0 and k == 0)))
    parts.append("</body></html>")
    return "".join(parts)


def logo_bytes(block):
    return base64.b64decode(block["logo"]) if block.get("logo") else b""


def all_row_images(doc):
    """[(nome risorsa, byte)] di tutte le foto riga, per caricarle nel documento da stampare."""
    out = []
    for bi, b in enumerate(doc["blocks"]):
        for si, s in enumerate(b["sections"]):
            for ri, data in enumerate(row_images(s)):
                if data:
                    out.append((row_img_name(bi, si, ri), base64.b64decode(data)))
    return out
