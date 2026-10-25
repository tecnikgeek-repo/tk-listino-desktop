import sys, json
sys.path.insert(0, r"C:\Users\TecnikGeek\tk-listino\.venv\Lib\site-packages"); sys.path.insert(0, r"C:\Users\TecnikGeek\tk-listino")
from PySide6.QtGui import QGuiApplication
app = QGuiApplication([])
from tklistino import importer
src = sys.argv[1]
try:
    doc = importer.import_file(src)
    out = [f"accent={doc['accent']} sezioni/righe={importer.summary(doc)}"]
    for s in doc["blocks"][0]["sections"]:
        out.append(f"## {s['title']}  {s['cols']}")
        for r in s["rows"]:
            out.append("   " + " | ".join(x.replace("\n", " / ") for x in r))
except Exception as e:
    out = ["ERRORE: " + repr(e)]
open(sys.argv[2], "w", encoding="utf-8").write("\n".join(out))
