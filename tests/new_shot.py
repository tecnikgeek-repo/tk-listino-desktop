import sys
sys.path.insert(0, r"C:\Users\TecnikGeek\tk-listino\.venv\Lib\site-packages"); sys.path.insert(0, r"C:\Users\TecnikGeek\tk-listino")
from PySide6.QtWidgets import QApplication
from tklistino.app import MainWindow
from tklistino.util import Settings
app = QApplication([]); app.setStyle("Fusion")
w = MainWindow(Settings()); w.resize(1400, 1000); w.show(); app.processEvents(); w.refresh_preview(); app.processEvents()
w.grab().save(r"C:\Users\TecnikGeek\tk-listino\tests\new.png"); print("ok")
