"""
/start, выбор языка интерфейса и определение роли (учитель/ученик), а также
общая проверка доступа (require_access), которой пользуются Writing/Speaking
в handlers/teacher.py — эти функции доступны и учителю, и одобренному ученику.

Роль пользователя всегда пересчитывается из TEACHER_IDS (.env) при каждом
/start — самоназначение роли исключено (ТЗ, разделы 4 и 7). Доступ ученика к
материалам (access_status) выдаётся учителем через handlers/access.py и
никогда не выставляется пользователем самостоятельно.
"""

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import ContextTypes

import config
from database import db
from handlers import access
from locales import t
from modules.content_tree import build_main_menu_keyboard

logger = logging.getLogger(__name__)


def build_language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🇺🇿 Oʻzbekcha", callback_data="lang:uz"),
                InlineKeyboardButton("🇷🇺 Русский", callback_data="lang:ru"),
                InlineKeyboardButton("🇬🇧 English", callback_data="lang:en"),
            ]
        ]
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_id = update.effective_user.id
    user = db.get_user_by_telegram_id(telegram_id)

    if user is None or user["language"] is None:
        await update.message.reply_text(
            t("choose_language_prompt", None),
            reply_markup=build_language_keyboard(),
        )
        return

    if user["role"] == "student" and user["access_status"] is None:
        # Пользователь зарегистрировался ещё до появления запроса доступа
        # (видел старую заглушку «скоро будет доступно») — переводим его в
        # 'pending' и уведомляем учителей сейчас, раз уж он вернулся в бота.
        db.set_user_access_status(telegram_id, "pending")
        user = db.get_user_by_telegram_id(telegram_id)
        await access.notify_teachers_new_request(context, user)

    await _enter_main_screen(update.effective_chat.id, context, user)


async def language_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    lang = query.data.split(":", 1)[1]
    telegram_user = query.from_user
    role = "teacher" if config.is_teacher(telegram_user.id) else "student"
    existed_before = db.get_user_by_telegram_id(telegram_user.id) is not None

    user = db.upsert_user(
        telegram_id=telegram_user.id,
        full_name=telegram_user.full_name,
        role=role,
        language=lang,
    )

    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:  # noqa: BLE001 - сообщение могло быть уже изменено/удалено
        pass

    if role == "student" and not existed_before:
        # Новый пользователь, не из TEACHER_IDS — запрашиваем у учителя(ей)
        # разрешение на доступ (см. handlers/access.py). Уведомляем только
        # один раз, в момент создания записи, а не при каждом /start.
        await access.notify_teachers_new_request(context, user)

    await _enter_main_screen(query.message.chat_id, context, user)


async def _enter_main_screen(chat_id: int, context: ContextTypes.DEFAULT_TYPE, user) -> None:
    """Показывает главное меню учителю/одобренному ученику либо статус запроса доступа."""
    context.user_data.clear()
    lang = user["language"]

    if user["role"] == "teacher":
        greeting = t("start_role_greeting", lang, name=user["full_name"] or "")
        await context.bot.send_message(
            chat_id=chat_id,
            text=greeting,
            reply_markup=build_main_menu_keyboard(lang),
        )
        return

    status = user["access_status"]
    if status == "approved":
        greeting = t("start_role_greeting", lang, name=user["full_name"] or "")
        await context.bot.send_message(
            chat_id=chat_id,
            text=greeting,
            reply_markup=build_main_menu_keyboard(lang),
        )
    elif status == "rejected":
        await context.bot.send_message(
            chat_id=chat_id,
            text=t("access_rejected_notice", lang),
            reply_markup=ReplyKeyboardRemove(),
        )
    else:
        await context.bot.send_message(
            chat_id=chat_id,
            text=t("student_pending", lang),
            reply_markup=ReplyKeyboardRemove(),
        )


async def require_access(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Возвращает строку users, если это учитель (по TEACHER_IDS) либо одобренный
    ученик (access_status == 'approved'). Иначе отправляет понятное сообщение
    о текущем статусе и возвращает None. Используется в handlers/teacher.py
    для Writing/Speaking — эти функции доступны обеим ролям, в отличие от
    навигации/Add-Edit-HW, где для учителя используется отдельная, более
    строгая проверка (_require_teacher).
    """
    telegram_id = update.effective_user.id
    user = db.get_user_by_telegram_id(telegram_id)

    if user is None or user["language"] is None:
        await update.effective_chat.send_message("/start")
        return None

    if user["role"] == "teacher" and config.is_teacher(telegram_id):
        return user

    if user["role"] == "student" and user["access_status"] == "approved":
        return user

    message_key = "access_rejected_notice" if user["access_status"] == "rejected" else "student_pending"
    await update.effective_message.reply_text(t(message_key, user["language"]))
    return None
