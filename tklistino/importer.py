"""Importa un listino da foto o PDF: lettura del testo (OCR di Windows o di macOS, Tesseract incluso su Linux) e ricostruzione di righe e colonne."""
import os
import re
import statistics

from PySide6.QtGui import QColor, QImage

from tklistino import model, ocr, prep

IMAGE_EXT = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tif", ".tiff")
PDF_EXT = (".pdf",)
MAX_PAGES = 12


# ------------------------------------------------------------------ PDF e immagini
# I PDF si leggono con pypdfium2 (PDFium, licenza Apache-2.0/BSD-3-Clause): testo con la posizione e pagine in immagine.
def _page_words(page):
    """Parole della pagina come (testo, x, y, larghezza, altezza), origine in alto a sinistra come sullo schermo.
    Una parola finisce a ogni spazio o a capo (anche quelli che PDFium aggiunge da sé) e quando si cambia riga."""
    import pypdfium2.raw as pdfium_c
    textpage = page.get_textpage()
    try:
        top_y = page.get_height()
        words, cur = [], None

        def close():
            if cur and cur["text"].strip():
                words.append((cur["text"], cur["x0"], top_y - cur["y1"], cur["x1"] - cur["x0"], cur["y1"] - cur["y0"]))

        for i in range(textpage.count_chars()):
            ch = chr(pdfium_c.FPDFText_GetUnicode(textpage, i) or 32)
            if ch.isspace() or ch == "\x00":
                close()
                cur = None
                continue
            left, bottom, right, top = textpage.get_charbox(i, loose=True)  # loose: altezza della riga, non del segno
            if cur is not None:
                mid, cur_mid = (bottom + top) / 2, (cur["y0"] + cur["y1"]) / 2
                if abs(mid - cur_mid) > 0.5 * (cur["y1"] - cur["y0"]) or left < cur["x0"]:
                    close()  # altra riga (o si torna indietro) senza spazio in mezzo
                    cur = None
            if cur is None:
                cur = {"text": ch, "x0": left, "x1": right, "y0": bottom, "y1": top}
            else:
                cur["text"] += ch
                cur["x0"], cur["x1"] = min(cur["x0"], left), max(cur["x1"], right)
                cur["y0"], cur["y1"] = min(cur["y0"], bottom), max(cur["y1"], top)
        close()
        return words
    finally:
        textpage.close()


def pdf_words(path):
    """Testo vero del PDF (se c'è): parole con posizione, una lista per pagina. None se è una scansione."""
    try:
        import pypdfium2 as pdfium
    except ImportError:
        return None
    try:
        doc = pdfium.PdfDocument(path)
    except Exception:
        return None
    pages, total = [], 0
    try:
        for i in range(min(len(doc), MAX_PAGES)):
            page = doc[i]
            try:
                ws = _page_words(page)
            finally:
                page.close()
            total += len(ws)
            pages.append(ws)
    except Exception:
        return None
    finally:
        doc.close()
    return pages if total >= 20 else None


def load_images(path, max_pages=MAX_PAGES):
    """Ritorna la lista di QImage del file (una per pagina, per i PDF)."""
    ext = os.path.splitext(path)[1].lower()
    if ext in PDF_EXT:
        import pypdfium2 as pdfium
        try:
            pdf = pdfium.PdfDocument(path)
        except Exception:
            raise ValueError("il PDF non si apre (protetto da password o danneggiato?)")
        images = []
        try:
            for i in range(min(len(pdf), max_pages)):
                page = pdf[i]
                try:
                    k = 2200 / max(page.get_width(), 1)
                    # rev_byteorder: i byte escono in ordine RGB, quello che vuole QImage
                    bmp = page.render(scale=k, rev_byteorder=True)
                    fmt = QImage.Format.Format_RGB888 if bmp.n_channels == 3 else QImage.Format.Format_RGBX8888
                    data = bytes(bmp.buffer)
                    images.append(QImage(data, bmp.width, bmp.height, bmp.stride, fmt)
                                  .convertToFormat(QImage.Format.Format_RGB888).copy())
                    bmp.close()
                finally:
                    page.close()
        finally:
            pdf.close()
        if not images:
            raise ValueError("il PDF non ha pagine leggibili")
        return images
    img = QImage(path)
    if img.isNull():
        raise ValueError("immagine non leggibile")
    return [img]


