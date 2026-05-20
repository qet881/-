from deal_alert.detector import detect_deal
from deal_alert.providers.base import ProviderItem


def item(text: str, url: str = "https://www.coupang.com/products/1") -> ProviderItem:
    return ProviderItem(
        id="1",
        source="test",
        url=url,
        author="seller",
        text=text,
        created_at="2026-05-20T00:00:00Z",
    )


def test_apple_deal_scores_and_alerts() -> None:
    result = detect_deal(
        item("쿠팡 iPad Pro 역대가 특가 쿠폰 적용 999,000원 https://www.coupang.com/products/1"),
        min_score=8,
        viral_threshold=7,
    )

    assert result.category == "apple"
    assert result.score >= 8
    assert result.should_alert is True
    assert result.blocked is False


def test_interest_product_is_required() -> None:
    result = detect_deal(
        item("쿠팡 역대가 특가 쿠폰 9,900원"),
        min_score=8,
        viral_threshold=7,
    )

    assert result.category is None
    assert result.should_alert is False
    assert "관심 상품 키워드 없음" in result.reasons


def test_ad_and_affiliate_terms_are_penalized() -> None:
    result = detect_deal(
        item("쿠팡파트너스 광고 iPad 핫딜 특가 쿠폰 800,000원 댓글 링크 확인"),
        min_score=8,
        viral_threshold=7,
    )

    assert result.viral_score >= 6
    assert result.should_alert is False
    assert any("광고/제휴" in reason for reason in result.reasons)


def test_negated_ad_terms_do_not_trigger_ad_penalty() -> None:
    result = detect_deal(
        item("광고 아님 제휴 아님 쿠팡 iPad 특가 쿠폰 800,000원 https://www.coupang.com/products/2"),
        min_score=8,
        viral_threshold=7,
    )

    assert not any("광고/제휴" in reason for reason in result.reasons)


def test_short_url_and_excessive_links_are_penalized() -> None:
    result = detect_deal(
        item(
            "쿠팡 iPad 특가 쿠폰 800,000원 https://bit.ly/a https://example.com/b https://example.com/c",
            url="https://www.coupang.com/products/3",
        ),
        min_score=8,
        viral_threshold=7,
    )

    assert result.viral_score >= 5
    assert any("링크 과다" in reason for reason in result.reasons)
    assert any("단축 URL" in reason for reason in result.reasons)


def test_ai_subscription_without_official_vendor_is_blocked() -> None:
    result = detect_deal(
        item("ChatGPT Plus 특가 할인 월 9,900원 선착순 구매 링크", url="https://example.com/chatgpt"),
        min_score=8,
        viral_threshold=7,
    )

    assert result.category == "ai"
    assert result.blocked is True
    assert result.should_alert is False
    assert any("공식/검증 판매처" in reason for reason in result.reasons)


def test_ai_scam_patterns_are_blocked() -> None:
    result = detect_deal(
        item(
            "ChatGPT Pro 평생 이용권 무제한 계정 공유 월 몇천원 공식보다 싸게",
            url="https://chatgpt.com/pricing",
        ),
        min_score=8,
        viral_threshold=7,
    )

    assert result.blocked is True
    assert result.should_alert is False
    assert any("AI 구독 사기/바이럴" in reason for reason in result.reasons)


def test_ai_70_percent_below_official_price_is_blocked() -> None:
    result = detect_deal(
        item(
            "ChatGPT Plus 공식 특가 할인 $5 쿠폰 https://chatgpt.com/pricing",
            url="https://chatgpt.com/pricing",
        ),
        min_score=8,
        viral_threshold=7,
    )

    assert result.blocked is True
    assert result.should_alert is False
    assert any("70% 이상 저렴" in reason for reason in result.reasons)


def test_repeated_author_phrase_is_penalized() -> None:
    text = "쿠팡 iPad Pro 역대가 특가 쿠폰 적용 999,000원 https://www.coupang.com/products/1"
    result = detect_deal(
        item(text),
        min_score=8,
        viral_threshold=7,
        author_history=[text],
    )

    assert result.viral_score >= 3
    assert any("반복 문구" in reason for reason in result.reasons)
