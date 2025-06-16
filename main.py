from fastapi import FastAPI, Request
import os

app = FastAPI()

@app.post("/greenapi")
async def greenapi_webhook(request: Request):
    try:
        data = await request.json()
        print("📥 ПОЛУЧЕНО СООБЩЕНИЕ ОТ GREEN API:")
        print(data)
        return {"status": "ok"}
    except Exception as e:
        print("❌ ОШИБКА ПРИ ОБРАБОТКЕ GREEN API:")
        print(e)
        return {"status": "error"}

@app.get("/")
async def root():
    return {"status": "бот работает"}
