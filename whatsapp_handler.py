import os
import httpx
from dialog_tree_whatsapp import dialog_tree_whatsapp
from state_manager import get_state, set_state, reset_state, touch_state
from send_to_admin import send_telegram_message

# Постоянный HTTP-клиент (keep-alive + HTTP/2) → меньше задержек
_http = httpx.AsyncClient(timeout=10.0, http2=True)

GREEN_API_INSTANCE_ID = os.getenv("GREEN_API_INSTANCE_ID") or "1103260718"
GREEN_API_TOKEN = os.getenv("GREEN_API_TOKEN") or "77776785617"
ADMIN = "842014271"

STATE_IDLE = "idle"
STATE_OFFLINE = "awaiting_offline_data"
STATE_ONLINE = "awaiting_online_data"
STATE_PRICE = "price_categories"

AUTO_REPLY = (
    "🤖 Это автоматический чат-бот. Я не могу ответить на текст или фото.\n"
    "Пожалуйста, выбирайте необходимую цифру из предложенного меню.\n"
    "Если хотите вернуться к началу, нажмите 0."
)

async def handle_whatsapp_webhook(data: dict):
    # Извлечение полей Green API с защитой от KeyError
    try:
        message_type = data.get("messageData", {}).get("typeMessage")
        chat_id_raw = data.get("senderData", {}).get("chatId", "")
        chat_id = chat_id_raw.replace("@c.us", "")
        message_body = None
        if message_type == "textMessage":
            message_body = data["messageData"]["textMessageData"]["textMessage"].strip()
    except Exception:
        return

    # Состояние (TTL)
    state = get_state(chat_id)
    if state is None:
        await send_whatsapp_message(chat_id, dialog_tree_whatsapp["start"]["message"])
        set_state(chat_id, STATE_IDLE)
        return

    touch_state(chat_id)

    if message_body:
        text = message_body

        if text == "0":
            set_state(chat_id, STATE_IDLE)
            await send_whatsapp_message(chat_id, dialog_tree_whatsapp["start"]["message"])
            return

        if state == STATE_OFFLINE:
            if text.isdigit() and text == "9":
                await send_telegram_message(ADMIN, f"❌ Отмена очной записи от {chat_id}")
                set_state(chat_id, STATE_IDLE)
                await send_whatsapp_message(chat_id, "🚫 Запись отменена.")
                return
            await send_telegram_message(ADMIN, f"📝 Новая запись (ОЧНО):\n{text}")
            await send_whatsapp_message(chat_id, "✅ Спасибо! Мы с Вами свяжемся по указанным данным.\n☎️ +7 747 4603509")
            set_state(chat_id, STATE_IDLE)
            return

        if state == STATE_ONLINE:
            if text.isdigit() and text == "9":
                await send_telegram_Message(ADMIN, f"❌ Отмена онлайн-записи от {chat_id}")
                set_state(chat_id, STATE_IDLE)
                await send_whatsapp_message(chat_id, "🚫 Запись отменена.")
                return
            await send_telegram_message(ADMIN, f"📝 Новая запись (ОНЛАЙН):\n{text}")
            await send_whatsapp_message(chat_id, "✅ Спасибо! Мы с Вами свяжемся по указанным данным.\n☎️ +7 747 4603509")
            set_state(chat_id, STATE_IDLE)
            return

        if text.isdigit():
            if state == STATE_PRICE and text in dialog_tree_whatsapp["price_categories"]["options"]:
                next_key = dialog_tree_whatsapp["price_categories"]["options"][text]
                response = dialog_tree_whatsapp[next_key]["message"]
                await send_whatsapp_message(chat_id, response)
                if text == "0":
                    set_state(chat_id, STATE_IDLE)
                else:
                    set_state(chat_id, STATE_PRICE)
                return

            if text in dialog_tree_whatsapp["start"]["options"]:
                next_key = dialog_tree_whatsapp["start"]["options"][text]
                response = dialog_tree_whatsapp[next_key]["message"]
                await send_whatsapp_message(chat_id, response)
                if text == "1":
                    set_state(chat_id, STATE_OFFLINE)
                elif text == "2":
                    set_state(chat_id, STATE_ONLINE)
                elif text == "3":
                    set_state(chat_id, STATE_PRICE)
                else:
                    set_state(chat_id, STATE_IDLE)
                return

        if state not in [STATE_OFFLINE, STATE_ONLINE]:
            await send_whatsapp_message(chat_id, AUTO_REPLY)
            return

    # Медиа/нет текста
    if state in [STATE_OFFLINE, STATE_ONLINE]:
        await send_whatsapp_message(chat_id, "Пожалуйста, отправьте данные текстом (имя, телефон и др.).")
    else:
        await send_whatsapp_message(chat_id, AUTO_REPLY)

async def send_whatsapp_message(to, message):
    url = f"https://api.green-api.com/waInstance{GREEN_API_INSTANCE_ID}/sendMessage/{GREEN_API_TOKEN}"
    payload = {"chatId": f"{to}@c.us", "message": message}
    await _http.post(url, json=payload)
