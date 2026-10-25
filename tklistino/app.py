"""Finestra principale di tk-listino: editor a lastre a sinistra, foglio A4 reale a destra."""
import base64
import html
import os
import sys
import time

from PySide6.QtCore import (
    QBuffer, QIODevice, QMarginsF, QPointF, QRectF, QSize, QSizeF, Qt, QThread, QTimer, QUrl, Signal,
)
from PySide6.QtGui import (
    QBrush, QColor, QFont, QFontDatabase, QIcon, QImage, QKeySequence, QLinearGradient, QPageLayout, QPageSize, QPainter,
    QPainterPath, QPen, QPixmap, QShortcut, QTextDocument,
)
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from PySide6.QtWidgets import (
    QApplication, QColorDialog, QComboBox, QDialog, QFileDialog, QFrame, QGraphicsDropShadowEffect, QGridLayout, QHBoxLayout,
    QHeaderView,
    QLabel, QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit, QProgressBar, QPushButton, QScrollArea,
    QSizePolicy, QSpinBox, QSplitter, QStyledItemDelegate, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from tklistino import APP_TITLE, AUTHOR, AUTHOR_URL, URL_SORGENTE, VERSION, model, pro, updater
from tklistino.tk_licenza_qt import dentro_lo_schermo, testata_compatta
from tklistino.util import (
    APP_ROOT, IS_WIN, Settings, create_desktop_shortcut, data_dir, ensure_folder_shortcut, human_size, is_installed,
    licenze_dir, migrate_old_names,
    log_dir, open_path,
)

MARK_BG = "#fde68a"  # celle da controllare dopo un'importazione (giallo)
RECOVERY_EVERY = 5 * 60 * 1000  # salvataggio di recupero ogni 5 minuti

NAVY = "#0f172a"
NAVY_2 = "#1e293b"
NAVY_3 = "#334155"
ACCENT = "#e11d48"
ACCENT_D = "#be123c"
ACCENT_L = "#ffe4e6"
GRAY_50 = "#f8fafc"
GRAY_100 = "#f1f5f9"
GRAY_200 = "#e2e8f0"
GRAY_300 = "#cbd5e1"
GRAY_400 = "#94a3b8"
GRAY_500 = "#64748b"

STYLE = f"""
QMainWindow {{ background:#e9edf4; }}
QDialog {{ background:#eef2f7; }}
QWidget {{ font-size:13px; color:{NAVY}; }}
QWidget#canvas {{ background:transparent; }}
QScrollArea {{ background:transparent; border:0; }}
QFrame#header {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {NAVY},stop:1 #1b2a4a); border-radius:16px; }}
QFrame#card {{ background:#ffffff; border-radius:16px; }}
QFrame#desk {{ background:#ffffff; border-radius:16px; }}
QFrame#pill {{ background:rgba(255,255,255,.10); border-radius:12px; }}
QLabel#brand {{ color:#fff; font-size:19px; font-weight:800; }}
QLabel#ver {{ color:{GRAY_300}; font-size:11px; }}
QPushButton#docname {{ background:rgba(255,255,255,.10); border:1px solid rgba(255,255,255,.10); border-radius:12px; color:#fff; font-size:12px; font-weight:700; padding:0 16px; min-height:38px; }}
QPushButton#docname:hover {{ background:rgba(255,255,255,.20); border-color:rgba(255,255,255,.30); }}
QLabel#cardtitle {{ color:{NAVY}; font-size:12px; font-weight:800; letter-spacing:1.5px; }}
QLabel#hint {{ color:{GRAY_500}; font-size:11px; }}
QLabel#field {{ color:{GRAY_500}; font-size:11px; font-weight:700; }}
QLabel#icobox {{ background:{ACCENT_L}; border-radius:10px; }}
QPushButton {{ background:#fff; border:1px solid {GRAY_300}; border-radius:10px; padding:0 14px; min-height:36px; color:{NAVY}; font-weight:600; }}
QPushButton:hover {{ background:{GRAY_100}; border-color:{GRAY_400}; }}
QPushButton:disabled {{ color:{GRAY_300}; background:{GRAY_50}; }}
QPushButton#ghost {{ background:rgba(255,255,255,.08); border:1px solid rgba(255,255,255,.14); color:#fff; }}
QPushButton#ghost:hover {{ background:rgba(255,255,255,.18); }}
QPushButton#accent {{ background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #f43f5e,stop:1 {ACCENT_D}); border:0; color:#fff; font-weight:800; padding:0 18px; }}
QPushButton#accent:hover {{ background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #fb7185,stop:1 {ACCENT}); }}
QPushButton#light {{ background:#fff; border:0; color:{NAVY}; font-weight:800; padding:0 18px; }}
QPushButton#light:hover {{ background:{ACCENT_L}; }}
QPushButton#mini {{ min-width:36px; max-width:36px; padding:0; }}
QPushButton#chip {{ background:{GRAY_100}; border:1px solid {GRAY_200}; border-radius:17px; min-height:32px; padding:0 14px; color:{NAVY_3}; }}
QPushButton#chip:hover {{ background:{GRAY_200}; }}
QPushButton#chip:checked {{ background:{NAVY}; border-color:{NAVY}; color:#fff; }}
QPushButton#chipadd {{ background:#fff; border:1px dashed {GRAY_400}; border-radius:17px; min-height:32px; min-width:34px; padding:0 10px; color:{GRAY_500}; }}
QPushButton#chipadd:hover {{ background:{ACCENT_L}; border-color:{ACCENT}; }}
QPushButton#danger:hover {{ background:{ACCENT_L}; border-color:{ACCENT}; }}
QFrame#stylerow {{ background:{GRAY_50}; border:1px solid {GRAY_200}; border-radius:14px; }}
QFrame#stylerow:hover {{ border-color:{GRAY_300}; background:#fff; }}
QLabel#stylename {{ color:{NAVY}; font-weight:700; background:transparent; }}
QFrame#sizebox {{ background:#fff; border:1px solid {GRAY_200}; border-radius:10px; }}
QPushButton#sizebtn {{ background:transparent; border:0; border-radius:8px; min-height:30px; min-width:30px; max-width:30px; padding:0; }}
QPushButton#sizebtn:hover {{ background:{GRAY_100}; }}
QLabel#sizelab {{ color:{NAVY}; font-weight:800; background:transparent; }}
QPushButton#toggle {{ background:#fff; border:1px solid {GRAY_200}; border-radius:10px; min-height:0; padding:0; color:{GRAY_500}; font-size:14px; }}
QPushButton#toggle:hover {{ border-color:{GRAY_400}; color:{NAVY}; }}
QPushButton#toggle:checked {{ background:{NAVY}; border-color:{NAVY}; color:#fff; }}
QLineEdit, QSpinBox {{ background:{GRAY_50}; border:1px solid {GRAY_200}; border-radius:10px; padding:0 12px; min-height:38px; selection-background-color:{ACCENT}; }}
QLineEdit:focus, QSpinBox:focus {{ background:#fff; border:1px solid {ACCENT}; }}
QSpinBox {{ padding-right:4px; }}
QComboBox#fontcombo {{ background:#fff; border:1px solid {GRAY_200}; border-radius:10px; padding:0 10px; min-height:32px; }}
QComboBox#fontcombo:hover {{ border:1px solid {GRAY_300}; }}
QComboBox#fontcombo::drop-down {{ border:0; width:22px; }}
QComboBox#fontcombo QAbstractItemView {{ background:#fff; border:1px solid {GRAY_200}; selection-background-color:{ACCENT_L}; selection-color:{NAVY}; outline:0; }}
QTableWidget {{ background:#fff; border:1px solid {GRAY_200}; border-radius:12px; gridline-color:{GRAY_200}; selection-background-color:{ACCENT_L}; selection-color:{NAVY}; outline:0; }}
QTableWidget::item {{ padding:4px 8px; }}
QHeaderView::section {{ background:{GRAY_50}; border:0; border-bottom:1px solid {GRAY_200}; border-right:1px solid {GRAY_200}; padding:6px; color:{GRAY_500}; font-size:11px; font-weight:700; }}
QScrollBar:vertical {{ background:transparent; width:12px; margin:2px; }}
QScrollBar::handle:vertical {{ background:{GRAY_300}; border-radius:5px; min-height:30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height:0; width:0; }}
QScrollBar:horizontal {{ background:transparent; height:12px; margin:2px; }}
QScrollBar::handle:horizontal {{ background:{GRAY_300}; border-radius:5px; min-width:30px; }}
QStatusBar {{ background:transparent; color:{GRAY_500}; }}
QToolTip {{ background:{NAVY}; color:#fff; border:0; padding:5px 8px; }}
QDialog#about {{ background:transparent; }}
QFrame#tkcard {{ background:{NAVY}; border-radius:20px; border:1px solid {NAVY_3}; }}
QDialog#about QProgressBar {{ background:{NAVY_2}; border:0; border-radius:5px; }}
QDialog#about QProgressBar::chunk {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #f43f5e,stop:1 #fb7185); border-radius:5px; }}
QDialog#about QLabel {{ color:#fff; }}
QDialog#about QFrame#acard {{ background:{NAVY_2}; border-radius:14px; }}
QDialog#about QLabel#atitle {{ color:{ACCENT}; font-size:11px; font-weight:800; letter-spacing:1.5px; }}
QDialog#about QLabel#asub {{ color:{GRAY_300}; }}
"""


def ic(name, color="#ffffff", size=20):
    """Icone a tratto disegnate a mano (niente emoji: nessun cambio di forma a schermo disegnato)."""
    pm = QPixmap(size * 2, size * 2)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.scale(size * 2 / 24, size * 2 / 24)
    pen = QPen(QColor(color), 2)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    L = lambda *a: p.drawLine(QPointF(a[0], a[1]), QPointF(a[2], a[3]))
    R = lambda x, y, w, h, r=2: p.drawRoundedRect(QRectF(x, y, w, h), r, r)

    def poly(*pts):
        path = QPainterPath(QPointF(*pts[0]))
        for pt in pts[1:]:
            path.lineTo(QPointF(*pt))
        p.drawPath(path)

    if name == "plus":
        L(12, 5, 12, 19); L(5, 12, 19, 12)
    elif name == "minus":
        L(5, 12, 19, 12)
    elif name == "close":
        L(7, 7, 17, 17); L(17, 7, 7, 17)
    elif name == "type":
        poly((5, 8), (5, 5), (19, 5), (19, 8)); L(12, 5, 12, 19); L(9, 19, 15, 19)
    elif name == "up":
        poly((6, 14), (12, 8), (18, 14))
    elif name == "down":
        poly((6, 10), (12, 16), (18, 10))
    elif name == "copy":
        R(9, 9, 11, 11); poly((15, 9), (15, 5), (5, 5), (5, 15), (9, 15))
    elif name == "trash":
        L(5, 7, 19, 7); R(7, 7, 10, 13); poly((9, 7), (9, 4), (15, 4), (15, 7)); L(10, 11, 10, 17); L(14, 11, 14, 17)
    elif name == "new":
        poly((7, 3), (14, 3), (19, 8), (19, 21), (7, 21), (7, 3)); L(12, 11, 12, 17); L(9, 14, 15, 14)
    elif name == "open":
        poly((3, 7), (3, 19), (19, 19), (21, 11), (8, 11), (6, 19)); poly((3, 7), (9, 7), (11, 9), (18, 9), (18, 11))
    elif name == "save":
        poly((5, 4), (16, 4), (20, 8), (20, 20), (5, 20), (5, 4)); R(8, 4, 7, 5, 1); R(8, 13, 8, 7, 1)
    elif name == "saveas":
        poly((5, 4), (16, 4), (20, 8), (20, 12)); poly((5, 4), (5, 20), (11, 20)); R(8, 4, 7, 5, 1)
        L(17, 14, 17, 22); L(13, 18, 21, 18)
    elif name == "pdf":
        poly((6, 3), (14, 3), (19, 8), (19, 21), (6, 21), (6, 3)); poly((14, 3), (14, 8), (19, 8))
        L(9, 13, 16, 13); L(9, 17, 16, 17)
    elif name == "print":
        poly((7, 9), (7, 3), (17, 3), (17, 9)); R(3, 9, 18, 8, 3); R(7, 14, 10, 7, 1); L(17, 12, 18, 12)
    elif name == "image":
        R(3, 4, 18, 16, 3); p.drawEllipse(QPointF(9, 10), 2, 2); poly((4, 19), (10, 13), (14, 17), (17, 14), (21, 18))
    elif name == "gear":
        import math
        p.drawEllipse(QPointF(12, 12), 3, 3); p.drawEllipse(QPointF(12, 12), 6.5, 6.5)
        for k in range(8):
            a = k * math.pi / 4
            L(12 + 6.5 * math.cos(a), 12 + 6.5 * math.sin(a), 12 + 9.5 * math.cos(a), 12 + 9.5 * math.sin(a))
    elif name == "info":
        p.drawEllipse(QPointF(12, 12), 9, 9); L(12, 11, 12, 17); L(12, 7.5, 12, 7.6)
    elif name == "refresh":
        p.drawArc(QRectF(4, 4, 16, 16), 40 * 16, 270 * 16); poly((17, 3), (19, 8), (14, 9))
    elif name == "down-arrow":
        L(12, 4, 12, 16); poly((7, 11), (12, 16), (17, 11)); L(5, 20, 19, 20)
    elif name == "alert":
        poly((12, 3), (22, 20), (2, 20), (12, 3)); L(12, 10, 12, 14); L(12, 17, 12, 17.1)
    elif name == "help":
        p.drawEllipse(QPointF(12, 12), 9, 9); L(12, 17, 12, 17.1); p.drawArc(QRectF(9, 7, 6, 6), 120 * 16, -250 * 16)
    elif name == "import":
        L(12, 3, 12, 15); poly((7, 10), (12, 15), (17, 10)); poly((4, 14), (4, 20), (20, 20), (20, 14))
    elif name == "edit":
        poly((4, 20), (4, 16), (15, 5), (19, 9), (8, 20), (4, 20)); L(13, 7, 17, 11)
    elif name == "sheet":
        R(4, 3, 16, 18, 3); L(4, 8, 20, 8); L(9, 8, 9, 21)
    elif name == "tag":
        poly((3, 12), (12, 3), (21, 3), (21, 12), (12, 21), (3, 12)); p.drawEllipse(QPointF(16.5, 7.5), 1.2, 1.2)
    elif name == "table":
        R(3, 5, 18, 14, 3); L(3, 10, 21, 10); L(9, 10, 9, 19)
    elif name == "zoomin":
        p.drawEllipse(QPointF(10.5, 10.5), 6.5, 6.5); L(15.5, 15.5, 20, 20); L(8, 10.5, 13, 10.5); L(10.5, 8, 10.5, 13)
    elif name == "zoomout":
        p.drawEllipse(QPointF(10.5, 10.5), 6.5, 6.5); L(15.5, 15.5, 20, 20); L(8, 10.5, 13, 10.5)
    elif name == "fit":
        poly((4, 9), (4, 4), (9, 4)); poly((15, 4), (20, 4), (20, 9)); poly((20, 15), (20, 20), (15, 20))
        poly((9, 20), (4, 20), (4, 15))
    p.end()
    pm.setDevicePixelRatio(2)
    return QIcon(pm)


def render_icon(size=64):
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    g = QLinearGradient(0, 0, size, size)
    g.setColorAt(0, QColor("#1e293b"))
    g.setColorAt(1, QColor(NAVY))
    p.setBrush(QBrush(g))
    p.drawRoundedRect(0, 0, size, size, size * 0.24, size * 0.24)
    p.setBrush(QColor("#f2b8c4"))
    p.drawRoundedRect(QRectF(size * .16, size * .17, size * .68, size * .17), size * .04, size * .04)
    p.setBrush(QColor("#ffffff"))
    for i in range(3):
        p.drawRoundedRect(QRectF(size * .16, size * (.42 + i * .16), size * .68, size * .1), size * .03, size * .03)
    p.setBrush(QColor(ACCENT))
    p.drawEllipse(QPointF(size * .78, size * .78), size * .13, size * .13)
    p.end()
    return QPixmap.fromImage(img)


def shadow(widget, blur=30, dy=6, alpha=45):
    e = QGraphicsDropShadowEffect(widget)
    e.setBlurRadius(blur)
    e.setOffset(0, dy)
    e.setColor(QColor(15, 23, 42, alpha))
    widget.setGraphicsEffect(e)


def shrink_logo(path, max_w=700):
    """Foto → PNG ridotto in base64 (il listino resta leggero e portatile)."""
    img = QImage(path)
    if img.isNull():
        raise ValueError("immagine non leggibile")
    if img.width() > max_w:
        img = img.scaledToWidth(max_w, Qt.TransformationMode.SmoothTransformation)
    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buf, "PNG")
    return base64.b64encode(bytes(buf.data())).decode("ascii")


