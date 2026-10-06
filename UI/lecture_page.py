import html
from pathlib import Path

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QFrame, QHBoxLayout, QInputDialog, QLabel, QListWidget, QListWidgetItem,
    QMessageBox, QStackedWidget, QTextBrowser, QVBoxLayout, QWidget,
)

from SETTINGS import InstructionsMap, QuizMap
from UI import styles
from UI.audio_player import AudioPlayer
from UI.controller import PROJECT_ROOT
from UI.helpers import action_info, format_date, format_relative, transcript_paragraphs
from UI.quiz_view import QuizView
from UI.widgets import (
    Clickable, IconSquare, SegmentedTabs, StatusPill, button, divider, icon_label, lecture_state,
)

QUIZ_KEY = QuizMap["instruction"]


class TranscriptView(QTextBrowser):
    """Transcript text in a centered reading column."""

    COLUMN = 720

    def resizeEvent(self, event):
        side = max(28, (self.width() - self.COLUMN) // 2)
        self.setViewportMargins(side, 0, side, 0)
        super().resizeEvent(event)

    def set_transcript(self, text: str):
        paragraphs = "".join(
            f"<p style='line-height:170%; margin:0 0 16px 0'>{html.escape(p)}</p>"
            for p in transcript_paragraphs(text)
        )
        self.setHtml(f"<div style='font-size:16px; color:{styles.TEXT}'>{paragraphs}</div>")
        self.document().setDocumentMargin(32)


class ActionCard(Clickable):
    def __init__(self, instruction: str):
        super().__init__("actionCard")
        self.instruction = instruction
        title, self.subtitle_text, icon_name, _ = action_info(instruction)
        self.setFixedHeight(62)
        self.setToolTip(InstructionsMap[instruction])

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(12)
        self.icon_square = IconSquare(icon_name)
        layout.addWidget(self.icon_square)
        texts = QVBoxLayout()
        texts.setSpacing(1)
        texts.addStretch()
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 15px; font-weight: 600;")
        texts.addWidget(title_label)
        self.subtitle = QLabel(self.subtitle_text)
        self.subtitle.setObjectName("faint")
        texts.addWidget(self.subtitle)
        texts.addStretch()
        layout.addLayout(texts, stretch=1)

    def set_state(self, selected: bool, busy: bool, available: bool):
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)
        self.icon_square.set_selected(selected)
        self.subtitle.setText("Gerando..." if busy else self.subtitle_text)
        self.setEnabled(available and not busy)


class HistoryItem(QWidget):
    def __init__(self, title: str, subtitle: str):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 9, 12, 9)
        layout.setSpacing(2)
        title_label = QLabel(title)
        title_label.setObjectName("historyTitle")
        layout.addWidget(title_label)
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("faint")
        layout.addWidget(subtitle_label)


