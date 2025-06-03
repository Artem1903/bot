
_user_states = {}

def get_state(chat_id, full=False):
    return _user_states.get(chat_id, {}).get("state") if not full else _user_states.get(chat_id, {})

def set_state(chat_id, state):
    _user_states[chat_id] = {"state": state}

def reset_state(chat_id):
    if chat_id in _user_states:
        del _user_states[chat_id]
