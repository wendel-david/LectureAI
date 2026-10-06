import html
import json

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QProgressBar, QScrollArea, QStackedWidget, QTextBrowser, QVBoxLayout,
    QWidget,
)

from Core.QuizModule import score
from UI import styles
from UI.helpers import format_date
from UI.widgets import Clickable, button, repolish

LETTERS = "ABCDEFGHIJ"


class OptionCard(Clickable):
    """A clickable answer option whose text wraps, unlike QPushButton."""

    def __init__(self, letter: str, text: str):
        super().__init__("optionCard")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 9, 14, 9)
        layout.setSpacing(12)

        self.letter = QLabel(letter)
        self.letter.setObjectName("optionLetter")
        self.letter.setFixedSize(22, 22)
        self.letter.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.letter, alignment=Qt.AlignmentFlag.AlignTop)

        text_label = QLabel(text)
        text_label.setObjectName("optionText")
        text_label.setWordWrap(True)
        layout.addWidget(text_label, stretch=1)

    def set_selected(self, selected: bool):
        for widget in (self, self.letter):
            widget.setProperty("selected", selected)
            repolish(widget)


def _page():
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(20, 18, 20, 20)
    layout.setSpacing(12)
    return page, layout


class QuizView(QWidget):
    """Interactive quiz: overview, one question at a time, results, AI review."""

    title_changed = Signal(str)

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.lecture_id = None
        self.quiz_id = None
        self.questions = []
        self.attempt_id = None
        self.answers = []
        self.index = 0
        self.option_cards = []
        self.results_attempt_id = None
        self.review_attempt_id = None
        self._waiting_for_quiz = False

        self.stack = QStackedWidget()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)

        self.empty_page = self._build_empty_page()
        self.loading_page = self._build_loading_page()
        self.overview_page = self._build_overview_page()
        self.question_page = self._build_question_page()
        self.results_page = self._build_results_page()
        self.review_page = self._build_review_page()
        for page in (self.empty_page, self.loading_page, self.overview_page,
                     self.question_page, self.results_page, self.review_page):
            self.stack.addWidget(page)

        controller.quiz_created.connect(self._on_quiz_created)
        controller.lecture_changed.connect(self._on_lecture_changed)

    # Page construction

    def _build_empty_page(self):
        page, layout = _page()
        layout.addStretch()
        self.empty_label = QLabel()
        self.empty_label.setObjectName("muted")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setWordWrap(True)
        layout.addWidget(self.empty_label)
        layout.addStretch()
        return page

    def _build_loading_page(self):
        page, layout = _page()
        layout.addStretch()
        self.loading_label = QLabel()
        self.loading_label.setObjectName("muted")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.loading_label)
        busy = QProgressBar()
        busy.setRange(0, 0)
        busy.setTextVisible(False)
        busy.setFixedSize(200, 6)
        layout.addWidget(busy, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch()
        return page

    def _build_overview_page(self):
        page, layout = _page()
        self.overview_info = QLabel()
        self.overview_info.setObjectName("muted")
        layout.addWidget(self.overview_info)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        self.start_button = button("")
        self.start_button.clicked.connect(self._start)
        self.restart_button = button("Recomeçar", "secondary")
        self.restart_button.clicked.connect(self._restart)
        self.last_result_button = button("Ver último resultado", "secondary")
        self.last_result_button.clicked.connect(self._show_last_result)
        for widget in (self.start_button, self.restart_button, self.last_result_button):
            buttons.addWidget(widget)
        buttons.addStretch()
        layout.addLayout(buttons)

        layout.addSpacing(10)
        grades_title = QLabel("Notas")
        grades_title.setObjectName("fieldLabel")
        layout.addWidget(grades_title)
        self.attempts_label = QLabel()
        self.attempts_label.setObjectName("muted")
        self.attempts_label.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(self.attempts_label)
        layout.addStretch()
        return page

    def _build_question_page(self):
        page, layout = _page()

        top = QHBoxLayout()
        self.question_counter = QLabel()
        self.question_counter.setObjectName("faint")
        top.addWidget(self.question_counter)
        top.addStretch()
        layout.addLayout(top)

        self.question_progress = QProgressBar()
        self.question_progress.setTextVisible(False)
        self.question_progress.setFixedHeight(4)
        layout.addWidget(self.question_progress)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 10, 6, 6)
        body_layout.setSpacing(12)

        question_row = QHBoxLayout()
        question_row.setSpacing(8)
        self.question_number = QLabel()
        self.question_number.setObjectName("questionNumber")
        question_row.addWidget(self.question_number, alignment=Qt.AlignmentFlag.AlignTop)
        self.question_label = QLabel()
        self.question_label.setObjectName("questionText")
        self.question_label.setWordWrap(True)
        question_row.addWidget(self.question_label, stretch=1)
        body_layout.addLayout(question_row)

        self.options_layout = QVBoxLayout()
        self.options_layout.setSpacing(8)
        body_layout.addLayout(self.options_layout)
        body_layout.addStretch()
        scroll.setWidget(body)
        layout.addWidget(scroll, stretch=1)

        nav = QHBoxLayout()
        self.prev_button = button("Anterior", "secondary", "arrow-left")
        self.prev_button.clicked.connect(self._prev)
        self.next_button = button("", icon_name="arrow-right")
        self.next_button.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.next_button.clicked.connect(self._next)
        nav.addWidget(self.prev_button)
        nav.addStretch()
        nav.addWidget(self.next_button)
        layout.addLayout(nav)
        return page

    def _build_results_page(self):
        page, layout = _page()
        score_row = QHBoxLayout()
        score_row.setSpacing(14)
        self.score_label = QLabel()
        self.score_label.setObjectName("scoreText")
        score_row.addWidget(self.score_label)
        self.score_message = QLabel()
        self.score_message.setObjectName("muted")
        self.score_message.setStyleSheet("font-size: 15px;")
        score_row.addWidget(self.score_message, alignment=Qt.AlignmentFlag.AlignVCenter)
        score_row.addStretch()
        layout.addLayout(score_row)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        self.review_button = button("", icon_name="sparkles")
        self.review_button.clicked.connect(lambda: self._show_review(self.results_attempt_id))
        self.new_quiz_button = button("Novo quiz", "secondary", "plus")
        self.new_quiz_button.clicked.connect(self.request_new_quiz)
        self.retry_button = button("Refazer este quiz", "secondary", "refresh")
        self.retry_button.clicked.connect(self._retry)
        for widget in (self.review_button, self.new_quiz_button, self.retry_button):
            buttons.addWidget(widget)
        buttons.addStretch()
        layout.addLayout(buttons)

        self.breakdown = QTextBrowser()
        layout.addWidget(self.breakdown, stretch=1)
        return page

    def _build_review_page(self):
        page, layout = _page()
        self.review_text = QTextBrowser()
        layout.addWidget(self.review_text, stretch=1)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        back = button("Voltar ao resultado", "secondary", "arrow-left")
        back.clicked.connect(lambda: self._show_results(self.review_attempt_id))
        self.review_retry_button = button("Tentar gerar de novo", "secondary", "refresh")
        self.review_retry_button.clicked.connect(lambda: self._show_review(self.review_attempt_id, retry=True))
        self.focused_quiz_button = button("Fazer um quiz sobre o que errei", icon_name="arrow-right")
        self.focused_quiz_button.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.focused_quiz_button.clicked.connect(self._focused_quiz)
        buttons.addWidget(back)
        buttons.addWidget(self.review_retry_button)
        buttons.addStretch()
        buttons.addWidget(self.focused_quiz_button)
        layout.addLayout(buttons)
        return page

    # Entry points used by the lecture page

    def set_lecture(self, lecture_id: int):
        self.lecture_id = lecture_id
        self.quiz_id = None
        self._waiting_for_quiz = lecture_id in self.controller.generating_quiz

    def is_waiting(self) -> bool:
        return self._waiting_for_quiz

    def show_waiting(self):
        self._show_loading("Gerando quiz...")

    def show_quiz(self, quiz_id: int):
        self._waiting_for_quiz = False
        self.quiz_id = quiz_id
        self.questions = self.controller.db.get_quiz_questions(quiz_id)
        self._show_overview()

    def request_new_quiz(self):
        self._request_quiz(None)

    def quiz_title(self) -> str:
        if self.quiz_id is None:
            return "Quiz"
        quiz = self.controller.db.get_quiz(self.quiz_id)
        return quiz["title"] or ("Quiz de reforço" if quiz["parent_attempt_id"] else "Quiz")

    def as_text(self) -> str:
        """Plain-text version of the quiz, for the copy button."""
        lines = [self.quiz_title(), ""]
        for i, q in enumerate(self.questions, start=1):
            lines.append(f"{i:02d}. {q['question']}")
            lines += [f"   {LETTERS[j]}) {option}" for j, option in enumerate(q["options"])]
            lines.append("")
        return "\n".join(lines)

    # Overview

    def _show_overview(self):
        db = self.controller.db
        quiz = db.get_quiz(self.quiz_id)
        total = len(self.questions)
        kind = "Quiz de reforço" if quiz["parent_attempt_id"] else "Quiz"
        self.overview_info.setText(f"{kind} · {total} perguntas · criado em {format_date(quiz['created_at'])}")

        in_progress = db.get_in_progress_attempt(self.quiz_id)
        completed = db.list_completed_attempts(self.quiz_id)

        if in_progress:
            self.start_button.setText(f"Continuar (pergunta {in_progress['current_index'] + 1} de {total})")
        else:
            self.start_button.setText("Refazer" if completed else "Começar")
        self.restart_button.setVisible(in_progress is not None)
        self.last_result_button.setVisible(bool(completed))

        if completed:
            rows = "".join(
                f"<tr><td style='padding:3px 24px 3px 0'>{format_date(a['completed_at'])}</td>"
                f"<td style='padding:3px 16px 3px 0; color:{styles.TEXT}; font-weight:600'>{a['score']}/{a['total']}</td>"
                f"<td style='padding:3px 0'>{round(100 * a['score'] / a['total'])}%</td></tr>"
                for a in completed
            )
            self.attempts_label.setText(f"<table>{rows}</table>")
        else:
            self.attempts_label.setText("Nenhuma tentativa concluída ainda.")

        self.title_changed.emit(self.quiz_title())
        self.stack.setCurrentWidget(self.overview_page)

    def _start(self):
        attempt = self.controller.db.get_in_progress_attempt(self.quiz_id)
        if attempt is None:
            self._begin_attempt(self.controller.db.start_attempt(self.quiz_id, len(self.questions)))
        else:
            self._begin_attempt(attempt["id"])

    def _restart(self):
        attempt = self.controller.db.get_in_progress_attempt(self.quiz_id)
        if attempt is not None:
            self.controller.db.save_attempt_progress(attempt["id"], [None] * len(self.questions), 0)
        self._start()

    def _retry(self):
        self.show_quiz(self.quiz_id)
        self._start()

    def _show_last_result(self):
        completed = self.controller.db.list_completed_attempts(self.quiz_id)
        if completed:
            self._show_results(completed[0]["id"])

    # Answering, saved after every change so progress survives closing the app

    def _begin_attempt(self, attempt_id: int):
        attempt = self.controller.db.get_attempt(attempt_id)
        self.attempt_id = attempt_id
        self.answers = json.loads(attempt["answers"])
        self.index = min(attempt["current_index"], len(self.questions) - 1)
        self._render_question()
        self.title_changed.emit(self.quiz_title())
        self.stack.setCurrentWidget(self.question_page)
        self.controller.lecture_changed.emit(self.lecture_id)

    def _render_question(self):
        total = len(self.questions)
        question = self.questions[self.index]

        self.question_counter.setText(f"Pergunta {self.index + 1} de {total}")
        self.question_progress.setRange(0, total)
        self.question_progress.setValue(self.index + 1)
        self.question_number.setText(f"{self.index + 1:02d}")
        self.question_label.setText(question["question"])

        while self.options_layout.count():
            widget = self.options_layout.takeAt(0).widget()
            widget.hide()
            widget.deleteLater()
        self.option_cards = []
        for i, option in enumerate(question["options"]):
            card = OptionCard(LETTERS[i] if i < len(LETTERS) else str(i + 1), option)
            card.clicked.connect(lambda i=i: self._select(i))
            self.options_layout.addWidget(card)
            self.option_cards.append(card)

        self._update_selection()
        self.prev_button.setEnabled(self.index > 0)
        last = self.index == total - 1
        self.next_button.setText("Finalizar" if last else "Próxima")

    def _update_selection(self):
        selected = self.answers[self.index]
        for i, card in enumerate(self.option_cards):
            card.set_selected(i == selected)
        self.next_button.setEnabled(selected is not None)

    def _select(self, option_index: int):
        self.answers[self.index] = option_index
        self.controller.db.save_attempt_progress(self.attempt_id, self.answers, self.index)
        self._update_selection()

    def _prev(self):
        self.index -= 1
        self.controller.db.save_attempt_progress(self.attempt_id, self.answers, self.index)
        self._render_question()

    def _next(self):
        if self.index == len(self.questions) - 1:
            self._finish()
            return
        self.index += 1
        self.controller.db.save_attempt_progress(self.attempt_id, self.answers, self.index)
        self._render_question()

    def _finish(self):
        self.controller.db.complete_attempt(self.attempt_id, self.answers, score(self.questions, self.answers))
        self.controller.lecture_changed.emit(self.lecture_id)
        self._show_results(self.attempt_id)

    # Results

    def _show_results(self, attempt_id: int):
        attempt = self.controller.db.get_attempt(attempt_id)
        self.results_attempt_id = attempt_id
        answers = json.loads(attempt["answers"])
        right, total = attempt["score"], attempt["total"]
        percent = round(100 * right / total)

        self.score_label.setText(f"{right}/{total}")
        if percent == 100:
            message = "Perfeito! Você acertou tudo."
        elif percent >= 70:
            message = f"{percent}% de acertos. Muito bem!"
        else:
            message = f"{percent}% de acertos. Vale revisar o conteúdo."
        self.score_message.setText(message)

        wrong = total - right
        self.review_button.setVisible(wrong > 0)
        self.review_button.setText("Ver revisão" if attempt["review"] else f"Revisar o que errei ({wrong})")

        blocks = []
        for i, (question, answer) in enumerate(zip(self.questions, answers), start=1):
            correct = question["correct_index"]
            chosen = html.escape(question["options"][answer]) if answer is not None else "sem resposta"
            if answer == correct:
                verdict = f"<span style='color:{styles.GREEN_TEXT}'>✓ {chosen}</span>"
            else:
                verdict = (
                    f"<span style='color:{styles.RED}'>✗ Sua resposta: {chosen}</span><br>"
                    f"<span style='color:{styles.GREEN_TEXT}'>✓ Resposta certa: {html.escape(question['options'][correct])}</span>"
                )
            blocks.append(
                f"<p style='margin-bottom:4px'><span style='font-family:Menlo; color:{styles.TEXT_FAINT}'>{i:02d}</span>"
                f"&nbsp; <b>{html.escape(question['question'])}</b></p>"
                f"<p style='margin:0 0 4px 0'>{verdict}</p>"
                f"<p style='margin:0 0 18px 0; color:{styles.TEXT_MUTED}'>{html.escape(question['explanation'])}</p>"
            )
        self.breakdown.setHtml("".join(blocks))

        self.title_changed.emit(self.quiz_title())
        self.stack.setCurrentWidget(self.results_page)

    # Review

    def _show_review(self, attempt_id: int, retry=False):
        self.review_attempt_id = attempt_id
        attempt = self.controller.db.get_attempt(attempt_id)
        generating = self.controller.is_generating_review(attempt_id)

        if attempt["review"] is None and not generating and (retry or self.stack.currentWidget() is not self.review_page):
            self.controller.generate_review(attempt_id)
            generating = self.controller.is_generating_review(attempt_id)

        if attempt["review"]:
            self.review_text.setMarkdown(attempt["review"])
        elif generating:
            self.review_text.setMarkdown("*Gerando a revisão do conteúdo que você errou...*")
        else:
            self.review_text.setMarkdown("*Não foi possível gerar a revisão.*")

        self.review_retry_button.setVisible(attempt["review"] is None and not generating)
        self.focused_quiz_button.setEnabled(attempt["review"] is not None)
        self.title_changed.emit("Revisão do que você errou")
        self.stack.setCurrentWidget(self.review_page)

    def _focused_quiz(self):
        self._request_quiz(self.review_attempt_id)

    # Waiting for the AI

    def _request_quiz(self, focus_attempt_id):
        self.controller.generate_quiz(self.lecture_id, focus_attempt_id)
        if self.lecture_id in self.controller.generating_quiz:
            self._waiting_for_quiz = True
            self._show_loading("Gerando um quiz sobre o que você errou..." if focus_attempt_id else "Gerando quiz...")

    def _show_loading(self, message: str):
        self.loading_label.setText(message)
        self.title_changed.emit("Novo quiz")
        self.stack.setCurrentWidget(self.loading_page)

    def _on_quiz_created(self, lecture_id, quiz_id):
        if lecture_id == self.lecture_id and self._waiting_for_quiz:
            self.show_quiz(quiz_id)
            self._start()

    def _on_lecture_changed(self, lecture_id):
        if lecture_id != self.lecture_id:
            return

        if self._waiting_for_quiz and lecture_id not in self.controller.generating_quiz:
            # Generation failed: go back to wherever the user was
            self._waiting_for_quiz = False
            if self.quiz_id is not None:
                self._show_overview()
            else:
                self.empty_label.setText("Não foi possível gerar o quiz.")
                self.stack.setCurrentWidget(self.empty_page)
        elif self.stack.currentWidget() is self.review_page:
            self._show_review(self.review_attempt_id)