def dominant_color(img):
    """Colore più presente tra quelli «colorati» (non grigi, non scuri): diventa il colore del foglio."""
    img = img.convertToFormat(QImage.Format.Format_RGB32)
    step = max(1, min(img.width(), img.height()) // 220)
    buckets = {}
    for y in range(0, img.height(), step):
        for x in range(0, img.width(), step):
            c = QColor(img.pixel(x, y))
            h, s, v, _ = c.getHsv()
            if s > 35 and v > 170:
                key = (h // 12, s // 40, v // 40)
                b = buckets.setdefault(key, [0, 0, 0, 0])
                b[0] += 1
                b[1] += c.red()
                b[2] += c.green()
                b[3] += c.blue()
    if not buckets:
        return None
    n, r, g, b = max(buckets.values(), key=lambda v: v[0])
    if n < 30:
        return None
    hue = QColor(r // n, g // n, b // n).hsvHue()
    return QColor.fromHsv(max(hue, 0), 85, 245).name()  # tinta della foto, in versione pastello


# ------------------------------------------------------------------ ricostruzione tabella
def _flatten(lines):
    words = []
    for line in lines:
        for text, r in line:
            text = text.strip()
            if text:
                words.append((text, r.x(), r.y(), r.width(), r.height()))
    return words


def _group_rows(words, h, tol=0.8):
    words = sorted(words, key=lambda w: w[2] + w[4] / 2)
    rows, cur, cur_y = [], [], None
    for w in words:
        cy = w[2] + w[4] / 2
        if cur and abs(cy - cur_y) <= tol * h:
            cur.append(w)
            cur_y = sum(x[2] + x[4] / 2 for x in cur) / len(cur)
        else:
            if cur:
                rows.append(cur)
            cur, cur_y = [w], cy
    if cur:
        rows.append(cur)
    return rows


def _cells(row, h, exact=False):
    """Parole di una riga → celle (testo, centro x). Parole vicine si uniscono; quelle impilate (due prezzi
    uno sotto l'altro nella stessa cella) diventano due righe."""
    row = sorted(row, key=lambda w: w[1])
    groups = []
    for w in row:
        if groups and w[1] - groups[-1]["end"] <= 1.7 * h:
            groups[-1]["words"].append(w)
            groups[-1]["end"] = max(groups[-1]["end"], w[1] + w[3])
        else:
            groups.append({"words": [w], "start": w[1], "end": w[1] + w[3]})
    cells = []
    for g in groups:
        ws = sorted(g["words"], key=lambda w: w[2] + w[4] / 2)
        lines, cur, cy = [], [], None
        for w in ws:
            c = w[2] + w[4] / 2
            if cur and abs(c - cy) > 0.45 * h:
                lines.append(cur)
                cur = []
            cur.append(w)
            cy = sum(x[2] + x[4] / 2 for x in cur) / len(cur)
        lines.append(cur)
        texts = []
        for ln in lines:
            ln.sort(key=lambda w: w[1])
            t = ln[0][0]
            for prev, w in zip(ln, ln[1:]):
                gap = w[1] - (prev[1] + prev[3])
                t += ("" if (not exact and gap < 0.15 * h) else " ") + w[0]
            texts.append(t)
        cells.append({"text": "\n".join(texts), "start": g["start"], "end": g["end"],
                      "cx": (g["start"] + g["end"]) / 2})
    return cells


def _columns(all_cells, h):
    xs = sorted(c["cx"] for c in all_cells)
    if not xs:
        return []
    groups, cur = [], [xs[0]]
    for x in xs[1:]:
        if x - cur[-1] > 3.5 * h:
            groups.append(cur)
            cur = [x]
        else:
            cur.append(x)
    groups.append(cur)
    top = max(len(g) for g in groups)
    return [sum(g) / len(g) for g in groups if len(g) >= max(2, 0.2 * top)]


NUM = re.compile(r"\d")


def _is_title(text):
    letters = [c for c in text if c.isalpha()]
    return len(letters) >= 5 and "+" not in text and not NUM.search(text) and text == text.upper()


MONEY = re.compile(r"-?€?(\d{1,3}(\.\d{3})+|\d+),\d\d")  # prezzo scritto per bene: 1.250,00 · 695,00 · -3,00


def _clean_line(text, money, exact):
    """Una riga di una cella di prezzi → (testo pulito, da controllare?). Da controllare = cambiata dalle regole
    (scritte prima delle cifre, virgola aggiunta) o, per le foto, con una forma che non è quella di un prezzo."""
    raw = text.strip()
    negative = bool(re.match(r"[-−–]\s*\d", raw))  # il segno meno resta (sconti, rettifiche)
    t = re.sub(r"^[^\d€]*(?=\d)", "", raw).replace(" ", "")
    if negative and not t.startswith("-"):
        t = "-" + t
    # «69500» → «695,00»: solo per il riconoscimento da foto (che a volte perde la virgola) e solo se la colonna
    # ha già i decimali veri; nel testo di un PDF le cifre sono esatte e non si toccano
    if money and not exact and re.fullmatch(r"-?\d{4,}", t):
        t = t[:-2] + "," + t[-2:]
    doubt = t != raw.replace(" ", "").replace("−", "-").replace("–", "-")
    if not exact and money and not MONEY.fullmatch(t):
        doubt = True
    return t, doubt


def _clean_numeric(text, money, exact=False):
    """Cella di una colonna di prezzi (anche con più righe: prezzo alternativo) → (testo, da controllare?)."""
    lines = [_clean_line(ln, money, exact) for ln in text.split("\n") if ln.strip()]
    return "\n".join(t for t, _d in lines), any(d for _t, d in lines)


def table_from_words(words, exact=False):
    """Parole con posizione → (sezioni [{title, cols, rows}], titolo del foglio, nome del marchio)."""
    if not words:
        return [], "", ""
    hs = [w[4] for w in words]
    med = statistics.median(hs)
    words = [w for w in words if 0.55 * med <= w[4] <= 2.4 * med]  # scarta scarabocchi, bordi, testo capovolto
    if not words:
        return [], "", ""
    h = statistics.median(w[4] for w in words)
    big = [w for w in words if w[4] > 1.3 * h]  # scritte grandi: titolo in cima o nome del marchio
    words = [w for w in words if w[4] <= 1.3 * h]
    top = min((w[2] for w in words), default=0)
    title = " ".join(w[0] for w in sorted((w for w in big if w[2] + w[4] <= top + 0.5 * h), key=lambda w: w[1]))
    brand = " ".join(w[0] for w in sorted((w for w in big if w[2] + w[4] > top + 0.5 * h),
                                          key=lambda w: (round(w[2] / (2 * h)), w[1])))
    rows_w = _group_rows(words, h)
    rows_c = [_cells(r, h, exact) for r in rows_w]
    cols = _columns([c for r in rows_c for c in r], h)
    if len(cols) < 2:
        return [], "", ""
    n = len(cols)

    def col_of(cx):
        i = min(range(n), key=lambda k: abs(cols[k] - cx))
        return i if abs(cols[i] - cx) <= 3 * 3.5 * h else None

    grid = []
    for r in rows_c:
        row = [""] * n
        for c in r:
            i = col_of(c["cx"])
            if i is None:
                continue
            row[i] = (row[i] + " " + c["text"]).strip()
        if any(row):
            grid.append(row)

    # colonne con quasi solo numeri → prezzi (pulizia delle cifre)
    numeric = []
    money = []
    for i in range(n):
        vals = [g[i] for g in grid if g[i]]
        digits = sum(1 for v in vals if NUM.search(v))
        numeric.append(bool(vals) and digits >= 0.7 * len(vals) and i > 0)
        # colonna di prezzi «con i decimali veri»: almeno metà dei valori (e almeno due) finisce con «,00»
        money.append(sum(1 for v in vals if re.search(r",\d\d$", v)) >= max(2, 0.5 * len(vals)))

    sections, cur, pending_title, doc_title = [], None, "", title

    def is_header(r):
        f = [v for v in r if v]
        return len(f) >= 2 and not any(NUM.search(v) for v in f)

    def start(title, cols_text):
        nonlocal cur
        # dubbi = per ogni riga, le colonne da far controllare (vedi model.row_marks)
        cur = {"title": title or f"SEZIONE {len(sections) + 1}", "cols": cols_text, "rows": [], "dubbi": []}
        sections.append(cur)

    def clean(i, v):
        if numeric[i] and v:
            return _clean_numeric(v, money[i], exact)
        return v, False

    for gi, row in enumerate(grid):
        filled = [v for v in row if v]
        has_digit = any(NUM.search(v) for v in filled)
        if len(filled) >= 2 and not has_digit:  # riga di intestazioni
            start(pending_title, [v or "" for v in row])
            pending_title = ""
            continue
        if cur is None and len(filled) == 1 and not has_digit and not pending_title and not doc_title                 and not (gi + 1 < len(grid) and is_header(grid[gi + 1])):
            doc_title = filled[0]  # una sola scritta in cima, prima della tabella: titolo del foglio
            continue
        if len(filled) == 1 and not has_digit:
            nxt = grid[gi + 1] if gi + 1 < len(grid) else None
            if _is_title(filled[0]) and (cur is None or (nxt is not None and is_header(nxt))):
                pending_title = filled[0]  # titolo di sezione: subito dopo c'è la riga delle intestazioni
                continue
            if cur is not None and cur["rows"] and row[0]:
                cur["rows"][-1][0] = (cur["rows"][-1][0] + " " + row[0]).strip()  # nome su due righe
                continue
        if cur is None:
            start(pending_title, [""] * n)
            pending_title = ""
        # seconda riga di una cella (prezzo alternativo): niente nella prima colonna e cifre sotto
        if not row[0] and has_digit and cur["rows"]:
            prev, marks = cur["rows"][-1], cur["dubbi"][-1]
            for i, v in enumerate(row):
                if v:
                    v, doubt = clean(i, v)
                    prev[i] = (prev[i] + "\n" + v) if prev[i] else v
                    if doubt and i not in marks:
                        marks.append(i)
            continue
        out, marks = [], []
        for i, v in enumerate(row):
            v, doubt = clean(i, v)
            out.append(v)
            if doubt:
                marks.append(i)
        cur["rows"].append(out)
        cur["dubbi"].append(marks)

    for s in sections:
        s["cols"] = (s["cols"] + [""] * n)[:n]
        s["rows"] = [(r + [""] * n)[:n] for r in s["rows"]]
        if not any(s["dubbi"]):
            del s["dubbi"]
    sections = [s for s in sections if s["rows"] or any(s["cols"])]
    _fix_headers(sections, n)
    return sections, doc_title, brand


KNOWN_HEADERS = ["MODELLO", "KW", "CASH", "IVATO", "BTU/h", "PREZZO", "DESCRIZIONE", "CODICE", "ARTICOLO", "QUANTITA",
                 "LISTINO", "SCONTO", "NETTO", "PEZZI", "COLORE", "MISURA", "TOTALE"]


def _fix_headers(sections, n):
    """Intestazioni storpiate dalla lettura («MOI)EIIO», «Atro») → quelle giuste, per somiglianza."""
    import difflib
    from collections import Counter
    for s in sections:
        s["cols"] = [_known(c, difflib) for c in s["cols"]]
    for i in range(n):
        count = Counter(s["cols"][i] for s in sections if s["cols"][i])
        if not count:
            continue
        common = count.most_common(1)[0][0]
        for s in sections:
            h = s["cols"][i]
            if not h:
                s["cols"][i] = common
            elif h != common and difflib.SequenceMatcher(None, h.upper(), common.upper()).ratio() >= 0.4                     and count[h] < count[common]:
                s["cols"][i] = common


def _known(text, difflib):
    t = text.strip()
    if not t:
        return ""
    key = re.sub(r"[^A-Za-z/]", "", t).upper()
    m = difflib.get_close_matches(key, [k.upper() for k in KNOWN_HEADERS], n=1, cutoff=0.55)
    if m:
        return next(k for k in KNOWN_HEADERS if k.upper() == m[0])
    return t.upper() if t.isalpha() else t


# ------------------------------------------------------------------ pubblico
def import_file(path, progress=None):
    """Foto o PDF → documento tk-listino (da controllare: l'OCR può sbagliare qualche cifra)."""
    is_pdf = path.lower().endswith(PDF_EXT)
    words_pages = pdf_words(path) if is_pdf else None
    if words_pages is not None:  # PDF con testo vero: nessun riconoscimento, cifre esatte
        if progress:
            progress("Leggo il testo del PDF…")
        try:
            color = dominant_color(load_images(path, 1)[0])
        except Exception:
            color = None
        sections, title, brand = [], "", ""
        for ws in words_pages:
            secs, t, b = table_from_words(ws, exact=True)
            sections += secs
            title, brand = title or t, brand or b
    else:
        images = load_images(path)
        if progress:
            progress("Preparo le immagini…")
        color = dominant_color(images[0])
        prepared = [prep.enhance(im) for im in images]
        if progress:
            progress("Leggo il testo…")
        pages = ocr.recognize(prepared)
        sections, title, brand = [], "", ""
        for lines in pages:
            secs, t, b = table_from_words(_flatten(lines))
            sections += secs
            title, brand = title or t, brand or b
    if not sections:
        raise ValueError("non ho trovato nessuna tabella: prova con una foto più nitida e dritta")
    doc = model.new_document()
    doc["name"] = os.path.splitext(os.path.basename(path))[0]
    doc["title"] = title
    if color:
        doc["accent"] = color
    block = model.new_block(brand.strip() or "Marchio 1")
    block["sections"] = sections
    doc["blocks"] = [block]
    doc["da_controllare"] = True  # prima del primo PDF o della prima stampa si chiede se è stato ricontrollato
    return doc


def summary(doc):
    secs = [s for b in doc["blocks"] for s in b["sections"]]
    return len(secs), sum(len(s["rows"]) for s in secs)
