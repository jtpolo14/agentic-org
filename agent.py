"""
High-level agent interface for memory and task management.
"""
from db import get_connection, init_db, seed
from session import start_session, end_session, log_note, wake_up

# Memory

def set_memory(conn, key, content, category=None):
    conn.execute("""
        INSERT INTO memories (key, content, category, updated_at)
        VALUES (?, ?, ?, datetime('now'))
        ON CONFLICT(key) DO UPDATE SET
            content    = excluded.content,
            category   = COALESCE(excluded.category, category),
            updated_at = excluded.updated_at
    """, (key, content, category))
    conn.commit()

def get_memory(conn, key):
    row = conn.execute("SELECT * FROM memories WHERE key = ?", (key,)).fetchone()
    return dict(row) if row else None

def list_memories(conn, category=None):
    if category:
        rows = conn.execute("SELECT * FROM memories WHERE category = ? ORDER BY updated_at DESC", (category,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM memories ORDER BY updated_at DESC").fetchall()
    return [dict(r) for r in rows]

def delete_memory(conn, key):
    conn.execute("DELETE FROM memories WHERE key = ?", (key,))
    conn.commit()

# Tasks

def create_task(conn, title, description=None, priority=5, effort="medium", urgent=False, due_at=None, recurs=None, assigned_to="cos"):
    status = "deferred" if recurs else "pending"
    cur = conn.execute("""
        INSERT INTO tasks (title, description, status, priority, effort, urgent, due_at, recurs, assigned_to)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (title, description, status, priority, effort, int(urgent), due_at, recurs, assigned_to))
    conn.commit()
    return cur.lastrowid

def create_cos_task(conn, title, description=None, priority=5, effort="medium", urgent=False):
    return create_task(conn, title, description, priority, effort, urgent, assigned_to="cos")

def create_coo_task(conn, title, description=None, priority=5, effort="medium", urgent=False):
    return create_task(conn, title, description, priority, effort, urgent, assigned_to="coo")

def update_task(conn, task_id, **kwargs):
    allowed = {"title", "description", "priority", "effort", "urgent", "due_at", "status", "recurs"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    fields["updated_at"] = "datetime('now')"
    set_clause = ", ".join(
        f"{k} = datetime('now')" if v == "datetime('now')" else f"{k} = ?"
        for k, v in fields.items()
    )
    values = [v for v in fields.values() if v != "datetime('now')"]
    conn.execute(f"UPDATE tasks SET {set_clause} WHERE id = ?", (*values, task_id))
    conn.commit()

def complete_task(conn, task_id):
    task = conn.execute("SELECT recurs FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if task and task["recurs"]:
        # Recurring: return to deferred with last_run_at stamped — picked up again when due
        conn.execute("""
            UPDATE tasks SET status = 'deferred', last_run_at = datetime('now'), updated_at = datetime('now')
            WHERE id = ?
        """, (task_id,))
    else:
        conn.execute("UPDATE tasks SET status = 'done', updated_at = datetime('now') WHERE id = ?", (task_id,))
    conn.commit()

def defer_task(conn, task_id):
    conn.execute("UPDATE tasks SET status = 'deferred', updated_at = datetime('now') WHERE id = ?", (task_id,))
    conn.commit()

def list_tasks(conn, status="pending"):
    rows = conn.execute("""
        SELECT * FROM tasks WHERE status = ?
        ORDER BY urgent DESC, priority ASC, due_at ASC NULLS LAST
    """, (status,)).fetchall()
    return [dict(r) for r in rows]

def get_task(conn, task_id):
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return dict(row) if row else None

def search_tasks(conn, query=None, status=None, within_days=None):
    conditions = []
    params = []

    if query:
        conditions.append("(title LIKE ? OR description LIKE ?)")
        q = f"%{query}%"
        params += [q, q]

    if status:
        conditions.append("status = ?")
        params.append(status)

    if within_days:
        conditions.append("created_at >= datetime('now', ?)")
        params.append(f"-{within_days} days")

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    rows = conn.execute(f"""
        SELECT * FROM tasks {where}
        ORDER BY created_at DESC
    """, params).fetchall()
    return [dict(r) for r in rows]

def add_dependency(conn, task_id, depends_on_id):
    conn.execute("INSERT OR IGNORE INTO task_dependencies (task_id, depends_on_id) VALUES (?, ?)",
                 (task_id, depends_on_id))
    conn.commit()

# Demo

if __name__ == "__main__":
    conn = get_connection()
    init_db(conn)
    seed(conn)

    # Memory
    set_memory(conn, "user.name", "CEO", category="context")
    set_memory(conn, "user.email_pref", "Prefers concise summaries, no fluff.", category="preference")
    set_memory(conn, "project.status", "Building agent memory and task system.", category="context")

    print("Memories:")
    for m in list_memories(conn):
        print(f"  [{m['category']}] {m['key']}: {m['content']}")

    # Tasks
    t2 = create_task(conn, "Migrate life.md context to DB", priority=2, effort="quick")
    t3 = create_task(conn, "Build email alert system", priority=3, effort="medium")
    t4 = create_task(conn, "Build agent wake-up scheduler", priority=4, effort="deep")
    add_dependency(conn, t4, t3)  # scheduler depends on email being ready

    print("\nOpen Tasks:")
    for t in list_tasks(conn):
        blocked = ""
        print(f"  P{t['priority']} [{t['effort'].upper()}] {t['title']}{blocked}")

    # Complete a task
    complete_task(conn, 1)
    print("\nAfter completing task 1:")
    for t in list_tasks(conn):
        print(f"  P{t['priority']} [{t['effort'].upper()}] {t['title']}")

    conn.close()
