from __future__ import annotations

from .base import DisabledProvider


class XProvider(DisabledProvider):
    def __init__(self, enabled: bool = False) -> None:
        reason = (
            "X public read/search is disabled in v1 because this project only "
            "uses free, official, terms-compliant access."
        )
        super().__init__(name="x", reason=reason, enabled=False and enabled)
