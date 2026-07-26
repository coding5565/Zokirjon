"""
Загрузка конфигурации из .env.

Все токены и ключи берутся только отсюда — в коде их быть не должно (ТЗ, раздел 7).
"""

import os

from dotenv import load_dotenv

load_dotenv()


def _parse_teacher_ids(raw: str) -> set[int]:
    ids = set()
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if chunk:
            ids.add(int(chunk))
    return ids


BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# ИИ-провайдер для проверки Writing/Speaking — OpenAI (см. README, раздел 9:
# отклонение от исходного ТЗ, которое требовало google-genai/Gemini).
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_TRANSCRIBE_MODEL = os.getenv("OPENAI_TRANSCRIBE_MODEL", "whisper-1")

TEACHER_IDS = _parse_teacher_ids(os.getenv("TEACHER_IDS", ""))
DATABASE_PATH = os.getenv("DATABASE_PATH", "bot.db")

# Максимальный размер аудио/видео файла, который бот скачивает и передаёт
# в OpenAI для проверки Speaking (в мегабайтах).
MAX_MEDIA_SIZE_MB = int(os.getenv("MAX_MEDIA_SIZE_MB", "20"))


def validate() -> None:
    """Проверяет, что обязательные переменные окружения заданы, до старта бота."""
    missing = []
    if not BOT_TOKEN:
        missing.append("BOT_TOKEN")
    if not OPENAI_API_KEY:
        missing.append("OPENAI_API_KEY")
    if not TEACHER_IDS:
        missing.append("TEACHER_IDS")
    if missing:
        raise RuntimeError(
            "Не заданы обязательные переменные окружения: "
            + ", ".join(missing)
            + ". Заполните файл .env по образцу .env.example."
        )


def is_teacher(telegram_id: int) -> bool:
    return telegram_id in TEACHER_IDS
