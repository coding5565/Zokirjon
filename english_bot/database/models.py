"""
SQL-схема базы данных бота и функция первоначального заполнения (seed).

Таблицы:
    users              — пользователи бота (учителя и ученики);
    lessons            — 144 урока (4 уровня × 12 юнитов × 3 урока), каждый
                          хранит текст домашнего задания;
    lesson_attachments — вложения (фото/видео/документы/ссылки) к уроку,
                          хранятся как ссылки на исходное сообщение в Telegram,
                          чтобы пересылать их через copy_message без повторной
                          загрузки файлов;
    submissions        — присланные работы (Writing/Speaking) и сгенерированный
                          ИИ-фидбек по ним.
"""

import sqlite3

# Уровни учебника Empower и структура юнитов/уроков — фиксированы ТЗ.
LEVELS = ("beginner", "elementary", "pre_intermediate", "intermediate")
UNITS_PER_LEVEL = 12
LESSONS_PER_UNIT = 3

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL UNIQUE,
    full_name TEXT,
    role TEXT NOT NULL CHECK (role IN ('teacher', 'student')),
    language TEXT CHECK (language IN ('ru', 'uz', 'en')),
    access_status TEXT CHECK (access_status IN ('pending', 'approved', 'rejected')),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS lessons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    level TEXT NOT NULL CHECK (
        level IN ('beginner', 'elementary', 'pre_intermediate', 'intermediate')
    ),
    unit_number INTEGER NOT NULL CHECK (unit_number BETWEEN 1 AND 12),
    lesson_number INTEGER NOT NULL CHECK (lesson_number BETWEEN 1 AND 3),
    content TEXT,
    teacher_id INTEGER REFERENCES users (id),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (level, unit_number, lesson_number)
);

CREATE TABLE IF NOT EXISTS lesson_attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lesson_id INTEGER NOT NULL REFERENCES lessons (id) ON DELETE CASCADE,
    source_chat_id INTEGER NOT NULL,
    source_message_id INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users (id),
    type TEXT NOT NULL CHECK (type IN ('writing', 'speaking')),
    source_chat_id INTEGER NOT NULL,
    source_message_id INTEGER NOT NULL,
    level TEXT,
    task_type TEXT,
    question TEXT,
    ai_feedback TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def init_schema(conn: sqlite3.Connection) -> None:
    """Создаёт таблицы, если их ещё нет."""
    conn.executescript(SCHEMA_SQL)
    conn.commit()


def seed_lessons(conn: sqlite3.Connection) -> None:
    """
    Заранее создаёт все 4×12×3 = 144 пустых записи уроков (content = NULL),
    чтобы навигация Level → Unit → Lesson всегда находила существующую
    строку в БД. Идемпотентно — при повторном запуске ничего не дублирует.
    """
    rows = [
        (level, unit, lesson)
        for level in LEVELS
        for unit in range(1, UNITS_PER_LEVEL + 1)
        for lesson in range(1, LESSONS_PER_UNIT + 1)
    ]
    conn.executemany(
        """
        INSERT OR IGNORE INTO lessons (level, unit_number, lesson_number)
        VALUES (?, ?, ?)
        """,
        rows,
    )
    conn.commit()
