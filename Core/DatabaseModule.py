import json
import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "lectureai.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS lectures (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    audio_path  TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS transcriptions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    lecture_id  INTEGER NOT NULL REFERENCES lectures(id) ON DELETE CASCADE,
    text        TEXT NOT NULL,
    model       TEXT,
    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS outputs (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    transcription_id  INTEGER NOT NULL REFERENCES transcriptions(id) ON DELETE CASCADE,
    instruction       TEXT NOT NULL,
    content           TEXT NOT NULL,
    model             TEXT,
    created_at        TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS quizzes (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    lecture_id         INTEGER NOT NULL REFERENCES lectures(id) ON DELETE CASCADE,
    questions          TEXT NOT NULL,  -- JSON list of {question, options, correct_index, explanation}
    parent_attempt_id  INTEGER REFERENCES quiz_attempts(id) ON DELETE SET NULL,  -- set for review quizzes
    title              TEXT,
    model              TEXT,
    created_at         TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS quiz_attempts (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    quiz_id        INTEGER NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
    answers        TEXT NOT NULL,  -- JSON list: chosen option index per question, or null
    current_index  INTEGER NOT NULL DEFAULT 0,
    score          INTEGER,        -- null while in progress
    total          INTEGER NOT NULL,
    review         TEXT,
    started_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at   TEXT
);

CREATE INDEX IF NOT EXISTS idx_transcriptions_lecture ON transcriptions(lecture_id);
CREATE INDEX IF NOT EXISTS idx_outputs_transcription ON outputs(transcription_id);
CREATE INDEX IF NOT EXISTS idx_quizzes_lecture ON quizzes(lecture_id);
CREATE INDEX IF NOT EXISTS idx_attempts_quiz ON quiz_attempts(quiz_id);
"""


class Database:
    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)
        self._migrate()

    def _migrate(self):
        """Add columns introduced after a database was first created."""
        quiz_columns = {row["name"] for row in self.conn.execute("PRAGMA table_info(quizzes)")}
        if "title" not in quiz_columns:
            with self.conn:
                self.conn.execute("ALTER TABLE quizzes ADD COLUMN title TEXT")

    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # Lectures

    def add_lecture(self, title: str, audio_path: Path) -> int:
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO lectures (title, audio_path) VALUES (?, ?)",
                (title, str(audio_path)),
            )
        return cur.lastrowid

    def get_lecture(self, lecture_id: int):
        return self.conn.execute(
            "SELECT * FROM lectures WHERE id = ?", (lecture_id,)
        ).fetchone()

    def list_lectures(self):
        return self.conn.execute(
            """
            SELECT l.*,
                   EXISTS(SELECT 1 FROM transcriptions t WHERE t.lecture_id = l.id) AS has_transcription
            FROM lectures l
            ORDER BY l.created_at DESC, l.id DESC
            """
        ).fetchall()

    def rename_lecture(self, lecture_id: int, title: str):
        with self.conn:
            self.conn.execute("UPDATE lectures SET title = ? WHERE id = ?", (title, lecture_id))

    def delete_lecture(self, lecture_id: int):
        with self.conn:
            self.conn.execute("DELETE FROM lectures WHERE id = ?", (lecture_id,))

    # Transcriptions

    def add_transcription(self, lecture_id: int, text: str, model: str = None) -> int:
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO transcriptions (lecture_id, text, model) VALUES (?, ?, ?)",
                (lecture_id, text, model),
            )
        return cur.lastrowid

    def get_transcription(self, transcription_id: int):
        return self.conn.execute(
            "SELECT * FROM transcriptions WHERE id = ?", (transcription_id,)
        ).fetchone()

    def get_latest_transcription(self, lecture_id: int = None):
        if lecture_id is None:
            return self.conn.execute(
                "SELECT * FROM transcriptions ORDER BY id DESC LIMIT 1"
            ).fetchone()
        return self.conn.execute(
            "SELECT * FROM transcriptions WHERE lecture_id = ? ORDER BY id DESC LIMIT 1",
            (lecture_id,),
        ).fetchone()

    def list_transcriptions(self, lecture_id: int):
        return self.conn.execute(
            "SELECT * FROM transcriptions WHERE lecture_id = ? ORDER BY id DESC",
            (lecture_id,),
        ).fetchall()

    # Outputs

    def add_output(self, transcription_id: int, instruction: str, content: str, model: str = None) -> int:
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO outputs (transcription_id, instruction, content, model) VALUES (?, ?, ?, ?)",
                (transcription_id, instruction, content, model),
            )
        return cur.lastrowid

    def list_outputs(self, transcription_id: int, instruction: str = None):
        if instruction is None:
            return self.conn.execute(
                "SELECT * FROM outputs WHERE transcription_id = ? ORDER BY id DESC",
                (transcription_id,),
            ).fetchall()
        return self.conn.execute(
            "SELECT * FROM outputs WHERE transcription_id = ? AND instruction = ? ORDER BY id DESC",
            (transcription_id, instruction),
        ).fetchall()

    # Quizzes

    def add_quiz(self, lecture_id: int, questions: list, model: str = None,
                 parent_attempt_id: int = None, title: str = None) -> int:
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO quizzes (lecture_id, questions, model, parent_attempt_id, title) VALUES (?, ?, ?, ?, ?)",
                (lecture_id, json.dumps(questions), model, parent_attempt_id, title),
            )
        return cur.lastrowid

    def get_quiz(self, quiz_id: int):
        return self.conn.execute("SELECT * FROM quizzes WHERE id = ?", (quiz_id,)).fetchone()

    def get_quiz_questions(self, quiz_id: int) -> list:
        return json.loads(self.get_quiz(quiz_id)["questions"])

    def list_quizzes(self, lecture_id: int):
        return self.conn.execute(
            """
            SELECT q.*,
                   json_array_length(q.questions) AS question_count,
                   (SELECT MAX(score) FROM quiz_attempts a
                     WHERE a.quiz_id = q.id AND a.completed_at IS NOT NULL) AS best_score,
                   (SELECT COUNT(*) FROM quiz_attempts a
                     WHERE a.quiz_id = q.id AND a.completed_at IS NOT NULL) AS completed_attempts,
                   EXISTS(SELECT 1 FROM quiz_attempts a
                     WHERE a.quiz_id = q.id AND a.completed_at IS NULL) AS in_progress
            FROM quizzes q
            WHERE q.lecture_id = ?
            ORDER BY q.id DESC
            """,
            (lecture_id,),
        ).fetchall()

    # Quiz attempts

    def start_attempt(self, quiz_id: int, total: int) -> int:
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO quiz_attempts (quiz_id, answers, total) VALUES (?, ?, ?)",
                (quiz_id, json.dumps([None] * total), total),
            )
        return cur.lastrowid

    def get_attempt(self, attempt_id: int):
        return self.conn.execute("SELECT * FROM quiz_attempts WHERE id = ?", (attempt_id,)).fetchone()

    def get_in_progress_attempt(self, quiz_id: int):
        return self.conn.execute(
            "SELECT * FROM quiz_attempts WHERE quiz_id = ? AND completed_at IS NULL ORDER BY id DESC LIMIT 1",
            (quiz_id,),
        ).fetchone()

    def list_completed_attempts(self, quiz_id: int):
        return self.conn.execute(
            "SELECT * FROM quiz_attempts WHERE quiz_id = ? AND completed_at IS NOT NULL ORDER BY id DESC",
            (quiz_id,),
        ).fetchall()

    def save_attempt_progress(self, attempt_id: int, answers: list, current_index: int):
        with self.conn:
            self.conn.execute(
                "UPDATE quiz_attempts SET answers = ?, current_index = ? WHERE id = ?",
                (json.dumps(answers), current_index, attempt_id),
            )

    def complete_attempt(self, attempt_id: int, answers: list, score: int):
        with self.conn:
            self.conn.execute(
                "UPDATE quiz_attempts SET answers = ?, score = ?, completed_at = CURRENT_TIMESTAMP WHERE id = ?",
                (json.dumps(answers), score, attempt_id),
            )

    def set_attempt_review(self, attempt_id: int, review: str):
        with self.conn:
            self.conn.execute("UPDATE quiz_attempts SET review = ? WHERE id = ?", (review, attempt_id))
