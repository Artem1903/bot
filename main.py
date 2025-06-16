from fastapi import FastAPI, Request
from telegram_handler import handle_telegram_webhook
from whatsapp_handler import handle_whatsapp_webhook

app = FastAPI()

@app.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    return await handle_telegram_webhook(await request.json())

@app.post("/whatsapp/webhook")
async def whatsapp_webhook(request: Request):
    # Оставляем старую совместимость с Twilio (если надо)
    form = await request.form()
    data = dict(form)
    return await handle_whatsapp_webhook(data)

@app.post("/greenapi")
async def greenapi_webhook(request: Request):
    # Обработка сообщений от Green API
    data = await request.json()
    return await handle_whatsapp_webhook(data)

@app.get("/")
async def root():
    return {"status": "ok"}  # заглушка, чтобы убрать 404 на /
