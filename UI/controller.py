import json
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

from Core.AIModule import AIEngine
from Core.DatabaseModule import Database
from Core.PipelineModule import transcribe_file
from Core.QuizModule import format_missed
from SETTINGS import SettingsMap, TranscriberMap

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RECORDINGS_DIR = PROJECT_ROOT / "recordings"


class _JobSignals(QObject):
    finished = Signal(object, object)  # tag, result
    failed = Signal(object, str)
    done = Signal(object)  # always emitted last, success or not


class _Job(QRunnable):
    """Runs fn(*args) on a pool thread and reports back with a tag."""

    def __init__(self, tag, fn, *args):
        super().__init__()
        self.tag = tag
        self.fn = fn
        self.args = args
        self.signals = _JobSignals()

    @Slot()
    def run(self):
        try:
            result = self.fn(*self.args)
        except Exception as e:
            self.signals.failed.emit(self.tag, str(e) or type(e).__name__)
        else:
            self.signals.finished.emit(self.tag, result)
        self.signals.done.emit(self.tag)


# Jobs save their own results with their own connection (SQLite connections
# can't cross threads), so a result is never lost if the window closes first.

def _transcribe_and_save(lecture_id: int, audio_path: str):
    text = transcribe_file(Path(audio_path))
    with Database() as db:
        db.add_transcription(lecture_id, text, TranscriberMap["model"])


def _run_instruction_and_save(engine: AIEngine, transcription_id: int, text: str, instruction: str):
    response = engine.call_llm(text, instruction)
    with Database() as db:
        db.add_output(transcription_id, instruction, response.output_text, SettingsMap["model"])


def _generate_quiz_and_save(engine: AIEngine, lecture_id: int, text: str, focus: str, parent_attempt_id: int):
    quiz = engine.generate_quiz(text, focus)
    with Database() as db:
        return db.add_quiz(lecture_id, quiz["questions"], SettingsMap["model"], parent_attempt_id, quiz["title"])


def _generate_review_and_save(engine: AIEngine, attempt_id: int, text: str, missed: str):
    review = engine.generate_review(text, missed)
    with Database() as db:
        db.set_attempt_review(attempt_id, review)


