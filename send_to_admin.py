
import os
import httpx

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

async def send_telegram_message(username, text):
    async with httpx.AsyncClient() as client:
        await client.post(API_URL, json={
            "chat_id": username,
            "text": text
        })
