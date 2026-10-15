#!/usr/bin/env python
# --!-- coding: utf8 --!--
"""Native PyQt5 Whiteboard view with parity to the Web App's whiteboard.

Supports:
- Multiple named whiteboards per project (`whiteboards.json` format)
- Shapes (Rectangle, Circle, Triangle, Arrow) starting with blank labels
- Sticky Note nodes
- Editable labels (double-click on node or toolbar inspector)
- Shape notes (unobtrusive badge + hover popover OR toolbar "Show notes" toggle)
- 4 connector line styles: solid, dash, dot, solid-dashed
- Color palette + custom color picker for shapes, notes, and connector lines
- Zoom in, zoom out, fit view, pan
"""

import json
import time
import uuid

from PyQt5.QtCore import Qt, QPointF, QRectF, pyqtSignal
from PyQt5.QtGui import (QBrush, QColor, QFont, QIcon, QPainter, QPainterPath,
                         QPainterPathStroker, QPen, QPixmap, QPolygonF)
from PyQt5.QtWidgets import (QColorDialog, QComboBox, QFrame, QGraphicsItem,
                             QGraphicsObject, QGraphicsPathItem, QGraphicsScene,
                             QGraphicsView, QHBoxLayout, QInputDialog, QLabel,
                             QLineEdit, QMenu, QMessageBox, QPushButton,
                             QToolButton, QVBoxLayout, QWidget)

from manuskript.appearance.config import Appearance

LINE_TYPES = [
    ("solid", "Solid", []),
    ("dash", "Dash", [4.0, 2.5]),
    ("dot", "Dot", [1.0, 2.5]),
    ("solid-dashed", "Solid dashed", [6.0, 2.0, 1.0, 2.0]),
]

WHITEBOARD_COLORS = [
    ("default", "Theme Accent", ""),
    ("red", "Red", "#ef4444"),
    ("orange", "Orange", "#f97316"),
    ("amber", "Amber", "#eab308"),
    ("emerald", "Emerald", "#22c55e"),
    ("teal", "Teal", "#14b8a6"),
    ("blue", "Blue", "#3b82f6"),
    ("indigo", "Indigo", "#6366f1"),
    ("purple", "Purple", "#a855f7"),
    ("pink", "Pink", "#ec4899"),
    ("slate", "Slate", "#64748b"),
]

SHAPES = [
    ("rectangle", "Rectangle"),
    ("circle", "Circle"),
    ("triangle", "Triangle"),
    ("arrow", "Arrow"),
]


def _theme_colors():
    """Return surface, bg, border, text, muted, accent colors from active theme."""
    s, d = Appearance.colours()
    if s is not None:
        return {
            "bg": QColor(s.window),
            "surface": QColor(s.panel),
            "editor": QColor(s.editor),
            "text": QColor(s.text),
            "muted": QColor(s.muted),
            "accent": QColor(d.get("accent", s.accent)),
            "border": QColor(d.get("border", "#3a3f4b")),
        }
    return {
        "bg": QColor("#14161b"),
        "surface": QColor("#1b1e25"),
        "editor": QColor("#0f1115"),
        "text": QColor("#e4e6eb"),
        "muted": QColor("#9aa0ac"),
        "accent": QColor("#6ea8fe"),
        "border": QColor("#2d323e"),
    }


def _line_icon(line_type_id, color=None):
    pm = QPixmap(28, 14)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    tc = _theme_colors()
    pen = QPen(QColor(color) if color else tc["text"], 2.0)
    for lid, _label, pattern in LINE_TYPES:
        if lid == line_type_id and pattern:
            pen.setStyle(Qt.CustomDashLine)
            pen.setDashPattern(pattern)
            break
    p.setPen(pen)
    p.drawLine(2, 7, 26, 7)
    p.end()
    return QIcon(pm)


def _shape_icon(shape_name, color=None):
    pm = QPixmap(20, 20)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    tc = _theme_colors()
    pen = QPen(QColor(color) if color else tc["accent"], 2.0)
    p.setPen(pen)
    if shape_name == "circle":
        p.drawEllipse(3, 3, 14, 14)
    elif shape_name == "triangle":
        poly = QPolygonF([QPointF(10, 3), QPointF(17, 17), QPointF(3, 17)])
        p.drawPolygon(poly)
    elif shape_name == "arrow":
        p.drawLine(3, 10, 16, 10)
        p.drawLine(11, 5, 16, 10)
        p.drawLine(11, 15, 16, 10)
    else:
        p.drawRoundedRect(3, 3, 14, 14, 2, 2)
    p.end()
    return QIcon(pm)


def _color_swatch_icon(hex_color):
    pm = QPixmap(16, 16)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    tc = _theme_colors()
    c = QColor(hex_color) if hex_color else tc["accent"]
    p.setBrush(QBrush(c))
    p.setPen(QPen(tc["border"], 1.0))
    p.drawEllipse(1, 1, 14, 14)
    p.end()
    return QIcon(pm)


