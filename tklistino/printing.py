"""Finestra di stampa di tk-listino con anteprima.

Su Windows 11 la finestra di sistema si intitola «Python - Stampa» (nome dell'eseguibile) e non ha
anteprima: qui si sceglie tutto dentro l'app e si stampa direttamente con QPrinter."""
import subprocess
import sys

from PySide6.QtCore import QMarginsF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPageLayout, QPageSize, QPainter
from PySide6.QtPrintSupport import QPrinter, QPrinterInfo
from PySide6.QtWidgets import (
    QComboBox, QDialog, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QSpinBox, QVBoxLayout, QWidget,
)

from tklistino import APP_TITLE
from tklistino.app import tk_warn

STATES = {
    QPrinter.PrinterState.Idle: ("Pronta", "#15803d"),
    QPrinter.PrinterState.Active: ("Sta stampando", "#1d4ed8"),
    QPrinter.PrinterState.Aborted: ("Stampa interrotta", "#b45309"),
    QPrinter.PrinterState.Error: ("Non pronta: controlla che sia accesa e collegata", "#b91c1c"),
}
MARGIN_MM = 12


class SheetPreview(QWidget):
    def __init__(self, dialog):
        super().__init__()
        self.dlg = dialog
        self.setMinimumSize(420, 480)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#dfe5ee"))
        doc = self.dlg.preview_doc
        if doc is None:
            return
        paper, paint = self.dlg.paper_rects()
        area = QRectF(self.rect()).adjusted(30, 30, -30, -30)
        k = min(area.width() / paper.width(), area.height() / paper.height())
        sheet = QRectF(0, 0, paper.width() * k, paper.height() * k)
        sheet.moveCenter(area.center())
        p.setPen(Qt.PenStyle.NoPen)
        for grow, alpha in ((7, 10), (4, 16), (2, 24)):
            p.setBrush(QColor(15, 23, 42, alpha))
            p.drawRoundedRect(sheet.adjusted(-grow * .4, grow * .2, grow * .4, grow), 4, 4)
        p.setBrush(QColor("white"))
        p.drawRect(sheet)
        # contenuto: un foglio alla volta, a colori o in grigi
        dpr = self.devicePixelRatioF()
        img = QImage(int(sheet.width() * dpr), int(sheet.height() * dpr), QImage.Format.Format_ARGB32)
        img.fill(QColor("white"))
        ip = QPainter(img)
        ip.setRenderHint(QPainter.RenderHint.Antialiasing)
        ip.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        ip.scale(dpr, dpr)
        ip.translate(paint.x() * k, paint.y() * k)
        ip.setClipRect(QRectF(0, 0, paint.width() * k, paint.height() * k))
        ip.scale(k, k)
        ph = doc.pageSize().height()
        ip.translate(0, -self.dlg.sheet * ph)
        doc.drawContents(ip, QRectF(0, self.dlg.sheet * ph, doc.pageSize().width(), ph))
        ip.end()
        if self.dlg.is_gray():
            img = img.convertToFormat(QImage.Format.Format_Grayscale8)
        img.setDevicePixelRatio(dpr)
        p.drawImage(sheet.topLeft(), img)


