from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .providers.base import ProviderItem


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def item_key(item: ProviderItem) -> str:
    if item.url:
        return f"url:{item.url.strip()}"
    return f"post:{item.source}:{item.id}"


@dataclass
class SeenState:
    path: Path
    seen: dict[str, dict[str, Any]] = field(default_factory=dict)
    authors: dict[str, list[dict[str, str]]] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> "SeenState":
        if not path.exists():
            return cls(path=path)
        with path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        return cls(
            path=path,
            seen=dict(payload.get("seen", {})),
            authors=dict(payload.get("authors", {})),
        )

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "seen": self.seen,
            "authors": self.authors,
        }
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write("\n")

    def should_notify(self, item: ProviderItem, *, re_alert_hours: int = 24) -> bool:
        record = self.seen.get(item_key(item))
        if not record:
            return True

        last_notified = record.get("last_notified")
        if not last_notified:
            return True
        return False

    def mark_seen(self, item: ProviderItem) -> None:
        key = item_key(item)
        now = utc_now().isoformat()
        record = self.seen.setdefault(key, {})
        record.update(
            {
                "id": item.id,
                "source": item.source,
                "url": item.url,
                "author": item.author,
                "last_seen": now,
            }
        )
        record.setdefault("first_seen", now)
        self._remember_author_text(item, now)

    def mark_notified(self, item: ProviderItem) -> None:
        self.mark_seen(item)
        self.seen[item_key(item)]["last_notified"] = utc_now().isoformat()

    def author_history(self, item: ProviderItem) -> list[str]:
        author_key = self._author_key(item)
        return [entry.get("text", "") for entry in self.authors.get(author_key, [])]

    def _remember_author_text(self, item: ProviderItem, now: str) -> None:
        if not item.author:
            return
        author_key = self._author_key(item)
        entries = self.authors.setdefault(author_key, [])
        entries.append({"text": item.text[:500], "seen_at": now})
        del entries[:-20]

    @staticmethod
    def _author_key(item: ProviderItem) -> str:
        return f"{item.source}:{item.author.casefold()}"
