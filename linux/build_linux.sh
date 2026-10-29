#!/bin/bash
# Crea dist/tk-listino-<versione>-linux-<arch>.AppImage. Da eseguire su Linux (Ubuntu di casa o runner di GitHub).
# Uso: bash linux/build_linux.sh
# Usa al massimo METÀ dei processori (JOBS per cambiarlo): con tutti, sul PC di casa la memoria si riempie.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export JOBS="${JOBS:-$(( $(nproc) / 2 > 0 ? $(nproc) / 2 : 1 ))}"  # esportato: dopo taskset nproc vede già la metà
if [ -z "${TK_BUILD_LIMITATA:-}" ] && command -v taskset >/dev/null; then
    export TK_BUILD_LIMITATA=1
    exec nice -n 10 taskset -c "0-$(( JOBS - 1 ))" bash "$0" "$@"
fi
ARCH="$(uname -m)"
PY="${PYTHON:-python3}"
VERSION="$($PY -c "import re;print(re.search(r'VERSION = \"(.+)\"', open('tklistino/__init__.py').read()).group(1))")"
APPIMAGETOOL_VER="1.9.0"
export OMP_THREAD_LIMIT="$JOBS"
echo "== tk-listino $VERSION per Linux ($ARCH), $JOBS processori"

$PY -m venv .venv-linux
# shellcheck disable=SC1091
source .venv-linux/bin/activate
python -m pip install --quiet --upgrade pip
# come sul Mac: niente PyMuPDF (i PDF da importare si leggono con pypdfium2)
python -m pip install --quiet "pyside6-essentials==6.11.*" "pypdfium2==5.14.*" certifi pyinstaller

mkdir -p dist build
echo "== Tesseract (riconoscimento del testo): preso dai pacchetti Ubuntu, non installato"
bash linux/prepara_tesseract.sh build/tesseract
echo "== prova dell'OCR (testo italiano con accenti e prezzi, posizioni delle parole)"
TK_TESSERACT_DIR="$ROOT/build/tesseract" python tests/verifica_ocr.py | tail -n 1

echo "== importazione dal codice (PDF con testo vero e foto di un listino)"
TESTDATI="$(mktemp -d)"
for src in prova.pdf prova.png; do
    TKLISTINO_DATI="$TESTDATI" TK_TESSERACT_DIR="$ROOT/build/tesseract" QT_QPA_PLATFORM=offscreen \
        python run.py --import-test "tests/$src" "dist/import-sorgente-$src.txt" || true
    echo "   $src: $(cat "dist/import-sorgente-$src.txt" 2>/dev/null)"
    grep -q "^OK 3 sezioni" "dist/import-sorgente-$src.txt" || { echo "TEST IMPORTAZIONE $src FALLITO"; exit 1; }
done

echo "== icona"
QT_QPA_PLATFORM=offscreen python -c "
import sys; sys.path.insert(0, '.')
from PySide6.QtWidgets import QApplication
app = QApplication([])
from tklistino.app import render_icon
assert render_icon(512).save('build/tk-listino-512.png')"

