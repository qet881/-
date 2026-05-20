from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from urllib.parse import urlparse

from .providers.base import ProviderItem

APPLE_KEYWORDS = [
    "아이패드",
    "ipad",
    "ipad pro",
    "macbook",
    "맥북",
    "airpods",
    "에어팟",
    "apple watch",
    "iphone",
    "애플펜슬",
]

AI_KEYWORDS = [
    "chatgpt pro",
    "gpt pro",
    "chatgpt plus",
    "claude",
    "claude pro",
    "gemini",
    "perplexity",
    "cursor",
    "copilot",
    "midjourney",
    "notion ai",
]

DEAL_SIGNALS = [
    "오가격",
    "역대가",
    "대란",
    "실수",
    "품절",
    "쿠폰",
    "반값",
    "무료",
    "할인",
    "핫딜",
    "특가",
    "카카오톡 선물하기",
    "쿠팡",
]

AD_KEYWORDS = [
    "광고",
    "협찬",
    "제휴",
    "파트너스",
    "쿠팡파트너스",
    "추천코드",
    "레퍼럴",
    "초대코드",
    "체험단",
    "공구",
    "댓글 링크",
    "프로필 링크",
    "dm",
    "카톡 문의",
    "오픈채팅",
]

AI_RISK_PATTERNS = [
    "평생 이용권",
    "무제한",
    "계정 공유",
    "대리 결제",
    "우회 결제",
    "vpn",
    "터키",
    "아르헨티나",
    "인도 우회",
    "월 몇천원",
    "공식보다 싸게",
]

NEGATED_AD_PATTERNS = [
    r"광고\s*(아님|아닙니다|아니에요|아니다)",
    r"협찬\s*(아님|아닙니다|아니에요|아니다)",
    r"제휴\s*(아님|아닙니다|아니에요|아니다)",
    r"파트너스\s*(아님|아닙니다|아니에요|아니다)",
]

SHORT_URL_HOSTS = {
    "bit.ly",
    "tinyurl.com",
    "t.co",
    "url.kr",
    "vo.la",
    "han.gl",
    "me2.kr",
    "is.gd",
    "cutt.ly",
    "linktr.ee",
}

VENDOR_KEYWORDS = [
    "쿠팡",
    "카카오톡 선물하기",
    "11번가",
    "g마켓",
    "지마켓",
    "옥션",
    "하이마트",
    "애플",
    "apple store",
    "공식",
    "openai",
    "anthropic",
    "google",
    "perplexity",
    "cursor",
    "github",
    "midjourney",
    "notion",
]

AI_OFFICIAL_HOSTS = {
    "openai.com",
    "chatgpt.com",
    "anthropic.com",
    "claude.ai",
    "google.com",
    "gemini.google.com",
    "perplexity.ai",
    "cursor.com",
    "cursor.sh",
    "github.com",
    "midjourney.com",
    "notion.so",
}

OFFICIAL_MONTHLY_USD = {
    "chatgpt pro": 200.0,
    "gpt pro": 200.0,
    "chatgpt plus": 20.0,
    "claude": 20.0,
    "claude pro": 20.0,
    "gemini": 19.99,
    "perplexity": 20.0,
    "cursor": 20.0,
    "copilot": 10.0,
    "midjourney": 10.0,
    "notion ai": 10.0,
}

URL_RE = re.compile(r"https?://[^\s)>\]]+", re.IGNORECASE)
KRW_RE = re.compile(r"(?P<num>\d[\d,\.]*)\s*(원|₩|만원|천원)")
USD_RE = re.compile(r"(\$|usd\s*)(?P<num>\d+(?:\.\d+)?)", re.IGNORECASE)
PERCENT_RE = re.compile(r"\d{1,2}\s*%")


@dataclass(frozen=True)
class DetectionResult:
    item: ProviderItem
    category: str | None
    matched_products: list[str] = field(default_factory=list)
    matched_signals: list[str] = field(default_factory=list)
    score: int = 0
    viral_score: int = 0
    confidence: str = "low"
    reasons: list[str] = field(default_factory=list)
    blocked: bool = False
    should_alert: bool = False


def detect_deal(
    item: ProviderItem,
    *,
    min_score: int,
    viral_threshold: int,
    author_history: list[str] | None = None,
) -> DetectionResult:
    text = item.text or ""
    normalized = _normalize(text)
    urls = _extract_urls(item)

    apple_matches = _matches(normalized, APPLE_KEYWORDS)
    ai_matches = _matches(normalized, AI_KEYWORDS)
    if not apple_matches and not ai_matches:
        return DetectionResult(
            item=item,
            category=None,
            reasons=["관심 상품 키워드 없음"],
        )

    category = "ai" if ai_matches else "apple"
    products = ai_matches if ai_matches else apple_matches
    signals = _matches(normalized, DEAL_SIGNALS)
    completeness = _completeness(normalized, urls)

    score = 2
    score += min(len(products), 2) * 2
    score += min(len(signals), 4) * 2
    score += completeness * 1
    if PERCENT_RE.search(normalized) or KRW_RE.search(normalized) or USD_RE.search(normalized):
        score += 2

    viral_score, reasons = _viral_penalty(normalized, urls, author_history or [], completeness)
    score = max(0, score - min(viral_score, 12))
    blocked = False

    if category == "ai":
        ai_risk_matches = _matches(normalized, AI_RISK_PATTERNS)
        if ai_risk_matches:
            viral_score += len(ai_risk_matches) * 5
            reasons.append("AI 구독 사기/바이럴 위험 표현: " + ", ".join(ai_risk_matches))

        official = _has_ai_official_url(urls)
        if not official:
            viral_score += 4
            blocked = True
            reasons.append("AI 구독권 공식/검증 판매처 URL 없음")

        cheap_reason = _official_price_discount_reason(normalized, products)
        if cheap_reason:
            viral_score += 7
            blocked = True
            reasons.append(cheap_reason)

        if ai_risk_matches:
            blocked = True

    if category == "apple" and score < min_score:
        reasons.append("특가 점수 기준 미달")
    if category == "ai" and viral_score >= viral_threshold:
        reasons.append("바이럴 점수 기준 초과")

    confidence = _confidence(score, viral_score, completeness, blocked)
    should_alert = (
        not blocked
        and score >= min_score
        and (category == "apple" or viral_score < viral_threshold)
    )

    return DetectionResult(
        item=item,
        category=category,
        matched_products=products,
        matched_signals=signals,
        score=score,
        viral_score=viral_score,
        confidence=confidence,
        reasons=reasons,
        blocked=blocked,
        should_alert=should_alert,
    )


