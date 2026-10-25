"""Registra tk-listino come programma dei file .listino (solo utente corrente, niente permessi admin):
doppio clic apre tk-listino, i file hanno la sua icona e «Apri con» lo mostra col suo nome (non «Python»)."""
import os
import sys

PROG_ID = "TKLISTINO.Listino"
APP_NAME = "tk-listino"
EXT = ".listino"
CAPS_KEY = r"Software\TecnikGeek\tk-listino\Capabilities"
STATE_KEY = r"Software\TecnikGeek\tk-listino"
# alzare quando cambia cosa viene scritto nel registro: all'avvio l'app si ri-registra da sola
SCHEMA = "2"  # 2: nome «tk-listino» al posto di «tkLISTINO» (1.8.13)


def _root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def launch_command():
    """(comando, icona): il pythonw.exe incluso nella cartella portatile (niente exe nuovi: Smart App Control)."""
    root = _root()
    pyw = os.path.join(root, "python", "pythonw.exe")
    return f'"{pyw}" "{os.path.join(root, "run.py")}" "%1"', f'"{os.path.join(root, "assets", "tk-listino.ico")}",0'


def _set(winreg, path, name, value):
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, path) as k:
        winreg.SetValueEx(k, name, 0, winreg.REG_SZ, value)


def _get(winreg, path, name=""):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as k:
            return winreg.QueryValueEx(k, name)[0]
    except OSError:
        return None


def _delete_value(winreg, path, name):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_SET_VALUE) as k:
            winreg.DeleteValue(k, name)
    except OSError:
        pass


def _delete_tree(winreg, path):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_ALL_ACCESS) as k:
            while True:
                try:
                    sub = winreg.EnumKey(k, 0)
                except OSError:
                    break
                _delete_tree(winreg, rf"{path}\{sub}")
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, path)
    except OSError:
        pass


def register():
    import winreg

    command, icon = launch_command()
    base = rf"Software\Classes\{PROG_ID}"
    _set(winreg, base, "", "Listino tk-listino")
    _set(winreg, base, "FriendlyTypeName", "Listino tk-listino")
    _set(winreg, rf"{base}\DefaultIcon", "", icon)
    _set(winreg, rf"{base}\shell\open", "FriendlyAppName", APP_NAME)
    _set(winreg, rf"{base}\shell\open\command", "", command)
    _set(winreg, rf"{base}\Application", "ApplicationName", APP_NAME)
    _set(winreg, rf"{base}\Application", "ApplicationIcon", icon)
    _set(winreg, rf"{base}\Application", "ApplicationCompany", "TecnikGeek")
    # .listino è nostro: tk-listino è il programma predefinito
    _set(winreg, rf"Software\Classes\{EXT}", "", PROG_ID)
    _set(winreg, rf"Software\Classes\{EXT}\OpenWithProgids", PROG_ID, "")
    # la voce creata da Windows quando il file era stato aperto con Python
    _delete_value(winreg, rf"Software\Classes\{EXT}\OpenWithProgids", "listino_auto_file")
    _delete_value(winreg, rf"Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\{EXT}\OpenWithProgids",
                  "listino_auto_file")
    _delete_tree(winreg, r"Software\Classes\listino_auto_file")
    # «App predefinite» di Impostazioni
    _set(winreg, CAPS_KEY, "ApplicationName", APP_NAME)
    _set(winreg, CAPS_KEY, "ApplicationDescription", "Listini con foto, sezioni e prezzi")
    _set(winreg, CAPS_KEY, "ApplicationIcon", icon)
    _set(winreg, rf"{CAPS_KEY}\FileAssociations", EXT, PROG_ID)
    _set(winreg, r"Software\RegisteredApplications", APP_NAME, CAPS_KEY)
    _delete_value(winreg, r"Software\RegisteredApplications", "tkLISTINO")  # nome fino alla 1.8.12
    _set(winreg, STATE_KEY, "RegistrationSchema", SCHEMA)
    _notify()


def ensure_registered():
    """All'avvio della versione portatile: rifà la registrazione se manca, è vecchia o punta a un'altra cartella
    (pennetta con un'altra lettera, cartella spostata). In sviluppo e nei test di build non tocca il registro."""
    if sys.platform != "win32" or "--selftest" in sys.argv:
        return
    from tklistino.util import is_installed
    if not is_installed():
        return
    try:
        import winreg
        command, _icon = launch_command()
        if (_get(winreg, STATE_KEY, "RegistrationSchema") != SCHEMA
                or _get(winreg, rf"Software\Classes\{PROG_ID}\shell\open\command") != command
                or _get(winreg, rf"Software\Classes\{EXT}") != PROG_ID):
            register()
    except Exception:
        pass


def _notify():
    try:
        import ctypes
        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)  # aggiorna le icone dei file
    except Exception:
        pass
