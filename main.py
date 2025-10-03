from fastapi import FastAPI, Request
from whatsapp_handler import handle_whatsapp_webhook
from telegram_handler import handle_telegram_webhook

app = FastAPI()

@app.post("/greenapi")
async def greenapi_webhook(request: Request):
    try:
        data = await request.json()
        print("📥 ПОЛУЧЕНО СООБЩЕНИЕ ОТ GREEN API:")
        print(data)
        return await handle_whatsapp_webhook(data)
    except Exception as e:
        print("❌ ОШИБКА ПРИ ОБРАБОТКЕ GREEN API:")
        print(e)
        return {"status": "error"}

@app.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        print("📥 ПОЛУЧЕНО СООБЩЕНИЕ ИЗ TELEGRAM:")
        print(data)
        return await handle_telegram_webhook(data)
    except Exception as e:
        print("❌ ОШИБКА ПРИ ОБРАБОТКЕ TELEGRAM:")
        print(e)
        return {"ok": False}

@app.get("/")
async def root():
    return {"status": "бот работает"}
