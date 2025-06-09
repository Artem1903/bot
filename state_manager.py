from state_manager import get_state, set_state

# ...

chat_id = from_number.replace("whatsapp:", "")
state = get_state(chat_id) or "start"

response = dialog_tree.get(state, {}).get("message", "Извините, я Вас не понял.")
next_state = dialog_tree.get(state, {}).get("next", {}).get(message_body.strip())

if next_state:
    set_state(chat_id, next_state)
    response = dialog_tree.get(next_state, {}).get("message", response)
