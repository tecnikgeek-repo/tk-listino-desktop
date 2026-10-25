import sys, traceback
sys.path.insert(0, r"")
out = open(r"C:\Users\TecnikGeek\tk-listino\tests\dbg.txt", "w", encoding="utf-8")
try:
    import pypdfium2; out.write(f"pypdfium2 {pypdfium2.PYPDFIUM_INFO} ok\n")
except Exception: out.write(traceback.format_exc())
try:
    from PySide6.QtGui import QGuiApplication; QGuiApplication([])
    from tklistino import importer
    d = importer.import_file(r"C:\Users\TecnikGeek\tk-listino\tests\prova.pdf"); out.write(str(importer.summary(d)))
except Exception: out.write(traceback.format_exc())
out.close()
