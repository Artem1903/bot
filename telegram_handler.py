import os
import httpx
import logging
from dialog_tree import dialog_tree
from state_manager import get_state, set_state, reset_state
from send_to_admin import send_telegram_message

# ✅ Все данные уже вставлены — не нужно менять
TOKEN = "7601158787:AAE52sbM7kd6DfBWpXPnr0_Q1w4y9am5h9o"
ADMIN = "5585802426"
API_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

logging.basicConfig(level=logging.INFO)

async def handle_telegram_webhook(payload):
    logging.info(f"📩 Входящий payload: {payload}")
    try:
        message = payload.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "").strip()

        if not chat_id:
            return {"ok": False}

        state = get_state(chat_id)

        # 🔁 Возврат в главное меню
        if text == "0":
            reset_state(chat_id)
            await send_message(chat_id, dialog_tree["start"]["message"])
            return {"ok": True}

        # ❌ Отмена онлайн-записи
        if text == "9" and state == "awaiting_online_data":
            await send_telegram_message(ADMIN, f"❌ Отмена онлайн-записи от пользователя {chat_id}")
            reset_state(chat_id)
            await send_message(chat_id, "🚫 Запись отменена.")
            return {"ok": True}

        # ✅ Очная запись — принимаем данные
        if state == "awaiting_offline_data":
            await send_message(chat_id, "✅ Вы успешно записаны!\nЕсли что-то изменится, пожалуйста, позвоните в клинику ☎️")
            await send_telegram_message(ADMIN, f"📝 Новая запись (ОЧНО):\n{text}")
            reset_state(chat_id)
            return {"ok": True}

        # ✅ Онлайн запись — принимаем данные
        if state == "awaiting_online_data":
            await send_message(chat_id, "✅ Вы успешно записаны!\nЕсли что-то изменится, нажмите 9 или позвоните ☎️ +7 747 4603509")
            await send_telegram_message(ADMIN, f"📝 Новая запись (ОНЛАЙН):\n{text}")
            reset_state(chat_id)
            return {"ok": True}

        # 💰 Вложенное меню — цены
        if state == "price_categories" and text in dialog_tree["price_categories"]["options"]:
            next_key = dialog_tree["price_categories"]["options"][text]
            response = dialog_tree[next_key]["message"]
            await send_message(chat_id, response)

            if text == "0":
                reset_state(chat_id)
            else:
                set_state(chat_id, "price_categories")
            return {"ok": True}

        # 🧭 Главное меню
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

        # ℹ️ Всё остальное — просто покажем главное меню
        await send_message(chat_id, dialog_tree["start"]["message"])
        return {"ok": True}

    except Exception as e:
        logging.error(f"❌ Ошибка в telegram_handler: {e}")
        return {"ok": False}


async def send_message(chat_id, text):
    async with httpx.AsyncClient() as client:
        await client.post(API_URL, json={
            "chat_id": chat_id,
            "text": text
        })
