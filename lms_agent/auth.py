from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional

from playwright.sync_api import Browser, BrowserContext, Error, Page, Playwright, sync_playwright

from .config import Settings

logger = logging.getLogger(__name__)


@dataclass
class LoggedInSession:
    playwright: Playwright
    browser: Browser
    context: BrowserContext
    page: Page

    def close(self) -> None:
        try:
            self.context.close()
            self.browser.close()
            self.playwright.stop()
        except Exception as exc:  # pragma: no cover - best effort cleanup
            logger.warning("Error during session close: %s", exc)


def login(settings: Settings) -> LoggedInSession:
    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=settings.headless)
    context = browser.new_context()
    page = context.new_page()

    login_url = settings.lms_base_url.rstrip("/") + "/login/index.php"
    logger.info("Navigating to login page: %s", login_url)
    page.goto(login_url, timeout=settings.request_timeout * 1000)

    _fill_if_present(page, selectors=["#username", "input[name='username']"], value=settings.lms_username)
    _fill_if_present(page, selectors=["#password", "input[name='password']"], value=settings.lms_password)

    _click_first(page, selectors=["#loginbtn", "button[type='submit']", "input[type='submit']"])
    page.wait_for_timeout(1000)

    if not _is_logged_in(page, settings):
        logger.error("Login failed; please verify credentials or selectors.")
        raise RuntimeError("Login failed")

    logger.info("Login successful")
    return LoggedInSession(playwright=pw, browser=browser, context=context, page=page)


def _fill_if_present(page: Page, selectors: list[str], value: str) -> None:
    for selector in selectors:
        try:
            element = page.wait_for_selector(selector, timeout=3000)
            element.fill(value)
            return
        except Error:
            continue
    raise RuntimeError(f"Could not find a username/password field using selectors {selectors}")


def _click_first(page: Page, selectors: list[str]) -> None:
    for selector in selectors:
        try:
            element = page.wait_for_selector(selector, timeout=3000)
            element.click()
            return
        except Error:
            continue
    raise RuntimeError(f"Could not click submit using selectors {selectors}")


def _is_logged_in(page: Page, settings: Settings) -> bool:
    markers = ["/logout.php", "log out", "Log out", "Dashboard"]
    time.sleep(1.0)
    content = page.content().lower()
    return any(marker.lower() in content for marker in markers)
