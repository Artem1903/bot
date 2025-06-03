
from fastapi import FastAPI, Request
from telegram_handler import handle_telegram_webhook
from whatsapp_handler import handle_whatsapp_webhook

app = FastAPI()

@app.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    return await handle_telegram_webhook(await request.json())

@app.post("/whatsapp/webhook")
async def whatsapp_webhook(request: Request):
    return await handle_whatsapp_webhook(await request.json())