class EdgeGraphicsItem(QGraphicsPathItem):
    """Cubic Bezier connector edge supporting solid, dash, dot, solid-dashed and color."""

    def __init__(self, edge_id, source_item, target_item, line_type="solid", color="", board_view=None):
        super().__init__()
        self.edge_id = edge_id
        self.source_item = source_item
        self.target_item = target_item
        self.line_type = line_type if any(lt[0] == line_type for lt in LINE_TYPES) else "solid"
        self.color = color or ""
        self.board_view = board_view

        self.setFlags(QGraphicsItem.ItemIsSelectable)
        self.setZValue(1)
        self.updatePosition()

    def setLineType(self, line_type):
        self.line_type = line_type
        self.update()

    def setColor(self, color):
        self.color = color or ""
        self.update()

    def updatePosition(self):
        if not self.source_item or not self.target_item:
            return
        p1 = self.source_item.rightHandleScenePos()
        p2 = self.target_item.leftHandleScenePos()
        dx = max(abs(p2.x() - p1.x()) * 0.5, 40.0)
        path = QPainterPath(p1)
        path.cubicTo(QPointF(p1.x() + dx, p1.y()), QPointF(p2.x() - dx, p2.y()), p2)
        self.setPath(path)

    def shape(self):
        stroker = QPainterPathStroker()
        stroker.setWidth(14.0)
        return stroker.createStroke(self.path())

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing)
        tc = _theme_colors()
        stroke_col = QColor(self.color) if self.color else tc["accent"]

        if self.isSelected():
            glow = QColor(stroke_col)
            glow.setAlpha(85)
            glow_pen = QPen(glow, 6.0, Qt.SolidLine, Qt.RoundCap)
            painter.setPen(glow_pen)
            painter.drawPath(self.path())

        pen = QPen(stroke_col, 2.2, Qt.SolidLine, Qt.RoundCap)
        for lid, _label, pattern in LINE_TYPES:
            if lid == self.line_type and pattern:
                pen.setStyle(Qt.CustomDashLine)
                pen.setDashPattern(pattern)
                break
        painter.setPen(pen)
        painter.drawPath(self.path())

    def to_dict(self):
        return {
            "id": self.edge_id,
            "source": self.source_item.node_id,
            "target": self.target_item.node_id,
            "sourceHandle": None,
            "targetHandle": None,
            "type": "dashed",
            "data": {
                "lineType": self.line_type,
                "color": self.color,
            },
        }


