"""Small reusable pieces of the LectureAI design."""

from pathlib import Path

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QRadialGradient
from PySide6.QtWidgets import (
    QAbstractButton, QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QWidget,
)

from UI import styles
from UI.icons import icon, pixmap

AUDIO_EXTENSIONS = {".m4a", ".mp3", ".wav", ".flac", ".ogg", ".aac", ".mp4"}


def repolish(widget):
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def divider() -> QFrame:
    line = QFrame()
    line.setObjectName("divider")
    return line


def icon_label(name: str, color: str = styles.TEXT, size: int = 16) -> QLabel:
    label = QLabel()
    label.setPixmap(pixmap(name, color, size))
    label.setFixedSize(size, size)
    return label


def button(text: str, kind: str = None, icon_name: str = None, icon_color: str = None) -> QPushButton:
    """kind: None (black primary), 'secondary', 'danger', 'flat', 'link' or 'iconButton'."""
    # Qt has no icon-to-text gap setting, so a leading space provides it
    result = QPushButton(f" {text}" if icon_name and text else text)
    if kind:
        result.setObjectName(kind)
    if icon_name:
        default_color = {None: "white", "danger": styles.RED}.get(kind, styles.TEXT)
        result.setIcon(icon(icon_name, icon_color or default_color))
        result.setIconSize(QSize(16, 16))
    result.setCursor(Qt.CursorShape.PointingHandCursor)
    return result


class Clickable(QFrame):
    clicked = Signal()

    def __init__(self, object_name: str):
        super().__init__()
        self.setObjectName(object_name)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mouseReleaseEvent(self, event):
        if self.isEnabled() and event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self.clicked.emit()


class StatusPill(QLabel):
    STATES = {
        "done": ("Transcrita", styles.GREEN),
        "working": ("Transcrevendo", styles.AMBER),
        "none": ("Sem transcrição", styles.TEXT_FAINT),
    }

    def __init__(self, state: str = "done"):
        super().__init__()
        self.setObjectName("pill")
        self.setFixedHeight(22)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.set_state(state)

    def set_state(self, state: str):
        text, dot = self.STATES[state]
        self.setText(f'<span style="color:{dot}">●</span>&nbsp; {text}')
        self.setProperty("state", state)
        repolish(self)


def lecture_state(has_transcription: bool, transcribing: bool) -> str:
    if has_transcription:
        return "done"
    return "working" if transcribing else "none"


class IconSquare(QLabel):
    """Rounded square holding an icon: soft blue normally, solid blue when selected."""

    def __init__(self, icon_name: str, size: int = 34):
        super().__init__()
        self.icon_name = icon_name
        self.setObjectName("iconSquare")
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.set_selected(False)

    def set_selected(self, selected: bool):
        self.setPixmap(pixmap(self.icon_name, "white" if selected else styles.BLUE, 16))
        self.setProperty("selected", selected)
        repolish(self)


class SegmentedTabs(QFrame):
    changed = Signal(int)

    def __init__(self, tabs):
        """tabs: list of (label, icon name)."""
        super().__init__()
        self.setObjectName("segmented")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        self.buttons = []
        for i, (label, icon_name) in enumerate(tabs):
            segment = QPushButton(f" {label}")
            segment.setObjectName("segment")
            segment.setCheckable(True)
            segment.setCursor(Qt.CursorShape.PointingHandCursor)
            segment.setIconSize(QSize(16, 16))
            segment.icon_name = icon_name
            segment.clicked.connect(lambda _=False, i=i: self.set_current(i, emit=True))
            # Reserve room for the bold checked state so the label never gets clipped
            bold = segment.font()
            bold.setBold(True)
            segment.setMinimumWidth(QFontMetrics(bold).horizontalAdvance(segment.text()) + 56)
            layout.addWidget(segment)
            self.buttons.append(segment)
        self.set_current(0)

    def set_current(self, index: int, emit=False):
        for i, segment in enumerate(self.buttons):
            segment.setChecked(i == index)
            segment.setIcon(icon(segment.icon_name, styles.BLUE if i == index else styles.TEXT_MUTED))
        if emit:
            self.changed.emit(index)


class LevelBars(QWidget):
    """A row of small bars that light up with the microphone level."""

    def __init__(self, bars: int = 12):
        super().__init__()
        self.bars = bars
        self.level = 0.0
        self.setFixedSize(bars * 6, 10)

    def set_level(self, level: float):
        # Rise instantly, fall gently so the bars don't flicker
        self.level = level if level > self.level else self.level * 0.8 + level * 0.2
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        lit = round(self.level * self.bars)
        for i in range(self.bars):
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(styles.BLUE if i < lit else "#D9DCE1"))
            painter.drawRoundedRect(QRectF(i * 6 + 1, 2, 3, 6), 1.5, 1.5)


class RecordButton(QAbstractButton):
    """Black disc with a red dot inside a soft ring; the dot turns into a stop square while recording."""

    def __init__(self):
        super().__init__()
        self.recording = False
        self.setFixedSize(232, 232)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)

    def set_recording(self, recording: bool):
        self.recording = recording
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        center = self.rect().center()
        cx, cy = center.x() + 0.5, center.y() + 0.5

        # Outer ring
        ring = QColor("#FDECEC") if self.recording else QColor("#F4F5F7")
        painter.setPen(QColor("#FADADA") if self.recording else QColor("#ECEDEF"))
        painter.setBrush(ring)
        painter.drawEllipse(QRectF(cx - 114, cy - 114, 228, 228))

        # Soft shadow under the disc
        shadow = QRadialGradient(cx, cy + 10, 84)
        shadow.setColorAt(0.75, QColor(0, 0, 0, 40))
        shadow.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(shadow)
        painter.drawEllipse(QRectF(cx - 84, cy - 74, 168, 168))

        # Disc
        hovered = self.underMouse()
        painter.setBrush(QColor("#25282E" if hovered else styles.TEXT))
        painter.drawEllipse(QRectF(cx - 69, cy - 69, 138, 138))

        # Dot or stop square
        painter.setBrush(QColor(styles.RED_DOT))
        if self.recording:
            painter.drawRoundedRect(QRectF(cx - 15, cy - 15, 30, 30), 6, 6)
        else:
            painter.drawEllipse(QRectF(cx - 18, cy - 18, 36, 36))


class DropZone(Clickable):
    """Dashed box that opens a file picker on click and accepts dropped audio files."""

    file_dropped = Signal(Path)

    def __init__(self):
        super().__init__("dropZone")
        self.setAcceptDrops(True)
        self.setFixedHeight(66)

        layout = QHBoxLayout(self)
        layout.addStretch()
        layout.addWidget(icon_label("upload", styles.BLUE))
        layout.addSpacing(6)
        text = QLabel(f'Importar arquivo de áudio <span style="color:{styles.TEXT_MUTED}">ou arraste aqui</span>')
        text.setStyleSheet("font-size: 15px;")
        layout.addWidget(text)
        layout.addStretch()

    def _audio_path(self, event):
        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())
            if path.suffix.lower() in AUDIO_EXTENSIONS:
                return path
        return None

    def _set_dragging(self, dragging: bool):
        self.setProperty("dragging", dragging)
        repolish(self)

    def dragEnterEvent(self, event):
        if self._audio_path(event):
            event.acceptProposedAction()
            self._set_dragging(True)

    def dragLeaveEvent(self, event):
        self._set_dragging(False)

    def dropEvent(self, event):
        self._set_dragging(False)
        path = self._audio_path(event)
        if path:
            self.file_dropped.emit(path)
