import os
import httpx
from dialog_tree_whatsapp import dialog_tree_whatsapp
from state_manager import get_state, set_state, reset_state
from send_to_admin import send_telegram_message

# Green API параметры
GREEN_API_INSTANCE_ID = os.getenv("GREEN_API_INSTANCE_ID") or "1103260718"
GREEN_API_TOKEN = os.getenv("GREEN_API_TOKEN") or "f4d88b563e5746d0bf2a01fb04898d4a53ff4afb9d"
ADMIN = "842014271"

async def handle_whatsapp_webhook(data: dict):
    # 1) Попробуем получить текст
    md = data.get('messageData', {})
    if 'textMessageData' in md:
        message_body = md['textMessageData']['textMessage']
    elif 'extendedTextMessageData' in md:
        message_body = md['extendedTextMessageData']['text']
    else:
        # Неформатное сообщение (фото, голос, документ и пр.)
        message_body = None

    # 2) Получаем chat_id
    chat_id = data.get('senderData', {}).get('chatId', '').replace("@c.us", "")
    if not chat_id:
        return {"status": "ignored"}

    # 3) Достаём цифры для меню
    digits = ''.join(filter(str.isdigit, message_body or ""))
    state = get_state(chat_id)

    # === Первое сообщение всегда даёт приветствие ===
    if not state:
        await send_whatsapp_message(chat_id, dialog_tree_whatsapp["start"]["message"])
        set_state(chat_id, "start")
        return {"status": "ok"}

    # === Стандартные ветки ===
    if digits == "0":
        reset_state(chat_id)
        await send_whatsapp_message(chat_id, dialog_tree_whatsapp["start"]["message"])
        return {"status": "ok"}

    if digits == "9" and state == "awaiting_online_data":
        await send_telegram_message(ADMIN, f"❌ Отмена онлайн-записи от пользователя {chat_id}")
        reset_state(chat_id)
        await send_whatsapp_message(chat_id, "🚫 Запись отменена.")
        return {"status": "ok"}

    if state in ("awaiting_offline_data", "awaiting_online_data"):
        await send_whatsapp_message(
            chat_id,
            "✅ Вы успешно записаны!\n"
            "Если что-то изменится, пожалуйста, позвоните в клинику ☎️ +7 747 8205944"
        )
        await send_telegram_message(
            ADMIN,
            f"📝 Новая запись ({'ОНЛАЙН' if state=='awaiting_online_data' else 'ОФФЛАЙН'}):\n"
            f"Сообщение клиента: <b>{message_body}</b>\n"
            f"Номер WhatsApp: <code>{chat_id}</code>"
        )
        reset_state(chat_id)
        return {"status": "ok"}

    if state == "price_categories" and digits in dialog_tree_whatsapp["price_categories"]["options"]:
        next_key = dialog_tree_whatsapp["price_categories"]["options"][digits]
        response = dialog_tree_whatsapp[next_key]["message"]
        await send_whatsapp_message(chat_id, response)
        if digits == "0":
            reset_state(chat_id)
        else:
            set_state(chat_id, "price_categories")
        return {"status": "ok"}

    if digits in dialog_tree_whatsapp["start"]["options"]:
        next_key = dialog_tree_whatsapp["start"]["options"][digits]
        response = dialog_tree_whatsapp[next_key]["message"]
        await send_whatsapp_message(chat_id, response)
        if digits == "1":
            set_state(chat_id, "awaiting_offline_data")
        elif digits == "2":
            set_state(chat_id, "awaiting_online_data")
        elif digits == "3":
            set_state(chat_id, "price_categories")
        else:
            reset_state(chat_id)
        return {"status": "ok"}

    # === Автоответ для "левых" сообщений ===
    if state not in ("awaiting_offline_data", "awaiting_online_data"):
        await send_whatsapp_message(chat_id,
            "🤖 Это автоматический чат-бот. Я не могу ответить на текст, аудио или фото.\n\n"
            "Пожалуйста, выбирайте необходимую цифру из предложенного меню.\n\n"
            "Если хотите вернуться к началу и записаться на консультацию, нажмите 0."
        )
        return {"status": "hint_shown"}

    return {"status": "ok"}


async def send_whatsapp_message(to, message):
    url = f"https://api.green-api.com/waInstance{GREEN_API_INSTANCE_ID}/sendMessage/{GREEN_API_TOKEN}"
    payload = {
        "chatId": f"{to}@c.us",
        "message": message
    }

    print("📤 ОТПРАВКА СООБЩЕНИЯ В WHATSAPP:")
    print(payload)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            print(f"✅ ОТВЕТ GREEN API: {response.status_code}")
            print(response.text)
    except Exception as e:
        print("❌ ОШИБКА ПРИ ОТПРАВКЕ В WHATSAPP:")
        print(e)
