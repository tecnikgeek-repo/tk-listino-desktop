"""Prepara una foto per la lettura del testo: il testo chiaro o colorato (rosa, azzurro…) diventa scuro."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage


def enhance(img):
    """Canale verde (il rosa lì è scuro) + stiramento dei livelli + scurimento dei grigi medi."""
    img = img.convertToFormat(QImage.Format.Format_RGB32)
    w, h = img.width(), img.height()
    ptr = img.constBits()
    raw = bytes(ptr)[: img.bytesPerLine() * h]
    bpl = img.bytesPerLine()
    # canale verde di ogni pixel (BGRA in memoria): si lavora su righe campionate per l'istogramma
    hist = [0] * 256
    for y in range(0, h, 4):
        row = raw[y * bpl: y * bpl + w * 4]
        for g in row[1::4][::3]:
            hist[g] += 1
    total = sum(hist) or 1
    lo = hi = None
    acc = 0
    for v in range(256):
        acc += hist[v]
        if lo is None and acc >= total * 0.015:
            lo = v
        if acc >= total * 0.80:  # il fondo carta: oltre l'80% dei pixel
            hi = v
            break
    lo = lo or 0
    hi = max((hi or 255), lo + 30)
    lut = bytes(max(0, min(255, int(255 * (((v - lo) / (hi - lo)) ** 1.6)))) if v > lo else 0 for v in range(256))
    out = bytearray(w * h)
    for y in range(h):
        row = raw[y * bpl: y * bpl + w * 4]
        out[y * w:(y + 1) * w] = row[1::4].translate(lut)
    gray = QImage(bytes(out), w, h, w, QImage.Format.Format_Grayscale8).copy()
    return gray.convertToFormat(QImage.Format.Format_RGB32)
