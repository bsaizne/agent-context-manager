from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtCore import QPoint
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap


ICON_SIZE = 24


def icon(name: str, color: str = "#6E6E73") -> QIcon:
    """Render one of the sidebar icons.

    The painter is always closed (try/finally). An unclosed QPainter leaves the
    QPixmap in a painting state, and destroying it then aborts the whole process
    with "QPaintDevice: Cannot destroy paint device that is being painted". That is
    exactly what used to happen for an unknown name (the fallback branch called the
    non-existent QPainter.drawCircle) and for "warning" (drawPolygon was given
    coordinate tuples instead of QPoint objects).
    """
    pixmap = QPixmap(ICON_SIZE, ICON_SIZE)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    try:
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor(color), 1.7, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        _draw_icon(painter, name)
    finally:
        painter.end()
    return QIcon(pixmap)


def _draw_icon(painter: QPainter, name: str) -> None:
    if name == "overview":
        painter.drawRoundedRect(4, 4, 16, 16, 3, 3)
        painter.drawLine(8, 9, 16, 9)
        painter.drawLine(8, 13, 16, 13)
        painter.drawLine(8, 17, 13, 17)
    elif name == "state":
        painter.drawRoundedRect(5, 3, 14, 18, 2, 2)
        painter.drawLine(8, 8, 16, 8)
        painter.drawLine(8, 12, 16, 12)
        painter.drawLine(8, 16, 13, 16)
    elif name == "tasks":
        for y in (7, 12, 17):
            painter.drawRoundedRect(5, y - 2, 3, 3, 0.8, 0.8)
            painter.drawLine(11, y, 19, y)
    elif name == "decisions":
        painter.drawRoundedRect(5, 4, 14, 16, 2, 2)
        painter.drawLine(8, 9, 16, 9)
        painter.drawLine(8, 13, 16, 13)
        painter.drawLine(8, 17, 12, 17)
    elif name == "changelog":
        painter.drawLine(6, 6, 18, 6)
        painter.drawLine(6, 12, 18, 12)
        painter.drawLine(6, 18, 14, 18)
        painter.drawLine(4, 6, 4, 6)
        painter.drawLine(4, 12, 4, 12)
        painter.drawLine(4, 18, 4, 18)
    elif name == "checkpoint":
        painter.drawRoundedRect(4, 5, 16, 14, 2, 2)
        painter.drawLine(8, 5, 8, 3)
        painter.drawLine(16, 5, 16, 3)
        painter.drawLine(8, 11, 16, 11)
        painter.drawLine(8, 15, 13, 15)
    elif name == "resume":
        painter.drawArc(5, 5, 14, 14, 45 * 16, 270 * 16)
        path = QPainterPath()
        path.moveTo(17, 5)
        path.lineTo(19, 9)
        path.lineTo(15, 8)
        painter.drawPath(path)
    elif name == "doctor":
        painter.drawEllipse(4, 4, 16, 16)
        painter.drawLine(12, 8, 12, 13)
        painter.drawLine(12, 16, 12, 16)
    elif name == "settings":
        painter.drawEllipse(9, 9, 6, 6)
        for x1, y1, x2, y2 in ((12, 3, 12, 6), (12, 18, 12, 21), (3, 12, 6, 12), (18, 12, 21, 12), (5.6, 5.6, 7.7, 7.7), (16.3, 16.3, 18.4, 18.4), (16.3, 7.7, 18.4, 5.6), (5.6, 18.4, 7.7, 16.3)):
            painter.drawLine(x1, y1, x2, y2)
    elif name == "folder":
        painter.drawPath(_folder_path())
    elif name == "save":
        painter.drawRoundedRect(4, 4, 16, 16, 3, 3)
        painter.drawLine(8, 4, 8, 10)
        painter.drawLine(16, 4, 16, 10)
        painter.drawRoundedRect(8, 14, 8, 6, 1, 1)
    elif name == "copy":
        painter.drawRoundedRect(8, 6, 11, 13, 2, 2)
        painter.drawRoundedRect(5, 4, 11, 13, 2, 2)
    elif name == "search":
        painter.drawEllipse(5, 5, 11, 11)
        painter.drawLine(14.5, 14.5, 19.5, 19.5)
    elif name == "refresh":
        painter.drawArc(5, 5, 14, 14, 45 * 16, 280 * 16)
        painter.drawLine(18, 5, 18, 9)
        painter.drawLine(18, 5, 14, 5)
    elif name == "check":
        painter.drawPolyline([QPoint(5, 12), QPoint(10, 17), QPoint(19, 7)])
    elif name == "warning":
        # drawPolygon needs QPoint/QPolygon objects. Passing coordinate tuples raised a
        # TypeError while the painter was open, which aborted the process.
        painter.drawPolygon([QPoint(12, 4), QPoint(20, 19), QPoint(4, 19)])
        painter.drawLine(12, 9, 12, 14)
        painter.drawLine(12, 17, 12, 17)
    elif name == "close":
        painter.drawLine(6, 6, 18, 18)
        painter.drawLine(18, 6, 6, 18)
    elif name == "sun":
        painter.drawEllipse(8, 8, 8, 8)
        for x1, y1, x2, y2 in ((12, 2, 12, 5), (12, 19, 12, 22), (2, 12, 5, 12), (19, 12, 22, 12), (5, 5, 7, 7), (17, 17, 19, 19), (17, 7, 19, 5), (5, 19, 7, 17)):
            painter.drawLine(x1, y1, x2, y2)
    elif name == "moon":
        painter.drawArc(6, 4, 13, 16, 55 * 16, 250 * 16)
    elif name == "system":
        painter.drawRoundedRect(4, 5, 16, 12, 2, 2)
        painter.drawLine(9, 20, 15, 20)
        painter.drawLine(12, 17, 12, 20)
    elif name == "arrow":
        painter.drawLine(5, 12, 19, 12)
        painter.drawLine(14, 7, 19, 12)
        painter.drawLine(14, 17, 19, 12)
    elif name == "changes":
        # Two panes with a plus and a minus: "what was added and removed".
        painter.drawRoundedRect(4, 4, 6, 16, 1.5, 1.5)
        painter.drawRoundedRect(14, 4, 6, 16, 1.5, 1.5)
        painter.drawLine(11, 8, 13, 8)
        painter.drawLine(12, 7, 12, 9)
        painter.drawLine(11, 16, 13, 16)
    else:
        # Unknown names must degrade to a plain circle, never to a crash.
        painter.drawEllipse(5, 5, 14, 14)


def _folder_path() -> QPainterPath:
    path = QPainterPath()
    path.moveTo(3, 7)
    path.lineTo(9, 7)
    path.lineTo(11, 9)
    path.lineTo(21, 9)
    path.lineTo(19, 19)
    path.lineTo(4, 19)
    path.closeSubpath()
    return path
