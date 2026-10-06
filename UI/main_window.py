from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)

from UI import styles
from UI.controller import Controller
from UI.icons import dot_icon, icon, pixmap
from UI.lecture_page import LecturePage
from UI.lectures_page import LecturesPage
from UI.record_page import RecordPage
from UI.settings_page import SettingsPage

RECENT_COUNT = 5


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LectureAI")
        self.resize(1320, 880)
        self.setMinimumSize(1000, 680)

        self.controller = Controller()
        self._active = None
        self.controller.error.connect(lambda message: QMessageBox.warning(self, "LectureAI", message))

        self.record_page = RecordPage(self.controller)
        self.lectures_page = LecturesPage(self.controller)
        self.lecture_page = LecturePage(self.controller)
        self.settings_page = SettingsPage()

        self.stack = QStackedWidget()
        self.stack.setObjectName("content")
        for page in (self.record_page, self.lectures_page, self.lecture_page, self.settings_page):
            page.setObjectName("page")
            self.stack.addWidget(page)

        root = QWidget()
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_sidebar())
        layout.addWidget(self.stack, stretch=1)
        self.setCentralWidget(root)

        self.record_page.lecture_created.connect(self.open_lecture)
        self.lectures_page.lecture_opened.connect(self.open_lecture)
        self.lectures_page.new_recording_requested.connect(self.show_record)
        self.lecture_page.back_requested.connect(self.show_lectures)
        self.settings_page.input_device_changed.connect(self.record_page.update_input_device)
        self.controller.lectures_changed.connect(self._refresh_recents)
        self.controller.lecture_changed.connect(lambda _id: self._refresh_recents())

        self.show_record()

    # Sidebar

    def _build_sidebar(self):
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        sidebar.setFixedWidth(242)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(14, 24, 14, 16)
        layout.setSpacing(4)

        logo = QHBoxLayout()
        logo.setContentsMargins(9, 0, 0, 0)
        logo.setSpacing(11)
        mark = QLabel()
        mark.setFixedSize(31, 31)
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mark.setStyleSheet(f"background: {styles.TEXT}; border-radius: 8px;")
        mark.setPixmap(pixmap("waveform", "white", 15, 2.2))
        logo.addWidget(mark)
        name = QLabel("LectureAI")
        name.setObjectName("logoText")
        logo.addWidget(name)
        logo.addStretch()
        layout.addLayout(logo)
        layout.addSpacing(22)

        self.nav_buttons = {}
        self.record_nav = self._nav_button("record", "Gravar", "mic", self.show_record)
        self.lectures_nav = self._nav_button("lectures", "Lectures", "lines", self.show_lectures)
        layout.addWidget(self.record_nav)
        layout.addWidget(self.lectures_nav)

        layout.addSpacing(26)
        self.recents_label = QLabel("Recentes")
        self.recents_label.setObjectName("sidebarSection")
        self.recents_label.setContentsMargins(11, 0, 0, 6)
        layout.addWidget(self.recents_label)
        self.recents_layout = QVBoxLayout()
        self.recents_layout.setSpacing(2)
        layout.addLayout(self.recents_layout)

        layout.addStretch()
        self.settings_nav = self._nav_button("settings", "Configurações", "settings", self.show_settings)
        layout.addWidget(self.settings_nav)

        self._refresh_recents()
        return sidebar

    def _nav_button(self, key, text, icon_name, handler):
        nav = QPushButton(f" {text}")
        nav.setObjectName("navButton")
        nav.setCheckable(True)
        nav.setCursor(Qt.CursorShape.PointingHandCursor)
        nav.setIconSize(QSize(18, 18))
        nav.icon_name = icon_name
        nav.clicked.connect(handler)
        self.nav_buttons[key] = nav
        return nav

    def _refresh_recents(self):
        while self.recents_layout.count():
            widget = self.recents_layout.takeAt(0).widget()
            self.nav_buttons.pop(widget.nav_key, None)
            widget.hide()
            widget.deleteLater()

        lectures = self.controller.db.list_lectures()[:RECENT_COUNT]
        for lecture in lectures:
            if lecture["has_transcription"]:
                color = styles.GREEN
            elif lecture["id"] in self.controller.transcribing:
                color = styles.AMBER
            else:
                color = styles.TEXT_FAINT

            key = f"lecture:{lecture['id']}"
            recent = QPushButton(f"  {lecture['title']}")
            recent.setObjectName("navButton")
            recent.setCheckable(True)
            recent.setCursor(Qt.CursorShape.PointingHandCursor)
            recent.setIcon(dot_icon(color))
            recent.setIconSize(QSize(6, 6))
            recent.setStyleSheet("font-size: 15px;")
            recent.nav_key = key
            recent.icon_name = None
            recent.clicked.connect(lambda _=False, i=lecture["id"]: self.open_lecture(i))
            self.recents_layout.addWidget(recent)
            self.nav_buttons[key] = recent

        self.recents_label.setVisible(bool(lectures))
        self._set_active(self._active)

    def _set_active(self, key):
        self._active = key
        for nav_key, nav in self.nav_buttons.items():
            active = nav_key == key
            nav.setChecked(active)
            if nav.icon_name:
                nav.setIcon(icon(nav.icon_name, styles.BLUE if active else "#4B5563", 18))

    # Navigation

    def show_record(self):
        self._set_active("record")
        self.stack.setCurrentWidget(self.record_page)

    def show_lectures(self):
        self._set_active("lectures")
        self.lectures_page.refresh()
        self.stack.setCurrentWidget(self.lectures_page)

    def show_settings(self):
        self._set_active("settings")
        self.stack.setCurrentWidget(self.settings_page)

    def open_lecture(self, lecture_id: int):
        self._set_active(f"lecture:{lecture_id}")
        self.lecture_page.show_lecture(lecture_id)
        self.stack.setCurrentWidget(self.lecture_page)

    def closeEvent(self, event):
        if self.record_page.is_recording():
            answer = QMessageBox.question(
                self, "Fechar LectureAI",
                "Uma gravação está em andamento e será descartada. Fechar mesmo assim?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self.record_page.stop()

        if self.controller.has_running_jobs():
            answer = QMessageBox.question(
                self, "Fechar LectureAI",
                "Há transcrições ou comandos da IA em andamento. O app vai esperar os que já "
                "começaram terminarem e salvarem antes de sair. Os que estão na fila podem ser "
                "refeitos depois. Fechar?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return

        self.hide()
        self.controller.shutdown()
        event.accept()
