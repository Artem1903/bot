import asyncio
from fastapi import FastAPI, Request
from whatsapp_handler import handle_whatsapp_webhook
from telegram_handler import handle_telegram_webhook

app = FastAPI()

@app.post("/greenapi")
async def greenapi_webhook(request: Request):
    try:
        data = await request.json()
        # Обрабатываем в фоне, чтобы сразу вернуть ответ Green API
        asyncio.create_task(handle_whatsapp_webhook(data))
        return {"status": "ok"}
    except Exception as e:
        print("❌ ОШИБКА ПРИ ОБРАБОТКЕ GREEN API:", e)
        return {"status": "error"}

@app.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        # Обрабатываем в фоне, чтобы сразу вернуть ответ Telegram
        asyncio.create_task(handle_telegram_webhook(data))
        return {"ok": True}
    except Exception as e:
        print("❌ ОШИБКА ПРИ ОБРАБОТКЕ TELEGRAM:", e)
        return {"ok": False}

@app.get("/")
async def root():
    return {"status": "бот работает"}
