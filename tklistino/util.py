import json
import os
import sys

from tklistino import APP_NAME

APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IS_MAC = sys.platform == "darwin"
IS_WIN = sys.platform == "win32"
IS_LINUX = sys.platform.startswith("linux")

from tklistino import tk_linux  # noqa: E402  (libreria comune dei software TK)

LINUX_DESKTOP_ID = "tk-listino"  # nome del file .desktop = app_id della finestra su Wayland (icona nella barra)
LINUX_MIME = "application/x-tk-listino"  # file .listino (tipo registrato in ~/.local/share/mime)


def mac_bundle_path():
    """Percorso di «tkLISTINO.app» se il programma gira dal bundle macOS."""
    exe = os.path.abspath(sys.executable)
    marker = ".app/Contents/MacOS/"
    i = exe.find(marker)
    return exe[:i + 4] if i >= 0 else None


def is_installed():
    """True se gira dal pacchetto portatile (Windows: cartella «app» con il Python incluso; Mac: bundle .app;
    Linux: file AppImage)."""
    if IS_MAC:
        return bool(getattr(sys, "frozen", False) and mac_bundle_path())
    if IS_LINUX:
        return bool(tk_linux.appimage_path())
    bundled = os.path.join(APP_ROOT, "python")
    return os.path.isfile(os.path.join(bundled, "pythonw.exe")) and         os.path.normcase(os.path.abspath(sys.base_prefix)) == os.path.normcase(bundled)


def _writable_dir(path):
    try:
        os.makedirs(path, exist_ok=True)
        probe = os.path.join(path, ".prova")
        open(probe, "w").close()
        os.remove(probe)
        return True
    except OSError:
        return False


def data_dir():
    """Cartella dei listini. Windows: «Listini» accanto a «app» (sulla pennetta). Mac: accanto al .app se sta su un
    disco esterno scrivibile (pennetta), altrimenti Documenti/tk-listino/Listini. Linux: accanto all'AppImage se sta
    su un disco esterno scrivibile (/media, /run/media), altrimenti ~/.local/share/tk-listino/Listini.
    Gli aggiornamenti non la toccano."""
    if os.environ.get("TKLISTINO_DATI"):  # collaudi
        path = os.environ["TKLISTINO_DATI"]
        os.makedirs(path, exist_ok=True)
        return path
    if IS_LINUX:
        appimage = tk_linux.appimage_path()
        parent = os.path.dirname(appimage) if appimage else ""
        if parent.startswith(("/media/", "/run/media/")) and _writable_dir(os.path.join(parent, "Listini")):
            return os.path.join(parent, "Listini")
        path = os.path.join(tk_linux.cartella_dati("tk-listino"), "Listini")
        os.makedirs(path, exist_ok=True)
        return path
    if IS_MAC and is_installed():
        parent = os.path.dirname(mac_bundle_path())
        if parent.startswith("/Volumes/") and _writable_dir(os.path.join(parent, "Listini")):
            return os.path.join(parent, "Listini")
        path = os.path.join(os.path.expanduser("~"), "Documents", "tkLISTINO", "Listini")
    else:
        base = os.path.dirname(APP_ROOT) if is_installed() else APP_ROOT
        path = os.path.join(base, "Listini")
    if not _writable_dir(path):
        path = os.path.join(os.path.expanduser("~"), "Documents", "tkListino")
        os.makedirs(path, exist_ok=True)
    return path


def log_dir():
    """Dove scrivere i log (su Mac non dentro Documenti; su Linux in ~/.local/share/tk-listino)."""
    if os.environ.get("TKLISTINO_DATI"):
        return data_dir()
    if IS_LINUX:
        path = tk_linux.cartella_dati("tk-listino")
        os.makedirs(path, exist_ok=True)
        return path
    if IS_MAC:
        path = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "tk-listino")
        os.makedirs(path, exist_ok=True)
        return path
    return data_dir()


def open_path(path):
    """Apre un file con il programma predefinito del sistema."""
    import subprocess
    if IS_WIN:
        os.startfile(path)
    elif IS_MAC:
        subprocess.Popen(["open", path])
    else:
        tk_linux.apri(path)


def human_size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024


class Settings:
    """Impostazioni in un file JSON nella cartella dei listini (portatili con la pennetta)."""

    def __init__(self):
        self.path = os.path.join(data_dir(), "impostazioni.json")
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                self.data = json.load(fh)
        except Exception:
            self.data = {}

    def value(self, key, default=None):
        return self.data.get(key, default)

    def setValue(self, key, value):
        self.data[key] = value
        # .tmp + os.replace: se il programma si chiude a metà, il file delle impostazioni resta intero
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(self.data, fh, ensure_ascii=False, indent=1)
            os.replace(tmp, self.path)
        except OSError:
            pass


