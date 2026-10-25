"""Genera le icone: assets/tk-listino.ico (Windows) e, con --iconset, assets/tk-listino.iconset (macOS)."""
import os
import struct
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
if sys.platform == "win32":
    sys.path.insert(0, r"C:\Users\TecnikGeek\tk-pdf\.venv\Lib\site-packages")

from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)
from tklistino.app import render_icon

ASSETS = os.path.join(ROOT, "assets")
os.makedirs(ASSETS, exist_ok=True)


def png_bytes(size):
    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    render_icon(size).save(buf, "PNG")
    return bytes(buf.data())


if "--iconset" in sys.argv:
    iconset = os.path.join(ASSETS, "tk-listino.iconset")
    os.makedirs(iconset, exist_ok=True)
    for base in (16, 32, 128, 256, 512):
        render_icon(base).save(os.path.join(iconset, f"icon_{base}x{base}.png"))
        render_icon(base * 2).save(os.path.join(iconset, f"icon_{base}x{base}@2x.png"))
else:
    images = [(size, png_bytes(size)) for size in (16, 32, 48, 64, 128, 256)]
    out = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    data = b""
    for size, png in images:
        out += struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(png), offset + len(data))
        data += png
    with open(os.path.join(ASSETS, "tk-listino.ico"), "wb") as fh:
        fh.write(out + data)
print("icone generate")
