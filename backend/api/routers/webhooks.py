import hmac
import hashlib
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.db.session import get_db
from api.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/telegram")
async def telegram_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
):
    """
    Receives messages from Telegram Bot API.
    Handles /start {magic_token} to link a user's Telegram account.
    """
    # Verify webhook secret
    if x_telegram_bot_api_secret_token != settings.TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid webhook secret")

    body = await request.json()
    message = body.get("message", {})
    text = message.get("text", "")
    chat = message.get("chat", {})
    chat_id = chat.get("id")

    if not chat_id:
        return {"ok": True}

    # Handle /start {token} deep link
    if text.startswith("/start "):
        magic_token = text[len("/start "):].strip()
        result = await db.execute(
            select(User).where(User.telegram_link_token == magic_token)
        )
        user = result.scalar_one_or_none()

        if user:
            user.telegram_chat_id = chat_id
            user.telegram_link_token = None  # consume the token
            db.add(user)
            await db.commit()
            logger.info(f"Linked Telegram chat_id={chat_id} to user={user.id}")
            # Send confirmation via Telegram
            try:
                from notifications.telegram import TelegramNotifier
                notifier = TelegramNotifier()
                await notifier.send_message(
                    chat_id=chat_id,
                    text="✅ Your Telegram account is now linked to Price Tracker!\n\nYou'll receive alerts here when tracked prices drop.",
                )
            except Exception as e:
                logger.warning(f"Could not send confirmation message: {e}")
        else:
            logger.warning(f"Invalid magic token received from chat_id={chat_id}")

    return {"ok": True}
