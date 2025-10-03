import sqlite3
import time
import threading
from contextlib import contextmanager

_DB_PATH = "state.db"
_TTL_SECONDS = 600  # 10 minutes

# Simple thread-safe DB access
_db_lock = threading.Lock()

def _init_db():
    with _db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS states (
                chat_id TEXT PRIMARY KEY,
                state   TEXT,
                updated_at REAL
            )
        """)
        conn.commit()

@contextmanager
def _db():
    with _db_lock:
        conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
        try:
            yield conn
        finally:
            conn.close()

def _is_expired(updated_at: float) -> bool:
    if updated_at is None:
        return True
    return (time.time() - float(updated_at)) > _TTL_SECONDS

def get_state(chat_id: str, full: bool = False):
    """
    Получить текущее состояние пользователя.
    Если состояние просрочено (тайм-аут 10 минут), возвращает None.
    Если full=True, вернёт dict(state, updated_at) или {}.
    """
    _init_db()
    with _db() as conn:
        cur = conn.execute("SELECT state, updated_at FROM states WHERE chat_id = ?", (str(chat_id),))
        row = cur.fetchone()
        if not row:
            return {} if full else None
        state, updated_at = row
        if _is_expired(updated_at):
            # авто-сброс по тайм-ауту
            conn.execute("DELETE FROM states WHERE chat_id = ?", (str(chat_id),))
            conn.commit()
            return {} if full else None
        return {"state": state, "updated_at": updated_at} if full else state

def set_state(chat_id: str, state: str):
    """
    Установить/обновить состояние пользователя (обновляет таймер активности).
    """
    _init_db()
    with _db() as conn:
        conn.execute(
            "INSERT INTO states(chat_id, state, updated_at) VALUES(?,?,?) "
            "ON CONFLICT(chat_id) DO UPDATE SET state=excluded.state, updated_at=excluded.updated_at",
            (str(chat_id), state, time.time())
        )
        conn.commit()

def touch_state(chat_id: str):
    """
    Обновить таймер активности, не меняя состояние.
    """
    _init_db()
    with _db() as conn:
        conn.execute(
            "UPDATE states SET updated_at=? WHERE chat_id=?",
            (time.time(), str(chat_id))
        )
        conn.commit()

def reset_state(chat_id: str):
    """
    Сбросить состояние пользователя.
    """
    _init_db()
    with _db() as conn:
        conn.execute("DELETE FROM states WHERE chat_id = ?", (str(chat_id),))
        conn.commit()