def licenze_dir():
    """Cartella «licenze» con i testi delle licenze (AGPL del programma e componenti inclusi): accanto a run.py
    (Windows e sviluppo) o nelle risorse del bundle (Mac)."""
    if getattr(sys, "frozen", False):
        for base in (getattr(sys, "_MEIPASS", ""), os.path.join(os.path.dirname(sys.executable), "..", "Resources")):
            path = os.path.join(base, "licenze")
            if base and os.path.isdir(path):
                return os.path.abspath(path)
    return os.path.join(APP_ROOT, "licenze")


def ps_quote(text):
    """Testo tra apici singoli per PowerShell: ogni apostrofo raddoppiato (cartelle come «L'Aquila» o «Dell'Orto»)."""
    return "'" + str(text).replace("'", "''") + "'"


def _make_shortcut(folder_expr):
    """Crea «tk-listino» sul Desktop: avvia il Python incluso (stesso pythonw.exe già accettato da Windows)."""
    import subprocess
    exe = os.path.join(APP_ROOT, "python", "pythonw.exe")
    if not os.path.isfile(exe):
        exe = sys.executable
    icon = os.path.join(APP_ROOT, "assets", "tk-listino.ico")
    run = os.path.join(APP_ROOT, "run.py")
    ps = (
        f"$d={folder_expr};"
        "$s=(New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $d 'tk-listino.lnk'));"
        f"$s.TargetPath={ps_quote(exe)};"
        f"$s.Arguments={ps_quote(chr(34) + run + chr(34))};"
        f"$s.WorkingDirectory={ps_quote(APP_ROOT)};"
        f"$s.IconLocation={ps_quote(icon + ',0')};"
        "$s.Description='tk-listino - listini in PDF';$s.Save();Write-Output (Join-Path $d 'tk-listino.lnk')"
    )
    ps_exe = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "WindowsPowerShell", "v1.0",
                          "powershell.exe")
    r = subprocess.run([ps_exe, "-NoProfile", "-NonInteractive", "-Command", ps], capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, creationflags=0x08000000, timeout=30)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout).strip()[-300:])
    return r.stdout.strip()


def create_desktop_shortcut():
    if not IS_WIN:
        raise RuntimeError("disponibile solo su Windows")
    return _make_shortcut("[Environment]::GetFolderPath('Desktop')")


def ensure_folder_shortcut():
    """Collegamento con icona nella cartella del programma (accanto a «app» e «Listini»). Solo Windows."""
    if not IS_WIN:
        return ""
    return _make_shortcut(ps_quote(os.path.dirname(APP_ROOT)))


OLD_TITLE = "tkLISTINO"  # nome visibile fino alla 1.8.12


def update_launcher(base):
    """Gli aggiornamenti sostituiscono solo «app»: il .cmd della cartella portatile si aggiorna da qui, copiando
    quello nuovo che viaggia nel pacchetto (assets/avvia.cmd; dalla 1.9.0 ripara un aggiornamento interrotto)."""
    from tklistino import APP_TITLE
    src = os.path.join(APP_ROOT, "assets", "avvia.cmd")
    dst = os.path.join(base, f"Avvia {APP_TITLE}.cmd")
    if not os.path.isfile(src) or not os.path.isfile(dst):
        return  # versione installata col setup: nessun .cmd di avvio
    try:
        with open(src, "rb") as fh:
            new = fh.read()
        with open(dst, "rb") as fh:
            if fh.read() == new:
                return
        with open(dst + ".tmp", "wb") as fh:
            fh.write(new)
        os.replace(dst + ".tmp", dst)
    except OSError:
        pass