class CellEditor(QPlainTextEdit):
    """Invio conferma, Ctrl+Invio va a capo (seconda riga = prezzo alternativo)."""
    done = Signal()

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if e.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self.insertPlainText("\n")
            else:
                self.done.emit()
            return
        super().keyPressEvent(e)


class CellDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        if not str(index.data(Qt.ItemDataRole.DisplayRole) or ""):
            painter.save()
            painter.setPen(QColor(GRAY_400))
            painter.drawText(option.rect.adjusted(10, 0, -4, 0), int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft), "Testo")
            painter.restore()

    def createEditor(self, parent, option, index):
        ed = CellEditor(parent)
        ed.setFrameShape(QFrame.Shape.NoFrame)
        ed.setStyleSheet(f"background:#fff; border:2px solid {ACCENT}; border-radius:6px; padding:2px;")
        ed.done.connect(lambda: (self.commitData.emit(ed), self.closeEditor.emit(ed)))
        return ed

    def setEditorData(self, editor, index):
        editor.setPlainText(str(index.data(Qt.ItemDataRole.EditRole) or ""))
        editor.selectAll()

    def setModelData(self, editor, model_, index):
        model_.setData(index, editor.toPlainText(), Qt.ItemDataRole.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        r = option.rect
        editor.setGeometry(r.x(), r.y(), r.width(), max(r.height(), 56))


class Card(QFrame):
    """Lastra bianca con ombra, titolo e icona in riquadro tondo."""

    def __init__(self, icon_name, title, right=None):
        super().__init__()
        self.setObjectName("card")
        shadow(self, 26, 5, 38)
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(20, 16, 20, 18)
        self.lay.setSpacing(10)
        head = QHBoxLayout()
        box = QLabel(objectName="icobox")
        box.setFixedSize(34, 34)
        box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box.setPixmap(ic(icon_name, ACCENT, 18).pixmap(18, 18))
        head.addWidget(box)
        head.addSpacing(4)
        head.addWidget(QLabel(title.upper(), objectName="cardtitle"))
        head.addStretch(1)
        if right is not None:
            head.addLayout(right)
        self.lay.addLayout(head)


def field(text):
    return QLabel(text.upper(), objectName="field")


def tool_btn(icon_name, tip, fn, color=NAVY, name="mini"):
    b = QPushButton()
    b.setObjectName(name)
    b.setIcon(ic(icon_name, color, 18))
    b.setIconSize(QSize(18, 18))
    b.setToolTip(tip)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    b.clicked.connect(fn)
    return b


def text_btn(icon_name, text, fn, color="#ffffff", name="ghost", tip=""):
    b = QPushButton(text)
    b.setObjectName(name)
    if icon_name:
        b.setIcon(ic(icon_name, color, 18))
        b.setIconSize(QSize(18, 18))
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    if tip:
        b.setToolTip(tip)
    b.clicked.connect(fn)
    return b


class Chips(QWidget):
    """Riga di «pillole» selezionabili + pulsante «+»; scorre in orizzontale se sono tante."""
    picked = Signal(int)
    add = Signal()

    def __init__(self, add_tip):
        super().__init__()
        self.setObjectName("canvas")
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFixedHeight(52)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inner = QWidget(objectName="canvas")
        self.row = QHBoxLayout(inner)
        self.row.setContentsMargins(0, 4, 0, 8)
        self.row.setSpacing(8)
        self.scroll.setWidget(inner)
        outer.addWidget(self.scroll, 1)
        self.add_tip = add_tip
        self.buttons = []

    def set_items(self, labels, current):
        while self.row.count():
            it = self.row.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        self.buttons = []
        for i, text in enumerate(labels):
            b = QPushButton(text if len(text) <= 22 else text[:21] + "…")
            b.setObjectName("chip")
            b.setCheckable(True)
            b.setChecked(i == current)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _=False, k=i: self.picked.emit(k))
            self.row.addWidget(b)
            self.buttons.append(b)
        plus = QPushButton()
        plus.setObjectName("chipadd")
        plus.setIcon(ic("plus", GRAY_500, 16))
        plus.setToolTip(self.add_tip)
        plus.setCursor(Qt.CursorShape.PointingHandCursor)
        plus.clicked.connect(self.add.emit)
        self.row.addWidget(plus)
        self.row.addStretch(1)

    def rename(self, i, text):
        if 0 <= i < len(self.buttons):
            self.buttons[i].setText(text if len(text) <= 22 else text[:21] + "…")


class ColorDot(QPushButton):
    """Pallino tondo col colore attuale: al clic si sceglie il colore."""
    changed = Signal(str)

    def __init__(self, title, size=32):
        super().__init__()
        self.title = title
        self.value = "#ffffff"
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Clicca per cambiare colore")
        self.clicked.connect(self._dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        shadow(self, 10, 1, 70)

    def set_value(self, value):
        self.value = value or "#ffffff"
        self.update()

    def paintEvent(self, e):
        # disegnato a mano: col solo foglio di stile Qt a volte ignora il raggio e il pallino esce quadrato
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        d = min(self.width(), self.height()) - 2
        rect = QRectF((self.width() - d) / 2, (self.height() - d) / 2, d, d)
        p.setPen(QPen(QColor(GRAY_300 if self.underMouse() else GRAY_200), 1))
        p.setBrush(QColor("#ffffff"))
        p.drawEllipse(rect)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(self.value))
        p.drawEllipse(rect.adjusted(3, 3, -3, -3))
        p.end()

    def _dialog(self):
        c = QColorDialog.getColor(QColor(self.value), self, self.title)
        if c.isValid():
            self.set_value(c.name())
            self.changed.emit(c.name())


class TextStyleRow(QFrame):
    """Una riga per ogni testo del foglio: anteprima «Aa», colore, grandezza, grassetto, corsivo."""
    changed = Signal(str, object)   # (chiave, {"color"|"size"|"bold"|"italic": valore})

    def __init__(self, key, label):
        super().__init__()
        self.key = key
        self.setObjectName("stylerow")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 6, 10, 6)
        lay.setSpacing(10)
        self.sample = QLabel("Aa")
        self.sample.setFixedSize(54, 38)
        self.sample.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.sample)
        name = QLabel(label)
        name.setObjectName("stylename")
        lay.addWidget(name, 1)
        self.dot = ColorDot(f"Colore: {label.lower()}", 28)
        self.dot.changed.connect(lambda c: self.changed.emit(self.key, {"color": c}))
        lay.addWidget(self.dot)
        lay.addSpacing(4)
        # carattere: ogni voce scritta col suo carattere
        self.family = QComboBox()
        self.family.setObjectName("fontcombo")
        self.family.setFixedWidth(150)
        self.family.setCursor(Qt.CursorShape.PointingHandCursor)
        self.family.setToolTip("Carattere del testo")
        for fam in model.FONT_FAMILIES:
            self.family.addItem(fam or "Predefinito", fam)
            f = QFont(fam or "Cambria", 11)
            self.family.setItemData(self.family.count() - 1, f, Qt.ItemDataRole.FontRole)
        self.family.currentIndexChanged.connect(self._famiglia)
        lay.addWidget(self.family)
        size_box = QFrame(objectName="sizebox")
        sb = QHBoxLayout(size_box)
        sb.setContentsMargins(2, 2, 2, 2)
        sb.setSpacing(0)
        minus = tool_btn("minus", "Più piccolo", lambda: self._size(-1), NAVY, "sizebtn")
        plus = tool_btn("plus", "Più grande", lambda: self._size(1), NAVY, "sizebtn")
        self.size_lab = QLabel("11")
        self.size_lab.setObjectName("sizelab")
        self.size_lab.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.size_lab.setFixedWidth(28)
        self.size_lab.setToolTip("Grandezza del testo (punti)")
        sb.addWidget(minus)
        sb.addWidget(self.size_lab)
        sb.addWidget(plus)
        lay.addWidget(size_box)
        self.bold = QPushButton("G")
        self.bold.setToolTip("Grassetto")
        self.italic = QPushButton("C")
        self.italic.setToolTip("Corsivo")
        for b, k in ((self.bold, "bold"), (self.italic, "italic")):
            b.setObjectName("toggle")
            b.setCheckable(True)
            b.setFixedSize(34, 34)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda on, kk=k: self.changed.emit(self.key, {kk: on}))
            lay.addWidget(b)
        f = self.bold.font(); f.setBold(True); self.bold.setFont(f)
        f = self.italic.font(); f.setItalic(True); f.setBold(True); self.italic.setFont(f)
        self.size = 11

    def _famiglia(self, i):
        self.changed.emit(self.key, {"family": self.family.itemData(i)})

    def _size(self, d):
        self.changed.emit(self.key, {"size": max(6, min(48, self.size + d))})

    def set_state(self, color, style, bg):
        self.size = style["size"]
        self.size_lab.setText(str(self.size))
        self.dot.set_value(color)
        self.bold.setChecked(style["bold"])
        self.italic.setChecked(style["italic"])
        fam = style.get("family", "")
        self.family.blockSignals(True)
        self.family.setCurrentIndex(max(0, self.family.findData(fam)))
        self.family.blockSignals(False)
        self.sample.setStyleSheet(
            f"background:{bg}; color:{color}; border:1px solid {GRAY_200}; border-radius:10px;"
            f"font-family:{repr(fam) + ', ' if fam else ''}Cambria, Georgia, serif;"
            f"font-size:{min(20, max(11, self.size + 3))}px;"
            f"font-weight:{'800' if style['bold'] else '400'}; font-style:{'italic' if style['italic'] else 'normal'};")


