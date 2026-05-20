from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass

from .config import Config
from .detector import DetectionResult, detect_deal
from .providers import Provider, build_providers
from .state import SeenState
from .telegram import DryRunTelegramClient, TelegramClient

LOGGER = logging.getLogger("deal_alert")


@dataclass
class RunSummary:
    fetched: int = 0
    candidates: int = 0
    alerted: int = 0
    blocked: int = 0
    provider_failures: int = 0
    disabled_providers: int = 0


def run(
    config: Config,
    *,
    dry_run: bool = False,
    providers: list[Provider] | None = None,
    telegram_client: TelegramClient | DryRunTelegramClient | None = None,
) -> RunSummary:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    state = SeenState.load(config.state_path)
    providers = providers if providers is not None else build_providers(config)
    summary = RunSummary()

    if telegram_client is None:
        if dry_run:
            telegram_client = DryRunTelegramClient()
        elif config.telegram_enabled:
            telegram_client = TelegramClient(config.telegram_bot_token or "", config.telegram_chat_id or "")

    for provider in providers:
        if not provider.enabled:
            summary.disabled_providers += 1
            reason = getattr(provider, "reason", "disabled")
            LOGGER.info("Provider %s disabled: %s", provider.name, reason)
            continue

        try:
            items = list(provider.fetch())
        except Exception:
            summary.provider_failures += 1
            LOGGER.exception("Provider %s failed; continuing", provider.name)
            continue

        for item in items:
            summary.fetched += 1
            result = detect_deal(
                item,
                min_score=config.min_score,
                viral_threshold=config.viral_threshold,
                author_history=state.author_history(item),
            )
            state.mark_seen(item)

            if result.category:
                summary.candidates += 1
            if result.blocked:
                summary.blocked += 1
                LOGGER.info("Blocked candidate %s: %s", item.url or item.id, "; ".join(result.reasons))
                continue
            if not result.should_alert:
                LOGGER.info("Skipped candidate %s: %s", item.url or item.id, "; ".join(result.reasons))
                continue
            if not state.should_notify(item, re_alert_hours=config.re_alert_hours):
                LOGGER.info("Duplicate candidate skipped: %s", item.url or item.id)
                continue
            if telegram_client is None:
                LOGGER.warning("Telegram is not configured; alert not sent for %s", item.url or item.id)
                continue

            telegram_client.send(result)
            state.mark_notified(item)
            summary.alerted += 1
            if dry_run:
                LOGGER.info("Dry-run alert prepared for %s", item.url or item.id)

    if not dry_run:
        state.save()

    LOGGER.info(
        "Summary fetched=%s candidates=%s alerted=%s blocked=%s provider_failures=%s disabled_providers=%s",
        summary.fetched,
        summary.candidates,
        summary.alerted,
        summary.blocked,
        summary.provider_failures,
        summary.disabled_providers,
    )
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Detect conservative deal candidates and alert Telegram.")
    parser.add_argument("--dry-run", action="store_true", help="Run without sending Telegram messages or saving state.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = Config.from_env()
    run(config, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