class BaseNodeGraphicsItem(QGraphicsObject):
    """Base draggable whiteboard node with left/right connection handles."""

    WIDTH = 110
    HEIGHT = 76

    def __init__(self, node_id, node_type, pos, data=None, board_view=None):
        super().__init__()
        self.node_id = node_id
        self.node_type = node_type
        self.data = dict(data or {})
        self.board_view = board_view
        self.edges = []
        self._hovered = False

        self.setPos(QPointF(float(pos.get("x", 80)), float(pos.get("y", 120))))
        self.setFlags(
            QGraphicsItem.ItemIsMovable
            | QGraphicsItem.ItemIsSelectable
            | QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        self.setZValue(10)

    def boundingRect(self):
        # Include space above for note popover
        return QRectF(-20, -68, self.WIDTH + 40, self.HEIGHT + 78)

    def nodeRect(self):
        return QRectF(0, 0, self.WIDTH, self.HEIGHT)

    def shape(self):
        path = QPainterPath()
        path.addRoundedRect(self.nodeRect(), 8, 8)
        return path

    def leftHandleScenePos(self):
        return self.mapToScene(QPointF(0, self.HEIGHT / 2.0))

    def rightHandleScenePos(self):
        return self.mapToScene(QPointF(self.WIDTH, self.HEIGHT / 2.0))

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            for edge in list(self.edges):
                edge.updatePosition()
            if self.board_view and not self.board_view._loading:
                self.board_view._onChanged()
        return super().itemChange(change, value)

    def hoverEnterEvent(self, event):
        self._hovered = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self._hovered = False
        self.update()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        if self.board_view and self.board_view.connection_mode:
            self.board_view.handleConnectionNodeClick(self)
            event.accept()
            return
        super().mousePressEvent(event)


class ShapeGraphicsItem(BaseNodeGraphicsItem):
    """Shape node (rectangle, circle, triangle, arrow) with label, note badge & popover, and color."""

    WIDTH = 108
    HEIGHT = 76

    def __init__(self, node_id, pos, data=None, board_view=None):
        super().__init__(node_id, "shape", pos, data, board_view)

    @property
    def shape_kind(self):
        return self.data.get("shape") or "rectangle"

    @property
    def label(self):
        return self.data.get("label") or ""

    @property
    def note(self):
        return self.data.get("note") or ""

    @property
    def color(self):
        return self.data.get("color") or ""

    def mouseDoubleClickEvent(self, event):
        if self.board_view:
            text, ok = QInputDialog.getText(
                self.board_view,
                "Rename Shape",
                "Shape label:",
                QLineEdit.Normal,
                self.label,
            )
            if ok:
                self.board_view.patchNodeData(self.node_id, {"label": text.strip()})
        event.accept()

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing)
        tc = _theme_colors()
        rect = self.nodeRect()

        node_col = QColor(self.color) if self.color else tc["accent"]
        bg = QColor(tc["surface"])
        if self.color:
            # Mix 12% of custom color into surface
            bg = QColor(
                int(bg.red() * 0.88 + node_col.red() * 0.12),
                int(bg.green() * 0.88 + node_col.green() * 0.12),
                int(bg.blue() * 0.88 + node_col.blue() * 0.12),
            )

        border_col = node_col if (self.isSelected() or self.color) else tc["border"]
        if self.isSelected():
            glow = QColor(node_col)
            glow.setAlpha(75)
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(glow, 4.0))
            painter.drawRoundedRect(rect.adjusted(-1, -1, 1, 1), 9, 9)

        painter.setBrush(QBrush(bg))
        painter.setPen(QPen(border_col, 1.5))
        painter.drawRoundedRect(rect, 8, 8)

        # Connection handles
        painter.setBrush(QBrush(node_col))
        painter.setPen(QPen(tc["surface"], 1.5))
        painter.drawEllipse(QPointF(0, self.HEIGHT / 2.0), 4.5, 4.5)
        painter.drawEllipse(QPointF(self.WIDTH, self.HEIGHT / 2.0), 4.5, 4.5)

        # Draw shape icon in center
        cx = self.WIDTH / 2.0
        cy = 28.0
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(node_col, 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        sk = self.shape_kind
        if sk == "circle":
            painter.drawEllipse(QPointF(cx, cy), 14, 14)
        elif sk == "triangle":
            poly = QPolygonF([
                QPointF(cx, cy - 14),
                QPointF(cx + 15, cy + 12),
                QPointF(cx - 15, cy + 12),
            ])
            painter.drawPolygon(poly)
        elif sk == "arrow":
            painter.drawLine(QPointF(cx - 14, cy), QPointF(cx + 14, cy))
            painter.drawLine(QPointF(cx + 5, cy - 8), QPointF(cx + 14, cy))
            painter.drawLine(QPointF(cx + 5, cy + 8), QPointF(cx + 14, cy))
        else:
            painter.drawRoundedRect(QRectF(cx - 14, cy - 14, 28, 28), 3, 3)

        # Label
        if self.label:
            painter.setPen(QPen(tc["text"]))
            font = QFont(painter.font())
            font.setPointSize(9)
            painter.setFont(font)
            lbl_rect = QRectF(6, 46, self.WIDTH - 12, 24)
            painter.drawText(lbl_rect, Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap, self.label)

        # Note badge & popover
        if self.note:
            badge_rect = QRectF(self.WIDTH - 18, 5, 12, 12)
            painter.setBrush(QBrush(node_col))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(badge_rect, 2, 2)

            show_pop = self._hovered or bool(self.data.get("showNotes"))
            if show_pop:
                pop_rect = QRectF(-16, -56, self.WIDTH + 32, 48)
                painter.setBrush(QBrush(tc["surface"]))
                painter.setPen(QPen(node_col, 1.0))
                painter.drawRoundedRect(pop_rect, 6, 6)
                painter.setPen(QPen(tc["text"]))
                f2 = QFont(painter.font())
                f2.setPointSize(8)
                painter.setFont(f2)
                painter.drawText(
                    pop_rect.adjusted(6, 4, -6, -4),
                    Qt.AlignLeft | Qt.AlignVCenter | Qt.TextWordWrap,
                    self.note,
                )

    def to_dict(self):
        return {
            "id": self.node_id,
            "type": "shape",
            "position": {"x": round(self.pos().x(), 2), "y": round(self.pos().y(), 2)},
            "data": {
                "shape": self.shape_kind,
                "label": self.label,
                "note": self.note,
                "color": self.color,
                "showNotes": bool(self.data.get("showNotes", False)),
            },
        }


class NoteGraphicsItem(BaseNodeGraphicsItem):
    """Sticky note node on the whiteboard."""

    WIDTH = 136
    HEIGHT = 68

    def __init__(self, node_id, pos, data=None, board_view=None):
        super().__init__(node_id, "note", pos, data, board_view)

    @property
    def text(self):
        return self.data.get("text") or "Note"

    @property
    def color(self):
        return self.data.get("color") or ""

    def mouseDoubleClickEvent(self, event):
        if self.board_view:
            val, ok = QInputDialog.getText(
                self.board_view,
                "Edit Note",
                "Note text:",
                QLineEdit.Normal,
                self.text,
            )
            if ok and val.strip():
                self.board_view.patchNodeData(self.node_id, {"text": val.strip()})
        event.accept()

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing)
        tc = _theme_colors()
        rect = self.nodeRect()

        node_col = QColor(self.color) if self.color else tc["accent"]
        bg = QColor(tc["surface"])
        if self.color:
            bg = QColor(
                int(bg.red() * 0.85 + node_col.red() * 0.15),
                int(bg.green() * 0.85 + node_col.green() * 0.15),
                int(bg.blue() * 0.85 + node_col.blue() * 0.15),
            )

        border_col = node_col if (self.isSelected() or self.color) else tc["border"]
        painter.setBrush(QBrush(bg))
        painter.setPen(QPen(border_col, 1.5))
        painter.drawRoundedRect(rect, 8, 8)

        painter.setBrush(QBrush(node_col))
        painter.setPen(QPen(tc["surface"], 1.5))
        painter.drawEllipse(QPointF(0, self.HEIGHT / 2.0), 4.5, 4.5)
        painter.drawEllipse(QPointF(self.WIDTH, self.HEIGHT / 2.0), 4.5, 4.5)

        painter.setPen(QPen(tc["text"]))
        font = QFont(painter.font())
        font.setPointSize(9)
        painter.setFont(font)
        painter.drawText(
            rect.adjusted(10, 8, -10, -8),
            Qt.AlignLeft | Qt.AlignVCenter | Qt.TextWordWrap,
            self.text,
        )

    def to_dict(self):
        return {
            "id": self.node_id,
            "type": "note",
            "position": {"x": round(self.pos().x(), 2), "y": round(self.pos().y(), 2)},
            "data": {
                "text": self.text,
                "color": self.color,
            },
        }


