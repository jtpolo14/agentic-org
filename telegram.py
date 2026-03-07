import os
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

TOKEN_COO = os.getenv("TELEGRAM_TOKEN_COO")
CHAT_ID_COO = os.getenv("TELEGRAM_CHAT_ID_COO")

def send(text):
    r = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": text}
    )
    if not r.ok:
        return False, f"HTTP {r.status_code}: {r.text[:200]}"
    return True, "sent"

def send_coo(text):
    r = requests.post(
        f"https://api.telegram.org/bot{TOKEN_COO}/sendMessage",
        json={"chat_id": CHAT_ID_COO, "text": text}
    )
    if not r.ok:
        return False, f"HTTP {r.status_code}: {r.text[:200]}"
    return True, "sent"

def _fetch(conn, token, offset_key, channel):
    from agent import get_memory, set_memory

    offset_mem = get_memory(conn, offset_key)
    try:
        offset = int(offset_mem["content"]) + 1 if offset_mem else None
    except (ValueError, TypeError):
        offset = None

    params = {"timeout": 5, "allowed_updates": ["message"]}
    if offset:
        params["offset"] = offset

    r = requests.get(f"https://api.telegram.org/bot{token}/getUpdates", params=params)
    if not r.ok:
        return []

    updates = r.json().get("result", [])
    new_messages = []

    for update in updates:
        msg = update.get("message", {})
        text = msg.get("text", "").strip()
        sender = msg.get("from", {}).get("username") or msg.get("from", {}).get("first_name", "unknown")
        update_id = update["update_id"]

        if text:
            conn.execute(
                "INSERT OR IGNORE INTO telegram_messages (update_id, sender, text, channel) VALUES (?, ?, ?, ?)",
                (update_id, sender, text, channel)
            )
            new_messages.append({"sender": sender, "text": text})

        set_memory(conn, offset_key, str(update_id), category="context")

    conn.commit()
    return new_messages

def _get_recent(conn, channel, limit=20):
    rows = conn.execute(
        "SELECT sender, text, received_at FROM telegram_messages WHERE channel=? ORDER BY received_at DESC LIMIT ?",
        (channel, limit)
    ).fetchall()
    return [dict(r) for r in reversed(rows)]

def fetch_messages(conn):
    return _fetch(conn, TOKEN, "telegram.last_update_id", "cos")

def fetch_messages_coo(conn):
    return _fetch(conn, TOKEN_COO, "telegram_coo.last_update_id", "coo")

def get_recent_messages(conn, limit=20):
    return _get_recent(conn, "cos", limit)

def get_recent_messages_coo(conn, limit=20):
    return _get_recent(conn, "coo", limit)
