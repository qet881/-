from deal_alert.config import Config
from deal_alert.main import run
from deal_alert.providers.base import ProviderItem
from deal_alert.telegram import DryRunTelegramClient


class FailingProvider:
    name = "failing"
    enabled = True

    def fetch(self):
        raise RuntimeError("provider failed")


class StaticProvider:
    name = "static"
    enabled = True

    def fetch(self):
        return [
            ProviderItem(
                id="1",
                source="static",
                url="https://www.coupang.com/products/1",
                author="dealbot",
                text="쿠팡 iPad Pro 역대가 특가 쿠폰 999,000원 https://www.coupang.com/products/1",
                created_at="2026-05-20T00:00:00Z",
            )
        ]


def test_provider_failure_isolated_and_other_provider_alerts(tmp_path) -> None:
    config = Config(state_path=tmp_path / "seen.json", min_score=8, viral_threshold=7)
    telegram = DryRunTelegramClient()

    summary = run(
        config,
        dry_run=False,
        providers=[FailingProvider(), StaticProvider()],
        telegram_client=telegram,
    )

    assert summary.provider_failures == 1
    assert summary.fetched == 1
    assert summary.alerted == 1
    assert len(telegram.payloads) == 1


def test_duplicate_candidate_is_not_sent_twice(tmp_path) -> None:
    config = Config(state_path=tmp_path / "seen.json", min_score=8, viral_threshold=7)
    telegram = DryRunTelegramClient()

    first = run(config, dry_run=False, providers=[StaticProvider()], telegram_client=telegram)
    second = run(config, dry_run=False, providers=[StaticProvider()], telegram_client=telegram)

    assert first.alerted == 1
    assert second.alerted == 0
    assert len(telegram.payloads) == 1