class XButton(QPushButton):
    """X tonda rossa disegnata a mano (col foglio di stile il tondo a volte esce tagliato o quadrato)."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setFixedSize(24, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(NAVY if self.underMouse() else ACCENT))
        p.drawEllipse(QRectF(1, 1, 22, 22))
        pen = QPen(QColor("#ffffff"), 2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawLine(QPointF(8.5, 8.5), QPointF(15.5, 15.5))
        p.drawLine(QPointF(15.5, 8.5), QPointF(8.5, 15.5))
        p.end()


class LogoBox(QLabel):
    clicked = Signal()
    removed = Signal()

    def __init__(self):
        super().__init__()
        self.setFixedSize(150, 100)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Clicca per scegliere o cambiare la foto, oppure trascinala qui sopra la finestra")
        # la X sulla foto la toglie
        self.x_btn = XButton(self)
        self.x_btn.move(self.width() - 30, 6)
        self.x_btn.setToolTip("Togli la foto")
        self.x_btn.clicked.connect(self.removed.emit)
        self.x_btn.hide()

    def set_logo(self, data):
        self.x_btn.setVisible(bool(data))
        if data:
            pm = QPixmap()
            pm.loadFromData(data)
            self.setPixmap(pm.scaled(self.width() - 12, self.height() - 12, Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation))
            self.setStyleSheet(f"QLabel {{ background:#fff; border:2px solid {GRAY_200}; border-radius:12px; }}")
        else:
            self.setPixmap(ic("image", GRAY_400, 30).pixmap(30, 30))
            self.setStyleSheet(f"QLabel {{ background:{GRAY_50}; border:2px dashed {GRAY_300}; border-radius:12px; }}")

    def mousePressEvent(self, e):
        self.clicked.emit()


class PaperView(QWidget):
    """Il foglio A4 vero: stessa impaginazione del PDF e della stampa, su un tavolo grigio con ombra."""
    PAGE_W, PAGE_H, MARGIN = 595.0, 842.0, 34.0

    def __init__(self):
        super().__init__()
        self.doc = None
        self.zoom = 1.0
        self.fit = True
        self.avail = 0  # larghezza utile data da PaperScroll, già senza la barra di scorrimento
        self.setMinimumWidth(380)

    def set_doc(self, doc):
        self.doc = doc
        self._resize()
        self.update()

    def scale_factor(self):
        # Non la larghezza del viewport: cambia quando compare la barra verticale, il foglio si ridimensiona,
        # la barra sparisce e si ricomincia all'infinito (programma bloccato all'avvio).
        vp = self.avail or (self.parentWidget().width() if self.parentWidget() else self.width())
        base = max(300, vp - 62) / self.PAGE_W
        return base * self.zoom

    def _resize(self):
        if self.doc is None:
            return
        pages = max(1, self.doc.pageCount())
        s = self.scale_factor()
        size = QSize(int(self.PAGE_W * s + 60), int((self.PAGE_H * s + 26) * pages + 34))
        if size != self.size() or self.minimumSize() != size:
            self.setFixedSize(size)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        p.fillRect(self.rect(), QColor("#dfe5ee"))
        if self.doc is None:
            return
        s = self.scale_factor()
        pages = max(1, self.doc.pageCount())
        ph = self.doc.pageSize().height()
        for i in range(pages):
            x, y = 30, 20 + i * (self.PAGE_H * s + 26)
            page = QRectF(x, y, self.PAGE_W * s, self.PAGE_H * s)
            for k, a in ((10, 10), (6, 16), (3, 22)):
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(15, 23, 42, a))
                p.drawRoundedRect(page.adjusted(-k * .4, k * .2, k * .4, k * .9), 4, 4)
            p.setBrush(QColor("#ffffff"))
            p.drawRect(page)
            p.save()
            p.setClipRect(QRectF(x + self.MARGIN * s, y + self.MARGIN * s,
                                 (self.PAGE_W - 2 * self.MARGIN) * s, (self.PAGE_H - 2 * self.MARGIN) * s))
            p.translate(x + self.MARGIN * s, y + self.MARGIN * s)
            p.scale(s, s)
            p.translate(0, -i * ph)
            self.doc.drawContents(p, QRectF(0, i * ph, self.doc.pageSize().width(), ph))
            p.restore()
            p.setPen(QColor(GRAY_400))
            f = QFont()
            f.setPointSize(8)
            p.setFont(f)
            p.drawText(QRectF(x, y + self.PAGE_H * s + 3, self.PAGE_W * s, 16), Qt.AlignmentFlag.AlignCenter,
                       f"Pagina {i + 1} di {pages}")

    def resizeEvent(self, e):
        super().resizeEvent(e)


class PaperScroll(QScrollArea):
    def __init__(self, paper):
        super().__init__()
        self.paper = paper
        self.setWidget(paper)
        self.setWidgetResizable(False)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet("background:#dfe5ee; border-radius:16px;")
        self.viewport().setStyleSheet("background:#dfe5ee;")
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        # Spazio per la barra verticale sempre tolto: così la larghezza del foglio non dipende dalla barra.
        avail = self.width() - self.verticalScrollBar().sizeHint().width()
        if avail != self.paper.avail:
            self.paper.avail = avail
            self.paper._resize()
            self.paper.update()

    def wheelEvent(self, e):
        if e.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.paper.zoom = max(0.4, min(3.0, self.paper.zoom * (1.1 if e.angleDelta().y() > 0 else 1 / 1.1)))
            self.paper._resize()
            self.paper.update()
            e.accept()
            return
        super().wheelEvent(e)


class ImportThread(QThread):
    status = Signal(str)
    done = Signal(object)
    failed = Signal(str)

    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.path = path

    def run(self):
        try:
            from tklistino import importer
            self.done.emit(importer.import_file(self.path, self.status.emit))
        except Exception as exc:
            self.failed.emit(str(exc))


class CheckThread(QThread):
    checked = Signal(object, str)

    def run(self):
        try:
            self.checked.emit(updater.fetch_manifest(), "")
        except Exception as exc:
            self.checked.emit(None, str(exc))


class DownloadThread(QThread):
    progress = Signal(float, float)
    ok = Signal(str)
    failed = Signal(str)

    def __init__(self, url, dest, sha256, parent=None):
        super().__init__(parent)
        self.url, self.dest, self.sha256 = url, dest, sha256
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        try:
            updater.download(self.url, self.dest, self.sha256,
                             lambda d, t: self.progress.emit(float(d), float(t)), lambda: self._cancel)
            self.ok.emit(self.dest)
        except InterruptedError:
            self.failed.emit("")
        except Exception as exc:
            self.failed.emit(str(exc))


class TkDialog(QDialog):
    """Finestra nel nostro stile: scheda navy arrotondata con ombra, senza la barra di sistema."""

    def __init__(self, parent, width=460):
        super().__init__(parent)
        self.setObjectName("about")
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.setFixedWidth(width + 56)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 22, 28, 34)
        self.card = QFrame(objectName="tkcard")
        shadow(self.card, 44, 12, 110)
        outer.addWidget(self.card)
        self.body = QVBoxLayout(self.card)
        self.body.setContentsMargins(26, 24, 26, 24)
        self.body.setSpacing(14)
        self._drag = None

    def head(self, icon_pixmap, title, sub=""):
        row = QHBoxLayout()
        row.setSpacing(14)
        ico = QLabel()
        ico.setPixmap(icon_pixmap)
        ico.setAlignment(Qt.AlignmentFlag.AlignTop)
        row.addWidget(ico)
        col = QVBoxLayout()
        col.setSpacing(3)
        t = QLabel(title)
        t.setWordWrap(True)
        t.setStyleSheet("font-size:20px; font-weight:800; color:#ffffff;")
        col.addWidget(t)
        if sub:
            s = QLabel(sub)
            s.setObjectName("asub")
            s.setWordWrap(True)
            col.addWidget(s)
        row.addLayout(col, 1)
        self.body.addLayout(row)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag is not None and e.buttons() & Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, e):
        self._drag = None


def _kind_icon(kind):
    names = {"info": ("info", "#7dd3fc"), "warn": ("alert", "#fbbf24"), "ask": ("help", "#fda4af")}
    name, color = names[kind]
    box = QPixmap(52, 52)
    box.fill(Qt.GlobalColor.transparent)
    p = QPainter(box)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(255, 255, 255, 22))
    p.drawRoundedRect(0, 0, 52, 52, 16, 16)
    p.drawPixmap(10, 10, ic(name, color, 32).pixmap(32, 32))
    p.end()
    return box


def tk_choice(parent, title, text, buttons, kind="ask", sub=""):
    """Domanda con più pulsanti [(testo, 'accent'|'ghost')]. Ritorna l'indice scelto (-1 se chiusa)."""
    dlg = TkDialog(parent, 440)
    dlg.head(_kind_icon(kind), title, sub)
    if text:
        lab = QLabel(text)
        lab.setWordWrap(True)
        lab.setStyleSheet("font-size:14px; color:#e2e8f0;")
        dlg.body.addWidget(lab)
    row = QHBoxLayout()
    row.setSpacing(8)
    row.addStretch(1)
    result = {"i": -1}
    for i, (label, style) in enumerate(buttons):
        b = QPushButton(label)
        b.setObjectName(style)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.clicked.connect(lambda _=False, k=i: (result.__setitem__("i", k), dlg.accept()))
        if style == "accent":
            b.setDefault(True)
        row.addWidget(b)
    dlg.body.addLayout(row)
    dlg.exec()
    return result["i"]


def tk_input(parent, title, label, text="", ok="OK"):
    """Chiede una riga di testo nel nostro stile. Ritorna il testo, o None se annullato."""
    dlg = TkDialog(parent, 440)
    dlg.head(_kind_icon("ask"), title, label)
    edit = QLineEdit(text)
    edit.setStyleSheet("background:#1e293b; border:1px solid #334155; color:#fff; selection-background-color:#e11d48;")
    dlg.body.addWidget(edit)
    row = QHBoxLayout()
    row.addStretch(1)
    cancel = QPushButton("Annulla")
    cancel.setObjectName("ghost")
    cancel.clicked.connect(dlg.reject)
    go = QPushButton(ok)
    go.setObjectName("accent")
    go.setDefault(True)
    go.clicked.connect(dlg.accept)
    edit.returnPressed.connect(dlg.accept)
    row.addWidget(cancel)
    row.addWidget(go)
    dlg.body.addLayout(row)
    edit.setFocus()
    edit.selectAll()
    return edit.text() if dlg.exec() == QDialog.DialogCode.Accepted else None


def tk_info(parent, title, text):
    tk_choice(parent, title, text, [("OK", "accent")], "info")


