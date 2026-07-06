"""
db.py — SQLite database layer for Boozo.ai.

Tables:
  users    — Google-authenticated users
  sessions — named chat sessions per user
  messages — individual messages per session
"""
import sqlite3
import uuid

from app.config import DB_PATH


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id         TEXT PRIMARY KEY,
            email      TEXT UNIQUE NOT NULL,
            name       TEXT,
            avatar     TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id         TEXT PRIMARY KEY,
            user_id    TEXT NOT NULL,
            title      TEXT NOT NULL DEFAULT 'New Chat',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS messages (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role       TEXT NOT NULL CHECK(role IN ('user','assistant')),
            content    TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
        );
    """)
    conn.commit()
    conn.close()


# ── Users ──────────────────────────────────────────────────────────────────────

def upsert_user(google_id: str, email: str, name: str, avatar: str) -> None:
    conn = get_conn()
    conn.execute("""
        INSERT INTO users (id, email, name, avatar)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name   = excluded.name,
            avatar = excluded.avatar
    """, (google_id, email, name, avatar))
    conn.commit()
    conn.close()


def get_user(google_id: str) -> dict | None:
    conn = get_conn()
    row  = conn.execute("SELECT * FROM users WHERE id = ?", (google_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ── Sessions ───────────────────────────────────────────────────────────────────

def create_session(user_id: str) -> str:
    sid  = str(uuid.uuid4())
    conn = get_conn()
    conn.execute("INSERT INTO sessions (id, user_id) VALUES (?, ?)", (sid, user_id))
    conn.commit()
    conn.close()
    return sid


def get_sessions(user_id: str) -> list[dict]:
    conn = get_conn()
    rows = conn.execute("""
        SELECT id, title, created_at, updated_at
        FROM   sessions
        WHERE  user_id = ?
        ORDER  BY updated_at DESC
    """, (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def rename_session(session_id: str, user_id: str, title: str) -> None:
    conn = get_conn()
    conn.execute(
        "UPDATE sessions SET title = ? WHERE id = ? AND user_id = ?",
        (title, session_id, user_id),
    )
    conn.commit()
    conn.close()


def delete_session(session_id: str, user_id: str) -> None:
    conn = get_conn()
    conn.execute(
        "DELETE FROM sessions WHERE id = ? AND user_id = ?",
        (session_id, user_id),
    )
    conn.commit()
    conn.close()


# ── Messages ───────────────────────────────────────────────────────────────────

def add_message(session_id: str, role: str, content: str) -> None:
    conn = get_conn()
    conn.execute(
        "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
        (session_id, role, content),
    )
    conn.execute(
        "UPDATE sessions SET updated_at = datetime('now') WHERE id = ?",
        (session_id,),
    )
    conn.commit()
    conn.close()


def get_messages(session_id: str, user_id: str) -> list[dict] | None:
    conn = get_conn()
    owns = conn.execute(
        "SELECT 1 FROM sessions WHERE id = ? AND user_id = ?",
        (session_id, user_id),
    ).fetchone()
    if not owns:
        conn.close()
        return None
    rows = conn.execute(
        "SELECT role, content, created_at FROM messages WHERE session_id = ? ORDER BY id",
        (session_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def auto_title(session_id: str, user_id: str) -> None:
    """Set session title from first user message if still default."""
    conn = get_conn()
    sess = conn.execute(
        "SELECT title FROM sessions WHERE id = ? AND user_id = ?",
        (session_id, user_id),
    ).fetchone()
    if sess and sess["title"] == "New Chat":
        msg = conn.execute(
            "SELECT content FROM messages WHERE session_id = ? AND role = 'user' LIMIT 1",
            (session_id,),
        ).fetchone()
        if msg:
            title = msg["content"][:52].strip()
            if len(msg["content"]) > 52:
                title += "…"
            conn.execute(
                "UPDATE sessions SET title = ? WHERE id = ?",
                (title, session_id),
            )
            conn.commit()
    conn.close()