class LecturePage(QWidget):
    back_requested = Signal()

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.lecture_id = None
        self.selected_key = None   # "output:<id>" or "quiz:<id>" shown in the result card
        self.entries = {}
        self.output_ids = None     # output keys already seen; None until the lecture's first load
        self.action_cards = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(42, 30, 42, 36)
        layout.setSpacing(0)

        # Breadcrumb
        crumbs = QHBoxLayout()
        crumbs.setSpacing(6)
        lectures_link = button("Lectures", "link")
        lectures_link.clicked.connect(self.back_requested)
        crumbs.addWidget(lectures_link)
        crumbs.addWidget(icon_label("chevron-right", styles.TEXT_FAINT, 14))
        self.crumb_label = QLabel()
        crumbs.addWidget(self.crumb_label)
        crumbs.addStretch()
        layout.addLayout(crumbs)
        layout.addSpacing(16)

        # Title, meta and actions
        header = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(8)
        self.title_label = QLabel()
        self.title_label.setObjectName("pageTitle")
        titles.addWidget(self.title_label)
        meta = QHBoxLayout()
        meta.setSpacing(10)
        self.date_label = QLabel()
        self.date_label.setObjectName("muted")
        meta.addWidget(self.date_label)
        self.status_pill = StatusPill()
        meta.addWidget(self.status_pill)
        meta.addStretch()
        titles.addLayout(meta)
        header.addLayout(titles, stretch=1)

        rename = button("Renomear", "secondary", "pencil")
        rename.clicked.connect(self._rename)
        delete = button("Apagar", "danger", "trash")
        delete.clicked.connect(self._delete)
        for widget in (rename, delete):
            widget.setStyleSheet("padding: 10px 16px; font-size: 15px;")
            header.addWidget(widget, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addLayout(header)
        layout.addSpacing(26)

        # Tabs and tab actions
        toolbar = QHBoxLayout()
        self.tabs = SegmentedTabs([("Transcrição", "text"), ("Assistente", "sparkles")])
        self.tabs.changed.connect(self._on_tab_changed)
        toolbar.addWidget(self.tabs)
        toolbar.addStretch()
        self.copy_button = button("Copiar", "flat", "copy")
        self.copy_button.clicked.connect(self._copy_transcript)
        self.export_button = button("Exportar", "flat", "download")
        self.export_button.clicked.connect(self._export_transcript)
        for widget in (self.copy_button, self.export_button):
            widget.setStyleSheet("font-size: 15px;")
            toolbar.addWidget(widget)
        layout.addLayout(toolbar)
        layout.addSpacing(18)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_transcript_tab())
        self.stack.addWidget(self._build_assistant_tab())
        layout.addWidget(self.stack, stretch=1)

        controller.lecture_changed.connect(self._on_lecture_changed)
        controller.quiz_created.connect(self._on_quiz_created)

    # Transcript tab

    def _build_transcript_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        # Temporary: listen back to the audio to check what the mic captured
        self.audio_player = AudioPlayer()
        layout.addWidget(self.audio_player)

        box = QFrame()
        box.setObjectName("transcriptBox")
        box_layout = QVBoxLayout(box)
        box_layout.setContentsMargins(1, 1, 1, 1)
        self.transcript_stack = QStackedWidget()

        self.transcript_view = TranscriptView()
        self.transcript_stack.addWidget(self.transcript_view)

        pending = QWidget()
        pending_layout = QVBoxLayout(pending)
        pending_layout.addStretch()
        self.transcript_status = QLabel()
        self.transcript_status.setObjectName("muted")
        self.transcript_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pending_layout.addWidget(self.transcript_status)
        pending_layout.addSpacing(8)
        self.transcribe_button = button("Transcrever")
        self.transcribe_button.clicked.connect(lambda: self.controller.transcribe(self.lecture_id))
        pending_layout.addWidget(self.transcribe_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        pending_layout.addStretch()
        self.transcript_stack.addWidget(pending)

        box_layout.addWidget(self.transcript_stack)
        layout.addWidget(box, stretch=1)
        return tab

    # Assistant tab

    def _build_assistant_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(22)

        cards = QHBoxLayout()
        cards.setSpacing(14)
        for instruction in InstructionsMap:
            card = ActionCard(instruction)
            card.clicked.connect(lambda key=instruction: self._run_action(key))
            cards.addWidget(card)
            self.action_cards[instruction] = card
        layout.addLayout(cards)

        body = QHBoxLayout()
        body.setSpacing(18)

        history_column = QVBoxLayout()
        history_column.setSpacing(8)
        history_label = QLabel("Histórico")
        history_label.setObjectName("faint")
        history_label.setContentsMargins(4, 0, 0, 0)
        history_column.addWidget(history_label)
        self.history = QListWidget()
        self.history.setObjectName("history")
        self.history.setFixedWidth(230)
        self.history.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.history.currentItemChanged.connect(self._on_history_selected)
        history_column.addWidget(self.history)
        body.addLayout(history_column)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        card_header = QHBoxLayout()
        card_header.setContentsMargins(20, 12, 12, 12)
        self.result_title = QLabel()
        self.result_title.setObjectName("cardTitle")
        card_header.addWidget(self.result_title, stretch=1)
        self.result_copy = button("", "iconButton", "copy", styles.TEXT_MUTED)
        self.result_copy.setToolTip("Copiar")
        self.result_copy.clicked.connect(self._copy_result)
        self.result_regenerate = button("", "iconButton", "refresh", styles.TEXT_MUTED)
        self.result_regenerate.setToolTip("Gerar de novo")
        self.result_regenerate.clicked.connect(self._regenerate)
        card_header.addWidget(self.result_copy)
        card_header.addWidget(self.result_regenerate)
        card_layout.addLayout(card_header)
        card_layout.addWidget(divider())

        self.result_stack = QStackedWidget()
        self.result_empty = QLabel()
        self.result_empty.setObjectName("muted")
        self.result_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_empty.setWordWrap(True)
        self.result_stack.addWidget(self.result_empty)
        self.result_text = QTextBrowser()
        self.result_text.setOpenExternalLinks(True)
        self.result_text.document().setDocumentMargin(20)
        self.result_stack.addWidget(self.result_text)
        self.quiz_view = QuizView(self.controller)
        self.quiz_view.title_changed.connect(self._on_quiz_title)
        self.result_stack.addWidget(self.quiz_view)
        card_layout.addWidget(self.result_stack, stretch=1)

        body.addWidget(card, stretch=1)
        layout.addLayout(body, stretch=1)
        return tab

    # Showing a lecture

    def show_lecture(self, lecture_id: int):
        self.lecture_id = lecture_id
        self.selected_key = None
        self.output_ids = None
        self.tabs.set_current(0)
        self._on_tab_changed(0)
        self._load_audio()
        self.quiz_view.set_lecture(lecture_id)
        self.result_stack.setCurrentWidget(self.result_empty)
        self.refresh()

        if self.quiz_view.is_waiting():
            self._show_quiz_waiting()
        elif self.history.count():
            self.history.setCurrentRow(0)

    def _load_audio(self):
        audio = Path(self.controller.db.get_lecture(self.lecture_id)["audio_path"])
        if not audio.is_absolute():
            audio = PROJECT_ROOT / audio
        self.audio_player.setVisible(audio.exists())
        self.audio_player.load(str(audio) if audio.exists() else "")

    def hideEvent(self, event):
        super().hideEvent(event)
        self.audio_player.stop()

    def refresh(self):
        lecture = self.controller.db.get_lecture(self.lecture_id)
        if lecture is None:
            return

        transcription = self.controller.db.get_latest_transcription(self.lecture_id)
        transcribing = self.lecture_id in self.controller.transcribing

        self.crumb_label.setText(lecture["title"])
        self.title_label.setText(lecture["title"])
        self.date_label.setText(f"Gravada em {format_date(lecture['created_at'])}")
        self.status_pill.set_state(lecture_state(transcription is not None, transcribing))

        if transcription is not None:
            if self.transcript_view.property("transcription_id") != transcription["id"]:
                self.transcript_view.set_transcript(transcription["text"])
                self.transcript_view.setProperty("transcription_id", transcription["id"])
            self.transcript_stack.setCurrentIndex(0)
        else:
            self.transcript_view.setProperty("transcription_id", None)
            self.transcript_status.setText(
                "Transcrevendo... isso pode levar alguns minutos." if transcribing
                else "Esta lecture ainda não foi transcrita."
            )
            self.transcribe_button.setVisible(not transcribing)
            self.transcript_stack.setCurrentIndex(1)
        self.copy_button.setEnabled(transcription is not None)
        self.export_button.setEnabled(transcription is not None)

        self._refresh_history(transcription)
        self._refresh_cards(transcription is not None)

    def _refresh_cards(self, available: bool):
        selected_instruction = self._selected_instruction()
        for instruction, card in self.action_cards.items():
            if instruction == QUIZ_KEY:
                busy = self.lecture_id in self.controller.generating_quiz
            else:
                busy = (self.lecture_id, instruction) in self.controller.running_instructions
            card.set_state(instruction == selected_instruction, busy, available)

    def _selected_instruction(self):
        if self.result_stack.currentWidget() is self.quiz_view:
            return QUIZ_KEY
        entry = self.entries.get(self.selected_key)
        return entry["instruction"] if entry else None

    # History of AI results and quizzes

    def _refresh_history(self, transcription):
        db = self.controller.db
        entries = []
        if transcription is not None:
            for output in db.list_outputs(transcription["id"]):
                entries.append({
                    "key": f"output:{output['id']}", "instruction": output["instruction"],
                    "created_at": output["created_at"], "title": action_info(output["instruction"])[3],
                    "subtitle": format_relative(output["created_at"]), "content": output["content"],
                })
        for quiz in db.list_quizzes(self.lecture_id):
            if quiz["completed_attempts"]:
                status = f"Melhor nota {quiz['best_score']}/{quiz['question_count']}"
            elif quiz["in_progress"]:
                status = "Em andamento"
            else:
                status = f"{quiz['question_count']} perguntas"
            entries.append({
                "key": f"quiz:{quiz['id']}", "instruction": QUIZ_KEY, "created_at": quiz["created_at"],
                "title": "Reforço" if quiz["parent_attempt_id"] else "Quiz",
                "subtitle": f"{format_relative(quiz['created_at'])} · {status}", "quiz_id": quiz["id"],
            })
        entries.sort(key=lambda e: (e["created_at"], e["key"]), reverse=True)
        self.entries = {e["key"]: e for e in entries}

        self.history.blockSignals(True)
        self.history.clear()
        for entry in entries:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, entry["key"])
            widget = HistoryItem(entry["title"], entry["subtitle"])
            item.setSizeHint(QSize(0, widget.sizeHint().height()))
            self.history.addItem(item)
            self.history.setItemWidget(item, widget)
            if entry["key"] == self.selected_key:
                self.history.setCurrentItem(item)
        self.history.blockSignals(False)

        # A text result that just finished is shown right away
        output_keys = {k for k in self.entries if k.startswith("output:")}
        first_load = self.output_ids is None
        new_outputs = output_keys - (self.output_ids or set())
        self.output_ids = output_keys
        if new_outputs and not first_load:
            self._select_key(max(new_outputs, key=lambda k: int(k.split(":")[1])))
        elif self.selected_key and self.selected_key.startswith("output:") and self.selected_key in self.entries:
            self._show_entry(self.selected_key)
        elif self.selected_key not in self.entries and self.result_stack.currentWidget() is not self.quiz_view:
            self.selected_key = None
            self._show_empty(transcription is not None)

    def _select_key(self, key):
        for row in range(self.history.count()):
            if self.history.item(row).data(Qt.ItemDataRole.UserRole) == key:
                self.history.setCurrentRow(row)
                return

    def _on_history_selected(self, item, _previous=None):
        if item is not None:
            self._show_entry(item.data(Qt.ItemDataRole.UserRole))
            self._refresh_cards(self.controller.db.get_latest_transcription(self.lecture_id) is not None)

    def _show_entry(self, key):
        self.selected_key = key
        entry = self.entries[key]
        self.result_copy.show()
        self.result_regenerate.show()
        if key.startswith("quiz:"):
            self.result_stack.setCurrentWidget(self.quiz_view)
            self.quiz_view.show_quiz(entry["quiz_id"])
        else:
            self.result_title.setText(entry["title"])
            self.result_text.setMarkdown(entry["content"])
            self.result_stack.setCurrentWidget(self.result_text)

    def _show_empty(self, has_transcription: bool):
        self.result_title.setText("Resultado")
        self.result_empty.setText(
            "Nenhum resultado ainda. Escolha uma ação acima." if has_transcription
            else "A lecture precisa ser transcrita antes de usar a IA."
        )
        self.result_copy.hide()
        self.result_regenerate.hide()
        self.result_stack.setCurrentWidget(self.result_empty)

    def _show_quiz_waiting(self):
        self.tabs.set_current(1)
        self._on_tab_changed(1)
        self.result_copy.hide()
        self.result_regenerate.hide()
        self.result_stack.setCurrentWidget(self.quiz_view)
        self.quiz_view.show_waiting()

    def _on_quiz_title(self, title: str):
        if self.result_stack.currentWidget() is self.quiz_view:
            self.result_title.setText(title)

    # Actions

    def _run_action(self, instruction: str):
        if instruction == QUIZ_KEY:
            self._new_quiz()
        else:
            self.controller.run_instruction(self.lecture_id, instruction)

    def _new_quiz(self):
        self.selected_key = None
        self.history.blockSignals(True)
        self.history.setCurrentRow(-1)
        self.history.blockSignals(False)
        self.result_copy.hide()
        self.result_regenerate.hide()
        self.result_stack.setCurrentWidget(self.quiz_view)
        self.quiz_view.request_new_quiz()
        self._refresh_cards(True)

    def _regenerate(self):
        instruction = self._selected_instruction()
        if instruction:
            self._run_action(instruction)

    def _copy_result(self):
        if self.result_stack.currentWidget() is self.quiz_view:
            QApplication.clipboard().setText(self.quiz_view.as_text())
        else:
            QApplication.clipboard().setText(self.result_text.toPlainText())

    def _on_tab_changed(self, index: int):
        self.stack.setCurrentIndex(index)
        self.copy_button.setVisible(index == 0)
        self.export_button.setVisible(index == 0)

    def _copy_transcript(self):
        transcription = self.controller.db.get_latest_transcription(self.lecture_id)
        if transcription is None:
            return
        QApplication.clipboard().setText(transcription["text"])
        self.copy_button.setText("Copiado")
        QTimer.singleShot(1500, lambda: self.copy_button.setText("Copiar"))

    def _export_transcript(self):
        transcription = self.controller.db.get_latest_transcription(self.lecture_id)
        if transcription is None:
            return
        title = self.controller.db.get_lecture(self.lecture_id)["title"]
        safe_name = "".join(c for c in title if c not in '/\\:*?"<>|').strip() or "transcricao"
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar transcrição", str(Path.home() / f"{safe_name}.txt"), "Texto (*.txt)"
        )
        if path:
            Path(path).write_text("\n\n".join(transcript_paragraphs(transcription["text"])), encoding="utf-8")

    # Updates from background jobs

    def _on_lecture_changed(self, lecture_id):
        if lecture_id != self.lecture_id or self.controller.db.get_lecture(lecture_id) is None:
            return
        self.refresh()

    def _on_quiz_created(self, lecture_id, quiz_id):
        if lecture_id != self.lecture_id:
            return
        self.refresh()
        # The quiz view opens the new quiz itself; just highlight it in the history
        if self.result_stack.currentWidget() is self.quiz_view and self.quiz_view.quiz_id == quiz_id:
            self.selected_key = f"quiz:{quiz_id}"
            self.result_copy.show()
            self.result_regenerate.show()
            self.history.blockSignals(True)
            self._select_key(self.selected_key)
            self.history.blockSignals(False)
            self._refresh_cards(True)

    def _rename(self):
        lecture = self.controller.db.get_lecture(self.lecture_id)
        title, ok = QInputDialog.getText(self, "Renomear lecture", "Novo nome:", text=lecture["title"])
        if ok and title.strip():
            self.controller.rename_lecture(self.lecture_id, title.strip())

    def _delete(self):
        if self.controller.is_lecture_busy(self.lecture_id):
            QMessageBox.information(self, "Apagar lecture", "Espere a transcrição ou a IA terminar antes de apagar.")
            return

        answer = QMessageBox.question(
            self, "Apagar lecture",
            "Apagar esta lecture, a transcrição e todos os resultados da IA? Isso não pode ser desfeito.",
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.audio_player.load("")
            self.controller.delete_lecture(self.lecture_id)
            self.lecture_id = None
            self.back_requested.emit()