class PrintDialog(QDialog):
    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.setWindowTitle("Stampa listino")
        self.resize(1040, 760)
        self.sheet = 0
        self.preview_doc = None
        root = QHBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(18)

        side_w = QWidget()
        side_w.setFixedWidth(320)
        side = QVBoxLayout(side_w)
        side.setContentsMargins(0, 0, 0, 0)
        side.setSpacing(6)

        side.addWidget(self._title("STAMPANTE"))
        self.printer = QComboBox()
        names = QPrinterInfo.availablePrinterNames()
        self.printer.addItems(names)
        default = QPrinterInfo.defaultPrinterName()
        wanted = win.settings.value("print_printer", default)
        self.printer.setCurrentIndex(max(0, self.printer.findText(wanted if wanted in names else default)))
        side.addWidget(self.printer)
        self.state = QLabel()
        self.state.setWordWrap(True)
        side.addWidget(self.state)
        if sys.platform == "win32":
            prefs = QPushButton("Preferenze della stampante…")
            prefs.setToolTip("Qualità, tipo di carta e altre opzioni del driver")
            prefs.clicked.connect(self._printer_prefs)
            side.addWidget(prefs)

        side.addSpacing(8)
        side.addWidget(self._title("COPIE"))
        self.copies = QSpinBox()
        self.copies.setRange(1, 999)
        self.copies.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        side.addWidget(self.copies)

        side.addSpacing(8)
        side.addWidget(self._title("FOGLIO"))
        self.paper = QComboBox()
        self.orient = QComboBox()
        self.orient.addItems(["Verticale", "Orizzontale"])
        self.color = QComboBox()
        self.color.addItems(["A colori", "Bianco e nero"])
        self.color.setCurrentIndex(1 if win.settings.value("print_gray", False) else 0)
        for w in (self.paper, self.orient, self.color):
            side.addWidget(w)
        side.addStretch(1)

        btns = QHBoxLayout()
        cancel = QPushButton("Annulla")
        cancel.clicked.connect(self.reject)
        self.print_b = QPushButton("Stampa")
        self.print_b.setObjectName("accent")
        self.print_b.setDefault(True)
        self.print_b.clicked.connect(self.accept)
        btns.addWidget(cancel)
        btns.addWidget(self.print_b, 1)
        side.addLayout(btns)
        root.addWidget(side_w)

        right = QVBoxLayout()
        self.preview = SheetPreview(self)
        right.addWidget(self.preview, 1)
        nav = QHBoxLayout()
        nav.addStretch(1)
        self.prev_b = QPushButton("‹")
        self.next_b = QPushButton("›")
        for b in (self.prev_b, self.next_b):
            b.setFixedWidth(46)
        self.prev_b.clicked.connect(lambda: self._go(-1))
        self.next_b.clicked.connect(lambda: self._go(1))
        self.sheet_label = QLabel()
        self.sheet_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sheet_label.setMinimumWidth(150)
        nav.addWidget(self.prev_b)
        nav.addWidget(self.sheet_label)
        nav.addWidget(self.next_b)
        nav.addStretch(1)
        right.addLayout(nav)
        root.addLayout(right, 1)

        self.printer.currentIndexChanged.connect(self._printer_changed)
        self.paper.currentIndexChanged.connect(lambda _: self._changed())
        self.orient.currentIndexChanged.connect(lambda _: self._changed())
        self.color.currentIndexChanged.connect(lambda _: self.preview.update())
        self._printer_changed()

    @staticmethod
    def _title(text):
        lab = QLabel(text)
        lab.setObjectName("field")
        return lab

    def _info(self):
        return QPrinterInfo.printerInfo(self.printer.currentText())

    def is_gray(self):
        return self.color.currentIndex() == 1

    def _printer_changed(self):
        info = self._info()
        text, color = STATES.get(info.state(), ("", "#64748b"))
        if not self.printer.count():
            text, color = "Nessuna stampante installata", "#b91c1c"
        self.state.setText(text)
        self.state.setStyleSheet(f"color:{color}; font-weight:700;")
        prev = self.paper.currentData()
        self.paper.blockSignals(True)
        self.paper.clear()
        for s in (info.supportedPageSizes() or [QPageSize(QPageSize.PageSizeId.A4)]):
            self.paper.addItem(f"Carta {s.name()}", s.id())
        idx = self.paper.findData(prev if prev is not None else QPageSize.PageSizeId.A4)
        self.paper.setCurrentIndex(max(0, idx))
        self.paper.blockSignals(False)
        self._changed()

    def _printer_prefs(self):
        name = self.printer.currentText()
        if name:
            subprocess.Popen(["rundll32", "printui.dll,PrintUIEntry", "/e", "/n", name])

    def _orientation(self):
        return QPageLayout.Orientation.Landscape if self.orient.currentIndex() == 1 else QPageLayout.Orientation.Portrait

    def _page_layout(self):
        size_id = self.paper.currentData()
        return QPageLayout(QPageSize(size_id if size_id is not None else QPageSize.PageSizeId.A4),
                           self._orientation(), QMarginsF(MARGIN_MM, MARGIN_MM, MARGIN_MM, MARGIN_MM),
                           QPageLayout.Unit.Millimeter)

    def paper_rects(self):
        lay = self._page_layout()
        return QRectF(lay.fullRectPoints()), QRectF(lay.paintRectPoints())

    def _changed(self):
        pr = QPrinter(QPrinter.PrinterMode.HighResolution)
        pr.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        pr.setPageLayout(self._page_layout())
        self.preview_doc = self.win.build_print_doc(pr)
        self.sheet = min(self.sheet, max(0, self.preview_doc.pageCount() - 1))
        self._refresh_nav()

    def _go(self, step):
        self.sheet = max(0, min(self.preview_doc.pageCount() - 1, self.sheet + step))
        self._refresh_nav()

    def _refresh_nav(self):
        n = self.preview_doc.pageCount() if self.preview_doc else 0
        self.sheet_label.setText(f"Foglio {self.sheet + 1} di {n}" if n else "")
        self.prev_b.setEnabled(self.sheet > 0)
        self.next_b.setEnabled(self.sheet < n - 1)
        self.print_b.setEnabled(self.printer.count() > 0)
        self.preview.update()

    def accept(self):
        self.win.settings.setValue("print_printer", self.printer.currentText())
        self.win.settings.setValue("print_gray", self.is_gray())
        pr = QPrinter(self._info(), QPrinter.PrinterMode.HighResolution)
        pr.setPageLayout(self._page_layout())
        pr.setDocName("Listino")
        pr.setColorMode(QPrinter.ColorMode.GrayScale if self.is_gray() else QPrinter.ColorMode.Color)
        pr.setCopyCount(self.copies.value())
        try:
            self.win.build_print_doc(pr).print_(pr)
        except Exception as exc:
            tk_warn(self, APP_TITLE, f"Impossibile stampare:\n{exc}")
            return
        super().accept()


def print_listino(win):
    if not QPrinterInfo.availablePrinterNames():
        tk_warn(win, APP_TITLE, "Nessuna stampante installata.")
        return False
    return PrintDialog(win).exec() == QDialog.DialogCode.Accepted
