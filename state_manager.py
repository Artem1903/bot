import sqlite3
import time
import threading
from contextlib import contextmanager

# SQLite + in-memory cache for ultra-fast state management
_DB_PATH = "state.db"
_TTL_SECONDS = 600  # 10 минут

_db_lock = threading.RLock()
_conn = None
_cache = {}  # chat_id -> (state, updated_at)

def _connect():
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
        _conn.execute("PRAGMA journal_mode=WAL;")
        _conn.execute("PRAGMA synchronous=NORMAL;")
        _conn.execute("PRAGMA temp_store=MEMORY;")
        _conn.execute("PRAGMA cache_size=-20000;")  # ~20MB page cache
        _conn.execute("""
            CREATE TABLE IF NOT EXISTS states (
                chat_id TEXT PRIMARY KEY,
                state   TEXT,
                updated_at REAL
            )
        """)
        _conn.commit()
    return _conn

def _expired(ts: float) -> bool:
    return (time.time() - float(ts)) > _TTL_SECONDS

def get_state(chat_id: str, full: bool = False):
    """Возвращает текущее состояние пользователя (или None при истёкшем TTL)."""
    with _db_lock:
        key = str(chat_id)
        if key in _cache:
            state, updated_at = _cache[key]
            if not _expired(updated_at):
                return {"state": state, "updated_at": updated_at} if full else state
            # TTL истёк — сбросим сразу
            reset_state(chat_id)
            return {} if full else None

        conn = _connect()
        cur = conn.execute("SELECT state, updated_at FROM states WHERE chat_id=?", (key,))
        row = cur.fetchone()
        if not row:
            return {} if full else None
        state, updated_at = row
        if _expired(updated_at):
            conn.execute("DELETE FROM states WHERE chat_id=?", (key,))
            conn.commit()
            _cache.pop(key, None)
            return {} if full else None

        _cache[key] = (state, float(updated_at))
        return {"state": state, "updated_at": updated_at} if full else state

def set_state(chat_id: str, state: str):
    """Установить состояние (обновляет TTL)."""
    with _db_lock:
        now = time.time()
        key = str(chat_id)
        _cache[key] = (state, now)
        conn = _connect()
        conn.execute(
            "INSERT INTO states(chat_id, state, updated_at) VALUES(?,?,?) "
            "ON CONFLICT(chat_id) DO UPDATE SET state=excluded.state, updated_at=excluded.updated_at",
            (key, state, now),
        )
        conn.commit()

def touch_state(chat_id: str):
    """Обновить TTL без смены состояния."""
    with _db_lock:
        now = time.time()
        key = str(chat_id)
        if key in _cache:
            st, _ = _cache[key]
            _cache[key] = (st, now)
        conn = _connect()
        conn.execute("UPDATE states SET updated_at=? WHERE chat_id=?", (now, key))
        conn.commit()

def reset_state(chat_id: str):
    """Сбросить состояние пользователя."""
    with _db_lock:
        key = str(chat_id)
        _cache.pop(key, None)
        conn = _connect()
        conn.execute("DELETE FROM states WHERE chat_id=?", (key,))
        conn.commit()
