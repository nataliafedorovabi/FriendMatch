from __future__ import annotations

from fastapi import FastAPI, Request, HTTPException
from aiogram.types import Update

from .config import get_settings
from .bot import bot, dp
from .db import init_db


settings = get_settings()
app = FastAPI(title="Girls Quiz Bot")


@app.on_event("startup")
async def on_startup() -> None:
    await init_db()
    # Set webhook
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
    await dp.feed_update(bot, update)
    return {"ok": True}
