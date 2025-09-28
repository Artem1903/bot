import httpx
import logging
from dialog_tree import dialog_tree
from state_manager import get_state, set_state, reset_state
from send_to_admin import send_telegram_message

TOKEN = "7601158787:AAE52sbM7kd6DfBWpXPnr0_Q1w4y9am5h9o"
ADMIN = "842014271"
API_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

logging.basicConfig(level=logging.INFO)

WELCOME_SENT = {}  # отслеживаем первое сообщение

async def handle_telegram_webhook(payload):
    try:
        message = payload.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "").strip() if "text" in message else None

        if not chat_id:
            return {"ok": False}

        state = get_state(chat_id)

        # Первое сообщение
        if chat_id not in WELCOME_SENT:
            WELCOME_SENT[chat_id] = True
            await send_message(chat_id, dialog_tree["start"]["message"])
            return {"ok": True}

        # Если цифра
        if text and text.isdigit():
            if text == "0":
                reset_state(chat_id)
                await send_message(chat_id, dialog_tree["start"]["message"])
                return {"ok": True}

            if text == "9" and state == "awaiting_online_data":
                await send_telegram_message(ADMIN, f"❌ Отмена онлайн-записи от {chat_id}")
                reset_state(chat_id)
                await send_message(chat_id, "🚫 Запись отменена.")
                return {"ok": True}

            if state == "awaiting_offline_data":
                await send_message(chat_id, "✅ Вы успешно записаны!\n☎️ +7 747 4603509")
                await send_telegram_message(ADMIN, f"📝 Новая запись (ОЧНО):\n{text}")
                reset_state(chat_id)
                return {"ok": True}

            if state == "awaiting_online_data":
                await send_message(chat_id, "✅ Вы успешно записаны!\n☎️ +7 747 4603509")
                await send_telegram_message(ADMIN, f"📝 Новая запись (ОНЛАЙН):\n{text}")
                reset_state(chat_id)
                return {"ok": True}

            if state == "price_categories" and text in dialog_tree["price_categories"]["options"]:
                next_key = dialog_tree["price_categories"]["options"][text]
                response = dialog_tree[next_key]["message"]
                await send_message(chat_id, response)
                if text == "0":
                    reset_state(chat_id)
                else:
                    set_state(chat_id, "price_categories")
                return {"ok": True}

            if text in dialog_tree["start"]["options"]:
                next_key = dialog_tree["start"]["options"][text]
                response = dialog_tree[next_key]["message"]
                await send_message(chat_id, response)
                if text == "1":
                    set_state(chat_id, "awaiting_offline_data")
                elif text == "2":
                    set_state(chat_id, "awaiting_online_data")
                elif text == "3":
                    set_state(chat_id, "price_categories")
                else:
                    reset_state(chat_id)
                return {"ok": True}

        # Если произвольный текст/медиа и не в процессе записи
        if state not in ["awaiting_offline_data", "awaiting_online_data"]:
            await send_message(chat_id,
                "🤖 Это автоматический чат-бот. Я не могу ответить на текст или фото.\n"
                "Пожалуйста, выбирайте необходимую цифру из предложенного меню.\n"
                "Если хотите вернуться к началу, нажмите 0."
            )
            return {"ok": True}

        return {"ok": True}

    except Exception as e:
        logging.error(f"❌ Ошибка в telegram_handler: {e}")
        return {"ok": False}

async def send_message(chat_id, text):
    async with httpx.AsyncClient() as client:
        await client.post(API_URL, json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        })
