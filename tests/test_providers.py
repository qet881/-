from deal_alert.config import Config
from deal_alert.providers import build_providers
from deal_alert.providers.json_feed import JsonFeedProvider
from deal_alert.providers.rss_feed import RssFeedProvider
from deal_alert.providers.threads import ThreadsProvider
from deal_alert.providers.x import XProvider


def test_x_and_threads_are_disabled_by_default() -> None:
    providers = build_providers(Config())

    assert [provider.name for provider in providers[:2]] == ["x", "threads"]
    assert all(provider.enabled is False for provider in providers[:2])


def test_x_and_threads_remain_disabled_even_if_env_flag_is_set() -> None:
    assert XProvider(enabled=True).enabled is False
    assert ThreadsProvider(enabled=True).enabled is False


def test_json_feed_accepts_posts_schema(monkeypatch) -> None:
    payload = b'{"posts":[{"id":123,"title":"MacBook Pro hot deal","price":2500000,"currency":"KRW","url":"https://example.com/p/123","created_at":"2026-05-20T00:00:00Z"}]}'

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return payload

    monkeypatch.setattr("urllib.request.urlopen", lambda request, timeout: Response())

    items = list(JsonFeedProvider(["https://example.com/feed.json"]).fetch())

    assert items[0].id == "123"
    assert items[0].url == "https://example.com/p/123"
    assert "MacBook Pro hot deal" in items[0].text
    assert "2500000" in items[0].text


def test_rss_feed_provider_parses_items(monkeypatch) -> None:
    payload = b"""<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0"><channel><title>Deals</title><item>
      <title>Apple Watch sale $199</title>
      <link>https://example.com/deal</link>
      <guid>deal-1</guid>
      <pubDate>Wed, 20 May 2026 06:00:00 GMT</pubDate>
      <description><![CDATA[<p>Coupon discount</p>]]></description>
    </item></channel></rss>"""

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return payload

    monkeypatch.setattr("urllib.request.urlopen", lambda request, timeout: Response())

    items = list(RssFeedProvider(["https://example.com/rss"]).fetch())

    assert items[0].id == "deal-1"
    assert items[0].source == "rss-feed"
    assert items[0].author == "Deals"
    assert items[0].url == "https://example.com/deal"
    assert "Apple Watch sale $199" in items[0].text