def tk_warn(parent, title, text):
    tk_choice(parent, title, text, [("OK", "accent")], "warn")


class TkProgress(TkDialog):
    """Barra di avanzamento nel nostro stile (download, importazione)."""
    canceled = Signal()

    def __init__(self, parent, title, sub, cancelable=False):
        super().__init__(parent, 420)
        self.head(render_icon(56), title, sub)
        self.bar = QProgressBar()
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(10)
        self.bar.setRange(0, 0)
        self.body.addWidget(self.bar)
        self.status = QLabel("")
        self.status.setObjectName("asub")
        self.body.addWidget(self.status)
        if cancelable:
            row = QHBoxLayout()
            row.addStretch(1)
            b = QPushButton("Annulla")
            b.setObjectName("ghost")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda: (self.canceled.emit(), self.close()))
            row.addWidget(b)
            self.body.addLayout(row)

    def set_progress(self, done, total, text=""):
        if total > 0:
            self.bar.setRange(0, 1000)
            self.bar.setValue(int(done * 1000 / total))
        self.status.setText(text)

    def set_status(self, text):
        self.status.setText(text)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            return
        super().keyPressEvent(e)


class UpdateDialog(TkDialog):
    """Aggiornamento disponibile: novità e tre scelte."""

    def __init__(self, parent, manifest):
        super().__init__(parent, 460)
        self.choice = "later"
        self.head(render_icon(56), f"È disponibile {APP_TITLE} {manifest['version']}",
                  f"Stai usando la versione {VERSION}" +
                  (f" · pubblicata il {manifest['date']}" if manifest.get("date") else ""))
        notes = manifest.get("notes") or []
        if notes:
            card = QFrame(objectName="acard")
            cl = QVBoxLayout(card)
            cl.setContentsMargins(16, 12, 16, 12)
            cl.setSpacing(4)
            cl.addWidget(QLabel("NOVITÀ", objectName="atitle"))
            for n in notes:
                lab = QLabel("•  " + str(n))
                lab.setWordWrap(True)
                lab.setStyleSheet("font-size:13px; font-weight:600;")
                cl.addWidget(lab)
            self.body.addWidget(card)
        row = QHBoxLayout()
        row.setSpacing(8)
        for label, style, value in (("Salta questa versione", "ghost", "skip"), ("Più tardi", "ghost", "later")):
            b = QPushButton(label)
            b.setObjectName(style)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _=False, v=value: self._done(v))
            row.addWidget(b)
        row.addStretch(1)
        go = text_btn("refresh", "Aggiorna ora", lambda: self._done("go"), "#fff", "accent")
        go.setDefault(True)
        row.addWidget(go)
        self.body.addLayout(row)

    def _done(self, value):
        self.choice = value
        self.accept()


class AboutDialog(TkDialog):
    """Stessa finestra Informazioni delle altre app TK: fondo navy, schede VERSIONE / SVILUPPATORE."""

    def __init__(self, win):
        super().__init__(win, 460)
        self.check = False
        lay = self.body
        head = QLabel("IMPOSTAZIONI", objectName="atitle")
        lay.addWidget(head)
        top = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(render_icon(72))
        top.addWidget(icon)
        top.addSpacing(10)
        col = QVBoxLayout()
        t = QLabel(APP_TITLE)
        t.setStyleSheet("font-size:24px; font-weight:800; color:#fff;")
        col.addWidget(t)
        s = QLabel("Crea listini con foto, sezioni e prezzi,\npronti da stampare o scaricare in PDF.")
        s.setObjectName("asub")
        col.addWidget(s)
        top.addLayout(col, 1)
        lay.addLayout(top)
        for title, body in (("VERSIONE", f"{VERSION}  ·  Software libero · AGPL-3.0"),
                            ("SVILUPPATORE", f"{AUTHOR} · {AUTHOR_URL.split('//')[1]}"),
                            ("I TUOI LISTINI", html.escape(data_dir()))):
            card = QFrame(objectName="acard")
            cl = QVBoxLayout(card)
            cl.setContentsMargins(16, 12, 16, 12)
            cl.setSpacing(2)
            cl.addWidget(QLabel(title, objectName="atitle"))
            v = QLabel(body)
            v.setWordWrap(True)
            v.setStyleSheet("font-size:14px; font-weight:600;")
            cl.addWidget(v)
            lay.addWidget(card)
        self.win = win
        self.txt_btn = text_btn("type", "", self._toggle_text, "#fff", "ghost",
                                "Pulsanti in alto: solo icona oppure icona e nome")
        self._label_text()
        lay.addWidget(self.txt_btn)
        stats = pro.casella_statistiche()
        stats.setStyleSheet("QCheckBox { color:#ffffff; font-size:13px; font-weight:600; spacing:8px; }")
        lay.addWidget(stats)
        lay.addWidget(text_btn("refresh", "Cerca aggiornamenti", self._check, "#fff", "accent"))
        lay.addWidget(text_btn("", "Licenze e codice sorgente", self._licenses, "#fff", "ghost"))
        caffe = pro.pulsante_caffe("ghost")
        if caffe is not None:
            lay.addWidget(caffe)
        row = QHBoxLayout()
        row.setSpacing(8)
        if IS_WIN:
            row.addWidget(text_btn("sheet", "Icona sul Desktop", self._shortcut, "#fff", "ghost"), 1)
        row.addWidget(text_btn("", "Chiudi", self.accept, "#fff", "ghost"), 1)
        lay.addLayout(row)

    def _label_text(self):
        self.txt_btn.setText("Pulsanti con testo: " + ("SÌ" if self.win.btn_text_on() else "NO"))

    def _toggle_text(self):
        self.win.settings.setValue("btn_text", not self.win.btn_text_on())
        self.win.apply_btn_text()
        self._label_text()

    def _shortcut(self):
        try:
            path = create_desktop_shortcut()
        except Exception as exc:
            tk_warn(self.parent(), APP_TITLE, f"Non riesco a creare l'icona sul Desktop:\n{exc}")
            return
        tk_info(self.parent(), APP_TITLE, f"Icona creata sul Desktop:\n{path}")

    def _check(self):
        self.check = True
        self.accept()

    def _licenses(self):
        from tklistino.tk_licenza_qt import LicenzeDialog
        LicenzeDialog(APP_TITLE, VERSION, URL_SORGENTE, licenze_dir(), self).exec()


