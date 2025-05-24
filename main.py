from fastapi import FastAPI, Request
import openai
import os

app = FastAPI()

openai.api_key = os.getenv("OPENAI_API_KEY")

system_prompt = """
Ты — вежливый и информативный помощник клиники пластической хирургии.
Говоришь кратко, по делу, без лишней болтовни.
Всегда помогаешь записаться, узнать цены и объясняешь процедуры.

Если спрашивают:
- "где находится клиника?" — Розыбакиева, 289/2, вход с Аль-Фараби.
- "врач мужчина или женщина?" — Женщина, 15 лет опыта, сертифицированный хирург.
- "что такое седация?" — Это мягкий наркоз, при котором пациент спокоен, но в сознании.
- "форма консультации" — Онлайн по видеосвязи или очная в Алматы.
- "цены" — От 150 000₸, зависит от процедуры. Точные цены — после консультации.

Если не знаешь точного ответа — предложи записаться на консультацию.
"""

@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    user_message = data.get("message")

    if not user_message:
        return {"error": "No message provided"}

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
    )

    reply = response.choices[0].message.content
    return {"reply": reply}
