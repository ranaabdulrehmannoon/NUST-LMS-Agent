from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Course:
    id: str
    name: str
    url: str


@dataclass
class FileItem:
    course_id: str
    name: str
    url: str
    modified_at: Optional[datetime]


@dataclass
class Assignment:
    course_id: str
    name: str
    url: str
    due_at: Optional[datetime]
    submitted: bool


@dataclass
class Notification:
    item_type: str
    item_key: str
    threshold: str
    course_name: str
    title: str
    due_at: Optional[datetime]
