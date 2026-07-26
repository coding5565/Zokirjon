"""
Навигация Level -> Unit -> Lesson (общая для учителя и одобренного ученика),
добавление/изменение домашнего задания (только учитель), а также приём и
проверка Writing/Speaking (учитель и одобренный ученик).

Навигация по дереву (уровень/юнит/урок и «Назад») реализована обычным
MessageHandler'ом поверх context.user_data — глубина дерева фиксирована и
переходы линейны, полноценный ConversationHandler здесь избыточен. Это ОДИН
хендлер на оба типа пользователей (не два параллельных): у учителя и ученика
кнопки называются одинаково («Beginner», «Unit 3», «Назад» ...), поэтому
различить, кто именно нажал, можно только по роли отправителя — если бы это
были два раздельных MessageHandler'а с одинаковым текстовым фильтром, порядок
регистрации решал бы, кто перехватит апдейт, а не отправитель. Роль
разрешается один раз в начале handle_navigation_text, и от неё зависит только
editable-флаг при показе урока (см. modules/content_tree.py::send_lesson_view).

Add/Edit HW, Writing и Speaking обёрнуты в ConversationHandler: каждый из них
ждёт следующее сообщение(-я) пользователя как единый акт ввода (ТЗ, раздел
5.2, механика «черновика»). Add/Edit HW — строго учительская функция
(_require_teacher); Writing/Speaking доступны и одобренному ученику
(common.require_access) — сохранение работы в submissions уже было
role-агностичным (использует user["id"] того, кто прислал).
"""

import logging
import re
from typing import Optional

from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

import config
from database import db
from database.models import LEVELS
from handlers import common
from locales import LABEL_TO_ACTION, labels_for_action, t
from modules import ai_feedback, content_tree, homework_draft

logger = logging.getLogger(__name__)

NAV_LEVEL = "nav_level"
NAV_UNIT = "nav_unit"

DRAFT_COLLECTING = 1

# Writing/Speaking — уровень (см. modules/ai_feedback.py::FEEDBACK_LEVELS) ->
# Task/Part (только IELTS-уровни) -> вопрос/задание -> сама работа.
WRITING_LEVEL, WRITING_TASK, WRITING_QUESTION, WRITING_CONTENT = range(1, 5)
SPEAKING_LEVEL, SPEAKING_TASK, SPEAKING_QUESTION, SPEAKING_CONTENT = range(1, 5)

_FEEDBACK_LEVEL_LABEL_TO_KEY = {label: key for key, label in ai_feedback.FEEDBACK_LEVELS}
_WRITING_TASK_LABEL_TO_KEY = {label: key for key, label in ai_feedback.WRITING_TASK_TYPES}
_SPEAKING_PART_LABEL_TO_KEY = {label: key for key, label in ai_feedback.SPEAKING_TEST_PARTS}


def _build_feedback_level_keyboard(lang: str) -> ReplyKeyboardMarkup:
    labels = [label for _, label in ai_feedback.FEEDBACK_LEVELS]
    rows = [labels[i : i + 2] for i in range(0, len(labels), 2)]
    rows.append([t("btn_back", lang)])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def _build_writing_task_keyboard(lang: str) -> ReplyKeyboardMarkup:
    labels = [label for _, label in ai_feedback.WRITING_TASK_TYPES]
    return ReplyKeyboardMarkup([labels, [t("btn_back", lang)]], resize_keyboard=True)


def _build_speaking_part_keyboard(lang: str) -> ReplyKeyboardMarkup:
    labels = [label for _, label in ai_feedback.SPEAKING_TEST_PARTS]
    return ReplyKeyboardMarkup([labels, [t("btn_back", lang)]], resize_keyboard=True)


