import os
import httpx
from dialog_tree import dialog_tree
from state_manager import get_state, set_state, reset_state
from send_to_admin import send_telegram_message

TWILIO_WHATSAPP_NUMBER = "whatsapp:+14155238886"
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
ADMIN = "5585802426"

async def handle_whatsapp_webhook(data: dict):
    from_number = data.get("From")
    message_body = data.get("Body", "").strip()
    chat_id = from_number.replace("whatsapp:", "")

    if not chat_id or not message_body:
        return {"status": "ignored"}

    # нормализуем: вытаскиваем только цифру (на случай "3️⃣", "3.", "3 - цены")
    text = ''.join(filter(str.isdigit, message_body))
    state = get_state(chat_id)

    # 0 — сброс
    if text == "0":
        reset_state(chat_id)
        await send_whatsapp_message(chat_id, dialog_tree["start"]["message"])
        return {"status": "ok"}

    # 9 — отмена онлайн-записи
    if text == "9" and state == "awaiting_online_data":
        await send_telegram_message(ADMIN, f"❌ Отмена онлайн-записи от пользователя {chat_id}")
        reset_state(chat_id)
        await send_whatsapp_message(chat_id, "🚫 Запись отменена.")
        return {"status": "ok"}

    # Завершение записи: оффлайн
    if state == "awaiting_offline_data":
        await send_whatsapp_message(chat_id, "✅ Вы успешно записаны!\nЕсли что-то изменится, пожалуйста, позвоните в клинику ☎️ +7 747 4603509")
        await send_telegram_message(ADMIN, f"📝 Новая запись (ОЧНО):\n{text}")
        reset_state(chat_id)
        return {"status": "ok"}

    # Завершение записи: онлайн
    if state == "awaiting_online_data":
        await send_whatsapp_message(chat_id, "✅ Вы успешно записаны!\nЕсли что-то изменится, пожалуйста, позвоните в клинику ☎️ +7 747 4603509")
        await send_telegram_message(ADMIN, f"📝 Новая запись (ОНЛАЙН):\n{text}")
        reset_state(chat_id)
        return {"status": "ok"}

    # Переход внутри "цены"
    if state == "price_categories" and text in dialog_tree["price_categories"]["options"]:
        next_key = dialog_tree["price_categories"]["options"][text]
        response = dialog_tree[next_key]["message"]
        await send_whatsapp_message(chat_id, response)

        if text == "0":
            reset_state(chat_id)
        else:
            set_state(chat_id, "price_categories")
        return {"status": "ok"}

    # Первый уровень: старт
    if text in dialog_tree["start"]["options"]:
        next_key = dialog_tree["start"]["options"][text]
        response = dialog_tree[next_key]["message"]
        await send_whatsapp_message(chat_id, response)

        if text == "1":
            set_state(chat_id, "awaiting_offline_data")
        elif text == "2":
            set_state(chat_id, "awaiting_online_data")
        elif text == "3":
            set_state(chat_id, "price_categories")
        else:
            reset_state(chat_id)
        return {"status": "ok"}

    # Иначе — вернуть стартовое меню
    await send_whatsapp_message(chat_id, dialog_tree["start"]["message"])
    return {"status": "ok"}

async def send_whatsapp_message(to, message):
    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
    auth = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    data = {
        "From": TWILIO_WHATSAPP_NUMBER,
        "To": f"whatsapp:{to}",
        "Body": message
    }

    async with httpx.AsyncClient() as client:
        await client.post(url, data=data, auth=auth)
