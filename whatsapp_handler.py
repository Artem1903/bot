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
    # 1) Попробуем получить текст из разных полей
    md = data.get('messageData', {})
    if 'textMessageData' in md:
        message_body = md['textMessageData']['textMessage']
    elif 'extendedTextMessageData' in md:
        message_body = md['extendedTextMessageData']['text']
    else:
        # Логируем непривычные payload’ы
        print("⚠️ Ignored non-text messageData:", md)
        return {"status": "ignored"}

    # 2) Получаем chat_id
    chat_id = data.get('senderData', {}).get('chatId', '').replace("@c.us", "")
    if not chat_id or not message_body:
        return {"status": "ignored"}

    # 3) Извлекаем цифры для обработки пунктов меню,
    #    но сохраняем исходный текст для передачи дальше
    digits = ''.join(filter(str.isdigit, message_body))
    text = message_body.strip()
    state = get_state(chat_id)

    # Обработка «Главного меню»
    if digits == "0":
        reset_state(chat_id)
        await send_whatsapp_message(chat_id, dialog_tree_whatsapp["start"]["message"])
        return {"status": "ok"}

    # Отмена онлайн-записи
    if digits == "9" and state == "awaiting_online_data":
        await send_telegram_message(ADMIN, f"❌ Отмена онлайн-записи от пользователя {chat_id}")
        reset_state(chat_id)
        await send_whatsapp_message(chat_id, "🚫 Запись отменена.")
        return {"status": "ok"}

    # Завершение записи (офлайн и онлайн)
    if state in ("awaiting_offline_data", "awaiting_online_data"):
        await send_whatsapp_message(
            chat_id,
            "✅ Вы успешно записаны!\n"
            "Если что-то изменится, пожалуйста, позвоните в клинику ☎️ +7 747 4603509"
        )
        await send_telegram_message(
            ADMIN,
            f"📝 Новая запись ({'ОНЛАЙН' if state=='awaiting_online_data' else 'ОФФЛАЙН'}):\n"
            f"Сообщение клиента: <b>{message_body}</b>\n"
            f"Номер WhatsApp: <code>{chat_id}</code>"
        )
        reset_state(chat_id)
        return {"status": "ok"}

    # Обработка выбора из прайс-категорий
    if state == "price_categories" and digits in dialog_tree_whatsapp["price_categories"]["options"]:
        next_key = dialog_tree_whatsapp["price_categories"]["options"][digits]
        response = dialog_tree_whatsapp[next_key]["message"]
        await send_whatsapp_message(chat_id, response)
        # Сбрасываем или сохраняем состояние
        if digits == "0":
            reset_state(chat_id)
        else:
            set_state(chat_id, "price_categories")
        return {"status": "ok"}

    # Обработка пунктов главного меню
    if digits in dialog_tree_whatsapp["start"]["options"]:
        next_key = dialog_tree_whatsapp["start"]["options"][digits]
        response = dialog_tree_whatsapp[next_key]["message"]
        await send_whatsapp_message(chat_id, response)

        # Устанавливаем новое состояние
        if digits == "1":
            set_state(chat_id, "awaiting_offline_data")
        elif digits == "2":
            set_state(chat_id, "awaiting_online_data")
        elif digits == "3":
            set_state(chat_id, "price_categories")
        else:
            reset_state(chat_id)

        return {"status": "ok"}

    # Если ничего не подошло — показываем стартовое меню
    await send_whatsapp_message(chat_id, dialog_tree_whatsapp["start"]["message"])
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
