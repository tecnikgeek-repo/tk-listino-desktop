import sys
sys.path.insert(0, r"C:\Users\TecnikGeek\tk-listino\.venv\Lib\site-packages"); sys.path.insert(0, r"C:\Users\TecnikGeek\tk-listino")
from PySide6.QtGui import QImage, QGuiApplication
app = QGuiApplication([])
from tklistino import ocr, prep
img = QImage(r"C:\Users\TecnikGeek\tk-listino\tests\foto.jpg")
img = prep.enhance(img)
img.save(r"C:\Users\TecnikGeek\tk-listino\tests\prep.png")
res = ocr.recognize([img])
with open(r"C:\Users\TecnikGeek\tk-listino\tests\ocr_dump.txt", "w", encoding="utf-8") as f:
    for line in res[0]:
        f.write(" | ".join(f"{t}@{r.x():.0f},{r.y():.0f},{r.width():.0f},{r.height():.0f}" for t, r in line) + "\n")
