# -*- mode: python -*-
# PyInstaller: crea "tkLISTINO.app" per macOS. Uso: pyinstaller --noconfirm --clean mac/tk-listino-mac.spec
import os
import re

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))
with open(os.path.join(ROOT, "tklistino", "__init__.py"), encoding="utf-8") as fh:
    VERSION = re.search(r'VERSION = "(.+)"', fh.read()).group(1)

a = Analysis(
    [os.path.join(ROOT, "run.py")],
    pathex=[ROOT],
    datas=[(os.path.join(ROOT, "tklistino", "fonts"), os.path.join("tklistino", "fonts")),  # caratteri Google
           # licenze del programma e dei componenti (le prepara build_mac.sh con tools_licenze.py)
           (os.path.join(ROOT, "licenze-pacchetto"), "licenze")]
          + collect_data_files("pypdfium2") + collect_data_files("pypdfium2_raw"),  # version.json di PDFium
    binaries=collect_dynamic_libs("pypdfium2_raw"),  # libpdfium.dylib
    hiddenimports=["PySide6.QtPrintSupport", "Vision", "Foundation", "objc", "pypdfium2", "pypdfium2_raw", "pypdfium2_cfg"],
    excludes=["tkinter", "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtWebEngineCore", "PySide6.QtMultimedia"],
)

# componenti Qt non usati da un'app a widget
DROP = ("QtQuick", "QtQml", "QtVirtualKeyboard", "QtPdf", "libqpdf", "QtWebEngine", "Qt3D", "QtMultimedia")
a.binaries = [b for b in a.binaries if not any(k in b[0] for k in DROP)]
a.datas = [d for d in a.datas if not any(k in d[0] for k in DROP)]

pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="tkLISTINO", console=False, argv_emulation=False)
coll = COLLECT(exe, a.binaries, a.datas, name="tkLISTINO")
app = BUNDLE(
    coll,
    name="tkLISTINO.app",
    icon=os.path.join(ROOT, "assets", "tk-listino.icns"),
    bundle_identifier="com.tecnikgeek.tklistino",
    version=VERSION,
    info_plist={
        "CFBundleName": "tkLISTINO",
        "CFBundleDisplayName": "tkLISTINO",
        # il bundle resta «tkLISTINO.app» (lo script di aggiornamento delle versioni installate cerca quel nome nel dmg):
        # il nome visibile «tk-listino» (Finder, Dock, menu) arriva dai InfoPlist.strings che build_mac.sh mette in *.lproj
        "LSHasLocalizedDisplayName": True,
        "CFBundleShortVersionString": VERSION,
        "CFBundleVersion": VERSION,
        "NSHighResolutionCapable": True,
        "NSRequiresAquaSystemAppearance": True,
        "NSHumanReadableCopyright": "© 2026 Pietro De Filippis (TecnikGeek) - software libero AGPL-3.0",
        "LSApplicationCategoryType": "public.app-category.productivity",
        "CFBundleDocumentTypes": [
            {
                "CFBundleTypeName": "Listino tk-listino",
                "CFBundleTypeRole": "Editor",
                "CFBundleTypeExtensions": ["listino"],
                "LSHandlerRank": "Owner",
            },
            {
                "CFBundleTypeName": "Documento PDF",
                "CFBundleTypeRole": "Viewer",
                "LSHandlerRank": "Alternate",
                "LSItemContentTypes": ["com.adobe.pdf"],
            },
        ],
    },
)
