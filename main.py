from fastapi import FastAPI, Request
import openai
import os

app = FastAPI()

# Установка API-ключа
openai.api_key = os.getenv("OPENAI_API_KEY")

system_prompt = """
Ты — вежливый и информативный помощник клиники пластической хирургии.
Говоришь кратко, по делу, без лишней болтовни.
"""

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
