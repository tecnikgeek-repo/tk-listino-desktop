"""Prepara la cartella «licenze» del pacchetto: AGPL di tk-listino, testi delle licenze dei componenti inclusi
DAVVERO nel pacchetto (copiati da licenze/ e dai *.dist-info dei pacchetti) e COMPONENTI.txt con le versioni.

Uso (lo chiamano installer/build.ps1 e mac/build_mac.sh):
    python tools_licenze.py <cartella di uscita> <site-packages> [--mac]
"""
import glob
import os
import platform
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
TESTI = os.path.join(ROOT, "licenze")

QT_SORGENTE = ("https://download.qt.io/official_releases/QtForPython/ e "
               "https://code.qt.io/cgit/pyside/pyside-setup.git (Qt: https://download.qt.io/official_releases/qt/)")


def versione(sp, nome):
    """Versione del pacchetto dal nome della sua cartella *.dist-info ("" se non c'è)."""
    for d in glob.glob(os.path.join(sp, "*.dist-info")):
        m = re.match(r"(.+?)-([^-]+)\.dist-info$", os.path.basename(d))
        if m and m.group(1).lower().replace("-", "_") == nome.lower().replace("-", "_"):
            return m.group(2), d
    return "", None


def copia_dist_info(dist, uscita, prefisso):
    """File di licenza di un *.dist-info (cartella licenses/ o LICENSE*/COPYING*), appiattiti con un prefisso."""
    if not dist:
        return []
    fatti = []
    trovati = glob.glob(os.path.join(dist, "licenses", "**", "*"), recursive=True)
    trovati += [p for p in glob.glob(os.path.join(dist, "*")) if re.match(r"(LICEN[CS]E|COPYING)", os.path.basename(p), re.I)]
    for p in sorted(set(trovati)):
        if not os.path.isfile(p) or "Qt-Commercial" in p:
            continue  # la licenza commerciale di Qt non è quella con cui lo distribuiamo (LGPL)
        nome, est = os.path.splitext(os.path.basename(p))
        if est.lower() not in ("", ".txt"):
            nome += "-" + est[1:]  # libjpeg_turbo.ijg e libjpeg_turbo.md: due file diversi
        dest = f"{prefisso}-{nome}.txt"
        shutil.copyfile(p, os.path.join(uscita, dest))
        fatti.append(dest)
    return fatti


