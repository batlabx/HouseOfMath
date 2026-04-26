"""SQLite wrapper for session + attempt logging."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from ..config import history_db_path

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
  id INTEGER PRIMARY KEY,
  started_at TIMESTAMP,
  topic TEXT,
  level TEXT,
  grade INTEGER,
  score INTEGER,
  total INTEGER,
  duration_seconds INTEGER
);

CREATE TABLE IF NOT EXISTS attempts (
  id INTEGER PRIMARY KEY,
  session_id INTEGER REFERENCES sessions(id),
  question_id TEXT,
  user_answer INTEGER,
  correct INTEGER,
  is_correct BOOLEAN,
  tags TEXT
);

CREATE INDEX IF NOT EXISTS idx_sessions_topic ON sessions(topic);
CREATE INDEX IF NOT EXISTS idx_attempts_session ON attempts(session_id);
"""


@dataclass
class SessionRow:
    id: int
    started_at: str
    topic: str
    level: str
    grade: int | None
    score: int
    total: int
    duration_seconds: int


@dataclass
class AttemptRow:
    session_id: int
    question_id: str
    user_answer: int
    correct: int
    is_correct: bool
    tags: list[str]


class History:
    """Lightweight SQLite store. Safe to construct on every page load."""

    def __init__(self, db_path: Path | None = None):
        self.db_path = Path(db_path) if db_path else history_db_path()
        self._init_schema()

    # ---------- internals ----------

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with closing(self._connect()) as conn:
            conn.executescript(SCHEMA)
            conn.commit()

    # ---------- writes ----------

    def record_session(
        self,
        *,
        topic: str,
        level: str,
        grade: int | None,
        score: int,
        total: int,
        duration_seconds: int,
        attempts: Iterable[AttemptRow] | None = None,
        started_at: datetime | None = None,
    ) -> int:
        ts = (started_at or datetime.utcnow()).isoformat(timespec="seconds")
        with closing(self._connect()) as conn:
            cur = conn.execute(
                """
                INSERT INTO sessions (started_at, topic, level, grade, score, total, duration_seconds)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (ts, topic, level, grade, score, total, duration_seconds),
            )
            session_id = cur.lastrowid
            if attempts:
                conn.executemany(
                    """
                    INSERT INTO attempts (session_id, question_id, user_answer, correct, is_correct, tags)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            session_id,
                            a.question_id,
                            a.user_answer,
                            a.correct,
                            1 if a.is_correct else 0,
                            ",".join(a.tags),
                        )
                        for a in attempts
                    ],
                )
            conn.commit()
            return session_id

    # ---------- reads ----------

    def recent_sessions(self, limit: int = 10) -> list[SessionRow]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT * FROM sessions ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [SessionRow(**dict(r)) for r in rows]

    def all_sessions(self) -> list[SessionRow]:
        with closing(self._connect()) as conn:
            rows = conn.execute("SELECT * FROM sessions ORDER BY id ASC").fetchall()
        return [SessionRow(**dict(r)) for r in rows]

    def attempts_for(self, session_id: int) -> list[AttemptRow]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT session_id, question_id, user_answer, correct, is_correct, tags "
                "FROM attempts WHERE session_id = ?",
                (session_id,),
            ).fetchall()
        return [
            AttemptRow(
                session_id=r["session_id"],
                question_id=r["question_id"],
                user_answer=r["user_answer"],
                correct=r["correct"],
                is_correct=bool(r["is_correct"]),
                tags=[t for t in (r["tags"] or "").split(",") if t],
            )
            for r in rows
        ]

    def topic_accuracy(self) -> list[dict[str, Any]]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                """
                SELECT topic,
                       SUM(score)            AS total_correct,
                       SUM(total)            AS total_questions,
                       COUNT(*)              AS sessions
                FROM sessions
                GROUP BY topic
                ORDER BY topic
                """
            ).fetchall()
        out: list[dict[str, Any]] = []
        for r in rows:
            tc, tq = r["total_correct"] or 0, r["total_questions"] or 0
            out.append(
                {
                    "topic": r["topic"],
                    "sessions": r["sessions"],
                    "total_correct": tc,
                    "total_questions": tq,
                    "accuracy": (tc / tq) if tq else 0.0,
                }
            )
        return out

    def tag_accuracy(self) -> list[dict[str, Any]]:
        """Aggregate accuracy per sub-skill tag across all attempts."""
        agg: dict[str, list[int]] = {}
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT is_correct, tags FROM attempts"
            ).fetchall()
        for r in rows:
            for tag in (r["tags"] or "").split(","):
                if not tag:
                    continue
                agg.setdefault(tag, [0, 0])
                agg[tag][1] += 1
                agg[tag][0] += int(bool(r["is_correct"]))
        out = [
            {
                "tag": tag,
                "correct": c,
                "total": t,
                "accuracy": (c / t) if t else 0.0,
            }
            for tag, (c, t) in agg.items()
        ]
        out.sort(key=lambda x: x["accuracy"])
        return out

    def lifetime_summary(self) -> dict[str, Any]:
        sessions = self.all_sessions()
        total_correct = sum(s.score for s in sessions)
        total_questions = sum(s.total for s in sessions)
        topic_acc = self.topic_accuracy()
        best = max(topic_acc, key=lambda x: x["accuracy"], default=None)
        weakest = min(topic_acc, key=lambda x: x["accuracy"], default=None)
        return {
            "sessions": len(sessions),
            "total_correct": total_correct,
            "total_questions": total_questions,
            "lifetime_accuracy": (total_correct / total_questions) if total_questions else 0.0,
            "best_topic": best["topic"] if best else None,
            "weakest_topic": weakest["topic"] if weakest else None,
        }
