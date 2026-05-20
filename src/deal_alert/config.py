from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {raw!r}") from exc


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_csv(name: str) -> list[str]:
    raw = os.getenv(name, "")
    return [part.strip() for part in raw.split(",") if part.strip()]


@dataclass(frozen=True)
class Config:
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    min_score: int = 8
    viral_threshold: int = 7
    state_path: Path = Path("state/seen.json")
    re_alert_hours: int = 24
    enable_x_provider: bool = False
    enable_threads_provider: bool = False
    json_feed_urls: list[str] = field(default_factory=list)

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN") or None,
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID") or None,
            min_score=_env_int("MIN_SCORE", 8),
            viral_threshold=_env_int("VIRAL_THRESHOLD", 7),
            state_path=Path(os.getenv("DEAL_ALERT_STATE_PATH", "state/seen.json")),
            re_alert_hours=_env_int("RE_ALERT_HOURS", 24),
            enable_x_provider=_env_bool("ENABLE_X_PROVIDER", False),
            enable_threads_provider=_env_bool("ENABLE_THREADS_PROVIDER", False),
            json_feed_urls=_env_csv("DEAL_ALERT_JSON_FEED_URLS"),
        )

    @property
    def telegram_enabled(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_chat_id)
