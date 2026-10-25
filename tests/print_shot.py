import os, sys
sys.path.insert(0, r"C:\Users\TecnikGeek\tk-listino\.venv\Lib\site-packages")
sys.path.insert(0, r"C:\Users\TecnikGeek\tk-listino")
from PySide6.QtWidgets import QApplication
from tklistino import model
from tklistino.app import MainWindow, STYLE
from tklistino.util import Settings
from tklistino.printing import PrintDialog
app = QApplication([]); app.setStyle("Fusion")
w = MainWindow(Settings()); w.load_document(model.sample_document(), ""); w.show()
d = PrintDialog(w); d.show(); app.processEvents()
d.grab().save(r"C:\Users\TecnikGeek\tk-listino\tests\print.png"); print("ok", d.printer.currentText())