class _WhiteboardCanvas(QGraphicsView):
    """QGraphicsView with dot-grid background and zoom/pan support."""

    def __init__(self, scene, board_view):
        super().__init__(scene, board_view)
        self.board_view = board_view
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setFrameShape(QFrame.NoFrame)

    def drawBackground(self, painter, rect):
        tc = _theme_colors()
        painter.fillRect(rect, tc["bg"])
        step = 24
        left = int(rect.left()) - (int(rect.left()) % step)
        top = int(rect.top()) - (int(rect.top()) % step)
        dot_pen = QPen(tc["border"], 2.0, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(dot_pen)
        pts = []
        x = left
        while x < rect.right():
            y = top
            while y < rect.bottom():
                pts.append(QPointF(x, y))
                y += step
            x += step
        if pts:
            painter.drawPoints(*pts)

    def mousePressEvent(self, event):
        item = self.itemAt(event.pos())
        if item is None and self.board_view.connection_mode:
            self.board_view.setConnectionMode(False)
        super().mousePressEvent(event)


class WhiteboardView(QWidget):
    """Main Desktop Whiteboard widget matching the Web App's multi-board whiteboard."""

    changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._loading = False
        self.boards = [self._defaultBoard()]
        self.active_board_id = "default"
        self.connection_mode = False
        self.connect_from_item = None
        self.edge_line_type = "solid"
        self.active_color = ""
        self.selected_node_shape = "rectangle"
        self.show_all_notes = False
        self._zoom = 1.0

        self._node_items = {}
        self._edge_items = []

        self._buildUi()
        self._applyBoard(self.boards[0])

    @staticmethod
    def _defaultBoard(board_id="default", name="Main Board"):
        return {
            "id": board_id,
            "name": name,
            "nodes": [],
            "edges": [],
            "viewport": {"x": 0.0, "y": 0.0, "zoom": 1.0},
            "show_all_notes": False,
        }

    def _buildUi(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Centered Top Toolbar bar
        top_bar = QFrame(self)
        top_bar.setObjectName("whiteboardToolbar")
        top_v = QVBoxLayout(top_bar)
        top_v.setContentsMargins(8, 6, 8, 6)
        top_v.setSpacing(4)

        row1 = QHBoxLayout()
        row1.setSpacing(6)
        row1.addStretch(1)

        # 1. Multi-board selector + CRUD buttons
        self.cmbBoards = QComboBox()
        self.cmbBoards.setMinimumWidth(140)
        self.cmbBoards.setToolTip(self.tr("Switch active whiteboard"))
        self.cmbBoards.activated.connect(self._onBoardComboActivated)
        row1.addWidget(self.cmbBoards)

        self.btnNewBoard = QToolButton()
        self.btnNewBoard.setText("+ Board")
        self.btnNewBoard.setToolTip(self.tr("Create a new whiteboard in this project"))
        self.btnNewBoard.clicked.connect(self.createNewBoardDialog)
        row1.addWidget(self.btnNewBoard)

        self.btnRenameBoard = QToolButton()
        self.btnRenameBoard.setText(self.tr("Rename"))
        self.btnRenameBoard.setToolTip(self.tr("Rename current whiteboard"))
        self.btnRenameBoard.clicked.connect(self.renameActiveBoardDialog)
        row1.addWidget(self.btnRenameBoard)

        self.btnDeleteBoard = QToolButton()
        self.btnDeleteBoard.setText(self.tr("Del Board"))
        self.btnDeleteBoard.setToolTip(self.tr("Delete current whiteboard"))
        self.btnDeleteBoard.clicked.connect(self.deleteActiveBoard)
        row1.addWidget(self.btnDeleteBoard)

        # 2. Add node menu button
        self.btnAddNode = QToolButton()
        self.btnAddNode.setText("+ Add")
        self.btnAddNode.setToolTip(self.tr("Add shape or note node"))
        self.btnAddNode.setPopupMode(QToolButton.InstantPopup)
        add_menu = QMenu(self.btnAddNode)
        for shape_id, label in SHAPES:
            act = add_menu.addAction(_shape_icon(shape_id), self.tr(label))
            act.triggered.connect(lambda _c=False, s=shape_id: self.addNode("shape", "", s))
        add_menu.addSeparator()
        act_note = add_menu.addAction(self.tr("Note"))
        act_note.triggered.connect(lambda: self.addNode("note", "Note"))
        self.btnAddNode.setMenu(add_menu)
        row1.addWidget(self.btnAddNode)

        # 3. Shape type switcher (when a shape is selected)
        self.btnShapeType = QToolButton()
        self.btnShapeType.setIcon(_shape_icon("rectangle"))
        self.btnShapeType.setToolTip(self.tr("Change selected shape type"))
        self.btnShapeType.setPopupMode(QToolButton.InstantPopup)
        shape_menu = QMenu(self.btnShapeType)
        for shape_id, label in SHAPES:
            act = shape_menu.addAction(_shape_icon(shape_id), self.tr(label))
            act.triggered.connect(lambda _c=False, s=shape_id: self.changeSelectedShape(s))
        self.btnShapeType.setMenu(shape_menu)
        row1.addWidget(self.btnShapeType)

        # 4. Line style button (with live preview + connection mode activation)
        self.btnLineStyle = QToolButton()
        self.btnLineStyle.setCheckable(True)
        self.btnLineStyle.setIcon(_line_icon(self.edge_line_type))
        self.btnLineStyle.setToolTip(self.tr("Line style (select to connect nodes or change selected line)"))
        self.btnLineStyle.setPopupMode(QToolButton.InstantPopup)
        line_menu = QMenu(self.btnLineStyle)
        for lid, label, _pat in LINE_TYPES:
            act = line_menu.addAction(_line_icon(lid), self.tr(label))
            act.triggered.connect(lambda _c=False, l=lid: self.selectLineType(l))
        self.btnLineStyle.setMenu(line_menu)
        row1.addWidget(self.btnLineStyle)

        # 5. Color picker button (palette + custom color dialog)
        self.btnColor = QToolButton()
        self.btnColor.setIcon(_color_swatch_icon(""))
        self.btnColor.setToolTip(self.tr("Color for selected shape, note, or line"))
        self.btnColor.setPopupMode(QToolButton.InstantPopup)
        color_menu = QMenu(self.btnColor)
        for cid, label, hex_val in WHITEBOARD_COLORS:
            act = color_menu.addAction(_color_swatch_icon(hex_val), self.tr(label))
            act.triggered.connect(lambda _c=False, c=hex_val: self.selectColor(c))
        color_menu.addSeparator()
        act_custom = color_menu.addAction(self.tr("Custom Color..."))
        act_custom.triggered.connect(self.pickCustomColor)
        self.btnColor.setMenu(color_menu)
        row1.addWidget(self.btnColor)

        # 6. Show notes toggle
        self.btnShowNotes = QToolButton()
        self.btnShowNotes.setCheckable(True)
        self.btnShowNotes.setText(self.tr("Show notes"))
        self.btnShowNotes.setToolTip(self.tr("Toggle showing all shape notes"))
        self.btnShowNotes.clicked.connect(self.toggleShowAllNotes)
        row1.addWidget(self.btnShowNotes)

        # 7. Delete selected
        self.btnDelete = QToolButton()
        self.btnDelete.setText(self.tr("Delete"))
        self.btnDelete.setToolTip(self.tr("Delete selected node or connector line"))
        self.btnDelete.clicked.connect(self.deleteSelected)
        row1.addWidget(self.btnDelete)

        # 8. Zoom controls
        self.btnZoomIn = QToolButton()
        self.btnZoomIn.setText("+")
        self.btnZoomIn.setToolTip(self.tr("Zoom in"))
        self.btnZoomIn.clicked.connect(self.zoomIn)
        row1.addWidget(self.btnZoomIn)

        self.btnZoomOut = QToolButton()
        self.btnZoomOut.setText("-")
        self.btnZoomOut.setToolTip(self.tr("Zoom out"))
        self.btnZoomOut.clicked.connect(self.zoomOut)
        row1.addWidget(self.btnZoomOut)

        self.btnFit = QToolButton()
        self.btnFit.setText(self.tr("Fit"))
        self.btnFit.setToolTip(self.tr("Reset zoom and fit view"))
        self.btnFit.clicked.connect(self.fitView)
        row1.addWidget(self.btnFit)

        row1.addStretch(1)
        top_v.addLayout(row1)

        # Row 2: Inspector for selected shape (Label + Note) or connection hint
        self.inspectorRow = QWidget()
        insp_h = QHBoxLayout(self.inspectorRow)
        insp_h.setContentsMargins(0, 0, 0, 0)
        insp_h.setSpacing(6)
        insp_h.addStretch(1)

        self.lblHint = QLabel("")
        self.lblHint.setVisible(False)
        insp_h.addWidget(self.lblHint)

        self.txtShapeLabel = QLineEdit()
        self.txtShapeLabel.setPlaceholderText(self.tr("Shape label..."))
        self.txtShapeLabel.setMaximumWidth(180)
        self.txtShapeLabel.textEdited.connect(self._onInspectorLabelEdited)
        insp_h.addWidget(self.txtShapeLabel)

        self.txtShapeNote = QLineEdit()
        self.txtShapeNote.setPlaceholderText(self.tr("Add shape note..."))
        self.txtShapeNote.setMaximumWidth(240)
        self.txtShapeNote.textEdited.connect(self._onInspectorNoteEdited)
        insp_h.addWidget(self.txtShapeNote)

        insp_h.addStretch(1)
        top_v.addWidget(self.inspectorRow)

        outer.addWidget(top_bar)

        # Scene & Canvas
        self.scene = QGraphicsScene(self)
        self.scene.setSceneRect(-1000, -1000, 3000, 3000)
        self.scene.selectionChanged.connect(self._onSelectionChanged)
        self.canvas = _WhiteboardCanvas(self.scene, self)
        outer.addWidget(self.canvas, 1)

        self._updateInspectorVisibility()

    # ------------------------------------------------------------------ Board CRUD
    def _refreshBoardCombo(self):
        self.cmbBoards.blockSignals(True)
        self.cmbBoards.clear()
        idx = 0
        for i, b in enumerate(self.boards):
            self.cmbBoards.addItem(b["name"], b["id"])
            if b["id"] == self.active_board_id:
                idx = i
        self.cmbBoards.setCurrentIndex(idx)
        self.cmbBoards.blockSignals(False)
        self.btnDeleteBoard.setEnabled(len(self.boards) > 1)

    def _syncActiveBoardDict(self):
        nodes_data = [item.to_dict() for item in self._node_items.values()]
        edges_data = [edge.to_dict() for edge in self._edge_items]
        for b in self.boards:
            if b["id"] == self.active_board_id:
                b["nodes"] = nodes_data
                b["edges"] = edges_data
                b["viewport"] = {"x": 0.0, "y": 0.0, "zoom": round(self._zoom, 2)}
                b["show_all_notes"] = bool(self.show_all_notes)
                break

    def _applyBoard(self, board):
        self._loading = True
        try:
            self.active_board_id = board["id"]
            self.show_all_notes = bool(board.get("show_all_notes", False))
            self.btnShowNotes.setChecked(self.show_all_notes)
            self.setConnectionMode(False)

            self.scene.clear()
            self._node_items = {}
            self._edge_items = []

            for n in board.get("nodes", []):
                nid = n.get("id") or f"node_{uuid.uuid4().hex[:6]}"
                ntype = n.get("type", "shape")
                pos = n.get("position") or {"x": 80, "y": 120}
                ndata = dict(n.get("data") or {})
                ndata["showNotes"] = self.show_all_notes
                if ntype == "note":
                    item = NoteGraphicsItem(nid, pos, ndata, self)
                else:
                    item = ShapeGraphicsItem(nid, pos, ndata, self)
                self.scene.addItem(item)
                self._node_items[nid] = item

            for e in board.get("edges", []):
                eid = e.get("id") or f"edge_{uuid.uuid4().hex[:6]}"
                src = self._node_items.get(e.get("source"))
                tgt = self._node_items.get(e.get("target"))
                if src and tgt:
                    edata = e.get("data") or {}
                    lt = edata.get("lineType", "solid")
                    col = edata.get("color", "")
                    edge_item = EdgeGraphicsItem(eid, src, tgt, lt, col, self)
                    src.edges.append(edge_item)
                    tgt.edges.append(edge_item)
                    self.scene.addItem(edge_item)
                    self._edge_items.append(edge_item)

            vp = board.get("viewport") or {}
            self._zoom = float(vp.get("zoom", 1.0)) or 1.0
            self.canvas.resetTransform()
            self.canvas.scale(self._zoom, self._zoom)

            self._refreshBoardCombo()
            self._updateInspectorVisibility()
        finally:
            self._loading = False

    def switchBoard(self, board_id):
        if board_id == self.active_board_id:
            return
        self._syncActiveBoardDict()
        for b in self.boards:
            if b["id"] == board_id:
                self._applyBoard(b)
                self._onChanged()
                return

    def _onBoardComboActivated(self, index):
        bid = self.cmbBoards.itemData(index)
        if bid:
            self.switchBoard(bid)

    def createNewBoard(self, name):
        clean = (name or "").strip()
        if not clean:
            return None
        self._syncActiveBoardDict()
        bid = f"board_{int(time.time() * 1000)}_{uuid.uuid4().hex[:4]}"
        new_board = self._defaultBoard(bid, clean)
        self.boards.append(new_board)
        self._applyBoard(new_board)
        self._onChanged()
        return bid

    def createNewBoardDialog(self):
        name, ok = QInputDialog.getText(
            self,
            self.tr("New Whiteboard"),
            self.tr("Whiteboard name:"),
            QLineEdit.Normal,
            f"Board {len(self.boards) + 1}",
        )
        if ok and name.strip():
            self.createNewBoard(name.strip())

    def renameActiveBoard(self, new_name):
        clean = (new_name or "").strip()
        if not clean:
            return
        for b in self.boards:
            if b["id"] == self.active_board_id:
                b["name"] = clean
                break
        self._refreshBoardCombo()
        self._onChanged()

    def renameActiveBoardDialog(self):
        cur = next((b["name"] for b in self.boards if b["id"] == self.active_board_id), "Main Board")
        name, ok = QInputDialog.getText(
            self,
            self.tr("Rename Whiteboard"),
            self.tr("New name:"),
            QLineEdit.Normal,
            cur,
        )
        if ok and name.strip():
            self.renameActiveBoard(name.strip())

    def deleteActiveBoard(self):
        if len(self.boards) <= 1:
            return
        self.boards = [b for b in self.boards if b["id"] != self.active_board_id]
        self._applyBoard(self.boards[0])
        self._onChanged()

    # ------------------------------------------------------------------ Node & Edge Operations
    def _nextPosition(self, index):
        col = index % 4
        row = index // 4
        return {"x": 80 + col * 150, "y": 120 + row * 120}

    def addNode(self, node_type="shape", label="", shape_override=None):
        nid = f"node_{int(time.time() * 1000)}_{uuid.uuid4().hex[:4]}"
        pos = self._nextPosition(len(self._node_items))
        shape = shape_override or self.selected_node_shape
        self.setConnectionMode(False)
        self.scene.clearSelection()

        if node_type == "note":
            data = {"text": label or "Note", "color": self.active_color}
            item = NoteGraphicsItem(nid, pos, data, self)
        else:
            data = {
                "shape": shape,
                "label": label or "",
                "note": "",
                "color": self.active_color,
                "showNotes": self.show_all_notes,
            }
            item = ShapeGraphicsItem(nid, pos, data, self)
            self.selected_node_shape = shape
            self.btnShapeType.setIcon(_shape_icon(shape, self.active_color))

        self.scene.addItem(item)
        self._node_items[nid] = item
        item.setSelected(True)
        self._onChanged()
        return item

    def addEdge(self, source_id, target_id, line_type=None, color=None):
        if source_id == target_id:
            return None
        src = self._node_items.get(source_id)
        tgt = self._node_items.get(target_id)
        if not src or not tgt:
            return None
        eid = f"edge_{int(time.time() * 1000)}_{uuid.uuid4().hex[:4]}"
        lt = line_type or self.edge_line_type
        col = self.active_color if color is None else color
        edge = EdgeGraphicsItem(eid, src, tgt, lt, col, self)
        src.edges.append(edge)
        tgt.edges.append(edge)
        self.scene.addItem(edge)
        self._edge_items.append(edge)
        self._onChanged()
        return edge

    def selectedNodeItem(self):
        for item in self.scene.selectedItems():
            if isinstance(item, BaseNodeGraphicsItem):
                return item
        return None

    def selectedEdgeItem(self):
        for item in self.scene.selectedItems():
            if isinstance(item, EdgeGraphicsItem):
                return item
        return None

    def patchNodeData(self, node_id, patch):
        item = self._node_items.get(node_id)
        if not item:
            return
        item.data.update(patch)
        item.update()
        self._updateInspectorVisibility()
        self._onChanged()

    def changeSelectedShape(self, shape_name):
        self.selected_node_shape = shape_name
        self.btnShapeType.setIcon(_shape_icon(shape_name, self.active_color))
        node = self.selectedNodeItem()
        if isinstance(node, ShapeGraphicsItem):
            self.patchNodeData(node.node_id, {"shape": shape_name})

    def selectLineType(self, line_type):
        self.edge_line_type = line_type
        self.btnLineStyle.setIcon(_line_icon(line_type, self.active_color))
        edge = self.selectedEdgeItem()
        if edge:
            edge.setLineType(line_type)
            self._onChanged()
        self.setConnectionMode(True)

    def setConnectionMode(self, enabled):
        self.connection_mode = bool(enabled)
        self.connect_from_item = None
        self.btnLineStyle.setChecked(self.connection_mode)
        self._updateInspectorVisibility()

    def handleConnectionNodeClick(self, node_item):
        if not self.connection_mode:
            return
        if self.connect_from_item is None:
            self.connect_from_item = node_item
            self.scene.clearSelection()
            node_item.setSelected(True)
            self._updateInspectorVisibility()
            return
        if self.connect_from_item is not node_item:
            self.addEdge(self.connect_from_item.node_id, node_item.node_id)
            self.connect_from_item = None
            self._updateInspectorVisibility()

    def selectColor(self, color_hex):
        self.active_color = color_hex or ""
        self.btnColor.setIcon(_color_swatch_icon(self.active_color))
        self.btnShapeType.setIcon(_shape_icon(self.selected_node_shape, self.active_color))
        self.btnLineStyle.setIcon(_line_icon(self.edge_line_type, self.active_color))

        node = self.selectedNodeItem()
        if node:
            self.patchNodeData(node.node_id, {"color": self.active_color})
            return
        edge = self.selectedEdgeItem()
        if edge:
            edge.setColor(self.active_color)
            self._onChanged()

    def pickCustomColor(self):
        start = QColor(self.active_color) if self.active_color else _theme_colors()["accent"]
        col = QColorDialog.getColor(start, self, self.tr("Select Color"))
        if col.isValid():
            self.selectColor(col.name())

    def toggleShowAllNotes(self):
        self.show_all_notes = not self.show_all_notes
        self.btnShowNotes.setChecked(self.show_all_notes)
        for item in self._node_items.values():
            item.data["showNotes"] = self.show_all_notes
            item.update()
        self._onChanged()

    def deleteSelected(self):
        edge = self.selectedEdgeItem()
        if edge:
            if edge in edge.source_item.edges:
                edge.source_item.edges.remove(edge)
            if edge in edge.target_item.edges:
                edge.target_item.edges.remove(edge)
            self.scene.removeItem(edge)
            if edge in self._edge_items:
                self._edge_items.remove(edge)
            self._onChanged()
            return

        node = self.selectedNodeItem()
        if node:
            for e in list(node.edges):
                if e.source_item and e in e.source_item.edges:
                    e.source_item.edges.remove(e)
                if e.target_item and e in e.target_item.edges:
                    e.target_item.edges.remove(e)
                self.scene.removeItem(e)
                if e in self._edge_items:
                    self._edge_items.remove(e)
            self.scene.removeItem(node)
            self._node_items.pop(node.node_id, None)
            if self.connect_from_item is node:
                self.connect_from_item = None
            self._updateInspectorVisibility()
            self._onChanged()

    def zoomIn(self):
        self._zoom = min(2.0, self._zoom * 1.2)
        self.canvas.resetTransform()
        self.canvas.scale(self._zoom, self._zoom)
        self._onChanged()

    def zoomOut(self):
        self._zoom = max(0.5, self._zoom / 1.2)
        self.canvas.resetTransform()
        self.canvas.scale(self._zoom, self._zoom)
        self._onChanged()

    def fitView(self):
        self._zoom = 1.0
        self.canvas.resetTransform()
        self.canvas.centerOn(250, 200)
        self._onChanged()

    # ------------------------------------------------------------------ Inspector & Selection
    def _onSelectionChanged(self):
        if self._loading or self.connection_mode:
            return
        node = self.selectedNodeItem()
        if isinstance(node, ShapeGraphicsItem):
            self.selected_node_shape = node.shape_kind
            self.active_color = node.color
            self.btnShapeType.setIcon(_shape_icon(self.selected_node_shape, self.active_color))
            self.btnColor.setIcon(_color_swatch_icon(self.active_color))
        elif isinstance(node, NoteGraphicsItem):
            self.active_color = node.color
            self.btnColor.setIcon(_color_swatch_icon(self.active_color))
        else:
            edge = self.selectedEdgeItem()
            if edge:
                self.edge_line_type = edge.line_type
                self.active_color = edge.color
                self.btnLineStyle.setIcon(_line_icon(self.edge_line_type, self.active_color))
                self.btnColor.setIcon(_color_swatch_icon(self.active_color))
        self._updateInspectorVisibility()

    def _updateInspectorVisibility(self):
        if self.connection_mode:
            self.lblHint.setVisible(True)
            self.lblHint.setText(
                self.tr("Click target node to link")
                if self.connect_from_item
                else self.tr("Click first node to link")
            )
            self.txtShapeLabel.setVisible(False)
            self.txtShapeNote.setVisible(False)
            self.inspectorRow.setVisible(True)
            return

        self.lblHint.setVisible(False)
        node = self.selectedNodeItem()
        if isinstance(node, ShapeGraphicsItem):
            self.txtShapeLabel.blockSignals(True)
            self.txtShapeNote.blockSignals(True)
            self.txtShapeLabel.setText(node.label)
            self.txtShapeNote.setText(node.note)
            self.txtShapeLabel.blockSignals(False)
            self.txtShapeNote.blockSignals(False)
            self.txtShapeLabel.setVisible(True)
            self.txtShapeNote.setVisible(True)
            self.inspectorRow.setVisible(True)
        else:
            self.txtShapeLabel.setVisible(False)
            self.txtShapeNote.setVisible(False)
            self.inspectorRow.setVisible(False)

    def _onInspectorLabelEdited(self, text):
        node = self.selectedNodeItem()
        if isinstance(node, ShapeGraphicsItem):
            node.data["label"] = text
            node.update()
            self._onChanged()

    def _onInspectorNoteEdited(self, text):
        node = self.selectedNodeItem()
        if isinstance(node, ShapeGraphicsItem):
            node.data["note"] = text
            node.update()
            self._onChanged()

    # ------------------------------------------------------------------ Serialization (`whiteboards.json`)
    def _onChanged(self):
        if not self._loading:
            self._syncActiveBoardDict()
            self.changed.emit()

    def toDict(self):
        self._syncActiveBoardDict()
        return {
            "active_board_id": self.active_board_id,
            "boards": self.boards,
        }

    def saveJson(self):
        return json.dumps(self.toDict(), indent=2)

    def clearBoards(self):
        self.boards = [self._defaultBoard()]
        self.active_board_id = "default"
        self._applyBoard(self.boards[0])

    def loadJson(self, raw_json):
        if not raw_json or not str(raw_json).strip():
            self.clearBoards()
            return
        try:
            data = json.loads(raw_json)
            if not isinstance(data, dict) or not data.get("boards"):
                self.clearBoards()
                return
            loaded_boards = []
            for b in data["boards"]:
                if isinstance(b, dict) and b.get("id") and b.get("name"):
                    loaded_boards.append({
                        "id": str(b["id"]),
                        "name": str(b["name"]),
                        "nodes": list(b.get("nodes") or []),
                        "edges": list(b.get("edges") or []),
                        "viewport": dict(b.get("viewport") or {"x": 0.0, "y": 0.0, "zoom": 1.0}),
                        "show_all_notes": bool(b.get("show_all_notes", False)),
                    })
            if not loaded_boards:
                self.clearBoards()
                return
            self.boards = loaded_boards
            active_id = str(data.get("active_board_id") or loaded_boards[0]["id"])
            target = next((b for b in self.boards if b["id"] == active_id), self.boards[0])
            self._applyBoard(target)
        except Exception:
            self.clearBoards()
