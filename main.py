import os
from fastapi import FastAPI, Request
from whatsapp_handler import handle_whatsapp_webhook
from telegram_handler import handle_telegram_webhook

# По умолчанию — синхронная обработка вебхуков (быстрее ощущается пользователем)
ASYNC_WEBHOOK = os.getenv("ASYNC_WEBHOOK", "0") == "1"

app = FastAPI()

@app.post("/greenapi")
async def greenapi_webhook(request: Request):
    data = await request.json()
    if ASYNC_WEBHOOK:
        import asyncio
        asyncio.create_task(handle_whatsapp_webhook(data))
        return {"status": "ok", "mode": "async"}
    else:
        await handle_whatsapp_webhook(data)
        return {"status": "ok", "mode": "sync"}

@app.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    if ASYNC_WEBHOOK:
        import asyncio
        asyncio.create_task(handle_telegram_webhook(data))
        return {"ok": True, "mode": "async"}
    else:
        await handle_telegram_webhook(data)
        return {"ok": True, "mode": "sync"}

@app.get("/")
async def root():
    return {"status": "бот работает", "async_webhook": ASYNC_WEBHOOK}
