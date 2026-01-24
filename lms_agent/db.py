import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import Assignment, FileItem


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    course_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    modified_at TEXT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(course_id, url)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS assignments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    course_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    due_at TEXT NULL,
                    submitted INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(course_id, url)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_type TEXT NOT NULL,
                    item_key TEXT NOT NULL,
                    threshold TEXT NOT NULL,
                    sent_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(item_type, item_key, threshold)
                )
                """
            )

    def record_file(self, item: FileItem) -> bool:
        modified_at = item.modified_at.isoformat() if item.modified_at else None
        with self._connect() as conn:
            try:
                conn.execute(
                    "INSERT INTO files(course_id, name, url, modified_at) VALUES (?, ?, ?, ?)",
                    (item.course_id, item.name, item.url, modified_at),
                )
                return True
            except sqlite3.IntegrityError:
                return False

    def upsert_assignment(self, assignment: Assignment) -> bool:
        due_at = assignment.due_at.isoformat() if assignment.due_at else None
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT submitted, due_at FROM assignments WHERE course_id = ? AND url = ?",
                (assignment.course_id, assignment.url),
            )
            row = cursor.fetchone()
            if row:
                conn.execute(
                    """
                    UPDATE assignments
                    SET name = ?, due_at = ?, submitted = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE course_id = ? AND url = ?
                    """,
                    (assignment.name, due_at, int(assignment.submitted), assignment.course_id, assignment.url),
                )
                return False
            conn.execute(
                "INSERT INTO assignments(course_id, name, url, due_at, submitted) VALUES (?, ?, ?, ?, ?)",
                (assignment.course_id, assignment.name, assignment.url, due_at, int(assignment.submitted)),
            )
            return True

    def mark_notification_sent(self, item_type: str, item_key: str, threshold: str) -> None:
        with self._connect() as conn:
            try:
                conn.execute(
                    "INSERT INTO notifications(item_type, item_key, threshold) VALUES (?, ?, ?)",
                    (item_type, item_key, threshold),
                )
            except sqlite3.IntegrityError:
                pass

    def was_notification_sent(self, item_type: str, item_key: str, threshold: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT 1 FROM notifications WHERE item_type = ? AND item_key = ? AND threshold = ?",
                (item_type, item_key, threshold),
            )
            return cursor.fetchone() is not None

    def pending_assignments(self):
        with self._connect() as conn:
            cursor = conn.execute(
                """
                SELECT course_id, name, url, due_at, submitted FROM assignments
                WHERE submitted = 0
                """
            )
            return cursor.fetchall()

    def set_assignment_submitted(self, course_id: str, url: str, submitted: bool) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE assignments SET submitted = ?, updated_at = CURRENT_TIMESTAMP WHERE course_id = ? AND url = ?",
                (int(submitted), course_id, url),
            )

    def get_latest_file(self, course_id: str) -> Optional[dict]:
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT * FROM files WHERE course_id = ? ORDER BY created_at DESC LIMIT 1",
                (course_id,),
            )
            return cursor.fetchone()
