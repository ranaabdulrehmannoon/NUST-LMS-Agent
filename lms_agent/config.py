from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    lms_base_url: str = Field(..., env="LMS_BASE_URL")
    lms_username: str = Field(..., env="LMS_USERNAME")
    lms_password: str = Field(..., env="LMS_PASSWORD")
    course_filter: Optional[List[str]] = Field(default=None, env="COURSE_FILTER")

    smtp_host: str = Field(..., env="SMTP_HOST")
    smtp_port: int = Field(default=587, env="SMTP_PORT")
    smtp_username: str = Field(..., env="SMTP_USERNAME")
    smtp_password: str = Field(..., env="SMTP_PASSWORD")
    smtp_from: str = Field(..., env="SMTP_FROM")
    smtp_to: str = Field(..., env="SMTP_TO")

    db_path: Path = Field(default=Path("lms_agent.db"))
    headless: bool = Field(default=True, env="HEADLESS")
    check_interval_minutes: int = Field(default=60, env="CHECK_INTERVAL_MINUTES")
    request_timeout: int = Field(default=30, env="REQUEST_TIMEOUT")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @field_validator("course_filter", mode="before")
    def split_courses(cls, value):
        if value in (None, "", [], ()):  # type: ignore
            return None
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    def get_smtp_to_list(self) -> List[str]:
        """Parse SMTP_TO as comma-separated string to list."""
        return [item.strip() for item in self.smtp_to.split(",") if item.strip()]


settings = Settings()
