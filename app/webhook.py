from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from fastapi import FastAPI, Request, HTTPException
from aiogram.types import Update

from .config import get_settings
from .bot import bot, dp
from .db import init_db


logging.basicConfig(level=logging.INFO)
aiologger = logging.getLogger("aiogram")
aiologger.setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)
settings = get_settings()
app = FastAPI(title="Girls Quiz Bot")

START_MONO = time.perf_counter()
START_WALL = datetime.now(timezone.utc)


def _extract_update_datetime(update: Update) -> datetime | None:
    if update.message and update.message.date:
        return update.message.date
    if update.channel_post and update.channel_post.date:
        return update.channel_post.date
    if update.edited_message and update.edited_message.date:
        return update.edited_message.date
    if update.edited_channel_post and update.edited_channel_post.date:
        return update.edited_channel_post.date
    if update.callback_query and update.callback_query.message and update.callback_query.message.date:
        return update.callback_query.message.date
    return None


@app.on_event("startup")
async def on_startup() -> None:
    try:
        await init_db()
    except Exception as e:
        logger.warning("DB init skipped (non-fatal): %s", e)
    url = settings.WEBHOOK_BASE_URL.rstrip("/") + "/webhook"
    logger.info("Setting webhook to %s", url)
    await bot.set_webhook(url=url, secret_token=settings.WEBHOOK_SECRET_TOKEN, drop_pending_updates=True)
    try:
        info = await bot.get_webhook_info()
        logger.info(
            "Webhook info: url=%s pending=%s ip=%s last_error_date=%s last_error_message=%s max_conn=%s",
            info.url,
            info.pending_update_count,
            getattr(info, "ip_address", None),
            getattr(info, "last_error_date", None),
            getattr(info, "last_error_message", None),
            getattr(info, "max_connections", None),
        )
    except Exception as e:
        logger.warning("Failed to get webhook info: %s", e)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    try:
        await bot.delete_webhook(drop_pending_updates=False)
    except Exception:
        pass


@app.post("/webhook")
async def telegram_webhook(request: Request):
    t0 = time.perf_counter()
    client = request.client
    raw = await request.body()
    t_body = time.perf_counter()
    # Truncate to avoid giant logs
    body_preview = raw.decode("utf-8", errors="ignore")[:4000]
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    logger.info(
        "Webhook POST from %s:%s secret_present=%s body_len=%s since_start_s=%.3f",
        getattr(client, "host", None) if client else None,
        getattr(client, "port", None) if client else None,
        bool(secret),
        len(raw),
        t0 - START_MONO,
    )

    if secret != settings.WEBHOOK_SECRET_TOKEN:
        logger.warning("Secret token mismatch: got=%s expected=%s", secret, settings.WEBHOOK_SECRET_TOKEN)
        raise HTTPException(status_code=401, detail="Invalid secret token")

    try:
        data = json.loads(body_preview) if body_preview else {}
    except Exception:
        data = await request.json()

    update = Update.model_validate(data)

    # Debug: log update type, lag and minimal context
    try:
        now = datetime.now(timezone.utc)
        upd_dt = _extract_update_datetime(update)
        lag_s = (now - upd_dt).total_seconds() if upd_dt else None
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
        logger.info(
            "Parsed update id=%s kind=%s chat_id=%s lag_s=%s text=%s",
            getattr(update, "update_id", None),
            kind,
            chat_id,
            f"{lag_s:.3f}" if isinstance(lag_s, float) else None,
            text,
        )
    except Exception:
        pass

    t_dispatch0 = time.perf_counter()
    try:
        logger.info("Dispatching update to aiogram handlers...")
        await dp.feed_update(bot, update)
        logger.info(
            "Update dispatched successfully parse_ms=%.1f dispatch_ms=%.1f total_ms=%.1f",
            (t_dispatch0 - t_body) * 1000.0,
            (time.perf_counter() - t_dispatch0) * 1000.0,
            (time.perf_counter() - t0) * 1000.0,
        )
    except Exception as e:
        logger.exception("Error while processing update: %s", e)
    return {"ok": True}
