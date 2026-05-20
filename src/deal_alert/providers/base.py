from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Protocol


@dataclass(frozen=True)
class ProviderItem:
    id: str
    source: str
    url: str
    author: str
    text: str
    created_at: str


class Provider(Protocol):
    name: str
    enabled: bool

    def fetch(self) -> Iterable[ProviderItem]:
        ...


@dataclass
class DisabledProvider:
    name: str
    reason: str
    enabled: bool = False

    def fetch(self) -> list[ProviderItem]:
        return []