echo "== libxcb-cursor (serve a Qt sotto X11; su Wayland no): presa dal pacchetto Ubuntu, non installata"
rm -rf build/xcb-cursor && mkdir -p build/xcb-cursor
(cd build/xcb-cursor && apt-get download libxcb-cursor0 >/dev/null && dpkg-deb -x libxcb-cursor0_*.deb x \
    && cp x/usr/lib/*/libxcb-cursor.so.0.* libxcb-cursor.so.0 && cp x/usr/share/doc/libxcb-cursor0/copyright .) \
    || echo "   libxcb-cursor non disponibile: il pacchetto funzionerà solo su Wayland o con la libreria di sistema"

echo "== licenze"
python tools_licenze.py "$ROOT/licenze-pacchetto" "$(python -c 'import sysconfig;print(sysconfig.get_paths()["purelib"])')" --linux

echo "== programma"
rm -rf build/tk-listino-linux dist/tk-listino
pyinstaller --noconfirm --clean --workpath build/tk-listino-linux linux/tk-listino-linux.spec
[ -f dist/tk-listino/_internal/licenze/COPYING-AGPL-3.0.txt ] || { echo "MANCANO LE LICENZE NEL PACCHETTO"; exit 1; }
if find dist/tk-listino -iname '*mupdf*' | grep -q .; then echo "PyMuPDF NON DEVE STARE NEL PACCHETTO"; exit 1; fi

echo "== AppImage"
APPDIR="build/AppDir"
rm -rf "$APPDIR" && mkdir -p "$APPDIR/usr/lib"
cp -a dist/tk-listino "$APPDIR/usr/lib/tk-listino"
# Tesseract accanto all'eseguibile (tklistino/ocr_linux.py lo cerca lì), con i permessi di esecuzione
cp -a build/tesseract "$APPDIR/usr/lib/tk-listino/tesseract"
cat > "$APPDIR/AppRun" <<'EOF'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/lib/tk-listino/tk-listino" "$@"
EOF
chmod 755 "$APPDIR/AppRun"
cat > "$APPDIR/tk-listino.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=tk-listino
GenericName=Listini prezzi
Comment=Listini con foto, sezioni e prezzi, in PDF o stampati (TecnikGeek)
Exec=tk-listino %U
Icon=tk-listino
Terminal=false
Categories=Office;
MimeType=application/x-tk-listino;
StartupWMClass=tk-listino
EOF
cp build/tk-listino-512.png "$APPDIR/tk-listino.png"
ln -sf tk-listino.png "$APPDIR/.DirIcon"

TOOLS="${TK_STRUMENTI_BUILD:-$HOME/.cache/tk-build}"
TOOL="$TOOLS/appimagetool-$APPIMAGETOOL_VER-$ARCH.AppImage"
if [ ! -x "$TOOL" ]; then
    mkdir -p "$TOOLS"
    curl -fsSL -o "$TOOL.part" \
        "https://github.com/AppImage/appimagetool/releases/download/$APPIMAGETOOL_VER/appimagetool-$ARCH.AppImage"
    chmod 755 "$TOOL.part" && mv "$TOOL.part" "$TOOL"
fi
OUT="dist/tk-listino-$VERSION-linux-$ARCH.AppImage"
rm -f "$OUT"
APPIMAGE_EXTRACT_AND_RUN=1 ARCH="$ARCH" "$TOOL" --no-appstream \
    --mksquashfs-opt -processors --mksquashfs-opt "$JOBS" "$APPDIR" "$OUT" > build/appimagetool.log 2>&1 || {
    tail -n 30 build/appimagetool.log; echo "CREAZIONE APPIMAGE FALLITA"; exit 1; }
chmod 755 "$OUT"
echo "== Creato $OUT ($(du -h "$OUT" | cut -f1))"

echo "== selftest (dal file AppImage: finestra, PDF, componenti)"
SHOT="$ROOT/dist/selftest-linux-$ARCH.png"
TXT="$ROOT/dist/selftest-linux-$ARCH.txt"
rm -f "$SHOT" "$TXT" "$ROOT/dist/selftest-linux-$ARCH.pdf"
QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}" timeout 90 "$OUT" --selftest "$SHOT" || true
[ -f "$SHOT" ] || { echo "SELFTEST FALLITO: il programma non si avvia"; exit 1; }
[ -f "$ROOT/dist/selftest-linux-$ARCH.pdf" ] || { echo "SELFTEST FALLITO: il PDF non viene creato"; exit 1; }
cat "$TXT"; echo
grep -q "^OK" "$TXT" || { echo "SELFTEST FALLITO: componenti mancanti nel pacchetto"; exit 1; }

echo "== importazione dal file AppImage (PDF con testo vero e foto con l'OCR incluso)"
for src in prova.pdf prova.png; do
    TKLISTINO_DATI="$TESTDATI" QT_QPA_PLATFORM=offscreen timeout 120 "$OUT" --import-test "$ROOT/tests/$src" \
        "$ROOT/dist/import-linux-$src.txt" || true
    echo "   $src: $(cat "$ROOT/dist/import-linux-$src.txt" 2>/dev/null)"
    grep -q "^OK 3 sezioni" "$ROOT/dist/import-linux-$src.txt" || { echo "TEST IMPORTAZIONE $src FALLITO"; exit 1; }
done
echo "== OCR dal file AppImage (testo e posizioni)"
OCR_OUT="$ROOT/dist/ocr-linux-$ARCH.txt"
rm -f "$OCR_OUT"
timeout 90 "$OUT" --ocr-test "$ROOT/tests/ocr-it.png" "$OCR_OUT" || true
python tests/verifica_ocr.py "$OCR_OUT" || { echo "TEST OCR FALLITO"; exit 1; }
rm -rf "$TESTDATI"

if [ "${SKIP_UPDATE_TEST:-0}" != "1" ]; then
    echo "== test aggiornamento automatico"
    WORK="$(mktemp -d)"
    TESTAPP="$WORK/Programmi/tk-listino.AppImage"     # copia «installata» che deve essere sostituita
    mkdir -p "$(dirname "$TESTAPP")"
    cp "$OUT" "$TESTAPP"
    BEFORE="$(stat -c %i "$TESTAPP")"
    COPY="$WORK/tk-listino-nuova.AppImage"
    cp "$OUT" "$COPY"   # lo script di aggiornamento cancella il file usato
    SHA="$(sha256sum "$COPY" | cut -d' ' -f1)"
    SIZE="$(stat -c %s "$COPY")"
    MANIFEST="$WORK/tk-listino.json"
    printf '{"version":"99.0.0","notes":["test"],"linux-%s":{"url":"file://%s","sha256":"%s","size":%s}}' \
        "$ARCH" "$COPY" "$SHA" "$SIZE" > "$MANIFEST"
    # aggiornamenti firmati: chiave usa e getta solo per questo test (la vera resta sul PC di Pietro)
    read -r SEME PUB <<< "$(python mac/firma_aggiornamenti.py prova)"
    TK_FIRMA_SEME_PROVA="$SEME" python mac/firma_aggiornamenti.py firma --slug tk-listino "$MANIFEST"
    export TKLISTINO_DATI="$WORK/dati"
    # prima la prova contraria: manifest firmato con un'altra chiave = rifiutato
    read -r _ ALTRA <<< "$(python mac/firma_aggiornamenti.py prova)"
    TK_AGGIORNAMENTI_PROVA="$ALTRA" "$TESTAPP" --update-test "file://$MANIFEST" --no-relaunch || true
    grep -q "rifiutato" "$TKLISTINO_DATI/update-test.log" || { cat "$TKLISTINO_DATI/update-test.log"; echo "TEST FIRMA FALLITO: accettato con la chiave sbagliata"; exit 1; }
    TK_AGGIORNAMENTI_PROVA="$PUB" "$TESTAPP" --update-test "file://$MANIFEST" --no-relaunch
    AFTER="$BEFORE"
    for _ in $(seq 1 120); do
        AFTER="$(stat -c %i "$TESTAPP" 2>/dev/null || echo "$BEFORE")"
        [ "$AFTER" != "$BEFORE" ] && break
        sleep 1
    done
    cat "$TKLISTINO_DATI/update-test.log" "$TKLISTINO_DATI/aggiornamento.log" 2>/dev/null || true
    unset TKLISTINO_DATI
    if [ "$AFTER" = "$BEFORE" ] || [ ! -x "$TESTAPP" ] || ! cmp -s "$TESTAPP" "$OUT"; then
        echo "TEST AGGIORNAMENTO FALLITO"
        exit 1
    fi
    rm -rf "$WORK"
    echo "   aggiornamento OK (file AppImage sostituito, firma sbagliata rifiutata)"
fi
