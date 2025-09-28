import os
import httpx
from dialog_tree_whatsapp import dialog_tree_whatsapp
from state_manager import get_state, set_state, reset_state
from send_to_admin import send_telegram_message

GREEN_API_INSTANCE_ID = os.getenv("GREEN_API_INSTANCE_ID") or "1103260718"
GREEN_API_TOKEN = os.getenv("GREEN_API_TOKEN") or "77776785617"
ADMIN = "842014271"

WELCOME_SENT = {}  # отслеживаем первое сообщение

async def handle_whatsapp_webhook(data: dict):
    try:
        message_type = data["messageData"]["typeMessage"]
        chat_id = data["senderData"]["chatId"].replace("@c.us", "")
        message_body = ""

        if message_type == "textMessage":
            message_body = data["messageData"]["textMessageData"]["textMessage"].strip()
        else:
            message_body = None  # фото, аудио и пр.

    except Exception:
        return {"status": "ignored"}

    state = get_state(chat_id)

    # Проверка: первое сообщение от пользователя
    if chat_id not in WELCOME_SENT:
        WELCOME_SENT[chat_id] = True
        await send_whatsapp_message(chat_id, dialog_tree_whatsapp["start"]["message"])
        return {"status": "ok"}

    # Если текст — это цифра из меню
    if message_body and message_body.isdigit():
        text = message_body
        if text == "0":
            reset_state(chat_id)
            await send_whatsapp_message(chat_id, dialog_tree_whatsapp["start"]["message"])
            return {"status": "ok"}

        if text == "9" and state == "awaiting_online_data":
            await send_telegram_message(ADMIN, f"❌ Отмена онлайн-записи от {chat_id}")
            reset_state(chat_id)
            await send_whatsapp_message(chat_id, "🚫 Запись отменена.")
            return {"status": "ok"}

        if state == "awaiting_offline_data":
            await send_whatsapp_message(chat_id, "✅ Вы успешно записаны!\n☎️ +7 747 4603509")
            await send_telegram_message(ADMIN, f"📝 Новая запись (ОЧНО):\n{text}")
            reset_state(chat_id)
            return {"status": "ok"}

        if state == "awaiting_online_data":
            await send_whatsapp_message(chat_id, "✅ Вы успешно записаны!\n☎️ +7 747 4603509")
            await send_telegram_message(ADMIN, f"📝 Новая запись (ОНЛАЙН):\n{text}")
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

    # Если это не цифра, а произвольный текст/медиа вне записи
    if state not in ["awaiting_offline_data", "awaiting_online_data"]:
        await send_whatsapp_message(chat_id,
            "🤖 Это автоматический чат-бот. Я не могу ответить на текст или фото.\n"
            "Пожалуйста, выбирайте необходимую цифру из предложенного меню.\n"
            "Если хотите вернуться к началу, нажмите 0."
        )
        return {"status": "ok"}

    return {"status": "ignored"}

async def send_whatsapp_message(to, message):
    url = f"https://api.green-api.com/waInstance{GREEN_API_INSTANCE_ID}/sendMessage/{GREEN_API_TOKEN}"
    payload = {"chatId": f"{to}@c.us", "message": message}
    async with httpx.AsyncClient() as client:
        await client.post(url, json=payload)
