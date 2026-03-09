import os
import sqlite3


def get_db_path() -> str:
    return os.getenv("DB_PATH", "data/bikes.db").strip() or "data/bikes.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(get_db_path(), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=10000")
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS scooters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                msg_type TEXT NOT NULL,
                text TEXT NOT NULL DEFAULT '',
                caption TEXT NOT NULL DEFAULT '',
                photo_file_id TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL,
                is_available INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                user_name TEXT NOT NULL,
                user_link TEXT NOT NULL,
                user_contact TEXT NOT NULL DEFAULT '',
                scooter_title TEXT NOT NULL,
                rental_date TEXT NOT NULL,
                delivery_type TEXT NOT NULL,
                delivery_map_link TEXT NOT NULL DEFAULT '',
                delivery_time TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pending',
                reminder_user_sent INTEGER NOT NULL DEFAULT 0,
                reminder_admin_sent INTEGER NOT NULL DEFAULT 0,
                rejection_reason TEXT NOT NULL DEFAULT ''
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_scooters_category_available
            ON scooters(category, is_available, id)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_bookings_user_status_id
            ON bookings(user_id, status, id DESC)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_bookings_status_id
            ON bookings(status, id DESC)
            """
        )
        columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(bookings)").fetchall()
        }
        if "user_contact" not in columns:
            conn.execute(
                "ALTER TABLE bookings ADD COLUMN user_contact TEXT NOT NULL DEFAULT ''"
            )
        if "reminder_user_sent" not in columns:
            conn.execute(
                "ALTER TABLE bookings ADD COLUMN reminder_user_sent INTEGER NOT NULL DEFAULT 0"
            )
        if "reminder_admin_sent" not in columns:
            conn.execute(
                "ALTER TABLE bookings ADD COLUMN reminder_admin_sent INTEGER NOT NULL DEFAULT 0"
            )
        scooter_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(scooters)").fetchall()
        }
        if "is_available" not in scooter_columns:
            conn.execute(
                "ALTER TABLE scooters ADD COLUMN is_available INTEGER NOT NULL DEFAULT 1"
            )
        conn.execute("UPDATE bookings SET status = 'active' WHERE status = 'approved'")
        conn.commit()


def list_scooters(
    category_code: str | None = None,
    *,
    only_available: bool = False,
) -> list[dict[str, str | int]]:
    with get_connection() as conn:
        if category_code and only_available:
            rows = conn.execute(
                "SELECT * FROM scooters WHERE category = ? AND is_available = 1 ORDER BY id",
                (category_code,),
            ).fetchall()
        elif category_code:
            rows = conn.execute(
                "SELECT * FROM scooters WHERE category = ? ORDER BY id",
                (category_code,),
            ).fetchall()
        elif only_available:
            rows = conn.execute(
                "SELECT * FROM scooters WHERE is_available = 1 ORDER BY id"
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM scooters ORDER BY id").fetchall()
    return [dict(row) for row in rows]


def get_scooter_by_id(scooter_id: int) -> dict[str, str | int] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM scooters WHERE id = ?", (scooter_id,)).fetchone()
    if not row:
        return None
    return dict(row)


def add_scooter(model: dict[str, str | int]) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO scooters (category, msg_type, text, caption, photo_file_id, title, is_available)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(model["category"]),
                str(model["msg_type"]),
                str(model["text"]),
                str(model["caption"]),
                str(model["photo_file_id"]),
                str(model["title"]),
                int(model.get("is_available", 1)),
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)


def delete_scooter(scooter_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM scooters WHERE id = ?", (scooter_id,))
        conn.commit()
        return cursor.rowcount > 0


def set_scooter_availability(scooter_id: int, is_available: bool) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            "UPDATE scooters SET is_available = ? WHERE id = ?",
            (1 if is_available else 0, scooter_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def toggle_scooter_availability(scooter_id: int) -> bool | None:
    scooter = get_scooter_by_id(scooter_id)
    if not scooter:
        return None
    current = bool(int(scooter.get("is_available", 1)))
    new_state = not current
    ok = set_scooter_availability(scooter_id, new_state)
    return new_state if ok else None


def set_setting(key: str, value: str) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO app_settings (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )
        conn.commit()


def get_setting(key: str) -> str:
    with get_connection() as conn:
        row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    return str(row["value"]) if row else ""


def create_booking(data: dict[str, str | int]) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO bookings (
                user_id, user_name, user_link, user_contact, scooter_title, rental_date,
                delivery_type, delivery_map_link, delivery_time, status, rejection_reason
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', '')
            """,
            (
                int(data["user_id"]),
                str(data["user_name"]),
                str(data["user_link"]),
                str(data.get("user_contact", "")),
                str(data["scooter_title"]),
                str(data["rental_date"]),
                str(data["delivery_type"]),
                str(data.get("delivery_map_link", "")),
                str(data.get("delivery_time", "")),
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)


