from fastapi import FastAPI, Request
import openai
import os
import httpx
import json
import time
from threading import Timer
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import asyncio

app = FastAPI()

openai.api_key = os.getenv("OPENAI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

# Загружаем fallback и timeout фразы
with open("fallback_phrases.json", encoding="utf-8") as f:
    fallback_phrases = json.load(f)

with open("timeout_consultation_phrases.json", encoding="utf-8") as f:
    timeout_phrases = json.load(f)

# Локальная модель эмбеддингов
model = SentenceTransformer("nli-MiniLM2-L6-H768-v2")

# Простая база знаний
knowledge_base = [
    "Сколько стоит липосакция спины?",
    "Какая цена на маммопластику?",
    "Сколько стоит липосакция боков живота?"
]

def embed(text):
    return model.encode(text).tolist()

kb_embeddings = np.array([embed(text) for text in knowledge_base]).astype("float32")
index = faiss.IndexFlatL2(len(kb_embeddings[0]))
index.add(kb_embeddings)

# Таймеры и память
user_timers = {}
user_offered = set()
chat_histories = {}

system_prompt = """
Вы — пластический хирург, который консультирует онлайн. Ваш стиль — профессиональный, вежливый, но живой. Вы говорите кратко, по делу, без шаблонных фраз. Обращаетесь к собеседнику на «Вы».

✅ Если цена известна — называйте её **точно**. Например:
— «Чек-лифт стоит 600 000 тг»
— «Увеличивающая маммопластика без учета импланта — 800 000 тг»

⛔ Не уходите от ответа фразами вроде «цена зависит от…», если процедура указана в прайсе. Уточнение «нужен осмотр» допустимо, но только **после конкретной цены**.

💬 Если человек пишет повторно, не здоровайтесь снова, если не прошло 24 часа.

🎯 Цель — ненавязчиво сподвигнуть человека записаться на консультацию, **после 2–3 реплик**, мягко, естественно. Используйте разные фразы, синонимы, не повторяйтесь.

🇰🇿 Все цены указывайте в тенге. Общение — с жителями и гостями Казахстана.

📍 Ниже — актуальный прайс (включите его в ответы, если запрашивают конкретную процедуру):

Липосакция плеч: 1 кат — 220 000 тг, 2 — 275 000 тг, 3 — 320 000 тг  
Липосакция бедер (внутр): 1 — 200 000 тг, 2 — 250 000 тг, 3 — 300 000 тг  
Липосакция поясницы: 1 — 220 000 тг, 2 — 275 000 тг, 3 — 420 000 тг  
Липосакция спины: 1 — 275 000 тг, 2 — 350 000 тг, 3 — 475 000 тг  
Липосакция ягодиц: 1 — 275 000 тг, 2 — 350 000 тг, 3 — 500 000 тг  
Липосакция груди: 1 — 220 000 тг, 2 — 300 000 тг, 3 — 400 000 тг  
Липосакция живота: 1 — 400 000 тг, 2 — 500 000 тг, 3 — 650 000 тг  
Липосакция боков: 1 — 220 000 тг, 2 — 300 000 тг, 3 — 350 000 тг  
Подмышечная область: 1 — 220 000 тг, 2 — 275 000 тг, 3 — 325 000 тг  
1 зона (15×10 см): 250 000 тг  

Маммопластика:  
— Переареолярная мастопексия — 500 000 тг  
— Вертикальная мастопексия — 700 000 тг  
— Редукционная — 800 000 тг  
— Увеличивающая (без импланта) — 800 000 тг  

Лабиопластика:  
— Липолифиллинг больших половых губ — 250 000 тг  
— Липолифиллинг одной губы — 150 000 тг  

Абдоминопластика: 1 кат — 850 000 тг, 2 — 1 000 000 тг, 3 — 1 200 000 тг  
Миниабдоминопластика — 700 000 тг  

Блефаропластика:  
— Верхние веки — 220 000 тг  
— Нижние веки — 250 000 тг  
— Верх+низ — 450 000 тг  
— Нижняя трансконъюктивальная — 220 000 тг  

Отопластика — от 275 000 тг  
Чек-лифт — 600 000 тг  

Наркоз — рассчитывается индивидуально после консультации.
"""

def gpt_response(messages):
    return openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages
    ).choices[0].message.content

async def send_message(chat_id, text):
    async with httpx.AsyncClient() as client:
        await client.post(TELEGRAM_API_URL, json={
            "chat_id": chat_id,
            "text": text
        })

def timeout_trigger(chat_id):
    if chat_id not in user_offered:
        phrase = np.random.choice(timeout_phrases)
        user_offered.add(chat_id)
        asyncio.create_task(send_message(chat_id, phrase))

def user_wants_consultation(text: str) -> bool:
    text = text.lower()
    return any(phrase in text for phrase in ["записаться", "хочу консультацию", "как попасть на прием", "можно записаться"])

@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    payload = await request.json()
    message = payload.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    user_message = message.get("text")

    if not chat_id or not user_message:
        return {"ok": True}

        # ⛳ Проверка на желание записаться
    if user_wants_consultation(user_message):
        user_offered.add(chat_id)
        await send_message(chat_id, "Конечно! Я Вас запишу. Пожалуйста, укажите, какой день и время Вам удобно — или напишите номер, чтобы администратор связался с Вами.")
        await send_message(chat_id, "Благодарю за общение. Через некоторое время с Вами свяжутся для подтверждения консультации.")
        return {"ok": True}

        
    # Добавляем в историю
    history = chat_histories.get(chat_id, [])
    history.append({"role": "user", "content": user_message})

    # Векторное сравнение
    user_embedding = np.array(embed(user_message)).astype("float32").reshape(1, -1)
    D, I = index.search(user_embedding, 1)

    if D[0][0] < 0.6:
        kb_match = knowledge_base[I[0][0]]
        history.insert(0, {"role": "user", "content": kb_match})

    else:
        fallback = np.random.choice(fallback_phrases)
        history.append({"role": "assistant", "content": fallback})

    history = [{"role": "system", "content": system_prompt}] + history[-10:]
    reply = gpt_response(history)
    await send_message(chat_id, reply)
    chat_histories[chat_id] = history[-10:]

    # Проверка желания записаться
    if user_wants_consultation(user_message):
        user_offered.add(chat_id)

    # Таймер, если ещё не предлагали
    if chat_id not in user_offered:
        if chat_id in user_timers:
            user_timers[chat_id].cancel()
        user_timers[chat_id] = Timer(900, timeout_trigger, args=[chat_id])
        user_timers[chat_id].start()

    return {"ok": True}
