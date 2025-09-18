from __future__ import annotations

import logging
from fastapi import FastAPI, Request, HTTPException
from aiogram.types import Update

from .config import get_settings
from .bot import bot, dp
from .db import init_db


logger = logging.getLogger(__name__)
settings = get_settings()
app = FastAPI(title="Girls Quiz Bot")


@app.on_event("startup")
async def on_startup() -> None:
    try:
        await init_db()
    except Exception as e:
        logger.warning("DB init skipped (non-fatal): %s", e)
    url = settings.WEBHOOK_BASE_URL.rstrip("/") + "/webhook"
    await bot.set_webhook(url=url, secret_token=settings.WEBHOOK_SECRET_TOKEN, drop_pending_updates=True)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    try:
        await bot.delete_webhook(drop_pending_updates=False)
    except Exception:
        pass


@app.post("/webhook")
async def telegram_webhook(request: Request):
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if secret != settings.WEBHOOK_SECRET_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid secret token")

    data = await request.json()
    update = Update.model_validate(data)

    # Debug: log update type and minimal context
    try:
        kind = (
            "message" if update.message else
            "channel_post" if update.channel_post else
            "callback_query" if update.callback_query else
            "my_chat_member" if update.my_chat_member else
            "chat_member" if update.chat_member else
            "unknown"
        )
        chat_id = (
            update.message.chat.id if update.message else
            update.channel_post.chat.id if update.channel_post else
            update.callback_query.message.chat.id if update.callback_query and update.callback_query.message else
            None
        )
        text = (
            update.message.text if update.message else
            update.channel_post.text if update.channel_post else
            update.callback_query.data if update.callback_query else
            None
        )
        logger.info("Incoming update kind=%s chat_id=%s text=%s", kind, chat_id, text)
    except Exception:
        pass

    try:
        await dp.feed_update(bot, update)
    except Exception as e:
        logger.exception("Error while processing update: %s", e)
    return {"ok": True}