class MainWindow(QMainWindow):
    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.doc = model.new_document()
        self.path = ""
        self.dirty = False
        self.closing_for_update = False
        self._loading = False
        self.bi = 0
        self.si = 0
        self.manifest = None
        self.check_thread = None
        self.dl_thread = None
        self.print_doc = None
        self.setWindowIcon(QIcon(render_icon(128)))
        self.setAcceptDrops(True)
        self.resize(1400, 880)
        self._build()
        # su finestre strette la testata perde le scritte (restano le icone); la finestra non esce dallo schermo (MacBook)
        testata_compatta(self, [(self.pdf_btn, ""), (self.stampa_btn, "")], 1120)
        dentro_lo_schermo(self)
        self.timer = QTimer(self, singleShot=True, interval=200)
        self.timer.timeout.connect(self.refresh_preview)
        self.load_document(model.new_document(), "")
        for keys, fn in (("Ctrl+N", self.act_new), ("Ctrl+O", self.act_open), ("Ctrl+S", self.act_save), ("Ctrl+I", self.act_import),
                         ("Ctrl+Shift+S", self.act_save_as), ("Ctrl+P", self.act_print)):
            QShortcut(QKeySequence(keys), self, activated=fn)
        self.recovery_timer = QTimer(self, interval=RECOVERY_EVERY)
        self.recovery_timer.timeout.connect(self.save_recovery)
        self.recovery_timer.start()
        QTimer.singleShot(1200, self.ensure_shortcut)
        QTimer.singleShot(1500, self.ensure_file_assoc)

    def start_network(self):
        """Dopo la finestra di benvenuto (mai prima): controllo aggiornamenti e, solo col consenso, statistiche."""
        QTimer.singleShot(2500, lambda: self.check_updates(False))
        if "--selftest" not in sys.argv and "--import-test" not in sys.argv:
            QTimer.singleShot(6000, self._avvia_licenza)

    def _avvia_licenza(self):
        # segnale giornaliero in sottofondo: parte solo se l'utente ha acconsentito alle statistiche
        lic = pro.licenza()
        if lic is not None:
            lic.avvia()

    # ---------------------------------------------------------------- recupero dopo una chiusura improvvisa
    def recovery_path(self):
        """Copia di recupero: accanto al listino («<nome>.listino.recupero»); se non è ancora salvato, nella
        cartella dei listini."""
        if self.path:
            return self.path + ".recupero"
        return os.path.join(data_dir(), "Listino senza nome.listino.recupero")

    def save_recovery(self):
        """Ogni 5 minuti, se ci sono modifiche non salvate: il listino non viene toccato, si scrive solo la copia."""
        if not self.dirty:
            return
        path = self.recovery_path()
        try:
            model.save(path, self.doc, backup=False)
        except OSError:
            return
        old = self.settings.value("recovery") or {}
        if isinstance(old, dict) and old.get("file") and old.get("file") != path:
            self._remove_quiet(old.get("file"))
        self.settings.setValue("recovery", {"file": path, "orig": self.path, "time": time.time()})

    def drop_recovery(self):
        """Il listino è stato salvato (o le modifiche scartate apposta): la copia di recupero non serve più."""
        old = self.settings.value("recovery")
        if not old:
            return
        if isinstance(old, dict):
            self._remove_quiet(old.get("file"))
        self.settings.setValue("recovery", None)

    @staticmethod
    def _remove_quiet(path):
        try:
            if path and path.endswith(".recupero") and os.path.isfile(path):
                os.remove(path)
        except OSError:
            pass

    def offer_recovery(self):
        """All'avvio: se l'ultima volta il programma si è chiuso con modifiche non salvate, propone di riprenderle
        (anche se è stato aperto con un doppio clic su un listino: la copia è una sola e non va persa)."""
        info = self.settings.value("recovery")
        if not isinstance(info, dict) or not info.get("file") or not os.path.isfile(info["file"]):
            if info:
                self.settings.setValue("recovery", None)
            return False
        orig = info.get("orig") or ""
        name = os.path.splitext(os.path.basename(orig))[0] if orig else "Listino senza nome"
        when = time.strftime("%d/%m/%Y alle %H:%M", time.localtime(float(info.get("time") or 0)))
        i = tk_choice(self, "Recupero del listino",
                      f"L'ultima volta {APP_TITLE} si è chiuso senza salvare le modifiche a «{name}».\n\n"
                      f"Ho una copia di recupero del {when}: vuoi riprenderla? Il file del listino non è stato "
                      "toccato: la copia diventa definitiva solo quando salvi.",
                      [("Riprendi le modifiche", "accent"), ("Scarta la copia", "ghost")])
        if i != 0:
            self.drop_recovery()
            return False
        try:
            doc = model.load(info["file"])
        except Exception as exc:
            tk_warn(self, APP_TITLE, f"Non riesco a leggere la copia di recupero:\n{exc}")
            return False
        self.load_document(doc, orig if orig and os.path.isdir(os.path.dirname(orig)) else "")
        self.dirty = True
        self.update_label()
        return True

    # ---------------------------------------------------------------- interfaccia
    def _build(self):
        central = QWidget(objectName="canvas")
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 14, 16, 8)
        root.setSpacing(14)

        header = QFrame(objectName="header")
        shadow(header, 30, 8, 70)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(18, 12, 18, 12)
        hl.setSpacing(8)
        icon = QLabel()
        icon.setPixmap(render_icon(44))
        hl.addWidget(icon)
        hl.addSpacing(4)
        col = QVBoxLayout()
        col.setSpacing(0)
        col.addWidget(QLabel(APP_TITLE, objectName="brand"))
        col.addWidget(QLabel(f"Versione {VERSION}", objectName="ver"))
        hl.addLayout(col)
        hl.addSpacing(16)
        self.doc_label = QPushButton("")
        self.doc_label.setObjectName("docname")
        self.doc_label.setIcon(ic("edit", "#ffffff", 16))
        self.doc_label.setIconSize(QSize(16, 16))
        self.doc_label.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.doc_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.doc_label.setToolTip("Clicca per rinominare il listino")
        self.doc_label.clicked.connect(self.act_rename)
        hl.addWidget(self.doc_label)
        hl.addStretch(1)
        self.update_btn = text_btn("refresh", "Aggiorna", self.show_update_dialog, "#fff", "accent")
        self.update_btn.hide()
        hl.addWidget(self.update_btn)
        # icona sola o icona + nome: si sceglie in Impostazioni («Pulsanti con testo»)
        self.head_btns = []
        for icon_name, label, fn, tip in (("new", "Nuovo", self.act_new, "Nuovo listino (Ctrl+N)"),
                                          ("open", "Apri", self.act_open, "Apri un listino (Ctrl+O)"),
                                          ("import", "Importa", self.act_import, "Importa da foto o PDF (Ctrl+I)"),
                                          ("save", "Salva", self.act_save, "Salva (Ctrl+S)"),
                                          ("saveas", "Salva come", self.act_save_as, "Salva con nome (Ctrl+Maiusc+S)")):
            btn = text_btn(icon_name, "", fn, tip=tip)
            hl.addWidget(btn)
            self.head_btns.append((btn, label))
        self.apply_btn_text()
        hl.addSpacing(10)
        self.pdf_btn = text_btn("pdf", "Scarica PDF", self.act_pdf, "#fff", "accent", "Crea il PDF del listino")
        hl.addWidget(self.pdf_btn)
        self.stampa_btn = text_btn("print", "Stampa", self.act_print, NAVY, "light", "Stampa il listino (Ctrl+P)")
        hl.addWidget(self.stampa_btn)
        hl.addWidget(text_btn("gear", "", self.act_about, tip="Impostazioni: aggiornamenti, icona sul Desktop, informazioni"))
        root.addWidget(header)

        split = QSplitter()
        split.setChildrenCollapsible(False)
        split.setHandleWidth(14)
        root.addWidget(split, 1)

        # ---- colonna editor
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setMinimumWidth(560)
        body = QWidget(objectName="canvas")
        scroll.setWidget(body)
        lay = QVBoxLayout(body)
        lay.setContentsMargins(2, 2, 10, 24)
        lay.setSpacing(16)

        c1 = Card("sheet", "Foglio")
        c1.lay.addWidget(field("Titolo in cima al foglio (facoltativo)"))
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Es. Listino caldaie e climatizzatori")
        self.title_edit.textChanged.connect(self.on_title)
        trow = QHBoxLayout()
        trow.setSpacing(8)
        trow.addWidget(self.title_edit, 1)
        self.title_bg = QPushButton("Sfondo")
        self.title_bg.setObjectName("toggle")
        self.title_bg.setCheckable(True)
        self.title_bg.setFixedSize(76, 34)
        self.title_bg.setCursor(Qt.CursorShape.PointingHandCursor)
        self.title_bg.setToolTip("Acceso: il titolo sta su una fascia del colore del foglio")
        self.title_bg.clicked.connect(self.on_title_bg)
        trow.addWidget(self.title_bg)
        c1.lay.addLayout(trow)
        acc = QHBoxLayout()
        acc.setSpacing(12)
        self.accent_color = ColorDot("Colore del foglio", 34)
        self.accent_color.changed.connect(self.set_color)
        acc.addWidget(self.accent_color)
        acc_lab = QLabel("<b>Colore del foglio</b><br><span style='color:#64748b; font-size:11px'>"
                         "riquadro del marchio e fasce delle sezioni</span>")
        acc.addWidget(acc_lab, 1)
        c1.lay.addLayout(acc)
        # ogni testo si regola nella sua scheda: titolo qui, marchio nel marchio, intestazioni e prezzi nelle sezioni
        self.style_rows = {"title": TextStyleRow("title", "Titolo del foglio")}
        self.style_rows["title"].changed.connect(self.on_text_style)
        c1.lay.addWidget(self.style_rows["title"])
        lay.addWidget(c1)

        c2 = Card("tag", "Marchio / foto")
        self.block_chips = Chips("Aggiungi un marchio")
        self.block_chips.picked.connect(self.on_block)
        self.block_chips.add.connect(self.block_add)
        c2.lay.addWidget(self.block_chips)
        mid = QHBoxLayout()
        mid.setSpacing(14)
        self.logo_box = LogoBox()
        self.logo_box.clicked.connect(self.pick_logo)
        mid.addWidget(self.logo_box)
        right = QVBoxLayout()
        right.setSpacing(6)
        right.addWidget(field("Nome del marchio"))
        self.block_name = QLineEdit()
        self.block_name.setPlaceholderText("Es. ARISTON (se non c'è la foto, appare questo)")
        self.block_name.textChanged.connect(self.on_block_name)
        right.addWidget(self.block_name)
        btns = QHBoxLayout()
        btns.setSpacing(6)
        self.logo_box.removed.connect(self.clear_logo)
        # colori del marchio: riquadro e fasce delle sue sezioni; testo = nome del marchio e titoli delle sezioni
        self.block_color = ColorDot("Colore del marchio", 34)
        self.block_color.setToolTip("Colore del riquadro del marchio e delle fasce delle sue sezioni")
        self.block_color.changed.connect(lambda c: self.set_block_color("color", c))
        self.block_color_reset = tool_btn("refresh", "Torna al colore del foglio",
                                          lambda: self.set_block_color("color", ""), GRAY_500, "sizebtn")
        self.block_text = ColorDot("Colore del testo del marchio", 34)
        self.block_text.setToolTip("Colore del nome del marchio e dei titoli delle sue sezioni")
        self.block_text.changed.connect(lambda c: self.set_block_color("text_color", c))
        self.block_text_reset = tool_btn("refresh", "Torna al colore predefinito",
                                         lambda: self.set_block_color("text_color", ""), GRAY_500, "sizebtn")
        for lab, dot, rst in (("Colore", self.block_color, self.block_color_reset),
                              ("Testo", self.block_text, self.block_text_reset)):
            btns.addWidget(field(lab))
            btns.addWidget(dot)
            btns.addWidget(rst)
            btns.addSpacing(8)
        self.bg_toggle = QPushButton("Sfondo")
        self.bg_toggle.setObjectName("toggle")
        self.bg_toggle.setCheckable(True)
        self.bg_toggle.setFixedSize(76, 34)
        self.bg_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bg_toggle.setToolTip("Acceso: la foto sta sul colore del marchio. Spento: foto su fondo bianco")
        self.bg_toggle.clicked.connect(self.on_bg_toggle)
        btns.addWidget(self.bg_toggle)
        btns.addStretch(1)
        btns.addWidget(tool_btn("up", "Sposta il marchio prima", lambda: self.block_move(-1)))
        btns.addWidget(tool_btn("down", "Sposta il marchio dopo", lambda: self.block_move(1)))
        btns.addWidget(tool_btn("trash", "Elimina il marchio e le sue sezioni", self.block_del, ACCENT, "mini"))
        right.addLayout(btns)
        mid.addLayout(right, 1)
        c2.lay.addLayout(mid)
        # testi del marchio: colore (uno solo, anche per i titoli delle sezioni), grandezza, grassetto, corsivo
        self.block_rows = {}
        for key, label in (("name", "Nome del marchio"), ("sec", "Titolo della sezione")):
            r = TextStyleRow(key, label)
            r.changed.connect(self.on_block_style)
            c2.lay.addWidget(r)
            self.block_rows[key] = r
        for r in self.block_rows.values():
            r.dot.hide()  # il colore si sceglie col pallino «Testo» qui sopra
        lay.addWidget(c2)

        c3 = Card("table", "Sezioni e prezzi")
        self.sec_chips = Chips("Aggiungi una sezione")
        self.sec_chips.picked.connect(self.on_section)
        self.sec_chips.add.connect(self.sec_add)
        c3.lay.addWidget(self.sec_chips)
        row = QHBoxLayout()
        row.setSpacing(8)
        tcol = QVBoxLayout()
        tcol.setSpacing(4)
        tcol.addWidget(field("Titolo della sezione"))
        self.sec_title = QLineEdit()
        self.sec_title.setPlaceholderText("Es. CONDENSAZIONE")
        self.sec_title.textChanged.connect(self.on_sec_title)
        tcol.addWidget(self.sec_title)
        row.addLayout(tcol, 1)
        ccol = QVBoxLayout()
        ccol.setSpacing(4)
        ccol.addWidget(field("Colonne"))
        self.cols_spin = QSpinBox()
        self.cols_spin.setRange(2, 7)
        self.cols_spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.cols_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cols_spin.setFixedWidth(46)
        self.cols_spin.valueChanged.connect(self.on_cols)
        cr = QHBoxLayout()
        cr.setSpacing(4)
        cr.addWidget(tool_btn("minus", "Una colonna in meno", lambda: self.cols_spin.stepBy(-1)))
        cr.addWidget(self.cols_spin)
        cr.addWidget(tool_btn("plus", "Una colonna in più", lambda: self.cols_spin.stepBy(1)))
        ccol.addLayout(cr)
        row.addLayout(ccol)
        row.addWidget(tool_btn("up", "Sposta la sezione su", lambda: self.sec_move(-1)), 0, Qt.AlignmentFlag.AlignBottom)
        row.addWidget(tool_btn("down", "Sposta la sezione giù", lambda: self.sec_move(1)), 0, Qt.AlignmentFlag.AlignBottom)
        row.addWidget(tool_btn("copy", "Duplica la sezione", self.sec_dup), 0, Qt.AlignmentFlag.AlignBottom)
        row.addWidget(tool_btn("trash", "Elimina la sezione", self.sec_del, ACCENT), 0, Qt.AlignmentFlag.AlignBottom)
        c3.lay.addLayout(row)
        # colori della sezione, come nel marchio: Colore = intestazioni e 2° prezzo, Testo = modelli e prezzi
        crow = QHBoxLayout()
        crow.setSpacing(6)
        self.sec_dots = {}
        for key, lab, tip in (("head_color", "Colore", "Colore delle intestazioni e del 2° prezzo di questa sezione"),
                              ("text_color", "Testo", "Colore di modelli e prezzi di questa sezione")):
            dot = ColorDot(tip, 34)
            dot.setToolTip(tip)
            dot.changed.connect(lambda c, k=key: self.set_sec_color(k, c))
            rst = tool_btn("refresh", "Torna al colore predefinito", lambda k=key: self.set_sec_color(k, ""),
                           GRAY_500, "sizebtn")
            crow.addWidget(field(lab))
            crow.addWidget(dot)
            crow.addWidget(rst)
            crow.addSpacing(8)
            self.sec_dots[key] = (dot, rst)
        crow.addStretch(1)
        c3.lay.addLayout(crow)
        self.sec_rows = {}
        for key, label in (("head", "Intestazioni e 2° prezzo"), ("text", "Modelli e prezzi")):
            r = TextStyleRow(key, label)
            r.dot.hide()  # il colore si sceglie coi pallini qui sopra
            r.changed.connect(self.on_sec_style)
            c3.lay.addWidget(r)
            self.sec_rows[key] = r
        hint = QLabel("La prima riga sono le intestazioni. Invio conferma la cella, <b>Ctrl+Invio</b> va a capo: "
                      "la seconda riga (es. prezzo alternativo) esce nel colore delle intestazioni. "
                      "Con <b>Foto</b> metti un'immagine nella prima colonna della riga selezionata.")
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        c3.lay.addWidget(hint)
        self.table = QTableWidget()
        self.table.setMinimumHeight(300)
        self.table.setItemDelegate(CellDelegate(self.table))
        self.table.itemChanged.connect(self.on_cell)
        self.table.verticalHeader().setDefaultSectionSize(38)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setWordWrap(True)
        self.table.horizontalHeader().hide()
        c3.lay.addWidget(self.table, 1)
        rb = QHBoxLayout()
        rb.setSpacing(6)
        rb.addWidget(text_btn("plus", "Riga", self.row_add, NAVY, ""))
        rb.addWidget(text_btn("copy", "Duplica", self.row_dup, NAVY, ""))
        rb.addWidget(tool_btn("up", "Sposta la riga su", lambda: self.row_move(-1)))
        rb.addWidget(tool_btn("down", "Sposta la riga giù", lambda: self.row_move(1)))
        rb.addWidget(text_btn("image", "Foto", self.row_img_pick, NAVY, "",
                              "Metti una foto nella prima colonna della riga selezionata"))
        rb.addWidget(tool_btn("trash", "Togli la foto dalla riga selezionata", self.row_img_clear))
        rb.addStretch(1)
        rb.addWidget(text_btn("trash", "Elimina riga", self.row_del, ACCENT, "danger"))
        c3.lay.addLayout(rb)
        lay.addWidget(c3, 1)
        split.addWidget(scroll)

        # ---- anteprima: foglio A4
        right_col = QWidget(objectName="canvas")
        rl = QVBoxLayout(right_col)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(8)
        tb = QHBoxLayout()
        tb.setContentsMargins(4, 0, 4, 0)
        tb.addWidget(QLabel("ANTEPRIMA · FOGLIO A4", objectName="cardtitle"))
        tb.addStretch(1)
        tb.addWidget(tool_btn("zoomout", "Riduci (Ctrl+rotella)", lambda: self.zoom_by(1 / 1.15)))
        tb.addWidget(tool_btn("fit", "Adatta alla larghezza", lambda: self.zoom_by(0)))
        tb.addWidget(tool_btn("zoomin", "Ingrandisci (Ctrl+rotella)", lambda: self.zoom_by(1.15)))
        rl.addLayout(tb)
        self.paper = PaperView()
        self.paper_scroll = PaperScroll(self.paper)
        shadow(self.paper_scroll, 26, 5, 38)
        rl.addWidget(self.paper_scroll, 1)
        split.addWidget(right_col)
        split.setStretchFactor(0, 5)
        split.setStretchFactor(1, 5)
        self.setCentralWidget(central)
        self.setStyleSheet(STYLE)

    def btn_text_on(self):
        return str(self.settings.value("btn_text", False)).lower() in ("true", "1")

    def apply_btn_text(self):
        on = self.btn_text_on()
        for btn, label in self.head_btns:
            btn.setText(label if on else "")

    def ensure_file_assoc(self):
        """Doppio clic su un .listino = tk-listino (non «Python»), con la nostra icona."""
        if IS_WIN:
            from tklistino import winreg_assoc
            winreg_assoc.ensure_registered()

    def ensure_shortcut(self):
        """Nella cartella del programma: collegamento «tk-listino» con la nostra icona (il .cmd non può averla).
        Prima rinomina quello che le versioni ≤ 1.8.12 hanno creato come «tkLISTINO»."""
        if not IS_WIN or not is_installed():
            return
        import threading
        threading.Thread(target=migrate_old_names, daemon=True).start()
        if self.settings.value("lnk_root", "") == APP_ROOT:
            return

        def work():
            try:
                ensure_folder_shortcut()
                self.settings.setValue("lnk_root", APP_ROOT)
            except Exception:
                pass
        threading.Thread(target=work, daemon=True).start()

    def zoom_by(self, f):
        self.paper.zoom = 1.0 if f == 0 else max(0.4, min(3.0, self.paper.zoom * f))
        self.paper._resize()
        self.paper.update()

    # ---------------------------------------------------------------- documento
    def load_document(self, doc, path):
        for b in doc.get("blocks", []):
            model.migrate_block_colors(b)
        self.doc = doc
        self.path = path
        self.dirty = False
        self.bi = self.si = 0
        self._loading = True
        self.title_edit.setText(doc.get("title", ""))
        self.title_bg.setChecked(bool(doc.get("title_bg")))
        self._loading = False
        self.fill_swatches()
        self.fill_blocks()
        self.update_label()
        self.refresh_preview()

    def doc_name(self):
        if self.path:
            return os.path.splitext(os.path.basename(self.path))[0]
        return self.doc.get("name") or "Listino senza nome"

    def update_label(self):
        name = self.doc_name()
        self.doc_label.setText(f"{name}{'  ●' if self.dirty else ''}")
        self.setWindowTitle(f"{APP_TITLE} — {name}{' *' if self.dirty else ''}")

    def touch(self):
        if self._loading:
            return
        self.dirty = True
        self.update_label()
        self.timer.start()

    def block(self):
        return self.doc["blocks"][self.bi] if self.doc["blocks"] else None

    def section(self):
        b = self.block()
        return b["sections"][self.si] if b and b["sections"] else None

    def fill_swatches(self):
        self.accent_color.set_value(self.doc.get("accent") or model.DEFAULT_ACCENT)
        accent = self.doc.get("accent") or model.DEFAULT_ACCENT
        for key, r in self.style_rows.items():
            on_accent = model.TEXT_COLOR_KEYS[key][1]
            r.set_state(model.text_color(self.doc, key), model.font_style(self.doc, key),
                        accent if on_accent else "#ffffff")

    def fill_blocks(self):
        self._loading = True
        self.bi = min(self.bi, max(0, len(self.doc["blocks"]) - 1))
        self.block_chips.set_items([f"{b.get('name') or 'Marchio'}" for b in self.doc["blocks"]], self.bi)
        self._loading = False
        self.fill_block()

    def fill_block(self):
        self._loading = True
        b = self.block()
        self.block_name.setText(b.get("name", "") if b else "")
        self.block_name.setEnabled(b is not None)
        self.logo_box.set_logo(model.logo_bytes(b) if b else b"")
        bg, _head, name_c, sec_c = model.block_colors(self.doc, b)
        self.block_color.set_value(bg)
        self.block_text.set_value(name_c)
        self.block_color.setEnabled(b is not None)
        self.block_text.setEnabled(b is not None)
        self.block_color_reset.setVisible(bool(b and b.get("color")))
        self.block_text_reset.setVisible(bool(b and b.get("text_color")))
        self.bg_toggle.setVisible(bool(b and b.get("logo")))
        self.bg_toggle.setChecked(not (b and b.get("no_bg")))
        for key, color in (("name", name_c), ("sec", sec_c)):
            self.block_rows[key].set_state(color, model.font_style(self.doc, key, b), bg)
            self.block_rows[key].setEnabled(b is not None)
        if b:
            self.si = min(self.si, max(0, len(b["sections"]) - 1))
            self.sec_chips.set_items([s.get("title") or "Sezione" for s in b["sections"]], self.si)
        else:
            self.sec_chips.set_items([], 0)
        self._loading = False
        self.fill_section()

    def fill_section(self):
        self._loading = True
        s = self.section()
        for w in (self.sec_title, self.cols_spin, self.table, *self.sec_rows.values()):
            w.setEnabled(s is not None)
        self.table.clear()
        head_c, text_c = model.section_colors(self.doc, self.block(), s)
        for key, color in (("head_color", head_c), ("text_color", text_c)):
            dot, rst = self.sec_dots[key]
            dot.set_value(color)
            dot.setEnabled(s is not None)
            rst.setVisible(bool(s and s.get(key)))
        for key, color in (("head", head_c), ("text", text_c)):
            self.sec_rows[key].set_state(color, model.font_style(self.doc, key, s=s), "#ffffff")
        if s:
            bg, _head, _name, _title = model.block_colors(self.doc, self.block())
            head = head_c
            accent = QColor(bg)
            self.sec_title.setText(s["title"])
            n = len(s["cols"])
            self.cols_spin.setValue(n)
            self.table.setColumnCount(n)
            self.table.setRowCount(len(s["rows"]) + 1)
            self.table.setVerticalHeaderLabels(["Intest."] + [str(i + 1) for i in range(len(s["rows"]))])
            for c, text in enumerate(s["cols"]):
                it = QTableWidgetItem(text)
                f = it.font()
                f.setBold(True)
                it.setFont(f)
                it.setBackground(accent)
                it.setForeground(QColor(head))
                self.table.setItem(0, c, it)
            imgs = model.row_images(s)
            marks = model.row_marks(s)
            self.table.setIconSize(QSize(34, 34))
            for r, rowv in enumerate(s["rows"]):
                for c in range(n):
                    it = QTableWidgetItem(rowv[c] if c < len(rowv) else "")
                    if c in marks[r]:
                        it.setBackground(QColor(MARK_BG))
                        it.setToolTip("Da controllare: cifra corretta in automatico o letta con qualche dubbio "
                                      "durante l'importazione. Quando la modifichi il giallo sparisce.")
                    if c == 0 and imgs[r]:
                        pm = QPixmap()
                        pm.loadFromData(base64.b64decode(imgs[r]))
                        it.setIcon(QIcon(pm))
                    self.table.setItem(r + 1, c, it)
            self.table.resizeRowsToContents()
            for r in range(self.table.rowCount()):
                self.table.setRowHeight(r, max(38, self.table.rowHeight(r)))
        else:
            self.sec_title.setText("")
        self._loading = False

    def _add_logos(self, d):
        for i, b in enumerate(self.doc["blocks"]):
            if b.get("logo"):
                d.addResource(QTextDocument.ResourceType.ImageResource, QUrl(model.logo_name(i)),
                              QImage.fromData(model.logo_bytes(b)))
        for name, data in model.all_row_images(self.doc):
            d.addResource(QTextDocument.ResourceType.ImageResource, QUrl(name), QImage.fromData(data))

    def refresh_preview(self):
        self.print_doc = self.build_print_doc(self.make_printer())
        self.paper.set_doc(self.print_doc)

    # ---------------------------------------------------------------- modifiche
    def on_title(self, text):
        if not self._loading:
            self.doc["title"] = text
            self.touch()

    def set_color(self, c):
        self.doc["accent"] = c
        self.fill_swatches()
        self.touch()
        self.fill_block()

    def on_text_style(self, key, change):
        if "color" in change:
            self.doc[model.TEXT_COLOR_KEYS[key][0]] = change["color"]
        else:
            fonts = self.doc.setdefault("fonts", {})
            fonts[key] = {**model.font_style(self.doc, key), **change}
        self.fill_swatches()
        self.touch()
        self.fill_block()

    def on_title_bg(self, on):
        if on:
            self.doc["title_bg"] = True
        else:
            self.doc.pop("title_bg", None)
        self.touch()

    def on_bg_toggle(self, on):
        b = self.block()
        if self._loading or not b:
            return
        if on:
            b.pop("no_bg", None)
        else:
            b["no_bg"] = True
        self.touch()
        self.fill_block()

    def on_block_style(self, key, change):
        b = self.block()
        if self._loading or not b:
            return
        if "color" in change:
            self.set_block_color("text_color", change["color"])
            return
        fonts = b.setdefault("fonts", {})
        fonts[key] = {**model.font_style(self.doc, key, b), **change}
        self.touch()
        self.fill_block()

    def set_sec_color(self, key, c):
        s = self.section()
        if self._loading or not s:
            return
        if c:
            s[key] = c
        else:
            s.pop(key, None)
        self.touch()
        self.fill_section()

    def on_sec_style(self, key, change):
        s = self.section()
        if self._loading or not s:
            return
        fonts = s.setdefault("fonts", {})
        fonts[key] = {**model.font_style(self.doc, key, s=s), **change}
        self.touch()
        self.fill_section()

    def set_block_color(self, key, c):
        b = self.block()
        if self._loading or not b:
            return
        if c:
            b[key] = c
        else:
            b.pop(key, None)
        self.touch()
        self.fill_block()

    def on_block(self, i):
        if self._loading or i < 0:
            return
        self.bi, self.si = i, 0
        self.fill_blocks()

    def on_block_name(self, text):
        if self._loading or not self.block():
            return
        self.block()["name"] = text
        self.block_chips.rename(self.bi, text or "Marchio")
        self.touch()

    def pick_logo(self):
        last = self.settings.value("last_img_dir", os.path.expanduser("~"))
        path, _ = QFileDialog.getOpenFileName(self, "Scegli la foto o il logo", last,
                                              "Immagini (*.png *.jpg *.jpeg *.webp *.bmp *.gif)")
        if path:
            self.set_logo_from(path)

    def set_logo_from(self, path):
        if not self.block():
            return
        self.settings.setValue("last_img_dir", os.path.dirname(path))
        try:
            self.block()["logo"] = shrink_logo(path)
        except Exception as exc:
            tk_warn(self, APP_TITLE, f"Non riesco a leggere l'immagine:\n{exc}")
            return
        self.fill_block()
        self.touch()

    def clear_logo(self):
        if self.block():
            self.block()["logo"] = ""
            self.fill_block()
            self.touch()

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        for u in e.mimeData().urls():
            f = u.toLocalFile()
            if f.lower().endswith(".listino"):
                if self.maybe_save():
                    self.open_path(f)
                return
            if f.lower().endswith(".pdf"):
                self.import_path(f)
                return
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif")):
                self.set_logo_from(f)
                return

    def block_add(self):
        self.doc["blocks"].append(model.new_block(f"Marchio {len(self.doc['blocks']) + 1}"))
        self.bi, self.si = len(self.doc["blocks"]) - 1, 0
        self.fill_blocks()
        self.touch()

    def block_del(self):
        if not self.block():
            return
        if tk_choice(self, "Eliminare il marchio?", "Verranno eliminate anche tutte le sue sezioni.",
                     [("Elimina", "accent"), ("Annulla", "ghost")]) != 0:
            return
        del self.doc["blocks"][self.bi]
        self.si = 0
        self.fill_blocks()
        self.touch()

    def block_move(self, d):
        j = self.bi + d
        if self.block() and 0 <= j < len(self.doc["blocks"]):
            bl = self.doc["blocks"]
            bl[self.bi], bl[j] = bl[j], bl[self.bi]
            self.bi = j
            self.fill_blocks()
            self.touch()

    def on_section(self, i):
        if self._loading or i < 0:
            return
        self.si = i
        self.fill_block()

    def on_sec_title(self, text):
        if self._loading or not self.section():
            return
        self.section()["title"] = text
        self.sec_chips.rename(self.si, text or "Sezione")
        self.touch()

    def sec_add(self):
        if not self.block():
            return
        self.block()["sections"].append(model.new_section())
        self.si = len(self.block()["sections"]) - 1
        self.fill_block()
        self.touch()

    def sec_del(self):
        if not self.section():
            return
        del self.block()["sections"][self.si]
        self.fill_block()
        self.touch()

    def sec_dup(self):
        if self.section():
            self.block()["sections"].insert(self.si + 1, model.clone(self.section()))
            self.si += 1
            self.fill_block()
            self.touch()

    def sec_move(self, d):
        j = self.si + d
        if self.section() and 0 <= j < len(self.block()["sections"]):
            ss = self.block()["sections"]
            ss[self.si], ss[j] = ss[j], ss[self.si]
            self.si = j
            self.fill_block()
            self.touch()

    def on_cols(self, n):
        s = self.section()
        if self._loading or not s:
            return
        cur = len(s["cols"])
        if n > cur:
            s["cols"] += [""] * (n - cur)
            for r in s["rows"]:
                r += [""] * (n - cur)
        else:
            s["cols"] = s["cols"][:n]
            s["rows"] = [r[:n] for r in s["rows"]]
        self.fill_section()
        self.touch()

    def on_cell(self, item):
        s = self.section()
        if self._loading or not s:
            return
        r, c = item.row(), item.column()
        if r == 0:
            s["cols"][c] = item.text()
        elif r - 1 < len(s["rows"]):
            s["rows"][r - 1][c] = item.text()
            marks = model.row_marks(s)
            if c in marks[r - 1]:  # cella ricontrollata: via il giallo
                marks[r - 1].remove(c)
                self._set_marks(s, marks)
                self._loading = True
                item.setBackground(QBrush())
                item.setToolTip("")
                self._loading = False
        self.table.resizeRowToContents(r)
        self.table.setRowHeight(r, max(38, self.table.rowHeight(r)))
        self.touch()

    def _cur_row(self):
        r = self.table.currentRow()
        if r >= 1:
            return r - 1
        s = self.section()
        return 0 if s and len(s["rows"]) == 1 else -1  # una riga sola: è quella, senza doverla cliccare

    def _set_imgs(self, s, imgs):
        s["imgs"] = imgs
        model.row_images(s)

    def _set_marks(self, s, marks):
        s["dubbi"] = marks
        model.row_marks(s)

    def row_add(self):
        s = self.section()
        if not s:
            return
        i = self._cur_row()
        pos = i + 1 if i >= 0 else len(s["rows"])
        imgs, marks = model.row_images(s), model.row_marks(s)
        s["rows"].insert(pos, [""] * len(s["cols"]))
        imgs.insert(pos, "")
        marks.insert(pos, [])
        self._set_imgs(s, imgs)
        self._set_marks(s, marks)
        self.fill_section()
        self.table.setCurrentCell(pos + 1, 0)
        self.table.editItem(self.table.item(pos + 1, 0))
        self.touch()

    def row_del(self):
        s, i = self.section(), self._cur_row()
        if s and i >= 0:
            imgs, marks = model.row_images(s), model.row_marks(s)
            del s["rows"][i]
            del imgs[i]
            del marks[i]
            self._set_imgs(s, imgs)
            self._set_marks(s, marks)
            self.fill_section()
            self.table.setCurrentCell(min(i + 1, len(s["rows"])), 0)
            self.touch()

    def row_dup(self):
        s, i = self.section(), self._cur_row()
        if s and i >= 0:
            imgs, marks = model.row_images(s), model.row_marks(s)
            s["rows"].insert(i + 1, list(s["rows"][i]))
            imgs.insert(i + 1, imgs[i])
            marks.insert(i + 1, list(marks[i]))
            self._set_imgs(s, imgs)
            self._set_marks(s, marks)
            self.fill_section()
            self.table.setCurrentCell(i + 2, 0)
            self.touch()

    def row_img_pick(self):
        s, i = self.section(), self._cur_row()
        if not s or i < 0:
            tk_info(self, APP_TITLE, "Clicca prima sulla riga a cui mettere la foto (non l'intestazione).")
            return
        last = self.settings.value("last_img_dir", os.path.expanduser("~"))
        path, _ = QFileDialog.getOpenFileName(self, "Foto per la prima colonna della riga", last,
                                              "Immagini (*.png *.jpg *.jpeg *.webp *.bmp *.gif)")
        if not path:
            return
        self.settings.setValue("last_img_dir", os.path.dirname(path))
        try:
            data = shrink_logo(path, 240)
        except Exception as exc:
            tk_warn(self, APP_TITLE, f"Non riesco a leggere l'immagine:\n{exc}")
            return
        imgs = model.row_images(s)
        imgs[i] = data
        self._set_imgs(s, imgs)
        self.fill_section()
        self.table.setCurrentCell(i + 1, 0)
        self.touch()

    def row_img_clear(self):
        s, i = self.section(), self._cur_row()
        if s and i >= 0:
            imgs = model.row_images(s)
            if imgs[i]:
                imgs[i] = ""
                self._set_imgs(s, imgs)
                self.fill_section()
                self.table.setCurrentCell(i + 1, 0)
                self.touch()

    def row_move(self, d):
        s, i = self.section(), self._cur_row()
        j = i + d
        if s and i >= 0 and 0 <= j < len(s["rows"]):
            imgs, marks = model.row_images(s), model.row_marks(s)
            s["rows"][i], s["rows"][j] = s["rows"][j], s["rows"][i]
            imgs[i], imgs[j] = imgs[j], imgs[i]
            marks[i], marks[j] = marks[j], marks[i]
            self._set_imgs(s, imgs)
            self._set_marks(s, marks)
            self.fill_section()
            self.table.setCurrentCell(j + 1, max(0, self.table.currentColumn()))
            self.touch()

    # ---------------------------------------------------------------- file
    def maybe_save(self):
        if not self.dirty:
            return True
        i = tk_choice(self, "Salvare le modifiche?", "Il listino ha modifiche non salvate.",
                      [("Salva", "accent"), ("Non salvare", "ghost"), ("Annulla", "ghost")])
        if i == 0:
            return self.act_save()
        if i == 1:
            self.drop_recovery()  # scartate apposta: niente proposta di recupero al prossimo avvio
        return i == 1

    def act_rename(self):
        value = tk_input(self, "Rinomina listino", "Nome del listino",
                         self.doc_name() if (self.path or self.doc.get("name")) else "", "Rinomina")
        if value is None:
            return
        name = "".join(c for c in value if c not in '\\/:*?"<>|').strip().rstrip(".")
        if not name:
            return
        if self.path:
            new = os.path.join(os.path.dirname(self.path), name + ".listino")
            if os.path.normcase(new) != os.path.normcase(self.path):
                if os.path.exists(new):
                    tk_warn(self, APP_TITLE, "Esiste già un listino con questo nome in questa cartella.")
                    return
                try:
                    os.replace(self.path, new)
                except OSError as exc:
                    tk_warn(self, APP_TITLE, f"Non riesco a rinominare il file:\n{exc}")
                    return
                self.path = new
        self.doc["name"] = name
        self.update_label()
        self.statusBar().showMessage(f"Listino rinominato in «{name}»", 4000)

    # Apri e Importa mostrano gli stessi file: un .listino si apre, una foto o un PDF si importa
    OPEN_FILTER = ("Listini, foto e PDF (*.listino *.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff *.pdf);;"
                   "Listini tk-listino (*.listino);;Foto e PDF (*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff *.pdf)")

    def open_any(self, path):
        if path.lower().endswith(".listino"):
            if self.maybe_save():
                self.open_path(path)
        else:
            self.import_path(path)

    def act_import(self):
        last = self.settings.value("last_import_dir", os.path.expanduser("~"))
        path, _ = QFileDialog.getOpenFileName(self, "Importa un listino da foto o PDF", last, self.OPEN_FILTER)
        if path:
            self.open_any(path)

    def import_path(self, path):
        if not self.maybe_save():
            return
        self.settings.setValue("last_import_dir", os.path.dirname(path))
        prog = TkProgress(self, "Importazione", "Sto leggendo il listino")
        prog.set_status("Può richiedere qualche secondo.")
        prog.show()
        self.imp_thread = t = ImportThread(path, self)
        t.status.connect(lambda m: prog.set_status(m + " Può richiedere qualche secondo."))

        def ok(doc):
            from tklistino import importer
            prog.close()
            self.load_document(doc, "")
            self.dirty = True
            self.update_label()
            secs, rows = importer.summary(doc)
            marks = model.count_marks(doc)
            yellow = (f"\n\n{marks} celle sono in giallo: le ho corrette in automatico o lette con qualche dubbio. "
                      "Controllale una per una (quando modifichi una cella il giallo sparisce)." if marks else "")
            tk_info(
                self, APP_TITLE,
                f"Ho letto {secs} sezioni e {rows} righe.\n\nControlla bene i dati, soprattutto i prezzi: "
                "quando la foto è sfocata o storta qualche cifra può essere sbagliata o mancare.\n"
                "I titoli delle sezioni, se non si leggono, hanno un nome provvisorio: rinominali a destra." + yellow)

        def ko(msg):
            prog.close()
            tk_warn(self, APP_TITLE, f"Importazione non riuscita:\n{msg}")

        t.done.connect(ok)
        t.failed.connect(ko)
        t.start()

    def act_new(self):
        if self.maybe_save():
            self.load_document(model.new_document(), "")

    def act_open(self):
        path, _ = QFileDialog.getOpenFileName(self, "Apri listino", data_dir(), self.OPEN_FILTER)
        if path:
            self.open_any(path)

    def open_path(self, path):
        try:
            self.load_document(model.load(path), path)
        except Exception as exc:
            tk_warn(self, APP_TITLE, f"Non riesco ad aprire il listino:\n{exc}")

    def act_save(self):
        if not self.path:
            return self.act_save_as()
        return self._write(self.path)

    def act_save_as(self):
        path, _ = QFileDialog.getSaveFileName(self, "Salva listino", os.path.join(data_dir(), self.doc_name() if (self.path or self.doc.get("name")) else "Listino")
                                              + ".listino",
                                              "Listini tk-listino (*.listino)")
        if not path:
            return False
        if not path.lower().endswith(".listino"):
            path += ".listino"
        return self._write(path)

    def _write(self, path):
        try:
            model.save(path, self.doc)
        except OSError as exc:
            tk_warn(self, APP_TITLE, f"Salvataggio non riuscito:\n{exc}")
            return False
        self.path = path
        self.dirty = False
        self.drop_recovery()
        self.update_label()
        self.statusBar().showMessage("Listino salvato", 4000)
        return True

    # ---------------------------------------------------------------- PDF e stampa
    def build_print_doc(self, printer):
        rect = printer.pageRect(QPrinter.Unit.Point)
        pages = self.paginate(rect.width(), rect.height())
        d = QTextDocument()
        self._add_logos(d)
        d.setHtml(model.render_html(self.doc, pages=pages))
        d.setPageSize(QSizeF(rect.width(), rect.height()))
        d.setDocumentMargin(0)
        return d

    def paginate(self, page_w, page_h):
        """Divide il listino in pagine misurando l'altezza vera: una riga non viene mai spezzata tra due pagine,
        una fascia di sezione non resta da sola in fondo alla pagina e chi continua ripete fascia e intestazioni.
        Ogni pagina si riempie con una ricerca binaria sulle righe (poche misure anche con listini lunghi)."""
        resources = {}
        for i, b in enumerate(self.doc["blocks"]):
            if b.get("logo"):
                resources[model.logo_name(i)] = QImage.fromData(model.logo_bytes(b))
        for name, data in model.all_row_images(self.doc):
            resources[name] = QImage.fromData(data)
        limit = page_h - 6  # un filo di margine: meglio una riga in meno che una riga tagliata

        def height(page, first):
            d = QTextDocument()
            for name, img in resources.items():
                d.addResource(QTextDocument.ResourceType.ImageResource, QUrl(name), img)
            d.setDocumentMargin(0)
            d.setTextWidth(page_w)
            d.setHtml(model.render_html(self.doc, pages=[page], title=first))  # titolo solo sulla prima pagina
            return d.size().height()

        def with_chunk(page, bi, chunk):
            page = [(b, list(ch)) for b, ch in page]
            if page and page[-1][0] == bi:
                page[-1][1].append(chunk)
            else:
                page.append((bi, [chunk]))
            return page

        pages, cur = [], []
        for bi, block in enumerate(self.doc["blocks"]):
            for si, s in enumerate(block["sections"]):
                n, a = len(s["rows"]), 0
                while True:
                    first = not pages
                    fits = lambda k: height(with_chunk(cur, bi, (si, a, a + k)), first) <= limit
                    if fits(n - a):  # il resto della sezione ci sta tutto
                        cur = with_chunk(cur, bi, (si, a, n))
                        break
                    lo, hi = 0, n - a - 1  # quante righe ci stanno al massimo (fits cresce al diminuire di k)
                    while lo < hi:
                        mid = (lo + hi + 1) // 2
                        if fits(mid):
                            lo = mid
                        else:
                            hi = mid - 1
                    k = lo
                    if k == 0:
                        if cur:  # nemmeno una riga: la sezione comincia sulla pagina dopo
                            pages.append(cur)
                            cur = []
                            continue
                        k = 1 if n > a else 0  # riga più alta di una pagina: la si mette comunque
                    cur = with_chunk(cur, bi, (si, a, a + k))
                    a += k
                    if a >= n:
                        break
                    pages.append(cur)
                    cur = []
        if cur or not pages:
            pages.append(cur)
        return pages

    @staticmethod
    def make_printer():
        pr = QPrinter(QPrinter.PrinterMode.HighResolution)
        pr.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        pr.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        pr.setPageMargins(QMarginsF(12, 12, 12, 12), QPageLayout.Unit.Millimeter)
        return pr

    def write_pdf(self, path):
        pr = self.make_printer()
        pr.setOutputFileName(path)
        self.build_print_doc(pr).print_(pr)

    def confirm_checked(self, what):
        """Listino importato e non ancora ricontrollato: prima del primo PDF (o della prima stampa) si chiede."""
        if not self.doc.get("da_controllare"):
            return True
        marks = model.count_marks(self.doc)
        yellow = (f"Ci sono ancora {marks} celle in giallo, corrette in automatico o lette con qualche dubbio.\n\n"
                  if marks else "")
        i = tk_choice(self, "Hai controllato i prezzi?",
                      f"Questo listino è stato importato da una foto o da un PDF e non è ancora stato ricontrollato.\n\n"
                      f"{yellow}Un prezzo letto male finirebbe nel {what}.",
                      [("Torna a controllare", "ghost"), ("Ho controllato: continua", "accent")], "warn")
        if i != 1:
            return False
        model.clear_marks(self.doc)
        self.fill_section()
        self.touch()
        return True

    def act_pdf(self):
        if not self.confirm_checked("PDF"):
            return
        base = self.doc_name() if (self.path or self.doc.get("name")) else "Listino"
        last = self.settings.value("last_pdf_dir", data_dir())
        path, _ = QFileDialog.getSaveFileName(self, "Scarica PDF", os.path.join(last, base + ".pdf"),
                                              "PDF (*.pdf)")
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        try:
            self.write_pdf(path)
        except Exception as exc:
            tk_warn(self, APP_TITLE, f"Creazione del PDF non riuscita:\n{exc}")
            return
        self.settings.setValue("last_pdf_dir", os.path.dirname(path))
        self.statusBar().showMessage(f"PDF creato: {path}", 8000)
        open_path(path)

    def act_print(self):
        from tklistino.printing import print_listino
        if not self.confirm_checked("foglio stampato"):
            return
        if print_listino(self):
            self.statusBar().showMessage("Inviato alla stampante", 5000)

    # ---------------------------------------------------------------- info e aggiornamenti
    def act_about(self):
        dlg = AboutDialog(self)
        dlg.exec()
        if dlg.check:
            self.check_updates(True)

    def show_update_button(self, version):
        self.update_btn.setVisible(bool(version))
        if version:
            self.update_btn.setText(f"Aggiorna a {version}")

    def check_updates(self, manual):
        if self.check_thread is not None and self.check_thread.isRunning():
            return
        if not manual and time.time() - float(self.settings.value("last_check", 0)) < updater.CHECK_INTERVAL:
            cached = self.settings.value("available", "")
            if cached and updater.is_newer(cached):
                self.show_update_button(cached)
            return
        self.check_thread = CheckThread(self)
        self.check_thread.checked.connect(lambda m, err: self._checked(m, err, manual))
        if manual:
            self.statusBar().showMessage("Controllo aggiornamenti…")
        self.check_thread.start()

    def _checked(self, manifest, error, manual):
        self.statusBar().clearMessage()  # «Controllo aggiornamenti…» non deve restare in basso
        if manifest is None:
            if manual:
                tk_warn(self, APP_TITLE, f"Impossibile controllare gli aggiornamenti.\n"
                                                     f"Verifica la connessione a internet.\n\n{error}")
            return
        self.settings.setValue("last_check", time.time())
        version = str(manifest["version"])
        if not updater.is_newer(version):
            self.settings.setValue("available", "")
            self.show_update_button(None)
            if manual:
                tk_info(self, APP_TITLE, f"Hai già l'ultima versione di {APP_TITLE} ({VERSION}).")
            return
        self.manifest = manifest
        self.settings.setValue("available", version)
        self.show_update_button(version)
        if manual or self.settings.value("skip_version", "") != version:
            self.show_update_dialog()

    def show_update_dialog(self):
        m = self.manifest
        if m is None:
            self.check_updates(True)
            return
        dlg = UpdateDialog(self, m)
        dlg.exec()
        if dlg.choice == "skip":
            self.settings.setValue("skip_version", str(m["version"]))
        elif dlg.choice == "go":
            self.start_update()

    def start_update(self):
        asset = updater.asset_for(self.manifest)
        if asset is None:
            tk_info(self, APP_TITLE, "Questa versione non è ancora disponibile per il tuo sistema.")
            return
        if not is_installed():
            tk_info(self, APP_TITLE, "Stai usando la versione di sviluppo: l'aggiornamento "
                                                     "automatico funziona solo con la versione portatile.")
            return
        if not self.maybe_save():
            return
        dest = os.path.join(updater.download_dir(), os.path.basename(asset["url"].split("?")[0]))
        prog = TkProgress(self, "Aggiornamento in corso", f"Scarico {APP_TITLE} {self.manifest['version']}", True)
        prog.show()
        self.dl_thread = t = DownloadThread(asset["url"], dest, asset.get("sha256"), self)

        def on_progress(done, total):
            prog.set_progress(done, total, f"{human_size(done)} di {human_size(total)}")

        def on_ok(path):
            prog.bar.setRange(0, 0)
            prog.set_status("Installazione dell'aggiornamento…")
            try:
                updater.apply_update(path, new_version=str(self.manifest["version"]))
            except Exception as exc:
                prog.close()
                tk_warn(self, APP_TITLE, f"Aggiornamento non riuscito:\n{exc}")
                return
            self.closing_for_update = True
            QTimer.singleShot(300, QApplication.instance().quit)

        def on_fail(msg):
            prog.close()
            if msg:
                tk_warn(self, APP_TITLE, f"Aggiornamento non riuscito:\n{msg}")

        prog.canceled.connect(t.cancel)
        t.progress.connect(on_progress)
        t.ok.connect(on_ok)
        t.failed.connect(on_fail)
        t.start()

    def closeEvent(self, e):
        if self.closing_for_update or self.maybe_save():
            e.accept()
        else:
            e.ignore()


