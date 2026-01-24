from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import List, Optional
from urllib.parse import urlparse, parse_qs

from dateutil import parser as date_parser
from playwright.sync_api import Page

from .models import Assignment, Course, FileItem

logger = logging.getLogger(__name__)


def extract_course_id(url: str) -> str:
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    if "id" in params and params["id"]:
        return params["id"][0]
    return parsed.path.rstrip("/").split("/")[-1]


def parse_datetime(text: str) -> Optional[datetime]:
    try:
        return date_parser.parse(text, fuzzy=True)
    except (ValueError, TypeError):
        return None


def get_enrolled_courses(page: Page, base_url: str, timeout_ms: int) -> List[Course]:
    site_home_url = base_url.rstrip("/")
    logger.info("Opening site home: %s", site_home_url)
    page.goto(site_home_url, timeout=timeout_ms)

    # Wait for courses to load dynamically
    try:
        page.wait_for_selector("a[href*='course/view.php']", timeout=timeout_ms)
        page.wait_for_timeout(1000)  # Extra wait for JS rendering
    except Exception:
        logger.warning("Timeout waiting for course links; continuing anyway")

    # Find all course name links (class "aalink coursename")
    # Note: There are two links per course: image link and name link
    # We want the name link specifically
    course_name_links = page.query_selector_all("a.aalink.coursename")
    logger.info("Found %d course name links", len(course_name_links))

    courses: List[Course] = []
    for anchor in course_name_links:
        href = anchor.get_attribute("href") or ""
        
        # Extract course name from nested span with class "text-truncate"
        course_name_elem = anchor.query_selector("span.text-truncate")
        name = ""
        if course_name_elem:
            name = (course_name_elem.inner_text() or "").strip()
        
        # Skip if name is still empty or too short
        if not href or not name or len(name) < 3:
            logger.debug("Skipping course with short name: %s", name[:50] if name else "(empty)")
            continue
        
        course_id = extract_course_id(href)
        # Avoid duplicates
        if not any(c.url == href for c in courses):
            courses.append(Course(id=course_id, name=name, url=href))
            logger.debug("Added course: %s (ID: %s)", name, course_id)
    
    logger.info("Found %d enrolled courses", len(courses))
    return courses


def fetch_course_content(page: Page, course: Course, timeout_ms: int) -> tuple[List[FileItem], List[Assignment]]:
    logger.info("Scraping course: %s", course.name)
    page.goto(course.url, timeout=timeout_ms)

    files = _scrape_files(page, course)
    assignments = _scrape_assignments(page, course)
    return files, assignments


def _scrape_files(page: Page, course: Course) -> List[FileItem]:
    items: List[FileItem] = []
    resource_selectors = [
        "li.activity.resource",  # standard resources
        "li.modtype_resource",
    ]
    resources = []
    for selector in resource_selectors:
        resources = page.query_selector_all(selector)
        if resources:
            break

    for resource in resources:
        link = resource.query_selector("a")
        if not link:
            continue
        href = link.get_attribute("href") or ""
        name = (link.inner_text() or "").strip()
        mod_text = resource.inner_text()
        modified_at = _find_modified_date(mod_text)
        if not href or not name:
            continue
        items.append(FileItem(course_id=course.id, name=name, url=href, modified_at=modified_at))
    return items


def _find_modified_date(text: str) -> Optional[datetime]:
    candidates = re.findall(r"(\d{1,2}\s+\w+\s+\d{4}[^\n]*)", text)
    for candidate in candidates:
        parsed = parse_datetime(candidate)
        if parsed:
            return parsed
    return None


def _scrape_assignments(page: Page, course: Course) -> List[Assignment]:
    items: List[Assignment] = []
    selectors = [
        "li.modtype_assign",  # standard assignments
        "li.activity.assign",
    ]
    blocks = []
    for selector in selectors:
        blocks = page.query_selector_all(selector)
        if blocks:
            break

    for block in blocks:
        link = block.query_selector("a")
        if not link:
            continue
        href = link.get_attribute("href") or ""
        name = (link.inner_text() or "").strip()
        if not href or not name:
            continue

        text = block.inner_text()
        due_at = _extract_due(text)
        submitted = "submitted" in text.lower() or "graded" in text.lower()
        items.append(
            Assignment(
                course_id=course.id,
                name=name,
                url=href,
                due_at=due_at,
                submitted=submitted,
            )
        )
    return items


def _extract_due(text: str) -> Optional[datetime]:
    patterns = [
        r"Due:\s*(.*)",
        r"Due date\s*(.*)",
        r"Deadline\s*(.*)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            parsed = parse_datetime(match.group(1))
            if parsed:
                return parsed
    return None
