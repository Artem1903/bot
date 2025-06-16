from fastapi import FastAPI, Request
from whatsapp_handler import handle_whatsapp_webhook

app = FastAPI()

@app.post("/greenapi")
async def greenapi_webhook(request: Request):
    try:
        data = await request.json()
        print("📥 ПОЛУЧЕНО СООБЩЕНИЕ ОТ GREEN API:")
        print(data)
        return await handle_whatsapp_webhook(data)
    except Exception as e:
        print("❌ ОШИБКА ПРИ ОБРАБОТКЕ:")
        print(e)
        return {"status": "error"}

@app.get("/")
async def root():
    return {"status": "бот работает"}
