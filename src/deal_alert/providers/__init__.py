from __future__ import annotations

from deal_alert.config import Config

from .base import DisabledProvider, Provider, ProviderItem
from .json_feed import JsonFeedProvider
from .threads import ThreadsProvider
from .x import XProvider


def build_providers(config: Config) -> list[Provider]:
    providers: list[Provider] = [
        XProvider(enabled=config.enable_x_provider),
        ThreadsProvider(enabled=config.enable_threads_provider),
    ]
    if config.json_feed_urls:
        providers.append(JsonFeedProvider(config.json_feed_urls))
    return providers


__all__ = [
    "DisabledProvider",
    "JsonFeedProvider",
    "Provider",
    "ProviderItem",
    "ThreadsProvider",
    "XProvider",
    "build_providers",
]
