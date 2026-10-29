"""Licenza (software libero), benvenuto, statistiche col consenso e donazione libera di tk-listino.

Dal 2026-10-25 tk-listino è software libero (AGPL-3.0) con tutte le funzioni per tutti: niente Pro né chiavi.
Restano il benvenuto al primo avvio, la casella delle statistiche e l'invito discreto al caffè (vedi tk_licenza_qt).
"""
import os
import sys

from PySide6.QtWidgets import QApplication

from tklistino import APP_TITLE, URL_SORGENTE


def crea_licenza(versione):
    """La memoria del programma sta nella cartella dell'utente, non accanto al programma: tk-listino gira anche da pennetta."""
    try:
        from tklistino.tk_licenza import Licenza
        if sys.platform == "darwin":
            base = os.path.expanduser("~/Library/Application Support")
        elif sys.platform.startswith("linux"):
            base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
        else:
            base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return Licenza("tk-listino", versione, os.path.join(base, "tk-listino"))
    except Exception:
        return None


def licenza():
    return getattr(QApplication.instance(), "licenza", None)


def _logo():
    from PySide6.QtGui import QPixmap
    from tklistino.app import render_icon
    pm = render_icon(104)
    return pm if isinstance(pm, QPixmap) else QPixmap.fromImage(pm)


def benvenuto(parent=None):
    """Primo avvio (una volta sola): software libero, nessuna garanzia, cosa va in rete e consenso alle statistiche."""
    try:
        from tklistino.tk_licenza_qt import benvenuto as mostra
        mostra(licenza(), APP_TITLE, URL_SORGENTE, parent=parent, logo=_logo(), righe_extra=(
            "In rete va solo il controllo degli aggiornamenti (dal sito pietrodefilippis.it) e, se lo permetti qui "
            "sotto, il segnale anonimo delle statistiche. I listini, le foto e i PDF che importi restano qui.",))
    except Exception:
        pass


def casella_statistiche():
    from tklistino.tk_licenza_qt import casella_statistiche as crea
    return crea(licenza())


def pulsante_caffe(nome_oggetto=""):
    from tklistino.tk_licenza_qt import pulsante_caffe as crea
    return crea(licenza(), nome_oggetto=nome_oggetto)


def invito(parent=None, puo_mostrare=None):
    """Invito al caffè all'avvio: la prima volta e poi al massimo una volta al mese (vedi tk_licenza_qt)."""
    try:
        from tklistino.tk_licenza_qt import invito_caffe
        invito_caffe(licenza(), APP_TITLE, parent, _logo(), puo_mostrare)
    except Exception:
        pass
