from fastapi import FastAPI, Request
import openai
import os
import httpx
import json
import time
from threading import Timer
import faiss
import numpy as np
import asyncio

app = FastAPI()

openai.api_key = os.getenv("OPENAI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

# Загрузка fallback и timeout-фраз
with open("fallback_phrases.json", encoding="utf-8") as f:
    fallback_phrases = json.load(f)

with open("timeout_consultation_phrases.json", encoding="utf-8") as f:
    timeout_phrases = json.load(f)

# Векторизация через OpenAI (embedding-ada-002)
def embed(text):
    response = openai.embeddings.create(
        input=text,
        model="text-embedding-ada-002"
    )
    return response.data[0].embedding

# Простейшая база знаний (можно расширять)
knowledge_base = [
    "Сколько стоит липосакция спины?",
    "Какая цена на маммопластику?",
    "Сколько стоит липосакция боков живота?"
]

# Создание эмбеддингов и индекс для поиска
kb_embeddings = np.array([embed(text) for text in knowledge_base]).astype("float32")
index = faiss.IndexFlatL2(len(kb_embeddings[0]))
index.add(kb_embeddings)

# Таймеры и флаг консультации
user_timers = {}
user_offered = set()

# Системный промпт для GPT
system_prompt = """
Ты — пластический хирург, здороваешься один раз, в начале диалога.
Говоришь кратко, по делу, без лишней болтовни.
Обращаешься уважительно на Вы.
Ты даёшь полную консультацию и отвечаешь на все вопросы.
Объективно ты не можешь сказать точную стоимость операций, потому что необходим реальный осмотр человека.
Тебе нужно незаметно и осторожно, спустя 3–5 реплик, сподвигнуть клиента записаться на очную или он-лайн консультацию, чтобы осмотреть его тело.
Ты общаешься с жителями и гостями Казахстана и говоришь цены в тенге.
Ты не пишешь одни и те же диалоги в одном и том же чате, а всегда импровизируешь и используешь синонимы.
Ты не здороваешься повторно, если не прошло 24 часа.
Ты даёшь консультацию по липосакции, но напоминаешь, что для точной стоимости необходим очный или онлайн осмотр.
"""

# Запрос к GPT
def gpt_response(messages):
    return openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages
    ).choices[0].message.content

# Отправка ответа в Telegram
async def send_message(chat_id, text):
    async with httpx.AsyncClient() as client:
        await client.post(TELEGRAM_API_URL, json={
            "chat_id": chat_id,
            "text": text
        })

# Отложенное предложение консультации
def timeout_trigger(chat_id):
    if chat_id not in user_offered:
        phrase = np.random.choice(timeout_phrases)
        user_offered.add(chat_id)
        asyncio.create_task(send_message(chat_id, phrase))

# Основной обработчик Telegram webhook
@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    payload = await request.json()
    message = payload.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    user_message = message.get("text")

    if not chat_id or not user_message:
        return {"ok": True}

    # Векторизация входа
    user_embedding = np.array(embed(user_message)).astype("float32").reshape(1, -1)
    D, I = index.search(user_embedding, 1)

    if D[0][0] < 0.8:
        # Используем RAG
        kb_match = knowledge_base[I[0][0]]
        reply = gpt_response([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": kb_match},
            {"role": "user", "content": user_message}
        ])
    else:
        # fallback
        phrase = np.random.choice(fallback_phrases)
        reply = gpt_response([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": phrase}
        ])

    # Запустить таймер, если предложение не делалось
    if chat_id not in user_offered:
        if chat_id in user_timers:
            user_timers[chat_id].cancel()
        user_timers[chat_id] = Timer(900, timeout_trigger, args=[chat_id])
        user_timers[chat_id].start()

    await send_message(chat_id, reply)
    return {"ok": True}
