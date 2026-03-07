import time
import signal
import sys
from datetime import datetime
from rich.live import Live
from rich.console import Console
from db import get_connection, init_db, seed, next_task
from agent import list_memories, get_memory
from telegram import fetch_messages, get_recent_messages, send as telegram_send
from llm import run_agent, build_daily_summary
from ui import build_layout, push_cycle

POLL_INTERVAL = 5
console = Console()
ui_state = {"status": "monitoring", "last_action": "Starting up..."}

def set_status(status, action):
    ui_state["status"] = status
    ui_state["last_action"] = action

def cycle(conn, live):
    new = fetch_messages(conn)

    keyword_mem = get_memory(conn, "agent.summary_keyword")
    keyword = keyword_mem["content"] if keyword_mem else "summary"

    if any(keyword.lower() in m["text"].lower() for m in new):
        set_status("working", "Generating daily summary...")
        live.update(build_layout(conn, **ui_state))
        summary = build_daily_summary(conn)
        telegram_send(summary)
        set_status("monitoring", "Daily summary sent to Telegram")
        return

    task = next_task(conn, agent="cos")

    if not task and not new:
        set_status("monitoring", f"Last checked {datetime.utcnow().strftime('%H:%M:%S')} UTC")
        live.update(build_layout(conn, **ui_state))
        return

    if new:
        set_status("message", f"{len(new)} new Telegram message(s)")
        live.update(build_layout(conn, **ui_state))

    if task:
        set_status("working", f"#{task['id']} [{task['effort']}] {task['title']}")
        live.update(build_layout(conn, **ui_state))
        if task["recurs"]:
            conn.execute("""
                UPDATE tasks
                SET last_run_at = datetime('now'),
                    next_run_at = datetime('now', '+' || recurs || ' seconds')
                WHERE id = ?
            """, (task["id"],))
            conn.commit()

    memories = list_memories(conn)
    recent_messages = get_recent_messages(conn)
    tool_log = []
    run_agent(conn, task, memories, recent_messages=recent_messages, new_messages=new, poll_interval=POLL_INTERVAL, tool_log=tool_log)
    action = task["title"] if task else f"{len(new)} message(s)"
    push_cycle(action, tool_log)
    set_status("monitoring", f"Done: {action}")

def main():
    conn = get_connection()
    init_db(conn)
    seed(conn)

    def shutdown(sig, frame):
        conn.close()
        console.print("\n[dim]Stopped.[/dim]")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    with Live(build_layout(conn, **ui_state), refresh_per_second=2, screen=True) as live:
        while True:
            cycle(conn, live)
            time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
