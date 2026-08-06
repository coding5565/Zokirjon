"""
/start, выбор языка интерфейса, выбор роли («Кто вы?») и общая проверка
доступа (require_access/is_active_teacher), которой пользуются Writing/
Speaking и вся навигация в handlers/teacher.py.

Роль пользователя-бутстрап-админа (TEACHER_IDS из .env) всегда «teacher» —
это фиксировано и не меняется. Все остальные явно выбирают роль (ученик/
учитель) при первом /start; выбор уходит на подтверждение администратору
(handlers/access.py) — самоназначение доступа по-прежнему исключено, но
самоназначение ЖЕЛАЕМОЙ роли теперь разрешено, при условии, что финальное
решение остаётся за админом (см. README, раздел про запрос доступа).
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


def build_role_choice_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(t("btn_role_student", lang), callback_data="role_choice:student"),
                InlineKeyboardButton(t("btn_role_teacher", lang), callback_data="role_choice:teacher"),
            ]
        ]
    )


def is_active_teacher(telegram_id: int, user) -> bool:
    """
    True для бутстрап-админов (TEACHER_IDS из .env, доступ всегда и
    безусловно) и для пользователей, которых админ одобрил именно как
    учителя (role='teacher' и access_status='approved') — обе категории
    получают одинаковый полный доступ (навигация с правом редактирования,
    Add/Edit HW). Общий helper — используется и здесь, и в handlers/teacher.py,
    чтобы проверка не разъезжалась по местам.
    """
    if config.is_teacher(telegram_id):
        return True
    return user["role"] == "teacher" and user["access_status"] == "approved"


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
        # 'pending' и уведомляем админов сейчас, раз уж он вернулся в бота.
        db.set_user_access_status(telegram_id, "pending")
        user = db.get_user_by_telegram_id(telegram_id)
        await access.notify_teachers_new_request(context, user)

    await _enter_main_screen(update.effective_chat.id, context, user)


async def language_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    lang = query.data.split(":", 1)[1]
    telegram_user = query.from_user

    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:  # noqa: BLE001 - сообщение могло быть уже изменено/удалено
        pass

    if config.is_teacher(telegram_user.id):
        # Бутстрап-админ — сразу полный доступ, без запроса/подтверждения,
        # как и раньше.
        user = db.upsert_user(
            telegram_id=telegram_user.id,
            full_name=telegram_user.full_name,
            role="teacher",
            language=lang,
            force_role=True,
        )
        await _enter_main_screen(query.message.chat_id, context, user)
        return

    # Не бутстрап-админ и (по построению start()) ещё не существует в БД —
    # сначала спрашиваем «Кто вы?», запись в БД создастся только после
    # ответа (role_choice_selected), вместе с языком, который пока держим
    # в user_data.
    context.user_data["pending_language"] = lang
    await query.message.reply_text(
        t("choose_role_prompt", lang),
        reply_markup=build_role_choice_keyboard(lang),
    )


async def role_choice_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    role = query.data.split(":", 1)[1]  # "student" или "teacher"
    telegram_user = query.from_user
    lang = context.user_data.pop("pending_language", None)

    if lang is None:
        # Сессия потеряна (например, бот перезапустился между шагами) —
        # начинаем заново с выбора языка.
        await query.message.reply_text(
            t("choose_language_prompt", None),
            reply_markup=build_language_keyboard(),
        )
        return

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

    # Уведомляем админов сразу — это единственный момент создания записи
    # для не-бутстрап пользователя, так что дублирования при повторных
    # /start (как раньше через existed_before) не требуется.
    await access.notify_teachers_new_request(context, user)
    await _enter_main_screen(query.message.chat_id, context, user)


async def _enter_main_screen(chat_id: int, context: ContextTypes.DEFAULT_TYPE, user) -> None:
    """Показывает главное меню учителю/одобренному пользователю либо статус запроса доступа."""
    context.user_data.clear()
    lang = user["language"]

    if is_active_teacher(user["telegram_id"], user):
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
            text=t("access_pending", lang),
            reply_markup=ReplyKeyboardRemove(),
        )


async def require_access(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Возвращает строку users для активного учителя (is_active_teacher) либо
    одобренного пользователя любой роли (access_status == 'approved').
    Иначе отправляет понятное сообщение о текущем статусе и возвращает None.
    Используется в handlers/teacher.py для Writing/Speaking — эти функции
    доступны и учителю, и одобренному ученику, в отличие от навигации/
    Add-Edit-HW, где для учителя используется отдельная, более строгая
    проверка (_require_teacher, тоже через is_active_teacher).
    """
    telegram_id = update.effective_user.id
    user = db.get_user_by_telegram_id(telegram_id)

    if user is None or user["language"] is None:
        await update.effective_chat.send_message("/start")
        return None

    if is_active_teacher(telegram_id, user):
        return user

    if user["access_status"] == "approved":
        return user

    message_key = "access_rejected_notice" if user["access_status"] == "rejected" else "access_pending"
    await update.effective_message.reply_text(t(message_key, user["language"]))
    return None
