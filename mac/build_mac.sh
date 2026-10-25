#!/bin/bash
# Crea dist/tk-listino-<versione>-mac-<arch>.dmg. Da eseguire su un Mac (o sul runner macOS di GitHub).
# Uso: bash mac/build_mac.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
ARCH="$(uname -m)"
PY="${PYTHON:-python3}"
VERSION="$($PY -c "import re;print(re.search(r'VERSION = \"(.+)\"', open('tklistino/__init__.py').read()).group(1))")"
echo "== tk-listino $VERSION per macOS ($ARCH)"

$PY -m venv .venv-mac
# shellcheck disable=SC1091
source .venv-mac/bin/activate
python -m pip install --quiet --upgrade pip
python -m pip install --quiet "pyside6-essentials==6.11.*" "pypdfium2==5.14.*" certifi pyinstaller \
    pyobjc-core pyobjc-framework-Vision

echo "== icona"
python tools_make_icon.py --iconset
iconutil -c icns assets/tk-listino.iconset -o assets/tk-listino.icns

echo "== app"
rm -rf build dist
# testi delle licenze (AGPL + componenti inclusi, dai *.dist-info) e COMPONENTI.txt → Contents/Resources/licenze
python tools_licenze.py "$ROOT/licenze-pacchetto" "$(python -c 'import sysconfig;print(sysconfig.get_paths()["purelib"])')" --mac
pyinstaller --noconfirm --clean mac/tk-listino-mac.spec
APP="dist/tkLISTINO.app"
# nome visibile (Finder, Dock, barra dei menu) «tk-listino»; il bundle resta «tkLISTINO.app» per gli aggiornamenti
for lang in Base en it; do
    mkdir -p "$APP/Contents/Resources/$lang.lproj"
    printf 'CFBundleName = "tk-listino";\nCFBundleDisplayName = "tk-listino";\n' >"$APP/Contents/Resources/$lang.lproj/InfoPlist.strings"
done
codesign --force --deep --sign - "$APP"
[ -f "$APP/Contents/Resources/licenze/COPYING-AGPL-3.0.txt" ] || { echo "MANCANO LE LICENZE NEL BUNDLE"; exit 1; }
if find "$APP" -iname '*mupdf*' | grep -q .; then echo "PyMuPDF NON DEVE STARE NEL BUNDLE"; exit 1; fi

echo "== selftest"
SHOT="$ROOT/dist/selftest-$ARCH.png"
run_selftest() {
    "$APP/Contents/MacOS/tkLISTINO" --selftest "$SHOT" &
    local pid=$!
    for _ in $(seq 1 60); do
        kill -0 "$pid" 2>/dev/null || break
        sleep 1
    done
    kill "$pid" 2>/dev/null || true
}
run_selftest
if [ ! -f "$SHOT" ]; then
    echo "   finestra non disponibile, riprovo in modalità offscreen"
    export QT_QPA_PLATFORM=offscreen
    run_selftest
    unset QT_QPA_PLATFORM
fi
[ -f "$SHOT" ] || { echo "SELFTEST FALLITO: l'app non si avvia"; exit 1; }
[ -f "$ROOT/dist/selftest-$ARCH.pdf" ] || { echo "SELFTEST FALLITO: il PDF non viene creato"; exit 1; }
echo "   selftest OK (finestra + PDF)"

echo "== test importazione PDF (testo vero)"
IMP_OUT="$ROOT/dist/import-$ARCH.txt"
"$APP/Contents/MacOS/tkLISTINO" --import-test "$ROOT/tests/prova.pdf" "$IMP_OUT" || true
cat "$IMP_OUT" 2>/dev/null || true; echo
grep -q "^OK 3 sezioni" "$IMP_OUT" 2>/dev/null || { echo "TEST IMPORTAZIONE PDF FALLITO"; exit 1; }
echo "   importazione PDF OK"

echo "== test importazione da immagine (Apple Vision)"
OCR_OUT="$ROOT/dist/ocr-$ARCH.txt"
"$APP/Contents/MacOS/tkLISTINO" --import-test "$ROOT/tests/prova.png" "$OCR_OUT" || true
cat "$OCR_OUT" 2>/dev/null || true; echo
grep -q "^OK" "$OCR_OUT" 2>/dev/null || { echo "TEST OCR FALLITO"; exit 1; }
echo "   importazione da immagine OK"

echo "== dmg"
STAGE="$(mktemp -d)"
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applicazioni"
cp mac/LEGGIMI.txt "$STAGE/Leggimi - primo avvio.txt"
DMG="dist/tk-listino-$VERSION-mac-$ARCH.dmg"
# i runner macOS a volte danno «Resource busy»: si riprova qualche volta
for tentativo in 1 2 3 4; do
    if hdiutil create -volname "tk-listino $VERSION" -srcfolder "$STAGE" -ov -format UDZO "$DMG"; then
        break
    fi
    echo "   hdiutil occupato, riprovo ($tentativo)"
    sleep 6
    [ "$tentativo" = "4" ] && { echo "CREAZIONE DMG FALLITA"; exit 1; }
done
rm -rf "$STAGE"
echo "== Creato $DMG ($(du -h "$DMG" | cut -f1))"

if [ "${SKIP_UPDATE_TEST:-0}" != "1" ]; then
    echo "== test aggiornamento automatico"
    TESTAPP="$HOME/Applications/tkLISTINO.app"
    mkdir -p "$HOME/Applications"
    rm -rf "$TESTAPP"
    cp -R "$APP" "$TESTAPP"
    BEFORE="$(stat -f %i "$TESTAPP/Contents/Info.plist")"
    COPY="$(mktemp -d)/tk-listino-test.dmg"
    cp "$DMG" "$COPY"   # lo script di aggiornamento cancella il dmg usato
    SHA="$(shasum -a 256 "$COPY" | cut -d' ' -f1)"
    MANIFEST="$(mktemp -d)/tk-listino.json"
    SIZE="$(stat -f %z "$COPY")"
    printf '{"version":"99.0.0","notes":["test"],"mac-%s":{"url":"file://%s","sha256":"%s","size":%s}}' "$ARCH" "$COPY" "$SHA" "$SIZE" > "$MANIFEST"
    # aggiornamenti firmati: chiave usa e getta solo per questo test (la vera resta sul PC di Pietro)
    read -r SEME PUB <<< "$(python mac/firma_aggiornamenti.py prova)"
    TK_FIRMA_SEME_PROVA="$SEME" python mac/firma_aggiornamenti.py firma --slug tk-listino "$MANIFEST"
    TK_AGGIORNAMENTI_PROVA="$PUB" "$TESTAPP/Contents/MacOS/tkLISTINO" --update-test "file://$MANIFEST" --no-relaunch
    AFTER="$BEFORE"
    for _ in $(seq 1 120); do
        if [ -f "$TESTAPP/Contents/Info.plist" ]; then
            # il bundle può sparire tra il controllo e stat (sostituzione in corso): non fermare lo script
            AFTER="$(stat -f %i "$TESTAPP/Contents/Info.plist" 2>/dev/null || echo "$BEFORE")"
            [ "$AFTER" != "$BEFORE" ] && break
        fi
        sleep 1
    done
    cat "$HOME/Library/Application Support/tk-listino/aggiornamento.log" 2>/dev/null || true
    if [ "$AFTER" = "$BEFORE" ] || [ ! -x "$TESTAPP/Contents/MacOS/tkLISTINO" ]; then
        echo "TEST AGGIORNAMENTO FALLITO"
        exit 1
    fi
    rm -rf "$TESTAPP"
    echo "   aggiornamento OK (bundle sostituito)"
fi
