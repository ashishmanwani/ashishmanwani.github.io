"""
TelegramNotifier — sends messages via the Telegram Bot API.
Handles rate limiting with retry logic.
"""

import logging

import httpx

from api.config import settings

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}"


class TelegramNotifier:
    def __init__(self):
        self.token = settings.TELEGRAM_BOT_TOKEN
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    async def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: str = "MarkdownV2",
        disable_web_page_preview: bool = False,
    ) -> int | None:
        """
        Send a Telegram message. Returns the message_id on success, None on failure.
        Raises on rate limit (HTTP 429) so the caller can handle retry.
        """
        if not self.token:
            logger.warning("TELEGRAM_BOT_TOKEN not set — skipping message send")
            return None

        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_web_page_preview,
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{self.base_url}/sendMessage",
                json=payload,
            )

        if response.status_code == 429:
            retry_after = response.json().get("parameters", {}).get("retry_after", 30)
            raise Exception(f"Telegram rate limit: retry after {retry_after}")

        if response.status_code != 200:
            body = response.text
            raise Exception(f"Telegram API error {response.status_code}: {body}")

        data = response.json()
        if not data.get("ok"):
            raise Exception(f"Telegram API returned ok=false: {data}")

        return data["result"]["message_id"]

    def send_message_sync(
        self,
        chat_id: int,
        text: str,
        parse_mode: str = "MarkdownV2",
    ) -> int | None:
        """Synchronous wrapper for use in non-async contexts (e.g., Celery tasks)."""
        import asyncio
        return asyncio.run(self.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode))

    async def set_webhook(self, webhook_url: str) -> bool:
        """Register the Telegram webhook URL with the Bot API."""
        if not self.token:
            return False

        payload = {
            "url": webhook_url,
            "secret_token": settings.TELEGRAM_WEBHOOK_SECRET,
            "allowed_updates": ["message"],
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{self.base_url}/setWebhook",
                json=payload,
            )
        data = response.json()
        success = data.get("ok", False)
        if success:
            logger.info(f"Telegram webhook set to: {webhook_url}")
        else:
            logger.error(f"Failed to set Telegram webhook: {data}")
        return success

    async def delete_webhook(self) -> bool:
        """Remove the Telegram webhook (useful for testing with polling)."""
        if not self.token:
            return False
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(f"{self.base_url}/deleteWebhook")
        return response.json().get("ok", False)
