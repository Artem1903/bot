import os
import httpx
from dialog_tree_whatsapp import dialog_tree_whatsapp
from state_manager import get_state, set_state, reset_state
from send_to_admin import send_telegram_message

# GREEN API credentials
GREEN_API_INSTANCE_ID = os.getenv("GREEN_API_INSTANCE_ID") or "1103260718"
GREEN_API_TOKEN = os.getenv("GREEN_API_TOKEN") or "77776785617"
ADMIN = "842014271"

async def handle_whatsapp_webhook(data: dict):
    # Green API формат
    try:
        message_body = data['messageData']['textMessageData']['textMessage']
        chat_id = data['senderData']['chatId']  # Пример: 77012345678@c.us
        chat_id = chat_id.replace("@c.us", "")
    except:
        return {"status": "ignored"}

    if not chat_id or not message_body:
        return {"status": "ignored"}

    text = ''.join(filter(str.isdigit, message_body))
    state = get_state(chat_id)

    if text == "0":
        reset_state(chat_id)
        await send_whatsapp_message(chat_id, dialog_tree_whatsapp["start"]["message"])
        return {"status": "ok"}

    if text == "9" and state == "awaiting_online_data":
        await send_telegram_message(ADMIN, f"\u274c Отмена онлайн-записи от пользователя {chat_id}")
        reset_state(chat_id)
        await send_whatsapp_message(chat_id, "\ud83d\udeab Запись отменена.")
        return {"status": "ok"}

    if state == "awaiting_offline_data":
        await send_whatsapp_message(chat_id, "\u2705 Вы успешно записаны!\nЕсли что-то изменится, пожалуйста, позвоните в клинику \u260e\ufe0f +7 747 4603509")
        await send_telegram_message(ADMIN, f"\ud83d\udcdd Новая запись (ОЧНО):\n{text}")
        reset_state(chat_id)
        return {"status": "ok"}

    if state == "awaiting_online_data":
        await send_whatsapp_message(chat_id, "\u2705 Вы успешно записаны!\nЕсли что-то изменится, пожалуйста, позвоните в клинику \u260e\ufe0f +7 747 4603509")
        await send_telegram_message(ADMIN, f"\ud83d\udcdd Новая запись (ОНЛАЙН):\n{text}")
        reset_state(chat_id)
        return {"status": "ok"}

    if state == "price_categories" and text in dialog_tree_whatsapp["price_categories"]["options"]:
        next_key = dialog_tree_whatsapp["price_categories"]["options"][text]
        response = dialog_tree_whatsapp[next_key]["message"]
        await send_whatsapp_message(chat_id, response)

        if text == "0":
            reset_state(chat_id)
        else:
            set_state(chat_id, "price_categories")
        return {"status": "ok"}

    if text in dialog_tree_whatsapp["start"]["options"]:
        next_key = dialog_tree_whatsapp["start"]["options"][text]
        response = dialog_tree_whatsapp[next_key]["message"]
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

    await send_whatsapp_message(chat_id, dialog_tree_whatsapp["start"]["message"])
    return {"status": "ok"}

async def send_whatsapp_message(to, message):
    url = f"https://api.green-api.com/waInstance{GREEN_API_INSTANCE_ID}/sendMessage/{GREEN_API_TOKEN}"
    payload = {
        "chatId": f"{to}@c.us",
        "message": message
    }

    async with httpx.AsyncClient() as client:
        await client.post(url, json=payload)
