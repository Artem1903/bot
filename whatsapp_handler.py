import os
import httpx
from dialog_tree import dialog_tree
from state_manager import get_user_state, set_user_state
from send_to_admin import send_to_admin

# Twilio данные
TWILIO_WHATSAPP_NUMBER = "whatsapp:+14155238886"  # Twilio Sandbox номер
ADMIN_PHONE = "whatsapp:+77771234567"             # WhatsApp-номер админа

# 👉 ВСТАВЬ СЮДА СВОИ ДАННЫЕ

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

async def handle_whatsapp_webhook(data: dict):
    from_number = data.get("From")                # Пример: whatsapp:+77771234567
    message_body = data.get("Body", "").strip()

    print(f"📩 WhatsApp сообщение от {from_number}: {message_body}")

    if not from_number or not message_body:
        return {"status": "ignored"}

    # Извлекаем ID (чистый номер без приставки)
    chat_id = from_number.replace("whatsapp:", "")
    state = get_user_state(chat_id) or "start"

    # Получаем ответ по текущему состоянию
    response = dialog_tree.get(state, {}).get("message", "Извините, я Вас не понял.")
    next_state = dialog_tree.get(state, {}).get("next", {}).get(message_body)

    # Если введён переход — обновляем состояние
    if next_state:
        set_user_state(chat_id, next_state)
        response = dialog_tree.get(next_state, {}).get("message", response)

    # Отправка ответа пользователю через Twilio
    await send_whatsapp_message(to=from_number, message=response)

    # Уведомляем админа (если нужно)
    await send_to_admin(f"💬 [WhatsApp] {chat_id} написал: {message_body}")

    return {"status": "ok"}

async def send_whatsapp_message(to: str, message: str):
    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
    auth = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    data = {
        "From": TWILIO_WHATSAPP_NUMBER,
        "To": to,
        "Body": message
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, data=data, auth=auth)
        print("📤 Ответ Twilio:", response.status_code, response.text)
