import sys
sys.path.insert(0, r"C:\Users\TecnikGeek\tk-listino\.venv\Lib\site-packages"); sys.path.insert(0, r"C:\Users\TecnikGeek\tk-listino")
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from tklistino import model
from tklistino.app import MainWindow, TkProgress, UpdateDialog, AboutDialog, tk_choice, STYLE
from tklistino.util import Settings
app = QApplication([]); app.setStyle("Fusion")
w = MainWindow(Settings()); w.load_document(model.sample_document(), ""); w.resize(1200, 800); w.show(); app.processEvents()
shots = []
d1 = TkProgress(w, "Aggiornamento in corso", "Scarico tk-listino 1.3.1", True); d1.set_progress(43e6, 55.4e6, "43.0 MB di 55.4 MB"); d1.show(); app.processEvents(); w.grab().save(r"C:\Users\TecnikGeek\tk-listino\tests\d_prog.png")
d1.grab().save(r"C:\Users\TecnikGeek\tk-listino\tests\d_prog.png"); d1.close()
d2 = UpdateDialog(w, {"version": "1.3.1", "date": "2026-10-08", "notes": ["Tabella pulita", "Nuove finestre"]}); d2.show(); app.processEvents(); d2.grab().save(r"C:\Users\TecnikGeek\tk-listino\tests\d_upd.png"); d2.close()
d3 = AboutDialog(w); d3.show(); app.processEvents(); d3.grab().save(r"C:\Users\TecnikGeek\tk-listino\tests\d_about.png"); d3.close()
QTimer.singleShot(300, lambda: [x.grab().save(r"C:\Users\TecnikGeek\tk-listino\tests\d_ask.png") or x.close() for x in app.topLevelWidgets() if x.objectName()=="about" and x.isVisible()])
tk_choice(w, "Salvare le modifiche?", "Il listino ha modifiche non salvate.", [("Salva","accent"),("Non salvare","ghost"),("Annulla","ghost")])
print("ok")
