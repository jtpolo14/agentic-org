from db import get_connection, init_db, seed, next_task
from datetime import datetime

def start_session(conn):
    cur = conn.execute("INSERT INTO sessions DEFAULT VALUES")
    conn.commit()
    return cur.lastrowid

def log_note(conn, session_id, note):
    conn.execute("""
        INSERT INTO session_notes (session_id, note)
        VALUES (?, ?)
    """, (session_id, note))
    conn.commit()

def end_session(conn, session_id, summary):
    conn.execute("""
        UPDATE sessions SET summary = ? WHERE id = ?
    """, (summary, session_id))
    conn.commit()

def wake_up(conn):
    last = conn.execute("""
        SELECT s.id, s.started_at, s.summary,
               GROUP_CONCAT(n.note, ' | ') as notes
        FROM sessions s
        LEFT JOIN session_notes n ON n.session_id = s.id
        WHERE s.summary IS NOT NULL
        GROUP BY s.id
        ORDER BY s.started_at DESC
        LIMIT 1
    """).fetchone()

    open_tasks = conn.execute("""
        SELECT * FROM tasks
        WHERE status = 'pending'
          AND id NOT IN (
              SELECT task_id FROM task_dependencies
              JOIN tasks dep ON dep.id = task_dependencies.depends_on_id
              WHERE dep.status != 'done'
          )
        ORDER BY urgent DESC, priority ASC, due_at ASC NULLS LAST
        LIMIT 5
    """).fetchall()

    urgent = [t for t in open_tasks if t["urgent"]]

    memories = conn.execute("""
        SELECT key, content FROM memories
        ORDER BY updated_at DESC
        LIMIT 5
    """).fetchall()

    print("=" * 50)
    print("AGENT BRIEFING -", datetime.now().strftime("%Y-%m-%d %H:%M"))
    print("=" * 50)

    if last:
        print(f"\nLAST SESSION ({last['started_at']})")
        print(f"  Summary: {last['summary']}")
        if last["notes"]:
            for note in last["notes"].split(" | "):
                print(f"  Note: {note}")
    else:
        print("\nNo previous session found.")

    if urgent:
        print("\nURGENT")
        for t in urgent:
            print(f"  ! [{t['effort'].upper()}] {t['title']}")

    print("\nOPEN TASKS")
    for t in open_tasks:
        flag = "!" if t["urgent"] else " "
        print(f"  {flag} [{t['effort'].upper()}] P{t['priority']} - {t['title']}")

    if memories:
        print("\nRECENT MEMORIES")
        for m in memories:
            print(f"  {m['key']}: {m['content'][:80]}")

    print("=" * 50)

def get_todays_data(conn):
    sessions = conn.execute("""
        SELECT s.started_at, s.summary,
               GROUP_CONCAT(n.note, ' | ') as notes
        FROM sessions s
        LEFT JOIN session_notes n ON n.session_id = s.id
        WHERE date(s.started_at) = date('now')
          AND s.summary IS NOT NULL
        GROUP BY s.id
        ORDER BY s.started_at
    """).fetchall()

    completed = conn.execute("""
        SELECT title, description FROM tasks
        WHERE status = 'done'
          AND date(updated_at) = date('now')
    """).fetchall()

    return [dict(s) for s in sessions], [dict(t) for t in completed]

if __name__ == "__main__":
    conn = get_connection()
    init_db(conn)
    seed(conn)

    # Simulate: end a previous session with a summary and note
    prev = start_session(conn)
    log_note(conn, prev, "Jordan mentioned wanting to set up email alerts soon.")
    end_session(conn, prev, "Reviewed schema design, built DB layer, seeded first task.")

    # Start new session and print briefing
    session_id = start_session(conn)
    wake_up(conn)
    conn.close()
