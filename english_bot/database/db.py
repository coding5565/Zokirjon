"""
Подключение к SQLite и CRUD-функции.

Используется обычный синхронный sqlite3 — операции короткие и локальные,
поэтому дополнительная асинхронная обёртка не нужна (в отличие от вызовов
OpenAI, которые обязаны уходить в executor, см. modules/ai_feedback.py).
"""

import os
import sqlite3
from pathlib import Path
from typing import Optional

from database.models import init_schema, seed_lessons

# Путь к файлу БД можно переопределить через .env (DATABASE_PATH),
# по умолчанию — файл рядом с проектом.
DB_PATH = os.getenv(
    "DATABASE_PATH", str(Path(__file__).resolve().parent.parent / "bot.db")
)


def get_connection() -> sqlite3.Connection:
    """Открывает новое подключение к БД с доступом к колонкам по имени."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _migrate_users_access_status(conn: sqlite3.Connection) -> None:
    """
    users.access_status добавлен уже после первого релиза бота (запрос доступа
    для учеников). У уже существующей БД этой колонки нет — добавляем её без
    потери данных (ALTER TABLE ADD COLUMN ничего не удаляет и не перезаписывает).
    """
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)")}
    if "access_status" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN access_status TEXT")
        conn.commit()


def _migrate_submissions_feedback_fields(conn: sqlite3.Connection) -> None:
    """
    submissions.level/task_type/question добавлены вместе со структурированным
    Writing/Speaking-флоу (уровень + task/part + вопрос перед самой работой).
    У уже существующей БД этих колонок нет — добавляем без потери истории.
    """
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(submissions)")}
    for column in ("level", "task_type", "question"):
        if column not in columns:
            conn.execute(f"ALTER TABLE submissions ADD COLUMN {column} TEXT")
    conn.commit()


def init_db() -> None:
    """Создаёт таблицы (если их нет), мигрирует старую схему и засеивает 144 пустых урока."""
    conn = get_connection()
    try:
        init_schema(conn)
        _migrate_users_access_status(conn)
        _migrate_submissions_feedback_fields(conn)
        seed_lessons(conn)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# users
# ---------------------------------------------------------------------------

def get_user_by_telegram_id(telegram_id: int) -> Optional[sqlite3.Row]:
    conn = get_connection()
    try:
        return conn.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        ).fetchone()
    finally:
        conn.close()


def upsert_user(
    telegram_id: int,
    full_name: str,
    role: str,
    language: Optional[str] = None,
    force_role: bool = False,
) -> sqlite3.Row:
    """
    Создаёт пользователя, если его ещё нет, либо обновляет его ФИО (и, если
    force_role=True, роль).

    force_role=True — только для TEACHER_IDS-бутстрап-админов из .env: их
    role принудительно пересчитывается в 'teacher' при каждом /start, как
    и раньше. Для всех остальных role выставляется один раз, при создании
    строки (это то, что пользователь выбрал в диалоге «Кто вы?» — ученик
    или учитель), и НЕ трогается при обновлении — иначе решение админа
    (одобрен как учитель/ученик) сбрасывалось бы при каждом следующем /start.

    access_status выставляется только при создании строки: NULL для
    force_role (бутстрап-админ, статус не используется), иначе 'pending' —
    и тоже никогда не трогается при обновлении.
    """
    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        ).fetchone()
        if existing is None:
            initial_status = None if force_role else "pending"
            conn.execute(
                """
                INSERT INTO users (telegram_id, full_name, role, language, access_status)
                VALUES (?, ?, ?, ?, ?)
                """,
                (telegram_id, full_name, role, language, initial_status),
            )
        elif force_role:
            conn.execute(
                "UPDATE users SET full_name = ?, role = ?, language = ? WHERE telegram_id = ?",
                (full_name, role, language, telegram_id),
            )
        else:
            conn.execute(
                "UPDATE users SET full_name = ?, language = ? WHERE telegram_id = ?",
                (full_name, language, telegram_id),
            )
        conn.commit()
        return conn.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        ).fetchone()
    finally:
        conn.close()


def set_user_language(telegram_id: int, language: str) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE users SET language = ? WHERE telegram_id = ?",
            (language, telegram_id),
        )
        conn.commit()
    finally:
        conn.close()


def set_user_access_status(telegram_id: int, status: str) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE users SET access_status = ? WHERE telegram_id = ?",
            (status, telegram_id),
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# lessons
# ---------------------------------------------------------------------------

def get_lesson(level: str, unit_number: int, lesson_number: int) -> Optional[sqlite3.Row]:
    conn = get_connection()
    try:
        return conn.execute(
            """
            SELECT * FROM lessons
            WHERE level = ? AND unit_number = ? AND lesson_number = ?
            """,
            (level, unit_number, lesson_number),
        ).fetchone()
    finally:
        conn.close()


def get_lesson_by_id(lesson_id: int) -> Optional[sqlite3.Row]:
    conn = get_connection()
    try:
        return conn.execute(
            "SELECT * FROM lessons WHERE id = ?", (lesson_id,)
        ).fetchone()
    finally:
        conn.close()


def update_lesson_content(lesson_id: int, content: Optional[str], teacher_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE lessons
            SET content = ?, teacher_id = ?, updated_at = datetime('now')
            WHERE id = ?
            """,
            (content, teacher_id, lesson_id),
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# lesson_attachments
# ---------------------------------------------------------------------------

def get_lesson_attachments(lesson_id: int) -> list[sqlite3.Row]:
    conn = get_connection()
    try:
        return conn.execute(
            "SELECT * FROM lesson_attachments WHERE lesson_id = ? ORDER BY id",
            (lesson_id,),
        ).fetchall()
    finally:
        conn.close()


def add_lesson_attachment(lesson_id: int, source_chat_id: int, source_message_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO lesson_attachments (lesson_id, source_chat_id, source_message_id)
            VALUES (?, ?, ?)
            """,
            (lesson_id, source_chat_id, source_message_id),
        )
        conn.commit()
    finally:
        conn.close()


def delete_lesson_attachments(lesson_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM lesson_attachments WHERE lesson_id = ?", (lesson_id,))
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# submissions
# ---------------------------------------------------------------------------

def insert_submission(
    user_id: int,
    submission_type: str,
    source_chat_id: int,
    source_message_id: int,
    level: Optional[str] = None,
    task_type: Optional[str] = None,
    question: Optional[str] = None,
) -> int:
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO submissions
                (user_id, type, source_chat_id, source_message_id, level, task_type, question)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, submission_type, source_chat_id, source_message_id, level, task_type, question),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_submission_feedback(submission_id: int, ai_feedback: str) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE submissions SET ai_feedback = ? WHERE id = ?",
            (ai_feedback, submission_id),
        )
        conn.commit()
    finally:
        conn.close()