def get_booking(booking_id: int) -> dict[str, str | int] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
    if not row:
        return None
    return dict(row)


def list_pending_bookings() -> list[dict[str, str | int]]:
    return list_bookings_by_status("pending")


def list_bookings_by_status(status: str, limit: int | None = None) -> list[dict[str, str | int]]:
    with get_connection() as conn:
        if limit is not None:
            rows = conn.execute(
                "SELECT * FROM bookings WHERE status = ? ORDER BY id DESC LIMIT ?",
                (status, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM bookings WHERE status = ? ORDER BY id DESC",
                (status,),
            ).fetchall()
    return [dict(row) for row in rows]


def delete_bookings_by_statuses(statuses: list[str]) -> int:
    if not statuses:
        return 0
    placeholders = ",".join("?" for _ in statuses)
    query = f"DELETE FROM bookings WHERE status IN ({placeholders})"
    with get_connection() as conn:
        cursor = conn.execute(query, tuple(statuses))
        conn.commit()
        return int(cursor.rowcount)


def delete_all_bookings() -> int:
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM bookings")
        conn.commit()
        return int(cursor.rowcount)


def wipe_all_data() -> dict[str, int]:
    with get_connection() as conn:
        scooters_count = int(conn.execute("SELECT COUNT(*) FROM scooters").fetchone()[0])
        bookings_count = int(conn.execute("SELECT COUNT(*) FROM bookings").fetchone()[0])
        settings_count = int(conn.execute("SELECT COUNT(*) FROM app_settings").fetchone()[0])

        conn.execute("DELETE FROM scooters")
        conn.execute("DELETE FROM bookings")
        conn.execute("DELETE FROM app_settings")
        conn.commit()

    return {
        "scooters": scooters_count,
        "bookings": bookings_count,
        "settings": settings_count,
    }


def list_user_bookings(user_id: int) -> list[dict[str, str | int]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM bookings
            WHERE user_id = ? AND status IN ('pending', 'active', 'rejected', 'finished')
            ORDER BY id DESC
            """,
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_latest_booking_by_status(user_id: int, status: str) -> dict[str, str | int] | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT * FROM bookings
            WHERE user_id = ? AND status = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (user_id, status),
        ).fetchone()
    return dict(row) if row else None


def get_latest_active_booking(user_id: int) -> dict[str, str | int] | None:
    return get_latest_booking_by_status(user_id, "active")


def get_latest_sos_booking(user_id: int) -> dict[str, str | int] | None:
    return get_latest_active_booking(user_id)


def set_booking_status(booking_id: int, status: str, rejection_reason: str = "") -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE bookings SET status = ?, rejection_reason = ? WHERE id = ?",
            (status, rejection_reason, booking_id),
        )
        conn.commit()


def list_active_bookings_for_reminders() -> list[dict[str, str | int]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM bookings
            WHERE status = 'active'
              AND (reminder_user_sent = 0 OR reminder_admin_sent = 0)
            ORDER BY id DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def mark_booking_reminders_sent(booking_id: int, *, user_sent: bool, admin_sent: bool) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE bookings
            SET reminder_user_sent = ?, reminder_admin_sent = ?
            WHERE id = ?
            """,
            (1 if user_sent else 0, 1 if admin_sent else 0, booking_id),
        )
        conn.commit()
