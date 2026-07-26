"""
Запрос и выдача доступа ученику (модель «учитель подтверждает»).

Любой пользователь не из TEACHER_IDS после выбора языка получает role='student'
и access_status='pending' (см. database/db.py::upsert_user). Отсюда его запрос
уходит всем учителям из TEACHER_IDS с инлайн-кнопками Разрешить/Отклонить.
Учитель решает — пользователь никогда не назначает себе доступ сам.

Модуль не импортирует handlers.common (наоборот — common.py импортирует этот
модуль для уведомления при регистрации нового ученика), чтобы не создавать
циклический импорт.
"""

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

import config
from database import db
from locales import t
from modules.content_tree import build_main_menu_keyboard

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


async def notify_teachers_new_request(context: ContextTypes.DEFAULT_TYPE, student_user) -> None:
    for teacher_telegram_id in config.TEACHER_IDS:
        lang = _teacher_lang(teacher_telegram_id)
        text = t(
            "teacher_new_request",
            lang,
            name=student_user["full_name"] or "-",
            telegram_id=student_user["telegram_id"],
        )
        try:
            await context.bot.send_message(
                chat_id=teacher_telegram_id,
                text=text,
                reply_markup=_approval_keyboard(lang, student_user["telegram_id"]),
            )
        except Exception:  # noqa: BLE001 - учитель мог не запускать бота/заблокировать его
            logger.exception(
                "Не удалось уведомить учителя %s о новом запросе доступа (ученик %s)",
                teacher_telegram_id,
                student_user["telegram_id"],
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

    student_lang = target["language"]
    if approve:
        await context.bot.send_message(target_telegram_id, t("access_approved_notice", student_lang))
        await context.bot.send_message(
            chat_id=target_telegram_id,
            text=t("main_menu_prompt", student_lang),
            reply_markup=build_main_menu_keyboard(student_lang),
        )
    else:
        await context.bot.send_message(target_telegram_id, t("access_rejected_notice", student_lang))
