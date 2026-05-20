from __future__ import annotations

import hashlib
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from html import unescape
from typing import Iterable

from .base import ProviderItem


@dataclass
class RssFeedProvider:
    urls: list[str]
    name: str = "rss-feed"
    enabled: bool = True

    def fetch(self) -> Iterable[ProviderItem]:
        for url in self.urls:
            yield from self._fetch_url(url)

    def _fetch_url(self, url: str) -> Iterable[ProviderItem]:
        if not url.startswith("https://"):
            raise ValueError(f"Only HTTPS RSS feeds are allowed: {url}")

        request = urllib.request.Request(
            url,
            headers={"User-Agent": "deal-alert/0.1 (+https://github.com/)"},
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = response.read()

        root = ET.fromstring(payload)
        channel_title = _find_text(root, "./channel/title") or self.name
        for item in root.findall("./channel/item"):
            title = _find_text(item, "title")
            description = _find_text(item, "description")
            link = _find_text(item, "link")
            guid = _find_text(item, "guid") or link or _stable_id(title, description)
            pub_date = _find_text(item, "pubDate")
            text = " ".join(part for part in [title, _strip_html(description)] if part)
            yield ProviderItem(
                id=guid,
                source=self.name,
                url=link,
                author=channel_title,
                text=text,
                created_at=pub_date,
            )


def _find_text(node: ET.Element, path: str) -> str:
    child = node.find(path)
    if child is None or child.text is None:
        return ""
    return unescape(child.text.strip())


def _strip_html(value: str) -> str:
    text = unescape(value or "")
    output: list[str] = []
    in_tag = False
    for char in text:
        if char == "<":
            in_tag = True
            output.append(" ")
        elif char == ">":
            in_tag = False
        elif not in_tag:
            output.append(char)
    return " ".join("".join(output).split())


def _stable_id(*parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return digest[:16]
