# -*- mode: python -*-
# PyInstaller: crea la cartella «dist/tk-listino» per Linux, poi build_linux.sh la mette nell'AppImage (insieme alla
# cartella di Tesseract preparata da linux/prepara_tesseract.sh). Uso: pyinstaller --noconfirm --clean linux/tk-listino-linux.spec
import os

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))

extra_bin = []
xcb_lib = os.path.join(ROOT, "build", "xcb-cursor", "libxcb-cursor.so.0")
if os.path.isfile(xcb_lib):
    extra_bin.append((xcb_lib, "."))  # libxcb-cursor per chi usa X11 (build_linux.sh)

a = Analysis(
    [os.path.join(ROOT, "run.py")],
    pathex=[ROOT],
    datas=[(os.path.join(ROOT, "tklistino", "fonts"), os.path.join("tklistino", "fonts")),  # caratteri Google
           (os.path.join(ROOT, "build", "tk-listino-512.png"), "assets"),
           # licenze del programma e dei componenti (le prepara build_linux.sh con tools_licenze.py --linux)
           (os.path.join(ROOT, "licenze-pacchetto"), "licenze")]
          + collect_data_files("pypdfium2") + collect_data_files("pypdfium2_raw"),  # version.json di PDFium
    binaries=collect_dynamic_libs("pypdfium2_raw") + extra_bin,  # libpdfium.so
    hiddenimports=["PySide6.QtPrintSupport", "pypdfium2", "pypdfium2_raw", "pypdfium2_cfg", "tklistino.ocr_linux",
                   "tklistino.tk_linux"],
    excludes=["tkinter", "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtWebEngineCore", "PySide6.QtMultimedia",
              "pymupdf", "fitz"],
)

# componenti Qt non usati da un'app a widget
DROP = ("QtQuick", "QtQml", "QtVirtualKeyboard", "QtPdf", "libqpdf", "QtWebEngine", "Qt3D", "QtMultimedia")
a.binaries = [b for b in a.binaries if not any(k in b[0] for k in DROP)]
a.datas = [d for d in a.datas if not any(k in d[0] for k in DROP)]
# stampa: si usa la libcups del sistema (c'è in ogni Ubuntu e parla con il suo servizio di stampa)
a.binaries = [b for b in a.binaries if not os.path.basename(b[0]).startswith("libcups.so")]

pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="tk-listino", console=False, strip=False)
coll = COLLECT(exe, a.binaries, a.datas, name="tk-listino")
