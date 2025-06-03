import os
import httpx
from dialog_tree import dialog_tree
from state_manager import get_state, set_state, reset_state
from send_to_admin import send_telegram_message

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN = os.getenv("TELEGRAM_ADMIN_USERNAME")
API_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"


async def handle_telegram_webhook(payload):
    message = payload.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "").strip()

    state = get_state(chat_id)

    # Возврат в главное меню
    if text == "0":
        reset_state(chat_id)
        await send_message(chat_id, dialog_tree["start"]["message"])
        return {"ok": True}

    # Отмена онлайн-записи
    if text == "9" and state == "awaiting_online_data":
        await send_telegram_message(ADMIN, f"❌ Отмена онлайн записи от пользователя {chat_id}")
        reset_state(chat_id)
        await send_message(chat_id, "🚫 Запись отменена. Если что-то изменится — напишите снова.")
        return {"ok": True}

    # Приём данных после выбора пунктов 1 и 2
    if state == "awaiting_offline_data":
        await send_message(chat_id, "✅ Вы успешно записаны!\nЕсли что-то изменится, пожалуйста, позвоните в клинику ☎️")
        await send_telegram_message(ADMIN, f"📝 Новая запись (ОЧНО):\n{text}")
        reset_state(chat_id)
        return {"ok": True}

    if state == "awaiting_online_data":
        await send_message(chat_id, "✅ Вы успешно записаны!\nЕсли что-то изменится, нажмите 9 или позвоните ☎️ +7 747 4603509")
        await send_telegram_message(ADMIN, f"📝 Новая запись (ОНЛАЙН):\n{text}")
        reset_state(chat_id)
        return {"ok": True}

    # Обработка выбора из главного меню
    if text in dialog_tree["start"]["options"]:
        next_key = dialog_tree["start"]["options"][text]
        response = dialog_tree[next_key]["message"]
        await send_message(chat_id, response)

        if text == "1":
            set_state(chat_id, "awaiting_offline_data")
        elif text == "2":
            set_state(chat_id, "awaiting_online_data")

        return {"ok": True}

    # Любое другое сообщение — показать меню
    await send_message(chat_id, dialog_tree["start"]["message"])
    return {"ok": True}


async def send_message(chat_id, text):
    async with httpx.AsyncClient() as client:
        await client.post(API_URL, json={
            "chat_id": chat_id,
            "text": text
        })
