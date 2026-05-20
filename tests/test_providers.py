from deal_alert.config import Config
from deal_alert.providers import build_providers
from deal_alert.providers.threads import ThreadsProvider
from deal_alert.providers.x import XProvider


def test_x_and_threads_are_disabled_by_default() -> None:
    providers = build_providers(Config())

    assert [provider.name for provider in providers[:2]] == ["x", "threads"]
    assert all(provider.enabled is False for provider in providers[:2])


def test_x_and_threads_remain_disabled_even_if_env_flag_is_set() -> None:
    assert XProvider(enabled=True).enabled is False
    assert ThreadsProvider(enabled=True).enabled is False
