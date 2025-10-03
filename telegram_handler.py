

STATE_IDLE = "idle"
STATE_OFFLINE = "awaiting_offline_data"
STATE_ONLINE = "awaiting_online_data"
STATE_PRICE = "price_categories"

AUTO_REPLY = (
    "🤖 Это автоматический чат-бот. Я не могу ответить на текст или фото.\n"
    "Пожалуйста, выбирайте необходимую цифру из предложенного меню.\n"
    "Если хотите вернуться к началу, нажмите 0."
)

async def handle_telegram_webhook(payload):
    try:
        message = payload.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "").strip() if "text" in message else None

        if not chat_id:
            return

        # Первое обращение / истёкший TTL → приветствие и переход в idle
        state = get_state(chat_id)
        if state is None:
            await send_message(chat_id, dialog_tree["start"]["message"])
            set_state(chat_id, STATE_IDLE)
            return

        # продлеваем TTL
        touch_state(chat_id)

        if text:
            # "0" — возврат в меню
            if text == "0":
                set_state(chat_id, STATE_IDLE)
                await send_message(chat_id, dialog_tree["start"]["message"])
                return

            # Этапы записи: принимаем произвольный текст как данные
            if state == STATE_OFFLINE:
                if text.isdigit() and text == "9":
                    await send_telegram_message(ADMIN, f"❌ Отмена очной записи от {chat_id}")
                    set_state(chat_id, STATE_IDLE)
                    await send_message(chat_id, "🚫 Запись отменена.")
                    return
                await send_telegram_message(ADMIN, f"📝 Новая запись (ОЧНО):\n{text}")
                await send_message(chat_id, "✅ Спасибо! Мы с Вами свяжемся по указанным данным.\n☎️ +7 747 4603509")
                set_state(chat_id, STATE_IDLE)
                return

            if state == STATE_ONLINE:
                if text.isdigit() and text == "9":
                    await send_telegram_message(ADMIN, f"❌ Отмена онлайн-записи от {chat_id}")
                    set_state(chat_id, STATE_IDLE)
                    await send_message(chat_id, "🚫 Запись отменена.")
                    return
                await send_telegram_message(ADMIN, f"📝 Новая запись (ОНЛАЙН):\n{text}")
                await send_message(chat_id, "✅ Спасибо! Мы с Вами свяжемся по указанным данным.\n☎️ +7 747 4603509")
                set_state(chat_id, STATE_IDLE)
                return

            # Цифровые пункты
            if text.isdigit():
                if state == STATE_PRICE and text in dialog_tree["price_categories"]["options"]:
                    next_key = dialog_tree["price_categories"]["options"][text]
                    response = dialog_tree[next_key]["message"]
                    await send_message(chat_id, response)
                    if text == "0":
                        set_state(chat_id, STATE_IDLE)
                    else:
                        set_state(chat_id, STATE_PRICE)
                    return

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
                    return

            # Прочий текст вне записи → автоответ
            if state not in [STATE_OFFLINE, STATE_ONLINE]:
                await send_message(chat_id, AUTO_REPLY)
                return

        # Медиа/нет текста
        if state in [STATE_OFFLINE, STATE_ONLINE]:
            await send_message(chat_id, "Пожалуйста, отправьте данные текстом (имя, телефон и др.).")
        else:
            await send_message(chat_id, AUTO_REPLY)

    except Exception as e:
        logging.error(f"❌ Ошибка в telegram_handler: {e}")

async def send_message(chat_id, text):
    await _http.post(API_URL, json={
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    })
