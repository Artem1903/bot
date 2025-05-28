from fastapi import FastAPI, Request
import openai
import os
import httpx

app = FastAPI()

openai.api_key = os.getenv("OPENAI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

system_prompt = """
Ты — платический хирург.
Говоришь кратко, по делу, без лишней болтовни.
Обращаешься уважительно на Вы.
Ты даёшь полную консультацию и отвечаешь на все вопросы.
Объективно ты не можешь сказать точную стоимость операций, потому что необходим реальный осмотр человека.
Тебе нужно незаметно и осторожно, спустя 3-5 реплик, сподвигнуть клиента записаться на очную или он-лайн консультацию, чтобы осмотреть его тело.
Ты общаешься с жителями и гостями Казастана и говоришь цены в тенге.
"""

# 🔹 Обработка запросов через Postman
@app.post("/chat")
async def chat(request: Request):
    try:
        data = await request.json()
        user_message = data.get("message")

        if not user_message:
            return {"error": "Пустое сообщение"}

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
        )

        reply = response.choices[0].message.content
        return {"reply": reply}

    except Exception as e:
        return {"error": str(e)}


# 🔹 Webhook для Telegram
@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    try:
        payload = await request.json()
        message = payload.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        user_message = message.get("text")

        if not chat_id or not user_message:
            return {"ok": True}

        # Получаем ответ от OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
        )

        reply = response.choices[0].message.content

        # Отправляем ответ обратно в Telegram
        async with httpx.AsyncClient() as client:
            await client.post(TELEGRAM_API_URL, json={
                "chat_id": chat_id,
                "text": reply
            })

        return {"ok": True}

    except Exception as e:
        return {"error": str(e)}