def migrate_old_names():
    """Dalla 1.8.13 il nome visibile è «tk-listino»: rinomina quello che le versioni precedenti hanno creato col
    nome vecchio (cmd e collegamento della cartella portatile, collegamenti del menu Start e del desktop, voce di
    «App installate» e script di disinstallazione del setup). Solo Windows, solo dal pacchetto; i listini restano dove sono.
    I collegamenti si rinominano (non si rifanno), così puntano sempre alla copia di prima."""
    if not IS_WIN or not is_installed() or "--selftest" in sys.argv:
        return
    from tklistino import APP_TITLE, VERSION
    base = os.path.dirname(APP_ROOT)

    def rename(old, new):
        try:
            if os.path.exists(old):
                if os.path.exists(new):
                    os.remove(old)
                else:
                    os.rename(old, new)
        except OSError:
            pass

    # portatile: il .cmd fa solo «start», quindi a programma aperto è già chiuso
    rename(os.path.join(base, f"Avvia {OLD_TITLE}.cmd"), os.path.join(base, f"Avvia {APP_TITLE}.cmd"))
    update_launcher(base)
    folders = [base, os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")]
    appdata = os.environ.get("APPDATA")
    if appdata:
        folders.append(os.path.join(appdata, "Microsoft", "Windows", "Start Menu", "Programs"))
    try:
        import ctypes
        buf = ctypes.create_unicode_buffer(260)
        if ctypes.windll.shell32.SHGetFolderPathW(None, 0x0010, None, 0, buf) == 0:  # desktop vero (anche OneDrive)
            folders.append(buf.value)
    except Exception:
        pass
    for folder in dict.fromkeys(folders):
        rename(os.path.join(folder, f"{OLD_TITLE}.lnk"), os.path.join(folder, f"{APP_TITLE}.lnk"))

    # versione installata col setup: voce in «App installate» e script di disinstallazione
    try:
        import winreg
        key = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\tk-listino"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_READ | winreg.KEY_SET_VALUE) as k:
            def get(name):
                try:
                    return winreg.QueryValueEx(k, name)[0]
                except OSError:
                    return ""
            if os.path.normcase(os.path.abspath(get("InstallLocation") or "?")) != os.path.normcase(base):
                return
            if get("DisplayName") != APP_TITLE:
                winreg.SetValueEx(k, "DisplayName", 0, winreg.REG_SZ, APP_TITLE)
            if get("DisplayVersion") != VERSION:
                winreg.SetValueEx(k, "DisplayVersion", 0, winreg.REG_SZ, VERSION)
            old_cmd = os.path.join(base, f"Disinstalla {OLD_TITLE}.cmd")
            new_cmd = os.path.join(base, f"Disinstalla {APP_TITLE}.cmd")
            if os.path.isfile(old_cmd):
                # lo script cancella il collegamento per nome: va riscritto col nome nuovo
                with open(old_cmd, encoding="ascii", errors="replace", newline="") as fh:
                    text = fh.read().replace(OLD_TITLE, APP_TITLE)
                with open(new_cmd, "w", encoding="ascii", errors="replace", newline="") as fh:
                    fh.write(text)
                winreg.SetValueEx(k, "UninstallString", 0, winreg.REG_SZ, f'cmd.exe /c ""{new_cmd}""')
                os.remove(old_cmd)
    except OSError:
        pass


# ------------------------------------------------------------------ Linux
MIME_XML = """<?xml version="1.0" encoding="UTF-8"?>
<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">
  <mime-type type="application/x-tk-listino">
    <comment>Listino tk-listino</comment>
    <sub-class-of type="application/json"/>
    <icon name="application-x-tk-listino"/>
    <glob pattern="*.listino"/>
  </mime-type>
</mime-info>
"""


def _run_quiet(cmd):
    import subprocess
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=30, env=tk_linux.system_env())
    except (OSError, subprocess.SubprocessError):
        return None


def install_linux_integration():
    """Linux (AppImage): tipo di file .listino con la sua icona (~/.local/share/mime), voce «tk-listino» nel menu
    delle applicazioni e doppio clic sui .listino = tk-listino. Si corregge da sola se l'AppImage è stato spostato.
    Ritorna il percorso del .desktop o "" (non gira dal pacchetto)."""
    if not tk_linux.appimage_path():
        return ""
    import shutil
    base = tk_linux.xdg_data_home()
    icon = os.path.join(getattr(sys, "_MEIPASS", APP_ROOT), "assets", "tk-listino-512.png")
    mime_dir = os.path.join(base, "mime")
    xml = os.path.join(mime_dir, "packages", "tk-listino.xml")
    try:
        with open(xml, encoding="utf-8") as fh:
            uguale = fh.read() == MIME_XML
    except OSError:
        uguale = False
    if not uguale:
        os.makedirs(os.path.dirname(xml), exist_ok=True)
        with open(xml + ".tmp", "w", encoding="utf-8") as fh:
            fh.write(MIME_XML)
        os.replace(xml + ".tmp", xml)
        _run_quiet(["update-mime-database", mime_dir])
    mime_icons = os.path.join(base, "icons", "hicolor", "512x512", "mimetypes")
    if os.path.isfile(icon) and not os.path.isfile(os.path.join(mime_icons, "application-x-tk-listino.png")):
        os.makedirs(mime_icons, exist_ok=True)
        shutil.copyfile(icon, os.path.join(mime_icons, "application-x-tk-listino.png"))
    desktop = tk_linux.installa_menu(LINUX_DESKTOP_ID, "tk-listino", "Listini con foto, sezioni e prezzi, in PDF o "
                                     "stampati (TecnikGeek)", "Office;", icon, nome_generico="Listini prezzi",
                                     parole="listino;prezzi;catalogo;pdf;stampa;", mime=LINUX_MIME + ";")
    r = _run_quiet(["xdg-mime", "query", "default", LINUX_MIME])
    if desktop and (r is None or r.stdout.strip() != LINUX_DESKTOP_ID + ".desktop"):
        _run_quiet(["xdg-mime", "default", LINUX_DESKTOP_ID + ".desktop", LINUX_MIME])
    return desktop

