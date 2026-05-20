from datetime import timedelta

from deal_alert.providers.base import ProviderItem
from deal_alert.state import SeenState, item_key, utc_now


def make_item(url: str = "https://example.com/post/1") -> ProviderItem:
    return ProviderItem(
        id="post-1",
        source="test",
        url=url,
        author="author",
        text="iPad 특가",
        created_at="2026-05-20T00:00:00Z",
    )


def test_state_dedupes_by_url(tmp_path) -> None:
    path = tmp_path / "seen.json"
    state = SeenState.load(path)
    candidate = make_item()

    assert state.should_notify(candidate) is True
    state.mark_notified(candidate)
    assert state.should_notify(candidate) is False

    state.save()
    loaded = SeenState.load(path)
    assert item_key(candidate) in loaded.seen
    assert loaded.should_notify(candidate) is False


def test_state_keeps_notified_items_new_only_after_realert_window(tmp_path) -> None:
    state = SeenState.load(tmp_path / "seen.json")
    candidate = make_item()
    state.mark_notified(candidate)
    key = item_key(candidate)
    state.seen[key]["last_notified"] = (utc_now() - timedelta(hours=25)).isoformat()

    assert state.should_notify(candidate, re_alert_hours=24) is False


def test_author_history_is_recorded(tmp_path) -> None:
    state = SeenState.load(tmp_path / "seen.json")
    candidate = make_item()
    state.mark_seen(candidate)

    assert state.author_history(candidate) == ["iPad 특가"]
