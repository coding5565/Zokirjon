"""
Запрос и выдача доступа (модель «админ подтверждает»).

Любой пользователь не из TEACHER_IDS после выбора языка сам указывает,
кто он — ученик или учитель (см. handlers/common.py::role_choice_selected) —
и получает access_status='pending' с этой ролью (см. database/db.py::
upsert_user). Отсюда его запрос уходит всем учителям из TEACHER_IDS с
именем/ID/заявленной ролью и инлайн-кнопками Разрешить/Отклонить. Решает
админ — пользователь никогда не назначает себе ДОСТУП сам, только желаемую
роль, которая активируется лишь после одобрения.

Модуль не импортирует handlers.common (наоборот — common.py импортирует этот
модуль для уведомления при регистрации нового пользователя), чтобы не
создавать циклический импорт.
"""

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

import config
from database import db
from locales import t
from modules.content_tree import build_main_menu_keyboard, build_student_menu_keyboard

logger = logging.getLogger(__name__)


def _teacher_lang(teacher_telegram_id: int) -> str:
    """Язык самого учителя (если он уже проходил /start), иначе — русский по умолчанию."""
    teacher_row = db.get_user_by_telegram_id(teacher_telegram_id)
    if teacher_row and teacher_row["language"]:
        return teacher_row["language"]
    return "ru"


def _approval_keyboard(lang: str, student_telegram_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    t("btn_approve", lang), callback_data=f"access_approve:{student_telegram_id}"
                ),
                InlineKeyboardButton(
                    t("btn_reject", lang), callback_data=f"access_reject:{student_telegram_id}"
                ),
            ]
        ]
    )


def _role_label(role: str, lang: str) -> str:
    key = "role_label_teacher" if role == "teacher" else "role_label_student"
    return t(key, lang)


async def notify_teachers_new_request(context: ContextTypes.DEFAULT_TYPE, requester_user) -> None:
    for teacher_telegram_id in config.TEACHER_IDS:
        lang = _teacher_lang(teacher_telegram_id)
        text = t(
            "teacher_new_request",
            lang,
            name=requester_user["full_name"] or "-",
            telegram_id=requester_user["telegram_id"],
            role=_role_label(requester_user["role"], lang),
        )
        try:
            await context.bot.send_message(
                chat_id=teacher_telegram_id,
                text=text,
                reply_markup=_approval_keyboard(lang, requester_user["telegram_id"]),
            )
        except Exception:  # noqa: BLE001 - админ мог не запускать бота/заблокировать его
            logger.exception(
                "Не удалось уведомить админа %s о новом запросе доступа (пользователь %s)",
                teacher_telegram_id,
                requester_user["telegram_id"],
            )


async def handle_access_decision(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    clicker_id = update.effective_user.id

    if not config.is_teacher(clicker_id):
        await query.answer()
        return

    await query.answer()
    decision, telegram_id_str = query.data.split(":")
    target_telegram_id = int(telegram_id_str)
    approve = decision == "access_approve"

    teacher_lang = _teacher_lang(clicker_id)
    target = db.get_user_by_telegram_id(target_telegram_id)

    if target is None or target["access_status"] != "pending":
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:  # noqa: BLE001 - сообщение могло быть уже изменено
            pass
        await query.message.reply_text(t("access_already_handled", teacher_lang))
        return

    new_status = "approved" if approve else "rejected"
    db.set_user_access_status(target_telegram_id, new_status)

    decision_label = t("btn_approve", teacher_lang) if approve else t("btn_reject", teacher_lang)
    try:
        await query.edit_message_text(f"{query.message.text}\n\n→ {decision_label}")
    except Exception:  # noqa: BLE001 - сообщение могло быть уже изменено/удалено
        pass

    target_lang = target["language"]
    if approve:
        # Материалы (Level→Unit→Lesson) — только для роли 'teacher'; одобренный
        # 'student' видит только Writing/Speaking (см. content_tree.py).
        menu_keyboard = (
            build_main_menu_keyboard(target_lang)
            if target["role"] == "teacher"
            else build_student_menu_keyboard(target_lang)
        )
        await context.bot.send_message(target_telegram_id, t("access_approved_notice", target_lang))
        await context.bot.send_message(
            chat_id=target_telegram_id,
            text=t("main_menu_prompt", target_lang),
            reply_markup=menu_keyboard,
        )
    else:
        await context.bot.send_message(target_telegram_id, t("access_rejected_notice", target_lang))