def cli_update_test(argv):
    url = argv[argv.index("--update-test") + 1]
    log = os.path.join(log_dir(), "update-test.log")

    def write(msg):
        with open(log, "a", encoding="utf-8") as fh:
            fh.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")

    try:
        m = updater.fetch_manifest(url)
        write(f"manifest {m['version']} (installata {VERSION})")
        if not updater.is_newer(m["version"]):
            write("nessun aggiornamento")
            return 0
        asset = updater.asset_for(m)
        dest = os.path.join(updater.download_dir(), os.path.basename(asset["url"].split("?")[0]))
        updater.download(asset["url"], dest, asset.get("sha256"))
        write(f"scaricato e verificato: {dest}")
        if not is_installed():
            write("versione di sviluppo: aggiornamento non applicato")
            return 3
        updater.apply_update(dest, relaunch="--no-relaunch" not in argv, new_version=m["version"])
        write("installazione avviata")
        return 0
    except Exception as exc:
        write(f"ERRORE: {exc}")
        return 1


def load_fonts():
    """Carica i caratteri Google inclusi (tklistino/fonts): li vedono anteprima, PDF e stampa."""
    folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
    loaded = set()
    if os.path.isdir(folder):
        for name in sorted(os.listdir(folder)):
            if name.lower().endswith(".ttf"):
                fid = QFontDatabase.addApplicationFont(os.path.join(folder, name))
                if fid >= 0:
                    loaded.update(QFontDatabase.applicationFontFamilies(fid))
    return loaded


