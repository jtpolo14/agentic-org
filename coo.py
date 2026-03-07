import time
import signal
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv
from rich.live import Live
from rich.console import Console
from db import get_connection, init_db, next_task
from agent import list_memories, create_cos_task
from telegram import send_coo, fetch_messages_coo, get_recent_messages_coo
from llm import run_agent
from ui import build_layout, push_cycle

load_dotenv()

POLL_INTERVAL = 10
AGENT = "coo"
console = Console()
ui_state = {"status": "monitoring", "last_action": "Starting up..."}

def set_status(status, action):
    ui_state["status"] = status
    ui_state["last_action"] = action

def seed_coo(conn):
    existing = conn.execute(
        "SELECT id FROM tasks WHERE assigned_to = 'coo' LIMIT 1"
    ).fetchone()
    if existing:
        return

    # Seed initial COO tasks
    create_cos_task(
        conn,
        title="Schedule COO Telegram channel setup",
        description=(
            "The COO agent needs its own Telegram channel for operational alerts. "
            "Please schedule 15 minutes on CEO's calendar to: "
            "1) Create a new Telegram group for COO alerts, "
            "2) Add the bot to the group, "
            "3) Add COO_TELEGRAM_CHAT_ID to .env."
        ),
        priority=2,
        effort="quick"
    )

    # COO's own first task
    conn.execute("""
        INSERT INTO tasks (title, description, priority, effort, assigned_to)
        VALUES (
            'Baseline infrastructure health check',
            'Run initial checks: DB size, session counts, memory usage. Log baseline to ops.health memory.',
            1, 'quick', 'coo'
        )
    """)
    conn.commit()

def cycle(conn, live):
    new = fetch_messages_coo(conn)
    task = next_task(conn, agent=AGENT)

    if not task and not new:
        set_status("monitoring", f"Last checked {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC")
        live.update(build_layout(conn, **ui_state, agent=AGENT))
        return

    if new:
        set_status("message", f"{len(new)} new Telegram message(s)")
        live.update(build_layout(conn, **ui_state, agent=AGENT))

    if task:
        set_status("working", f"#{task['id']} [{task['effort']}] {task['title']}")
        live.update(build_layout(conn, **ui_state, agent=AGENT))
        if task["recurs"]:
            conn.execute("""
                UPDATE tasks
                SET last_run_at = datetime('now'),
                    next_run_at = datetime('now', '+' || recurs || ' seconds')
                WHERE id = ?
            """, (task["id"],))
            conn.commit()

    memories = list_memories(conn)
    recent_messages = get_recent_messages_coo(conn)
    tool_log = []
    run_agent(
        conn, task, memories,
        recent_messages=recent_messages,
        new_messages=new,
        poll_interval=POLL_INTERVAL,
        tool_log=tool_log,
        system_files=("START_HERE_COO.md", "job_coo.md"),
        telegram_fn=send_coo
    )
    action = task["title"] if task else f"{len(new)} message(s)"
    push_cycle(action, tool_log, agent=AGENT)
    set_status("monitoring", f"Done: {action}")

def main():
    conn = get_connection()
    init_db(conn)
    seed_coo(conn)

    def shutdown(sig, frame):
        conn.close()
        console.print("\n[dim]COO stopped.[/dim]")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    with Live(build_layout(conn, **ui_state, agent=AGENT), refresh_per_second=2, screen=True) as live:
        while True:
            cycle(conn, live)
            time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
