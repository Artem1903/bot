# state_manager.py

_user_states = {}

def get_state(chat_id, full=False):
    """
    Получить текущее состояние пользователя.
    Если full=True, вернёт весь словарь состояний.
    """
    return _user_states.get(chat_id, {}).get("state") if not full else _user_states.get(chat_id, {})

def set_state(chat_id, state):
    """
    Установить/обновить состояние пользователя.
    """
    _user_states[chat_id] = {"state": state}

def reset_state(chat_id):
    """
    Сбросить состояние пользователя.
    """
    if chat_id in _user_states:
        del _user_states[chat_id]
