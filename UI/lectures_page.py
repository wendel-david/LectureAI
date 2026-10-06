from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QScrollArea, QVBoxLayout, QWidget,
)

from UI import styles
from UI.helpers import format_date
from UI.icons import dot_icon, icon
from UI.widgets import Clickable, IconSquare, StatusPill, button, icon_label, lecture_state

# Column proportions shared by the header and the rows: name, date, status
COLUMNS = (9, 6, 4)


class LectureRow(Clickable):
    def __init__(self, lecture, state):
        super().__init__("tableRow")
        self.setFixedHeight(66)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(21, 0, 22, 0)
        layout.setSpacing(0)

        name = QHBoxLayout()
        name.setSpacing(13)
        name.addWidget(IconSquare("waveform"))
        title = QLabel(lecture["title"])
        title.setObjectName("rowTitle")
        name.addWidget(title, stretch=1)
        layout.addLayout(name, COLUMNS[0])

        date = QLabel(format_date(lecture["created_at"]))
        date.setObjectName("rowText")
        layout.addWidget(date, COLUMNS[1])

        status = QHBoxLayout()
        status.addWidget(StatusPill(state))
        status.addStretch()
        layout.addLayout(status, COLUMNS[2])

        layout.addWidget(icon_label("chevron-right", styles.TEXT_FAINT))


class LecturesPage(QWidget):
    lecture_opened = Signal(int)
    new_recording_requested = Signal()

    def __init__(self, controller):
        super().__init__()
        self.controller = controller

        layout = QVBoxLayout(self)
        layout.setContentsMargins(42, 34, 42, 40)
        layout.setSpacing(0)

        header = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(4)
        title = QLabel("Lectures")
        title.setObjectName("pageTitle")
        titles.addWidget(title)
        self.count_label = QLabel()
        self.count_label.setObjectName("muted")
        self.count_label.setStyleSheet("font-size: 15px;")
        titles.addWidget(self.count_label)
        header.addLayout(titles)
        header.addStretch()
        new_recording = button("  Nova gravação")
        new_recording.setIcon(dot_icon(styles.RED_DOT, 8))
        new_recording.setIconSize(QSize(8, 8))
        new_recording.setStyleSheet("padding: 10px 16px; font-size: 15px;")
        new_recording.clicked.connect(self.new_recording_requested)
        header.addWidget(new_recording, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addLayout(header)
        layout.addSpacing(22)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar pelo nome")
        self.search.addAction(icon("search", styles.TEXT_MUTED), QLineEdit.ActionPosition.LeadingPosition)
        self.search.setMaximumWidth(438)
        self.search.textChanged.connect(self.refresh)
        layout.addWidget(self.search)
        layout.addSpacing(24)

        self.table = QFrame()
        self.table.setObjectName("table")
        table_layout = QVBoxLayout(self.table)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(0)
        table_layout.addWidget(self._build_header())

        self.rows_layout = QVBoxLayout()
        self.rows_layout.setSpacing(0)
        table_layout.addLayout(self.rows_layout)

        # The table is only as tall as its rows; the area around it scrolls
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(self.table)
        container_layout.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(container)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(scroll, stretch=1)

        self.empty_label = QLabel()
        self.empty_label.setObjectName("muted")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setContentsMargins(0, 28, 0, 28)

        controller.lectures_changed.connect(self.refresh)
        controller.lecture_changed.connect(lambda _id: self.refresh())
        self.refresh()

    def _build_header(self):
        header = QFrame()
        header.setObjectName("tableHeader")
        header.setFixedHeight(43)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(21, 0, 22, 0)
        layout.setSpacing(0)
        for text, stretch in zip(("Nome", "Gravada em", "Status"), COLUMNS):
            label = QLabel(text)
            label.setObjectName("columnLabel")
            layout.addWidget(label, stretch)
        layout.addSpacing(16)
        return header

    def refresh(self):
        query = self.search.text().strip().lower()
        lectures = self.controller.db.list_lectures()
        self.count_label.setText(f"{len(lectures)} gravação" if len(lectures) == 1 else f"{len(lectures)} gravações")

        while self.rows_layout.count():
            item = self.rows_layout.takeAt(0)
            widget = item.widget()
            if widget is not None and widget is not self.empty_label:
                widget.hide()
                widget.deleteLater()

        shown = 0
        for lecture in lectures:
            if query and query not in lecture["title"].lower():
                continue
            state = lecture_state(lecture["has_transcription"], lecture["id"] in self.controller.transcribing)
            row = LectureRow(lecture, state)
            row.clicked.connect(lambda i=lecture["id"]: self.lecture_opened.emit(i))
            self.rows_layout.addWidget(row)
            shown += 1

        if not shown:
            self.empty_label.setText(
                "Nenhuma lecture encontrada." if lectures else "Nenhuma lecture ainda. Clique em Nova gravação para começar."
            )
            self.rows_layout.addWidget(self.empty_label)
