from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from typing import List

from .auth import login
from .config import settings, Settings
from .db import Database
from .fetcher import fetch_course_content, get_enrolled_courses
from .logging_config import setup_logging
from .models import Notification
from .notifier import Notifier

logger = logging.getLogger(__name__)


THRESHOLDS = [72, 48, 24]


def compute_notifications(assignments, course_name: str, db: Database) -> List[Notification]:
    now = datetime.now()
    notes: List[Notification] = []
    for assignment in assignments:
        if assignment.submitted:
            db.set_assignment_submitted(assignment.course_id, assignment.url, True)
            continue
        if not assignment.due_at:
            continue
        delta = assignment.due_at - now
        hours_left = delta.total_seconds() / 3600
        key = assignment.url
        if hours_left < 0:
            threshold = "overdue"
            if not db.was_notification_sent("assignment", key, threshold):
                notes.append(
                    Notification(
                        item_type="assignment",
                        item_key=key,
                        threshold=threshold,
                        course_name=course_name,
                        title=assignment.name,
                        due_at=assignment.due_at,
                    )
                )
            continue
        for limit in THRESHOLDS:
            if hours_left <= limit:
                label = f"due<={limit}h"
                if not db.was_notification_sent("assignment", key, label):
                    notes.append(
                        Notification(
                            item_type="assignment",
                            item_key=key,
                            threshold=label,
                            course_name=course_name,
                            title=assignment.name,
                            due_at=assignment.due_at,
                        )
                    )
                break
    return notes


def run_once(custom_settings: Settings | None = None, *, send_no_new_files_alert: bool = False, configure_logging: bool = True) -> None:
    cfg = custom_settings or settings
    if configure_logging:
        setup_logging()
    db = Database(cfg.db_path)
    notifier = Notifier(cfg, db)

    session = login(cfg)
    page = session.page

    courses = get_enrolled_courses(page, cfg.lms_base_url, timeout_ms=cfg.request_timeout * 1000)
    
    # Filter courses: match by exact name, partial name, or course code
    if cfg.course_filter:
        filtered = []
        for course in courses:
            for filter_term in cfg.course_filter:
                # Case-insensitive partial match
                if filter_term.lower() in course.name.lower() or course.name.lower() in filter_term.lower():
                    filtered.append(course)
                    break
        courses = filtered
        logger.info("Filtered courses to %d entries", len(courses))
    
    new_files_found = False

    try:
        for course in courses:
            files, assignments = fetch_course_content(page, course, timeout_ms=cfg.request_timeout * 1000)

            new_files = [item for item in files if db.record_file(item)]
            if new_files:
                new_files_found = True
                notifier.send_new_files(course.name, new_files)

            for assignment in assignments:
                db.upsert_assignment(assignment)

            notes = compute_notifications(assignments, course.name, db)
            notifier.send_notifications(notes)
    finally:
        session.close()

    if send_no_new_files_alert and not new_files_found:
        notifier.send_no_new_files(len(courses))


def run_forever(custom_settings: Settings | None = None) -> None:
    cfg = custom_settings or settings
    setup_logging()
    interval_minutes = max(cfg.check_interval_minutes, 1)

    while True:
        start = datetime.now()
        try:
            run_once(cfg, send_no_new_files_alert=True, configure_logging=False)
        except KeyboardInterrupt:
            logger.info("Stopping LMS agent due to keyboard interrupt.")
            break
        except Exception:
            logger.exception("Run failed; will retry after the interval.")

        elapsed = (datetime.now() - start).total_seconds()
        sleep_seconds = max(0, interval_minutes * 60 - elapsed)
        logger.info("Sleeping for %.0f seconds before next check", sleep_seconds)
        time.sleep(sleep_seconds)


if __name__ == "__main__":
    run_forever()
