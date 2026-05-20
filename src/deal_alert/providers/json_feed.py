from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from typing import Iterable

from .base import ProviderItem


@dataclass
class JsonFeedProvider:
    urls: list[str]
    name: str = "json-feed"
    enabled: bool = True

    def fetch(self) -> Iterable[ProviderItem]:
        for url in self.urls:
            yield from self._fetch_url(url)

    def _fetch_url(self, url: str) -> Iterable[ProviderItem]:
        if not url.startswith("https://"):
            raise ValueError(f"Only HTTPS JSON feeds are allowed: {url}")

        request = urllib.request.Request(
            url,
            headers={"User-Agent": "deal-alert/0.1 (+https://github.com/)"},
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))

        raw_items = payload.get("items", payload) if isinstance(payload, dict) else payload
        if not isinstance(raw_items, list):
            raise ValueError(f"JSON feed must be a list or an object with items: {url}")

        for raw in raw_items:
            if not isinstance(raw, dict):
                continue
            yield ProviderItem(
                id=str(raw.get("id") or raw.get("url") or ""),
                source=str(raw.get("source") or self.name),
                url=str(raw.get("url") or ""),
                author=str(raw.get("author") or ""),
                text=str(raw.get("text") or ""),
                created_at=str(raw.get("created_at") or ""),
            )
