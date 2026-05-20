from datetime import datetime
from zoneinfo import ZoneInfo

from deal_alert.detector import detect_deal
from deal_alert.providers.base import ProviderItem
from deal_alert.telegram import build_payload


def test_telegram_payload_contains_required_fields() -> None:
    item = ProviderItem(
        id="1",
        source="test",
        url="https://www.coupang.com/products/1",
        author="dealbot",
        text="쿠팡 iPad Pro 역대가 특가 쿠폰 999,000원 https://www.coupang.com/products/1",
        created_at="2026-05-20T00:00:00Z",
    )
    result = detect_deal(item, min_score=8, viral_threshold=7)

    payload = build_payload(
        "123",
        result,
        now=datetime(2026, 5, 20, 9, 30, tzinfo=ZoneInfo("Asia/Seoul")),
    )

    assert payload["chat_id"] == "123"
    assert payload["disable_web_page_preview"] is True
    text = str(payload["text"])
    assert "상품/키워드:" in text
    assert "특가 점수:" in text
    assert "신뢰도:" in text
    assert "광고/바이럴 의심 사유:" in text
    assert "원문:" in text
    assert "URL: https://www.coupang.com/products/1" in text
    assert "소스: test" in text
    assert "2026-05-20 09:30:00 KST" in text
