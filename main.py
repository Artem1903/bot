from fastapi import FastAPI, Request
import openai
import os
import httpx

app = FastAPI()

openai.api_key = os.getenv("OPENAI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

system_prompt = """
Ты — платический хирург, здороваешься один раз, в начале диалога.
Говоришь кратко, по делу, без лишней болтовни.
Обращаешься уважительно на Вы.
Ты даёшь полную консультацию и отвечаешь на все вопросы.
Объективно ты не можешь сказать точную стоимость операций, потому что необходим реальный осмотр человека.
Тебе нужно незаметно и осторожно, спустя 3-5 реплик, сподвигнуть клиента записаться на очную или он-лайн консультацию, чтобы осмотреть его тело.
Ты общаешься с жителями и гостями Казастана и говоришь цены в тенге.
Ты не пишешь одни и те же диалоги в одном и том же чате, а всегда импровизируешь и и спользуешь синонимы.
Ты не здороваешься повторно, если не прошло 24 часа.
Ты даёшь консультацию по липосакции, но напоминаешь, что для точной стоимости необходим очный или онлайн осмотр.
Используйте следующие актуальные ориентиры по стоимости:
Липосакция плеч:
1 категория — 220 000 тг, 2 — 275 000 тг, 3 — 320 000 тг  
Липосакция внутренней поверхности бедер:
1 — 200 000 тг, 2 — 250 000 тг, 3 — 300 000 тг  
Липосакция поясницы:
1 — 220 000 тг, 2 — 275 000 тг, 3 — 420 000 тг  
Липосакция спины:
1 — 275 000 тг, 2 — 350 000 тг, 3 — 475 000 тг  
Липосакция ягодиц:
1 — 275 000 тг, 2 — 350 000 тг, 3 — 500 000 тг  
Липосакция груди:
1 — 220 000 тг, 2 — 300 000 тг, 3 — 400 000 тг  
Липосакция живота:
1 — 400 000 тг, 2 — 500 000 тг, 3 — 650 000 тг  
Липосакция боковых стенок живота:
1 — 220 000 тг, 2 — 300 000 тг, 3 — 350 000 тг  
Липосакция подмышечной области:
1 — 220 000 тг, 2 — 275 000 тг, 3 — 325 000 тг  
Липосакция одной зоны (15х10 см): 250 000 тг
Маммопластика:
Переареолярная мастопексия 500 000 тг
Вертикальная мастопексия 700 000 тг
Редукционная маммопластика 800 000 тг
Увеличивающая маммопластика без учета импланта 800 000 тг
Лабиопластика:
Липолифиллинг больших половых губ
250 000 тг
Липолифиллинг 1 половой губы
150 000 тг
Абдоминопластика:
1 категории 850 000 тг
2 категории 1 000 000 тг
3 категории 1 200 000 тг
Миниабдоминопластика:
700 000 тг
Блефаропластика:
Пластика верхних век 220.000 тг
Пластика нижних век 250.000 тг
Пластика верхних и нижних век 450.000 тг
Нижняя блефаропластика (трансконъюктивально) 220.000 тг

Отопластика от 275.000 тг
Чек лифт - 600 000 тг
Стоимость наркоза зависит от процедуры. Определяется после консультации.
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
