import sqlite3

def get_connection(path="agent.db"):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS memories (
            id          INTEGER PRIMARY KEY,
            key         TEXT UNIQUE NOT NULL,
            category    TEXT,
            content     TEXT,
            updated_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id          INTEGER PRIMARY KEY,
            title       TEXT NOT NULL,
            description TEXT,
            status      TEXT DEFAULT 'pending',
            priority    INTEGER DEFAULT 5,
            effort      TEXT DEFAULT 'medium',
            urgent      INTEGER DEFAULT 0,
            due_at      TEXT,
            recurs      INTEGER,
            last_run_at TEXT,
            created_at  TEXT DEFAULT (datetime('now')),
            updated_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS task_dependencies (
            task_id        INTEGER REFERENCES tasks(id),
            depends_on_id  INTEGER REFERENCES tasks(id),
            PRIMARY KEY (task_id, depends_on_id)
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id           INTEGER PRIMARY KEY,
            started_at   TEXT DEFAULT (datetime('now')),
            summary      TEXT,
            next_task_id INTEGER REFERENCES tasks(id)
        );

        CREATE TABLE IF NOT EXISTS telegram_messages (
            id          INTEGER PRIMARY KEY,
            update_id   INTEGER UNIQUE,
            sender      TEXT,
            text        TEXT,
            received_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS session_notes (
            id         INTEGER PRIMARY KEY,
            session_id INTEGER REFERENCES sessions(id),
            note       TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    # migrations
    try:
        conn.execute("ALTER TABLE telegram_messages ADD COLUMN channel TEXT DEFAULT 'cos'")
        conn.commit()
    except Exception:
        pass
    try:
        conn.execute("ALTER TABLE tasks ADD COLUMN assigned_to TEXT DEFAULT 'cos'")
        conn.commit()
    except Exception:
        pass
    try:
        conn.execute("ALTER TABLE tasks ADD COLUMN next_run_at TEXT")
        conn.commit()
    except Exception:
        pass
    try:
        conn.execute("ALTER TABLE tasks ADD COLUMN last_run_at TEXT")
        conn.commit()
    except Exception:
        pass

def seed(conn):
    existing = conn.execute("SELECT id FROM tasks WHERE id = 1").fetchone()
    if existing:
        return
    conn.execute("""
        INSERT INTO tasks (title, description, priority, effort, urgent)
        VALUES (
            'Configure email alerts',
            'Ask CEO for email details needed to send urgent notifications: SMTP host, port, sender address, recipient address, and credentials (or API key if using a service like SendGrid).',
            1, 'quick', 0
        )
    """)
    conn.commit()

def next_task(conn, agent="cos"):
    recurring = conn.execute("""
        SELECT * FROM tasks
        WHERE recurs IS NOT NULL
          AND status = 'deferred'
          AND (assigned_to = ? OR assigned_to IS NULL)
          AND (next_run_at IS NULL OR next_run_at <= datetime('now'))
        ORDER BY urgent DESC, priority ASC
        LIMIT 1
    """, (agent,)).fetchone()

    if recurring:
        return recurring

    return conn.execute("""
        SELECT * FROM tasks
        WHERE status = 'pending'
          AND recurs IS NULL
          AND (assigned_to = ? OR assigned_to IS NULL)
          AND id NOT IN (
              SELECT task_id FROM task_dependencies
              JOIN tasks AS dep ON dep.id = task_dependencies.depends_on_id
              WHERE dep.status != 'done'
          )
        ORDER BY urgent DESC, priority ASC, due_at ASC NULLS LAST
        LIMIT 1
    """, (agent,)).fetchone()

if __name__ == "__main__":
    conn = get_connection()
    init_db(conn)
    seed(conn)
    task = next_task(conn)
    print(f"Next task: [{task['effort'].upper()}] {task['title']}")
    conn.close()
