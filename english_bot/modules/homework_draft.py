"""
Черновик дом. задания (Add/Edit HW): сбор нескольких сообщений от учителя
и их сохранение в БД одним действием («Сохранить») либо отмена («Отмена»).

Черновик хранится в context.user_data["hw_draft"] на время диалога
(ConversationHandler в handlers/teacher.py). Текстовые сообщения идут в
lessons.content, остальные типы сообщений (фото/видео/документ/ссылка как
отдельное сообщение) — в lesson_attachments как ссылки source_chat_id/
source_message_id для последующей рассылки через copy_message.
"""

from typing import Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.ext import ContextTypes

from database import db
from locales import t

DRAFT_KEY = "hw_draft"


def start_draft(context: ContextTypes.DEFAULT_TYPE, lesson_id: int, is_edit: bool) -> None:
    context.user_data[DRAFT_KEY] = {
        "lesson_id": lesson_id,
        "is_edit": is_edit,
        "text_parts": [],
        "attachments": [],  # список (chat_id, message_id)
    }


def get_draft(context: ContextTypes.DEFAULT_TYPE) -> Optional[dict]:
    return context.user_data.get(DRAFT_KEY)


def clear_draft(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop(DRAFT_KEY, None)


def add_message_to_draft(context: ContextTypes.DEFAULT_TYPE, message: Message) -> int:
    """
    Добавляет присланное учителем сообщение в черновик.
    Возвращает текущее суммарное количество элементов в черновике (для «Добавлено (N)»).
    """
    draft = context.user_data[DRAFT_KEY]

    if message.text:
        # Обычное текстовое сообщение (без медиа) — идёт в текст Д.З.
        draft["text_parts"].append(message.text)
    else:
        # Фото/видео/документ/голосовое и т.п. — сохраняем как вложение
        # (ссылку на исходное сообщение), подпись (caption), если есть,
        # тоже добавляем в текстовую часть.
        draft["attachments"].append((message.chat_id, message.message_id))
        if message.caption:
            draft["text_parts"].append(message.caption)

    return len(draft["text_parts"]) + len(draft["attachments"])


def build_draft_confirm_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(t("btn_save", lang), callback_data="hw_save"),
                InlineKeyboardButton(t("btn_cancel", lang), callback_data="hw_cancel"),
            ]
        ]
    )


def is_draft_empty(context: ContextTypes.DEFAULT_TYPE) -> bool:
    draft = context.user_data.get(DRAFT_KEY)
    if not draft:
        return True
    return not draft["text_parts"] and not draft["attachments"]


def save_draft(context: ContextTypes.DEFAULT_TYPE, teacher_id: int) -> None:
    """
    Фиксирует черновик в БД: текст -> lessons.content, вложения -> lesson_attachments.
    При редактировании существующего урока старые вложения удаляются перед вставкой новых.
    """
    draft = context.user_data[DRAFT_KEY]
    lesson_id = draft["lesson_id"]

    content = "\n\n".join(draft["text_parts"]) if draft["text_parts"] else None
    db.update_lesson_content(lesson_id, content, teacher_id)

    if draft["is_edit"]:
        db.delete_lesson_attachments(lesson_id)

    for chat_id, message_id in draft["attachments"]:
        db.add_lesson_attachment(lesson_id, chat_id, message_id)

    clear_draft(context)
