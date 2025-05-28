from fastapi import FastAPI, Request
import openai
import os
import requests

app = FastAPI()

# Настройка ключей
openai.api_key = os.getenv("OPENAI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# Системный промпт
system_prompt = """
Ты — помощник платического хирурга, консультант.
Говоришь кратко, по делу, без лишней болтовни.
Обращаешься уважительно на вы.
Твоя цель — записать человека на консультацию, чтобы его смог осмотреть врач.
"""

# Основной чат-эндпоинт
@app.post("/chat")
async def chat(request: Request):
    try:
        data = await request.json()
        user_message = data.get("message")

        if not user_message:
            return {"error": "Пустое сообщение"}

        client = openai.OpenAI(api_key=openai.api_key)

        response = client.chat.completions.create(
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


# Webhook для Telegram
@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        message = data.get("message", {}).get("text")
        chat_id = data.get("message", {}).get("chat", {}).get("id")

        if message and chat_id:
            # Запрос к нашему /chat эндпоинту
            response = requests.post("https://bot-j2ci.onrender.com/chat", json={"message": message})
            reply = response.json().get("reply", "Произошла ошибка при генерации ответа.")

            # Ответ в Telegram
            requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={
                "chat_id": chat_id,
                "text": reply
            })

        return {"ok": True}
    except Exception as e:
        return {"error": str(e)}