def main():
    uscita, sp = sys.argv[1], sys.argv[2]
    mac = "--mac" in sys.argv
    if os.path.isdir(uscita):
        shutil.rmtree(uscita)
    os.makedirs(uscita)

    testi = ["COPYING-AGPL-3.0.txt", "LGPL-3.0.txt", "GPL-3.0.txt", "MPL-2.0.txt", "Apache-2.0.txt",
             "BSD-3-Clause.txt", "OFL-1.1.txt", "Python-PSF.txt"]
    if mac:
        testi += ["MIT.txt", "GPL-2.0.txt"]  # pyobjc (MIT); PyInstaller (GPL-2.0 con eccezione per il bootloader)
    for t in testi:
        shutil.copyfile(os.path.join(TESTI, t), os.path.join(uscita, t))

    from tklistino import VERSION  # noqa: E402 (ROOT è nel percorso: questo file sta nella radice del repo)
    v_qt, _d = versione(sp, "pyside6_essentials")
    v_shiboken, _d = versione(sp, "shiboken6")
    v_certifi, d_certifi = versione(sp, "certifi")
    v_pdfium2, d_pdfium2 = versione(sp, "pypdfium2")
    extra = copia_dist_info(d_pdfium2, uscita, "pypdfium2")
    copia_dist_info(d_certifi, uscita, "certifi")
    pdfium_build = ""
    try:
        import json
        with open(os.path.join(sp, "pypdfium2_raw", "version.json"), encoding="utf-8") as fh:
            j = json.load(fh)
        pdfium_build = f"{j['major']}.{j['minor']}.{j['build']}.{j['patch']}"
    except Exception:
        pass

    righe = [
        f"tk-listino {VERSION} — componenti inclusi nel pacchetto ({'macOS' if mac else 'Windows'})",
        "=" * 72,
        "",
        f"tk-listino {VERSION}",
        "  Licenza: GNU AGPL-3.0-or-later (COPYING-AGPL-3.0.txt)",
        f"  Sorgente: https://github.com/tecnikgeek-repo/tk-listino-desktop/tree/v{VERSION}",
        "  Il nome tk-listino e il logo non sono coperti dalla licenza (AGPL sez. 7):",
        "  una versione modificata deve avere un nome diverso.",
        "",
        f"Python {platform.python_version()}",
        "  Licenza: PSF License (Python-PSF.txt; i componenti di Python sono elencati nel suo LICENSE.txt)",
        "  Sorgente: https://www.python.org/downloads/source/",
        "",
        f"Qt for Python (PySide6 {v_qt}, shiboken6 {v_shiboken}) e le librerie Qt {v_qt}",
        "  Licenza: GNU LGPL-3.0 (LGPL-3.0.txt, che si legge insieme a GPL-3.0.txt)",
        f"  Sorgente: {QT_SORGENTE}",
        "  Le librerie Qt sono file separati nel pacchetto e si possono sostituire con una versione compatibile.",
        "",
        f"pypdfium2 {v_pdfium2} (lettura dei PDF) con PDFium {pdfium_build}",
        "  Licenza: Apache-2.0 / BSD-3-Clause (Apache-2.0.txt, BSD-3-Clause.txt); PDFium e le librerie che",
        "  contiene (FreeType, ICU, Little CMS, libjpeg-turbo, OpenJPEG, libpng, zlib, Abseil...): file pypdfium2-*.txt",
        "  Sorgente: https://github.com/pypdfium2-team/pypdfium2 · https://pdfium.googlesource.com/pdfium/",
        "           · https://github.com/bblanchon/pdfium-binaries",
        "",
        f"certifi {v_certifi} (certificati per le connessioni sicure)",
        "  Licenza: MPL-2.0 (MPL-2.0.txt)",
        "  Sorgente: https://github.com/certifi/python-certifi",
        "",
        "Caratteri Roboto, Open Sans, Lato, Montserrat, Poppins, Oswald, Raleway, Nunito, Playfair Display,",
        "Merriweather (cartella tklistino/fonts)",
        "  Licenza: SIL Open Font License 1.1 (OFL-1.1.txt); Roboto: Apache-2.0",
        "  Sorgente: https://fonts.google.com · https://github.com/google/fonts",
        "",
    ]
    if mac:
        v_pyi, d_pyi = versione(sp, "pyinstaller")
        v_objc, d_objc = versione(sp, "pyobjc_core")
        copia_dist_info(d_pyi, uscita, "pyinstaller")
        copia_dist_info(d_objc, uscita, "pyobjc")
        righe += [
            f"PyInstaller {v_pyi} (avvio del programma nel bundle .app)",
            "  Licenza: GPL-2.0 con eccezione per il bootloader (GPL-2.0.txt, pyinstaller-*.txt)",
            "  Sorgente: https://github.com/pyinstaller/pyinstaller",
            "",
            f"PyObjC {v_objc} (riconoscimento del testo con Apple Vision)",
            "  Licenza: MIT (MIT.txt)",
            "  Sorgente: https://github.com/ronaldoussoren/pyobjc",
            "",
        ]
    else:
        righe += [
            "Microsoft Visual C++ Runtime (msvcp140, vcruntime140, concrt140: arrivano con PySide6)",
            "  Licenza: file ridistribuibili di Microsoft Visual Studio",
            "",
        ]
    with open(os.path.join(uscita, "COMPONENTI.txt"), "w", encoding="utf-8", newline="\r\n" if not mac else "\n") as fh:
        fh.write("\n".join(righe))
    print(f"licenze: {len(os.listdir(uscita))} file ({len(extra)} da pypdfium2)")


if __name__ == "__main__":
    sys.path.insert(0, ROOT)
    main()
