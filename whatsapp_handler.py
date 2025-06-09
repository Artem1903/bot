import os
import httpx
from dialog_tree import dialog_tree
from state_manager import get_state, set_state
from send_to_admin import send_telegram_message

TWILIO_WHATSAPP_NUMBER = "whatsapp:+14155238886"
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
ADMIN_TELEGRAM_ID = "5585802426"

async def handle_whatsapp_webhook(data: dict):
    from_number = data.get("From")
    message_body = data.get("Body", "").strip()

    print(f"📩 WhatsApp сообщение от {from_number}: {message_body}")

    if not from_number or not message_body:
        return {"status": "ignored"}

    chat_id = from_number.replace("whatsapp:", "")
    state = get_state(chat_id) or "start"

    # 🔧 Нормализуем вход: оставляем только цифры (чтобы отловить "3", "3️⃣", "3. ...", "3 - текст")
    normalized_input = ''.join(filter(str.isdigit, message_body))

    # Получаем следующее состояние
    next_state = dialog_tree.get(state, {}).get("next", {}).get(normalized_input)

    if next_state:
        set_state(chat_id, next_state)
        response = dialog_tree.get(next_state, {}).get("message", "Ошибка. Нет сообщения в дереве.")
    else:
        response = dialog_tree.get(state, {}).get("message", "Извините, я Вас не понял.")

    # Отправка ответа в WhatsApp
    await send_whatsapp_message(to=from_number, message=response)

    # Уведомление администратору
    await send_telegram_message(chat_id=ADMIN_TELEGRAM_ID, text=f"💬 [WhatsApp] {chat_id} написал: {message_body}")

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
        print("📤 Twilio ответ:", response.status_code, response.text)
