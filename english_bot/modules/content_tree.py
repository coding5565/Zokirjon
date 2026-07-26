"""
Навигация по дереву Уровень → Юнит → Урок: построение клавиатур, разбор
нажатий и рендер самого урока. Работа с данными уроков (lessons/
lesson_attachments) идёт через database.db.

send_lesson_view() — единая точка показа урока, используется и учителем
(editable=True, с кнопкой Добавить/Изменить Д.З.), и учеником (editable=False,
только просмотр) — см. handlers/teacher.py::handle_navigation_text.
"""

import logging
import re
from typing import Optional

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

from database import db
from database.models import LESSONS_PER_UNIT, UNITS_PER_LEVEL
from locales import LEVEL_LABELS, t

logger = logging.getLogger(__name__)

_UNIT_RE = re.compile(r"^Unit (\d+)$")
_LESSON_RE = re.compile(r"^Lesson (\d+)$")


def level_display_name(level: str) -> str:
    return LEVEL_LABELS[level]


def build_main_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    """Главное меню учителя: 2 столбца, как задано в ТЗ 5.2."""
    rows = [
        [t("btn_beginner", lang), t("btn_elementary", lang)],
        [t("btn_pre_intermediate", lang), t("btn_intermediate", lang)],
        [t("btn_writing", lang), t("btn_speaking", lang)],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def build_units_keyboard(lang: str) -> ReplyKeyboardMarkup:
    """Unit 1 .. Unit 12, по 3 в ряд, + кнопка Назад."""
    labels = [t("unit_button", lang, n=n) for n in range(1, UNITS_PER_LEVEL + 1)]
    rows = [labels[i : i + 3] for i in range(0, len(labels), 3)]
    rows.append([t("btn_back", lang)])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def build_lessons_keyboard(lang: str) -> ReplyKeyboardMarkup:
    """Lesson 1 / Lesson 2 / Lesson 3 + кнопка Назад."""
    labels = [t("lesson_button", lang, n=n) for n in range(1, LESSONS_PER_UNIT + 1)]
    rows = [labels, [t("btn_back", lang)]]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def build_lesson_inline_keyboard(lang: str, lesson_id: int, has_content: bool) -> InlineKeyboardMarkup:
    """Инлайн-кнопка «Добавить Д.З.» либо «Изменить Д.З.» под просмотром урока."""
    if has_content:
        label = t("btn_edit_hw", lang)
        callback_data = f"hw_edit:{lesson_id}"
    else:
        label = t("btn_add_hw", lang)
        callback_data = f"hw_add:{lesson_id}"
    return InlineKeyboardMarkup([[InlineKeyboardButton(label, callback_data=callback_data)]])


def parse_unit_number(text: str) -> Optional[int]:
    match = _UNIT_RE.match(text)
    return int(match.group(1)) if match else None


def parse_lesson_number(text: str) -> Optional[int]:
    match = _LESSON_RE.match(text)
    return int(match.group(1)) if match else None


async def send_lesson_view(bot: Bot, chat_id: int, lang: str, lesson, editable: bool) -> None:
    """
    Показывает урок: заголовок + текст Д.З. (или заглушку "не добавлено") и
    пересылает все вложения через copy_message. При editable=True добавляет
    инлайн-кнопку "Добавить/Изменить Д.З." (учитель); при editable=False —
    только просмотр, без единой кнопки (ученик).
    """
    title = t(
        "lesson_title",
        lang,
        level=level_display_name(lesson["level"]),
        unit=lesson["unit_number"],
        lesson=lesson["lesson_number"],
    )
    attachments = db.get_lesson_attachments(lesson["id"])
    # Д.З. считается заполненным, если есть текст ИЛИ хотя бы одно вложение —
    # урок мог быть заполнен одним файлом без подписи (текста при этом нет).
    has_material = bool(lesson["content"]) or bool(attachments)
    body = (
        f'{t("lesson_content_header", lang)}\n{lesson["content"]}'
        if lesson["content"]
        else t("lesson_not_added", lang)
    )

    reply_markup = (
        build_lesson_inline_keyboard(lang, lesson["id"], has_material) if editable else None
    )
    await bot.send_message(chat_id=chat_id, text=f"{title}\n\n{body}", reply_markup=reply_markup)

    for attachment in attachments:
        try:
            await bot.copy_message(
                chat_id=chat_id,
                from_chat_id=attachment["source_chat_id"],
                message_id=attachment["source_message_id"],
            )
        except Exception:  # noqa: BLE001 - исходное сообщение могло быть удалено
            logger.exception(
                "Не удалось переслать вложение id=%s урока id=%s",
                attachment["id"],
                lesson["id"],
            )