def _clear_feedback_draft(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("fb_level", None)
    context.user_data.pop("fb_task", None)
    context.user_data.pop("fb_question", None)


def _regex_filter_for_action(action: str) -> filters.BaseFilter:
    labels = labels_for_action(action)
    pattern = "^(?:" + "|".join(re.escape(label) for label in labels) + ")$"
    return filters.Regex(pattern)


WRITING_FILTER = _regex_filter_for_action("writing")
SPEAKING_FILTER = _regex_filter_for_action("speaking")
BACK_FILTER = _regex_filter_for_action("back")


async def _require_teacher(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Возвращает строку users для учителя, либо None (и отправляет понятное
    сообщение), если это не учитель или пользователь ещё не прошёл /start.
    Доступ к учительским функциям определяется только TEACHER_IDS из .env
    (ТЗ, раздел 7) — не самоназначением роли в БД.
    """
    telegram_id = update.effective_user.id
    user = db.get_user_by_telegram_id(telegram_id)

    if user is None or user["language"] is None:
        await update.effective_chat.send_message("/start")
        return None

    if not config.is_teacher(telegram_id) or user["role"] != "teacher":
        await update.effective_message.reply_text(t("error_not_teacher", user["language"]))
        return None

    return user


async def _cancel_to_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await common.start(update, context)
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Показ экранов навигации
# ---------------------------------------------------------------------------

async def _show_main_menu(chat_id: int, context: ContextTypes.DEFAULT_TYPE, user) -> None:
    lang = user["language"]
    context.user_data[NAV_LEVEL] = None
    context.user_data[NAV_UNIT] = None
    await context.bot.send_message(
        chat_id=chat_id,
        text=t("main_menu_prompt", lang),
        reply_markup=content_tree.build_main_menu_keyboard(lang),
    )


async def _show_units(chat_id: int, context: ContextTypes.DEFAULT_TYPE, user) -> None:
    lang = user["language"]
    level = context.user_data[NAV_LEVEL]
    await context.bot.send_message(
        chat_id=chat_id,
        text=t("level_menu_title", lang, level=content_tree.level_display_name(level)),
        reply_markup=content_tree.build_units_keyboard(lang),
    )


async def _show_lessons(chat_id: int, context: ContextTypes.DEFAULT_TYPE, user) -> None:
    lang = user["language"]
    level = context.user_data[NAV_LEVEL]
    unit = context.user_data[NAV_UNIT]
    await context.bot.send_message(
        chat_id=chat_id,
        text=t(
            "unit_menu_title", lang, level=content_tree.level_display_name(level), unit=unit
        ),
        reply_markup=content_tree.build_lessons_keyboard(lang),
    )


# ---------------------------------------------------------------------------
# Навигация Level -> Unit -> Lesson + Back — общая для учителя и ученика
# ---------------------------------------------------------------------------

async def handle_navigation_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_id = update.effective_user.id
    user = db.get_user_by_telegram_id(telegram_id)

    if user is None or user["language"] is None:
        await update.effective_chat.send_message("/start")
        return

    lang = user["language"]

    if user["role"] == "teacher" and config.is_teacher(telegram_id):
        editable = True
    elif user["role"] == "student" and user["access_status"] == "approved":
        editable = False
    else:
        status = user["access_status"]
        message_key = "access_rejected_notice" if status == "rejected" else "student_pending"
        await update.message.reply_text(t(message_key, lang))
        return

    text = update.message.text
    chat_id = update.effective_chat.id

    action = LABEL_TO_ACTION.get(text)
    nav_level = context.user_data.get(NAV_LEVEL)
    nav_unit = context.user_data.get(NAV_UNIT)

    if action == "back":
        if nav_unit is not None:
            context.user_data[NAV_UNIT] = None
            await _show_units(chat_id, context, user)
        elif nav_level is not None:
            context.user_data[NAV_LEVEL] = None
            await _show_main_menu(chat_id, context, user)
        else:
            await _show_main_menu(chat_id, context, user)
        return

    if nav_level is None:
        if action in LEVELS:
            context.user_data[NAV_LEVEL] = action
            await _show_units(chat_id, context, user)
            return
        await update.message.reply_text(t("error_use_buttons", lang))
        return

    if nav_unit is None:
        unit_number = content_tree.parse_unit_number(text)
        if unit_number is not None:
            context.user_data[NAV_UNIT] = unit_number
            await _show_lessons(chat_id, context, user)
            return
        await update.message.reply_text(t("error_use_buttons", lang))
        return

    lesson_number = content_tree.parse_lesson_number(text)
    if lesson_number is not None:
        lesson = db.get_lesson(nav_level, nav_unit, lesson_number)
        await content_tree.send_lesson_view(context.bot, chat_id, lang, lesson, editable=editable)
        return

    await update.message.reply_text(t("error_use_buttons", lang))


# ---------------------------------------------------------------------------
# Add/Edit HW — ConversationHandler «черновик»
# ---------------------------------------------------------------------------

async def draft_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    user = await _require_teacher(update, context)
    if user is None:
        await query.answer()
        return ConversationHandler.END

    await query.answer()
    action, lesson_id_str = query.data.split(":")
    lesson_id = int(lesson_id_str)
    is_edit = action == "hw_edit"

    homework_draft.start_draft(context, lesson_id, is_edit)
    lang = user["language"]
    await query.message.reply_text(
        t("draft_start_prompt", lang, save=t("btn_save", lang)),
        reply_markup=homework_draft.build_draft_confirm_keyboard(lang),
    )
    return DRAFT_COLLECTING


async def draft_collect_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = await _require_teacher(update, context)
    if user is None:
        return ConversationHandler.END

    lang = user["language"]
    count = homework_draft.add_message_to_draft(context, update.message)
    await update.message.reply_text(
        t("draft_added", lang, count=count),
        reply_markup=homework_draft.build_draft_confirm_keyboard(lang),
    )
    return DRAFT_COLLECTING


async def _finish_draft(chat_id: int, context: ContextTypes.DEFAULT_TYPE, user, cancelled: bool) -> None:
    lang = user["language"]
    draft = homework_draft.get_draft(context)
    lesson_id = draft["lesson_id"] if draft else None

    if cancelled:
        homework_draft.clear_draft(context)
        await context.bot.send_message(chat_id, t("draft_cancelled", lang))
    else:
        if homework_draft.is_draft_empty(context):
            await context.bot.send_message(chat_id, t("draft_empty_error", lang))
            return
        homework_draft.save_draft(context, teacher_id=user["id"])
        await context.bot.send_message(chat_id, t("draft_saved", lang))

    if lesson_id is not None:
        lesson = db.get_lesson_by_id(lesson_id)
        await content_tree.send_lesson_view(context.bot, chat_id, lang, lesson, editable=True)


async def draft_save_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    user = await _require_teacher(update, context)
    if user is None:
        await query.answer()
        return ConversationHandler.END
    await query.answer()

    if homework_draft.is_draft_empty(context):
        await query.message.reply_text(t("draft_empty_error", user["language"]))
        return DRAFT_COLLECTING

    await _finish_draft(query.message.chat_id, context, user, cancelled=False)
    return ConversationHandler.END


async def draft_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    user = await _require_teacher(update, context)
    if user is None:
        await query.answer()
        return ConversationHandler.END
    await query.answer()
    await _finish_draft(query.message.chat_id, context, user, cancelled=True)
    return ConversationHandler.END


async def draft_back_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Нажатие reply-кнопки «Назад» посреди сбора черновика трактуется как отмена."""
    user = await _require_teacher(update, context)
    if user is None:
        return ConversationHandler.END
    await _finish_draft(update.effective_chat.id, context, user, cancelled=True)
    return ConversationHandler.END


draft_conversation = ConversationHandler(
    entry_points=[CallbackQueryHandler(draft_entry, pattern=r"^hw_(add|edit):\d+$")],
    states={
        DRAFT_COLLECTING: [
            CallbackQueryHandler(draft_save_callback, pattern=r"^hw_save$"),
            CallbackQueryHandler(draft_cancel_callback, pattern=r"^hw_cancel$"),
            MessageHandler(BACK_FILTER, draft_back_cancel),
            MessageHandler(filters.ALL & ~filters.COMMAND, draft_collect_message),
        ]
    },
    fallbacks=[CommandHandler("start", _cancel_to_start)],
)


# ---------------------------------------------------------------------------
# Writing — ConversationHandler: уровень -> Task 1/2 (только IELTS) -> вопрос -> сочинение
# ---------------------------------------------------------------------------

async def writing_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = await common.require_access(update, context)
    if user is None:
        return ConversationHandler.END

    _clear_feedback_draft(context)
    lang = user["language"]
    await update.message.reply_text(
        t("choose_feedback_level_prompt", lang),
        reply_markup=_build_feedback_level_keyboard(lang),
    )
    return WRITING_LEVEL


async def writing_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = await common.require_access(update, context)
    if user is None:
        return ConversationHandler.END
    _clear_feedback_draft(context)
    await _show_main_menu(update.effective_chat.id, context, user)
    return ConversationHandler.END


async def writing_level_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = await common.require_access(update, context)
    if user is None:
        return ConversationHandler.END

    lang = user["language"]
    level_key = _FEEDBACK_LEVEL_LABEL_TO_KEY.get(update.message.text)
    if level_key is None:
        await update.message.reply_text(t("error_use_buttons", lang))
        return WRITING_LEVEL

    context.user_data["fb_level"] = level_key
    back_only_keyboard = ReplyKeyboardMarkup([[t("btn_back", lang)]], resize_keyboard=True)

    if level_key in ai_feedback.IELTS_LEVEL_KEYS:
        await update.message.reply_text(
            t("choose_writing_task_prompt", lang),
            reply_markup=_build_writing_task_keyboard(lang),
        )
        return WRITING_TASK

    await update.message.reply_text(t("writing_question_prompt", lang), reply_markup=back_only_keyboard)
    return WRITING_QUESTION


async def writing_task_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = await common.require_access(update, context)
    if user is None:
        return ConversationHandler.END

    lang = user["language"]
    task_key = _WRITING_TASK_LABEL_TO_KEY.get(update.message.text)
    if task_key is None:
        await update.message.reply_text(t("error_use_buttons", lang))
        return WRITING_TASK

    context.user_data["fb_task"] = task_key
    await update.message.reply_text(
        t("writing_question_prompt", lang),
        reply_markup=ReplyKeyboardMarkup([[t("btn_back", lang)]], resize_keyboard=True),
    )
    return WRITING_QUESTION


async def writing_question_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = await common.require_access(update, context)
    if user is None:
        return ConversationHandler.END

    lang = user["language"]
    if not update.message.text:
        await update.message.reply_text(t("error_question_needs_text", lang))
        return WRITING_QUESTION

    context.user_data["fb_question"] = update.message.text
    await update.message.reply_text(
        t("writing_prompt", lang),
        reply_markup=ReplyKeyboardMarkup([[t("btn_back", lang)]], resize_keyboard=True),
    )
    return WRITING_CONTENT


async def writing_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = await common.require_access(update, context)
    if user is None:
        return ConversationHandler.END

    lang = user["language"]
    message = update.message

    text: Optional[str] = None
    image_bytes: Optional[bytes] = None
    image_mime: Optional[str] = None

    if message.text:
        text = message.text
    elif message.photo:
        tg_file = await context.bot.get_file(message.photo[-1].file_id)
        image_bytes = bytes(await tg_file.download_as_bytearray())
        image_mime = "image/jpeg"
    else:
        await message.reply_text(t("error_writing_needs_text_or_photo", lang))
        return WRITING_CONTENT

    level_key = context.user_data.get("fb_level")
    task_key = context.user_data.get("fb_task")
    question = context.user_data.get("fb_question", "")

    submission_id = db.insert_submission(
        user["id"],
        "writing",
        message.chat_id,
        message.message_id,
        level=level_key,
        task_type=task_key,
        question=question,
    )
    await message.reply_text(t("writing_received", lang))

    try:
        feedback = await ai_feedback.get_writing_feedback(
            question=question,
            text=text,
            image_bytes=image_bytes,
            image_mime=image_mime,
            level_key=level_key,
            task_type_key=task_key,
            lang=lang,
        )
    except Exception:  # noqa: BLE001 - любая ошибка/таймаут OpenAI API
        logger.exception("Ошибка OpenAI при проверке Writing (submission id=%s)", submission_id)
        await message.reply_text(
            t("error_ai_provider", lang), reply_markup=content_tree.build_main_menu_keyboard(lang)
        )
        _clear_feedback_draft(context)
        return ConversationHandler.END

    db.update_submission_feedback(submission_id, feedback)
    await message.reply_text(
        f'{t("writing_feedback_header", lang)}\n\n{feedback}',
        reply_markup=content_tree.build_main_menu_keyboard(lang),
    )
    _clear_feedback_draft(context)
    return ConversationHandler.END


writing_conversation = ConversationHandler(
    entry_points=[MessageHandler(WRITING_FILTER, writing_entry)],
    states={
        WRITING_LEVEL: [
            MessageHandler(BACK_FILTER, writing_back),
            MessageHandler(filters.TEXT & ~filters.COMMAND, writing_level_chosen),
        ],
        WRITING_TASK: [
            MessageHandler(BACK_FILTER, writing_back),
            MessageHandler(filters.TEXT & ~filters.COMMAND, writing_task_chosen),
        ],
        WRITING_QUESTION: [
            MessageHandler(BACK_FILTER, writing_back),
            MessageHandler(filters.ALL & ~filters.COMMAND, writing_question_received),
        ],
        WRITING_CONTENT: [
            MessageHandler(BACK_FILTER, writing_back),
            MessageHandler(filters.ALL & ~filters.COMMAND, writing_receive),
        ],
    },
    fallbacks=[CommandHandler("start", _cancel_to_start)],
)


# ---------------------------------------------------------------------------
# Speaking — ConversationHandler: уровень -> Part 1/2/3 (только IELTS) -> вопрос -> запись
# ---------------------------------------------------------------------------

async def speaking_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = await common.require_access(update, context)
    if user is None:
        return ConversationHandler.END

    _clear_feedback_draft(context)
    lang = user["language"]
    await update.message.reply_text(
        t("choose_feedback_level_prompt", lang),
        reply_markup=_build_feedback_level_keyboard(lang),
    )
    return SPEAKING_LEVEL


async def speaking_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = await common.require_access(update, context)
    if user is None:
        return ConversationHandler.END
    _clear_feedback_draft(context)
    await _show_main_menu(update.effective_chat.id, context, user)
    return ConversationHandler.END


async def speaking_level_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = await common.require_access(update, context)
    if user is None:
        return ConversationHandler.END

    lang = user["language"]
    level_key = _FEEDBACK_LEVEL_LABEL_TO_KEY.get(update.message.text)
    if level_key is None:
        await update.message.reply_text(t("error_use_buttons", lang))
        return SPEAKING_LEVEL

    context.user_data["fb_level"] = level_key
    back_only_keyboard = ReplyKeyboardMarkup([[t("btn_back", lang)]], resize_keyboard=True)

    if level_key in ai_feedback.IELTS_LEVEL_KEYS:
        await update.message.reply_text(
            t("choose_speaking_part_prompt", lang),
            reply_markup=_build_speaking_part_keyboard(lang),
        )
        return SPEAKING_TASK

    await update.message.reply_text(t("speaking_question_prompt", lang), reply_markup=back_only_keyboard)
    return SPEAKING_QUESTION


async def speaking_task_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = await common.require_access(update, context)
    if user is None:
        return ConversationHandler.END

    lang = user["language"]
    part_key = _SPEAKING_PART_LABEL_TO_KEY.get(update.message.text)
    if part_key is None:
        await update.message.reply_text(t("error_use_buttons", lang))
        return SPEAKING_TASK

    context.user_data["fb_task"] = part_key
    await update.message.reply_text(
        t("speaking_question_prompt", lang),
        reply_markup=ReplyKeyboardMarkup([[t("btn_back", lang)]], resize_keyboard=True),
    )
    return SPEAKING_QUESTION


async def speaking_question_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = await common.require_access(update, context)
    if user is None:
        return ConversationHandler.END

    lang = user["language"]
    if not update.message.text:
        await update.message.reply_text(t("error_question_needs_text", lang))
        return SPEAKING_QUESTION

    context.user_data["fb_question"] = update.message.text
    await update.message.reply_text(
        t("speaking_prompt", lang),
        reply_markup=ReplyKeyboardMarkup([[t("btn_back", lang)]], resize_keyboard=True),
    )
    return SPEAKING_CONTENT


async def speaking_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = await common.require_access(update, context)
    if user is None:
        return ConversationHandler.END

    lang = user["language"]
    message = update.message

    if message.voice:
        media = message.voice
        mime_type = media.mime_type or "audio/ogg"
    elif message.video:
        media = message.video
        mime_type = media.mime_type or "video/mp4"
    elif message.video_note:
        media = message.video_note
        mime_type = "video/mp4"
    else:
        await message.reply_text(t("error_speaking_needs_media", lang))
        return SPEAKING_CONTENT

    max_bytes = config.MAX_MEDIA_SIZE_MB * 1024 * 1024
    if media.file_size and media.file_size > max_bytes:
        await message.reply_text(t("error_file_too_large", lang, max_mb=config.MAX_MEDIA_SIZE_MB))
        return SPEAKING_CONTENT

    level_key = context.user_data.get("fb_level")
    task_key = context.user_data.get("fb_task")
    question = context.user_data.get("fb_question", "")

    submission_id = db.insert_submission(
        user["id"],
        "speaking",
        message.chat_id,
        message.message_id,
        level=level_key,
        task_type=task_key,
        question=question,
    )
    await message.reply_text(t("speaking_received", lang))

    try:
        tg_file = await context.bot.get_file(media.file_id)
        media_bytes = bytes(await tg_file.download_as_bytearray())
        feedback = await ai_feedback.get_speaking_feedback(
            question=question,
            media_bytes=media_bytes,
            mime_type=mime_type,
            level_key=level_key,
            test_part_key=task_key,
            lang=lang,
        )
    except Exception:  # noqa: BLE001 - большой файл, неподдерживаемый формат, таймаут и т.п.
        logger.exception("Ошибка OpenAI при проверке Speaking (submission id=%s)", submission_id)
        await message.reply_text(
            t("error_ai_provider", lang), reply_markup=content_tree.build_main_menu_keyboard(lang)
        )
        _clear_feedback_draft(context)
        return ConversationHandler.END

    db.update_submission_feedback(submission_id, feedback)
    await message.reply_text(
        f'{t("speaking_feedback_header", lang)}\n\n{feedback}',
        reply_markup=content_tree.build_main_menu_keyboard(lang),
    )
    _clear_feedback_draft(context)
    return ConversationHandler.END


speaking_conversation = ConversationHandler(
    entry_points=[MessageHandler(SPEAKING_FILTER, speaking_entry)],
    states={
        SPEAKING_LEVEL: [
            MessageHandler(BACK_FILTER, speaking_back),
            MessageHandler(filters.TEXT & ~filters.COMMAND, speaking_level_chosen),
        ],
        SPEAKING_TASK: [
            MessageHandler(BACK_FILTER, speaking_back),
            MessageHandler(filters.TEXT & ~filters.COMMAND, speaking_task_chosen),
        ],
        SPEAKING_QUESTION: [
            MessageHandler(BACK_FILTER, speaking_back),
            MessageHandler(filters.ALL & ~filters.COMMAND, speaking_question_received),
        ],
        SPEAKING_CONTENT: [
            MessageHandler(BACK_FILTER, speaking_back),
            MessageHandler(filters.ALL & ~filters.COMMAND, speaking_receive),
        ],
    },
    fallbacks=[CommandHandler("start", _cancel_to_start)],
)
