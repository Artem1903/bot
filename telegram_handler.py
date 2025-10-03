import httpx
import logging
from dialog_tree import dialog_tree
from state_manager import get_state, set_state, reset_state, touch_state
from send_to_admin import send_telegram_message

# ВАЖНО: Все тексты в dialog_tree остаются без изменений.

TOKEN = "7601158787:AAE52sbM7kd6DfBWpXPnr0_Q1w4y9am5h9o"
ADMIN = "842014271"
API_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

logging.basicConfig(level=logging.INFO)

# Служебные константы
STATE_IDLE = "idle"
STATE_OFFLINE = "awaiting_offline_data"
STATE_ONLINE = "awaiting_online_data"
STATE_PRICE = "price_categories"

AUTO_REPLY = (
    "🤖 Это автоматический чат-бот. Я не могу ответить на текст или фото.\n\n"
    "Пожалуйста, выбирайте необходимую цифру из предложенного меню.\n"
    "Если хотите вернуться к началу, нажмите 0."
)

async def handle_telegram_webhook(payload):
    try:
        message = payload.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "").strip() if "text" in message else None

        if not chat_id:
            return {"ok": False}

        # Получаем текущее состояние (с TTL 10 мин)
        state = get_state(chat_id)

        # Правило "первое сообщение — приветствие (без автоответа)"
        if state is None:
            # Первое обращение или истёк тайм-аут → показываем стартовое меню
            await send_message(chat_id, dialog_tree["start"]["message"])
            set_state(chat_id, STATE_IDLE)
            return {"ok": True}

        # Обновляем таймер активности
        touch_state(chat_id)

        # Если есть текст
        if text:
            # "0" — всегда возвращение в стартовое меню
            if text == "0":
                set_state(chat_id, STATE_IDLE)
                await send_message(chat_id, dialog_tree["start"]["message"])
                return {"ok": True}

            # Обработка стадий записи: ждём свободный текст с данными
            if state == STATE_OFFLINE:
                if text.isdigit() and text == "9":
                    await send_telegram_message(ADMIN, f"❌ Отмена очной записи от {chat_id}")
                    set_state(chat_id, STATE_IDLE)
                    await send_message(chat_id, "🚫 Запись отменена.")
                    return {"ok": True}
                # Любой текст считаем данными записи
                await send_telegram_message(ADMIN, f"📝 Новая запись (ОЧНО):\n{text}")
                await send_message(chat_id, "✅ Спасибо! Мы с Вами свяжемся по указанным данным.\n Если возникнуть вопросы или изменения, то позвоните по этому номеру: ☎️ +7 747 4603509")
                set_state(chat_id, STATE_IDLE)
                return {"ok": True}

            if state == STATE_ONLINE:
                if text.isdigit() and text == "9":
                    await send_telegram_message(ADMIN, f"❌ Отмена онлайн-записи от {chat_id}")
                    set_state(chat_id, STATE_IDLE)
                    await send_message(chat_id, "🚫 Запись отменена.")
                    return {"ok": True}
                await send_telegram_message(ADMIN, f"📝 Новая запись (ОНЛАЙН):\n{text}")
                await send_message(chat_id, "✅ Спасибо! Мы с Вами свяжемся по указанным данным.\n Если возникнуть вопросы или изменения, то позвоните по этому номеру: ☎️ +7 747 4603509")
                set_state(chat_id, STATE_IDLE)
                return {"ok": True}

            # Цифровые пункты меню
            if text.isdigit():
                # Внутри ценового раздела
                if state == STATE_PRICE and text in dialog_tree["price_categories"]["options"]:
                    next_key = dialog_tree["price_categories"]["options"][text]
                    response = dialog_tree[next_key]["message"]
                    await send_message(chat_id, response)
                    if text == "0":
                        set_state(chat_id, STATE_IDLE)
                    else:
                        set_state(chat_id, STATE_PRICE)
                    return {"ok": True}

                # Главное меню
                if text in dialog_tree["start"]["options"]:
                    next_key = dialog_tree["start"]["options"][text]
                    response = dialog_tree[next_key]["message"]
                    await send_message(chat_id, response)
                    if text == "1":
                        set_state(chat_id, STATE_OFFLINE)
                    elif text == "2":
                        set_state(chat_id, STATE_ONLINE)
                    elif text == "3":
                        set_state(chat_id, STATE_PRICE)
                    else:
                        set_state(chat_id, STATE_IDLE)
                    return {"ok": True}

            # Любой другой текст вне сценария записи → автоответ
            if state not in [STATE_OFFLINE, STATE_ONLINE]:
                await send_message(chat_id, AUTO_REPLY)
                return {"ok": True}

        # Нет текста (фото/аудио и т.п.)
        if state in [STATE_OFFLINE, STATE_ONLINE]:
            await send_message(chat_id, "Пожалуйста, отправьте данные текстом (имя, телефон и др.).")
            return {"ok": True}
        else:
            await send_message(chat_id, AUTO_REPLY)
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