def _normalize(text: str) -> str:
    return " ".join(text.casefold().split())


def _matches(normalized: str, keywords: list[str]) -> list[str]:
    return [keyword for keyword in keywords if keyword.casefold() in normalized]


def _extract_urls(item: ProviderItem) -> list[str]:
    urls = URL_RE.findall(item.text or "")
    if item.url:
        urls.append(item.url)
    return list(dict.fromkeys(urls))


def _ad_text_without_negations(normalized: str) -> str:
    filtered = normalized
    for pattern in NEGATED_AD_PATTERNS:
        filtered = re.sub(pattern, " ", filtered, flags=re.IGNORECASE)
    return filtered


def _viral_penalty(
    normalized: str,
    urls: list[str],
    author_history: list[str],
    completeness: int,
) -> tuple[int, list[str]]:
    viral_score = 0
    reasons: list[str] = []
    ad_text = _ad_text_without_negations(normalized)
    ad_matches = _matches(ad_text, AD_KEYWORDS)
    if ad_matches:
        viral_score += len(ad_matches) * 3
        reasons.append("광고/제휴 의심 표현: " + ", ".join(ad_matches))

    if len(urls) >= 3:
        viral_score += 2
        reasons.append("링크 과다")

    short_hosts = sorted({urlparse(url).netloc.casefold().removeprefix("www.") for url in urls})
    short_matches = [host for host in short_hosts if host in SHORT_URL_HOSTS]
    if short_matches:
        viral_score += 3
        reasons.append("단축 URL 포함: " + ", ".join(short_matches))

    if completeness < 2:
        viral_score += 2
        reasons.append("가격/판매처/구매 링크/할인 조건 정보 부족")

    if _repeated_author_text(normalized, author_history):
        viral_score += 3
        reasons.append("같은 작성자의 반복 문구 의심")

    return viral_score, reasons


def _completeness(normalized: str, urls: list[str]) -> int:
    count = 0
    if KRW_RE.search(normalized) or USD_RE.search(normalized) or "무료" in normalized or "반값" in normalized:
        count += 1
    if _matches(normalized, VENDOR_KEYWORDS):
        count += 1
    if urls:
        count += 1
    if any(token in normalized for token in ["쿠폰", "할인", "카드", "선착순", "무료", "반값", "특가"]):
        count += 1
    return count


def _repeated_author_text(normalized: str, author_history: list[str]) -> bool:
    if not author_history:
        return False
    for previous in author_history[-10:]:
        previous_normalized = _normalize(previous)
        if not previous_normalized:
            continue
        if normalized[:80] == previous_normalized[:80]:
            return True
        if SequenceMatcher(None, normalized, previous_normalized).ratio() >= 0.88:
            return True
    return False


def _has_ai_official_url(urls: list[str]) -> bool:
    for url in urls:
        host = urlparse(url).netloc.casefold().removeprefix("www.")
        if host in AI_OFFICIAL_HOSTS or any(host.endswith("." + official) for official in AI_OFFICIAL_HOSTS):
            return True
    return False


def _official_price_discount_reason(normalized: str, products: list[str]) -> str | None:
    advertised_usd = _extract_monthly_usd(normalized)
    if advertised_usd is None:
        return None
    official_prices = [OFFICIAL_MONTHLY_USD[p] for p in products if p in OFFICIAL_MONTHLY_USD]
    if not official_prices:
        return None
    official = min(official_prices)
    if advertised_usd <= official * 0.30:
        return "사기/바이럴 의심: 공식가 대비 70% 이상 저렴"
    return None


def _extract_monthly_usd(normalized: str) -> float | None:
    usd_match = USD_RE.search(normalized)
    if usd_match:
        return float(usd_match.group("num"))

    krw_match = KRW_RE.search(normalized)
    if not krw_match:
        return None
    raw = krw_match.group("num").replace(",", "")
    amount = float(raw)
    unit = krw_match.group(2)
    if unit == "만원":
        amount *= 10_000
    elif unit == "천원":
        amount *= 1_000
    return amount / 1350.0


def _confidence(score: int, viral_score: int, completeness: int, blocked: bool) -> str:
    if blocked or viral_score >= 7 or completeness < 2:
        return "low"
    if score >= 11 and completeness >= 3 and viral_score <= 2:
        return "high"
    return "medium"