def main():
    argv = sys.argv[1:]
    if "--import-test" in argv:
        from PySide6.QtGui import QGuiApplication
        _qapp = QGuiApplication(sys.argv)
        i = argv.index("--import-test")
        from tklistino import importer
        try:
            d = importer.import_file(argv[i + 1])
            secs, rows = importer.summary(d)
            res = f"OK {secs} sezioni {rows} righe"
        except Exception as exc:
            res = f"ERRORE {exc}"
        with open(argv[i + 2], "w", encoding="utf-8") as fh:
            fh.write(res)
        return
    if "--update-test" in argv:
        sys.exit(cli_update_test(argv))
    app = QApplication(sys.argv)
    load_fonts()
    # memoria del programma (benvenuto, consenso alle statistiche, invito al caffè): nessuna rete qui
    app.licenza = pro.crea_licenza(VERSION)
    app.setApplicationName(APP_TITLE)
    app.setStyle("Fusion")
    import PySide6
    from PySide6.QtCore import QLibraryInfo, QTranslator
    tr = QTranslator(app)
    for folder in (os.path.join(os.path.dirname(PySide6.__file__), "translations"),
                   QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)):
        if tr.load("qtbase_it", folder):
            app.installTranslator(tr)
            break
    if IS_WIN:
        app.setFont(QFont("Segoe UI", 10))
    settings = Settings()
    win = MainWindow(settings)
    sample = os.path.join(data_dir(), "Esempio.listino")
    if not os.path.exists(sample):
        try:
            model.save(sample, model.sample_document())
        except OSError:
            pass

    files = [a for a in argv if a.lower().endswith(".listino") and os.path.isfile(a)]
    if "--selftest" in argv:
        out = argv[argv.index("--selftest") + 1]
        win.load_document(model.sample_document(), "")
        win.resize(1400, 1300)
        win.show()
        app.processEvents()
        win.refresh_preview()
        QTimer.singleShot(600, lambda: (win.grab().save(out), win.write_pdf(os.path.splitext(out)[0] + ".pdf"),
                                        app.quit()))
        app.exec()
        return
    if files:
        win.open_path(files[0])
    elif os.path.exists(sample) and not settings.value("sample_seen", False):
        win.open_path(sample)
        settings.setValue("sample_seen", True)
    win.show()
    app.processEvents()
    # primo avvio: benvenuto (software libero, privacy, consenso alle statistiche); nessuna rete prima della risposta
    pro.benvenuto(win)
    win.offer_recovery()
    win.start_network()
    pro.invito(win)
    sys.exit(app.exec())