class Controller(QObject):
    """Owns the database and the background jobs shared by every page."""

    lectures_changed = Signal()
    lecture_changed = Signal(int)  # lecture_id: transcription, outputs or quizzes changed
    quiz_created = Signal(int, int)  # lecture_id, quiz_id
    error = Signal(str)

    def __init__(self):
        super().__init__()
        self.db = Database()
        self._engine = None
        self._jobs = set()
        self.transcribing = set()           # lecture ids
        self.running_instructions = set()   # (lecture_id, instruction)
        self.generating_quiz = set()        # lecture ids
        self.generating_review = set()      # (lecture_id, attempt_id)

        # One transcription at a time: each one already uses every CPU core
        self._transcribe_pool = QThreadPool(self)
        self._transcribe_pool.setMaxThreadCount(1)
        self._ai_pool = QThreadPool(self)

    # Lectures

    def add_lecture(self, title: str, audio_path: Path) -> int:
        lecture_id = self.db.add_lecture(title, audio_path)
        self.lectures_changed.emit()
        self.transcribe(lecture_id)
        return lecture_id

    def rename_lecture(self, lecture_id: int, title: str):
        self.db.rename_lecture(lecture_id, title)
        self.lectures_changed.emit()
        self.lecture_changed.emit(lecture_id)

    def delete_lecture(self, lecture_id: int):
        lecture = self.db.get_lecture(lecture_id)
        self.db.delete_lecture(lecture_id)

        # Only remove audio the app recorded itself, never an imported file
        audio = Path(lecture["audio_path"]).resolve()
        if audio.parent == RECORDINGS_DIR and audio.exists():
            audio.unlink()

        self.lectures_changed.emit()

    # Transcription

    def transcribe(self, lecture_id: int):
        if lecture_id in self.transcribing:
            return
        lecture = self.db.get_lecture(lecture_id)
        self.transcribing.add(lecture_id)
        self._start(self._transcribe_pool, lecture_id, _transcribe_and_save,
                    self._on_transcription_done, self._on_transcription_failed,
                    lecture_id, lecture["audio_path"])
        self.lecture_changed.emit(lecture_id)

    @Slot(object, object)
    def _on_transcription_done(self, lecture_id, _result):
        self.transcribing.discard(lecture_id)
        self.lectures_changed.emit()
        self.lecture_changed.emit(lecture_id)

    @Slot(object, str)
    def _on_transcription_failed(self, lecture_id, message):
        self.transcribing.discard(lecture_id)
        self.lecture_changed.emit(lecture_id)
        self.error.emit(f"A transcrição falhou:\n{message}")

    # AI instructions

    def run_instruction(self, lecture_id: int, instruction: str):
        key = (lecture_id, instruction)
        if key in self.running_instructions:
            return

        transcription = self.db.get_latest_transcription(lecture_id)
        if transcription is None:
            return

        engine = self._get_engine()
        if engine is None:
            return

        self.running_instructions.add(key)
        self._start(self._ai_pool, key, _run_instruction_and_save,
                    self._on_instruction_done, self._on_instruction_failed,
                    engine, transcription["id"], transcription["text"], instruction)
        self.lecture_changed.emit(lecture_id)

    @Slot(object, object)
    def _on_instruction_done(self, key, _result):
        self.running_instructions.discard(key)
        self.lecture_changed.emit(key[0])

    @Slot(object, str)
    def _on_instruction_failed(self, key, message):
        self.running_instructions.discard(key)
        self.lecture_changed.emit(key[0])
        self.error.emit(f"A chamada à OpenAI falhou:\n{message}")

    # Quizzes

    def generate_quiz(self, lecture_id: int, focus_attempt_id: int = None):
        """New quiz for the lecture; with focus_attempt_id it targets that attempt's mistakes."""
        if lecture_id in self.generating_quiz:
            return

        transcription = self.db.get_latest_transcription(lecture_id)
        engine = self._get_engine()
        if transcription is None or engine is None:
            return

        focus = None
        if focus_attempt_id is not None:
            attempt = self.db.get_attempt(focus_attempt_id)
            questions = self.db.get_quiz_questions(attempt["quiz_id"])
            focus = format_missed(questions, json.loads(attempt["answers"]))

        self.generating_quiz.add(lecture_id)
        self._start(self._ai_pool, lecture_id, _generate_quiz_and_save,
                    self._on_quiz_done, self._on_quiz_failed,
                    engine, lecture_id, transcription["text"], focus, focus_attempt_id)
        self.lecture_changed.emit(lecture_id)

    @Slot(object, object)
    def _on_quiz_done(self, lecture_id, quiz_id):
        self.generating_quiz.discard(lecture_id)
        self.quiz_created.emit(lecture_id, quiz_id)
        self.lecture_changed.emit(lecture_id)

    @Slot(object, str)
    def _on_quiz_failed(self, lecture_id, message):
        self.generating_quiz.discard(lecture_id)
        self.lecture_changed.emit(lecture_id)
        self.error.emit(f"Não foi possível gerar o quiz:\n{message}")

    def generate_review(self, attempt_id: int):
        attempt = self.db.get_attempt(attempt_id)
        quiz = self.db.get_quiz(attempt["quiz_id"])
        key = (quiz["lecture_id"], attempt_id)
        if key in self.generating_review:
            return

        transcription = self.db.get_latest_transcription(quiz["lecture_id"])
        engine = self._get_engine()
        if transcription is None or engine is None:
            return

        missed = format_missed(json.loads(quiz["questions"]), json.loads(attempt["answers"]))
        self.generating_review.add(key)
        self._start(self._ai_pool, key, _generate_review_and_save,
                    self._on_review_done, self._on_review_failed,
                    engine, attempt_id, transcription["text"], missed)
        self.lecture_changed.emit(key[0])

    @Slot(object, object)
    def _on_review_done(self, key, _result):
        self.generating_review.discard(key)
        self.lecture_changed.emit(key[0])

    @Slot(object, str)
    def _on_review_failed(self, key, message):
        self.generating_review.discard(key)
        self.lecture_changed.emit(key[0])
        self.error.emit(f"Não foi possível gerar a revisão:\n{message}")

    def is_generating_review(self, attempt_id: int) -> bool:
        return any(a == attempt_id for _, a in self.generating_review)

    # Jobs

    def _get_engine(self):
        try:
            if self._engine is None:
                self._engine = AIEngine()
        except Exception as e:
            self.error.emit(f"Não foi possível conectar à OpenAI:\n{e}")
        return self._engine

    def is_lecture_busy(self, lecture_id: int) -> bool:
        return (
            lecture_id in self.transcribing
            or lecture_id in self.generating_quiz
            or any(l == lecture_id for l, _ in self.running_instructions)
            or any(l == lecture_id for l, _ in self.generating_review)
        )

    def has_running_jobs(self) -> bool:
        return bool(self.transcribing or self.running_instructions or self.generating_quiz or self.generating_review)

    def shutdown(self):
        """Drop queued jobs and wait for the running ones to save their results."""
        self._transcribe_pool.clear()
        self._ai_pool.clear()
        self._transcribe_pool.waitForDone()
        self._ai_pool.waitForDone()
        self.db.close()

    def _start(self, pool, tag, fn, on_done, on_fail, *args):
        job = _Job(tag, fn, *args)
        # Bound methods of this QObject, so Qt delivers them on the main thread
        job.signals.finished.connect(on_done)
        job.signals.failed.connect(on_fail)
        job.signals.done.connect(self._forget_job)
        job.setAutoDelete(False)
        self._jobs.add(job)
        pool.start(job)

    @Slot(object)
    def _forget_job(self, tag):
        self._jobs = {job for job in self._jobs if job.tag != tag}
