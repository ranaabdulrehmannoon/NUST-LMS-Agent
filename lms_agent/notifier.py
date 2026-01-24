import logging
import smtplib
from datetime import datetime
from email.message import EmailMessage
from typing import Iterable, List, Optional

from .config import Settings
from .db import Database
from .models import FileItem, Notification

logger = logging.getLogger(__name__)


class Notifier:
    def __init__(self, settings: Settings, db: Database) -> None:
        self.settings = settings
        self.db = db

    def _send(self, subject: str, body_text: str, body_html: Optional[str] = None) -> None:
        """Send email via SMTP with optional HTML alternative."""
        try:
            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = self.settings.smtp_from
            msg["To"] = ", ".join(self.settings.get_smtp_to_list())
            msg.set_content(body_text)
            if body_html:
                msg.add_alternative(body_html, subtype="html")

            with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port, timeout=30) as server:
                server.starttls()
                server.login(self.settings.smtp_username, self.settings.smtp_password)
                server.send_message(msg)
            logger.info("Email sent via SMTP: %s", subject)
        except smtplib.SMTPAuthenticationError as e:
            logger.error("SMTP authentication failed: %s", e)
        except Exception as e:
            logger.error("SMTP email failed: %s", e)

    def send_new_files(self, course_name: str, files: List[FileItem]) -> None:
        if not files:
            return
        subject = f"[LMS] New files in {course_name}"
        timestamp = datetime.now().isoformat(timespec="seconds")
        text_lines = [f"New uploads detected in course: {course_name}", ""]
        html_lines = [f"<p>New uploads in course <strong>{course_name}</strong>:</p>", "<ul>"]

        for item in files:
            when = item.modified_at.isoformat(timespec="seconds") if item.modified_at else "unknown time"
            text_lines.append(f"- {item.name} ({item.url}) [{when}]")
            html_lines.append(
                f"<li><strong>{item.name}</strong> - <a href=\"{item.url}\">Open file</a> - {when}</li>"
            )

        html_lines.append("</ul>")
        html_lines.append(f"<p>Checked at {timestamp}</p>")

        body_text = "\n".join(text_lines)
        body_html = "\n".join(html_lines)
        self._send(subject, body_text, body_html)

    def send_notifications(self, notifications: Iterable[Notification]) -> None:
        for note in notifications:
            if self.db.was_notification_sent(note.item_type, note.item_key, note.threshold):
                continue
            subject = f"[LMS] {note.threshold} - {note.title}"
            due = note.due_at.isoformat() if note.due_at else "unknown"
            body = (
                f"Course: {note.course_name}\n"
                f"Item: {note.title}\n"
                f"Due: {due}\n"
                f"Status: {note.threshold}\n"
                f"Link: {note.item_key}"
            )
            body_html = (
                f"<p><strong>Course:</strong> {note.course_name}<br>"
                f"<strong>Item:</strong> {note.title}<br>"
                f"<strong>Due:</strong> {due}<br>"
                f"<strong>Status:</strong> {note.threshold}<br>"
                f"<strong>Link:</strong> <a href=\"{note.item_key}\">Open</a></p>"
            )
            self._send(subject, body, body_html)
            self.db.mark_notification_sent(note.item_type, note.item_key, note.threshold)

    def send_no_new_files(self, course_count: int) -> None:
        subject = "[LMS] No new files"
        timestamp = datetime.now().isoformat(timespec="seconds")
        body_text = f"Checked {course_count} courses at {timestamp}. No new files were found."
        body_html = (
            f"<p>No new files were found across <strong>{course_count}</strong> courses.</p>"
            f"<p>Checked at {timestamp}</p>"
        )
        self._send(subject, body_text, body_html)
