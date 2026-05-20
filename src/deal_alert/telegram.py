from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from .detector import DetectionResult
from .providers.base import ProviderItem


KST = ZoneInfo("Asia/Seoul")


def kst_now() -> datetime:
    return datetime.now(KST)


def build_message(result: DetectionResult, *, now: datetime | None = None) -> str:
    item = result.item
    timestamp = (now or kst_now()).astimezone(KST).strftime("%Y-%m-%d %H:%M:%S KST")
    products = ", ".join(result.matched_products) or "-"
    signals = ", ".join(result.matched_signals) or "-"
    reasons = ", ".join(result.reasons) or "특이사항 없음"
    excerpt = _excerpt(item.text)

    return "\n".join(
        [
            "[특가 후보]",
            f"상품/키워드: {products}",
            f"특가 신호: {signals}",
            f"특가 점수: {result.score}",
            f"신뢰도: {result.confidence}",
            f"광고/바이럴 의심 사유: {reasons}",
            f"원문: {excerpt}",
            f"URL: {item.url or '-'}",
            f"소스: {item.source}",
            f"작성자: {item.author or '-'}",
            f"시각: {timestamp}",
        ]
    )


def build_payload(chat_id: str, result: DetectionResult, *, now: datetime | None = None) -> dict[str, object]:
    return {
        "chat_id": chat_id,
        "text": build_message(result, now=now),
        "disable_web_page_preview": True,
    }


@dataclass
class TelegramClient:
    bot_token: str
    chat_id: str

    def send(self, result: DetectionResult) -> dict[str, object]:
        payload = build_payload(self.chat_id, result)
        encoded = urllib.parse.urlencode(payload).encode("utf-8")
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        request = urllib.request.Request(url, data=encoded, method="POST")
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read().decode("utf-8")
        return json.loads(body)


class DryRunTelegramClient:
    def __init__(self) -> None:
        self.sent: list[ProviderItem] = []
        self.payloads: list[dict[str, object]] = []

    def send(self, result: DetectionResult) -> dict[str, object]:
        self.sent.append(result.item)
        payload = build_payload("dry-run", result)
        self.payloads.append(payload)
        return {"ok": True, "dry_run": True, "payload": payload}


def _excerpt(text: str, limit: int = 180) -> str:
    collapsed = " ".join((text or "").split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 1] + "…"
