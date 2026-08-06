"""
Модуль локализации интерфейса (ru/uz/en).

Весь текст, который видит пользователь, должен браться отсюда через t(key, lang),
а не быть захардкожен внутри хендлеров — так требует ТЗ. Здесь же собран
LABEL_TO_ACTION — единый словарь «текст кнопки reply-keyboard → действие»,
построенный сразу для всех языков, чтобы хендлеры не сравнивали строки вручную.
"""

from database.models import LEVELS

DEFAULT_LANG = "ru"

# Названия уровней и Writing/Speaking одинаковы на всех языках (см. ТЗ, раздел 3).
LEVEL_LABELS = {
    "beginner": "Beginner",
    "elementary": "Elementary",
    "pre_intermediate": "Pre-Intermediate",
    "intermediate": "Intermediate",
}

LOCALES: dict[str, dict[str, str]] = {
    "ru": {
        "btn_beginner": "Beginner",
        "btn_elementary": "Elementary",
        "btn_pre_intermediate": "Pre-Intermediate",
        "btn_intermediate": "Intermediate",
        "btn_writing": "Writing",
        "btn_speaking": "Speaking",
        "btn_add_hw": "➕ Добавить Д.З.",
        "btn_edit_hw": "✏️ Изменить Д.З.",
        "btn_back": "⬅️ Назад",
        "btn_save": "✅ Сохранить",
        "btn_cancel": "❌ Отмена",
        "unit_button": "Unit {n}",
        "lesson_button": "Lesson {n}",
        "start_role_greeting": "Здравствуйте, {name}! Выберите раздел:",
        "choose_role_prompt": "Кто вы?",
        "btn_role_student": "🎓 Я ученик",
        "btn_role_teacher": "🧑‍🏫 Я учитель",
        "role_label_student": "Ученик",
        "role_label_teacher": "Учитель",
        "access_pending": (
            "Ваш запрос на доступ отправлен администратору.\n"
            "Как только он подтвердит — вы получите доступ."
        ),
        "access_approved_notice": "✅ Вам открыт доступ к материалам бота!",
        "access_rejected_notice": "❌ Вам не предоставлен доступ к материалам бота.",
        "teacher_new_request": (
            "🔔 Новый запрос на доступ.\n"
            "Имя: {name}\n"
            "Telegram ID: {telegram_id}\n"
            "Роль: {role}\n\n"
            "Выдать доступ?"
        ),
        "btn_approve": "✅ Разрешить",
        "btn_reject": "❌ Отклонить",
        "access_already_handled": "Этот запрос уже обработан.",
        "level_menu_title": "Уровень {level}. Выберите юнит:",
        "unit_menu_title": "{level}, Unit {unit}. Выберите урок:",
        "lesson_not_added": "Домашнее задание для этого урока пока не добавлено.",
        "lesson_content_header": "📄 Домашнее задание:",
        "lesson_title": "{level}, Unit {unit}, Lesson {lesson}",
        "draft_start_prompt": (
            "Пришлите одно или несколько сообщений (текст, фото, видео, документ "
            "или ссылку) для домашнего задания этого урока.\n"
            "Когда закончите — нажмите «{save}»."
        ),
        "draft_added": "Добавлено в черновик ({count}).",
        "draft_saved": "✅ Домашнее задание сохранено.",
        "draft_cancelled": "❌ Черновик отменён, изменения не сохранены.",
        "draft_empty_error": "Черновик пуст — нечего сохранять. Пришлите хотя бы одно сообщение.",
        "choose_feedback_level_prompt": "Выберите свой уровень для проверки:",
        "choose_writing_task_prompt": "Выберите тип задания:",
        "choose_speaking_part_prompt": "Выберите часть экзамена:",
        "writing_question_prompt": "Пришлите вопрос/задание, на которое вы отвечали (текстом).",
        "speaking_question_prompt": "Пришлите вопрос/задание, на которое вы отвечали (текстом).",
        "writing_prompt": "Теперь пришлите текст сочинения (или фото сочинения).",
        "writing_received": "Работа получена, проверяю с помощью ИИ...",
        "writing_feedback_header": "📝 Фидбек по Writing:",
        "speaking_prompt": "Теперь пришлите голосовое или видео-сообщение.",
        "speaking_received": "Запись получена, проверяю с помощью ИИ...",
        "speaking_feedback_header": "🗣 Фидбек по Speaking:",
        "error_generic": "Произошла ошибка. Попробуйте ещё раз.",
        "error_ai_provider": "Не удалось получить ответ от ИИ. Попробуйте ещё раз позже.",
        "error_file_too_large": "Файл слишком большой (максимум {max_mb} МБ). Пришлите файл меньшего размера.",
        "error_unsupported_format": "Неподдерживаемый формат файла.",
        "error_use_buttons": "Пожалуйста, используйте кнопки меню.",
        "error_not_teacher": "Эта функция пока доступна только учителю.",
        "error_writing_needs_text_or_photo": "Пришлите, пожалуйста, текст или фото сочинения.",
        "error_question_needs_text_or_file": "Пришлите вопрос/задание текстом, фото, PDF или .docx файлом.",
        "error_unsupported_question_format": "Неподдерживаемый формат файла. Пришлите текст, фото, PDF или .docx.",
        "error_speaking_needs_media": "Пришлите, пожалуйста, голосовое или видео-сообщение.",
        "feedback_document_caption": "📄 Фидбек готов — файл выше.",
        "batch_next_hint": "Пришлите следующий ответ на этот же вопрос — или нажмите «{back}», чтобы закончить.",
        "main_menu_prompt": "Главное меню:",
        "back_to_main": "Вы вернулись в главное меню.",
        "choose_language_prompt": "🌐 Выберите язык интерфейса / Tilni tanlang / Choose language:",
    },
    "uz": {
        "btn_beginner": "Beginner",
        "btn_elementary": "Elementary",
        "btn_pre_intermediate": "Pre-Intermediate",
        "btn_intermediate": "Intermediate",
        "btn_writing": "Writing",
        "btn_speaking": "Speaking",
        "btn_add_hw": "➕ Uy vazifasi qo'shish",
        "btn_edit_hw": "✏️ Uy vazifasini o'zgartirish",
        "btn_back": "⬅️ Orqaga",
        "btn_save": "✅ Saqlash",
        "btn_cancel": "❌ Bekor qilish",
        "unit_button": "Unit {n}",
        "lesson_button": "Lesson {n}",
        "start_role_greeting": "Assalomu alaykum, {name}! Bo'limni tanlang:",
        "choose_role_prompt": "Siz kimsiz?",
        "btn_role_student": "🎓 O'quvchiman",
        "btn_role_teacher": "🧑‍🏫 O'qituvchiman",
        "role_label_student": "O'quvchi",
        "role_label_teacher": "O'qituvchi",
        "access_pending": (
            "So'rovingiz administratorga yuborildi.\n"
            "U tasdiqlashi bilan kirish huquqini olasiz."
        ),
        "access_approved_notice": "✅ Sizga bot materiallariga kirish huquqi berildi!",
        "access_rejected_notice": "❌ Sizga bot materiallariga kirish huquqi berilmadi.",
        "teacher_new_request": (
            "🔔 Yangi kirish so'rovi.\n"
            "Ism: {name}\n"
            "Telegram ID: {telegram_id}\n"
            "Rol: {role}\n\n"
            "Ruxsat berasizmi?"
        ),
        "btn_approve": "✅ Ruxsat berish",
        "btn_reject": "❌ Rad etish",
        "access_already_handled": "Bu so'rov allaqachon ko'rib chiqilgan.",
        "level_menu_title": "{level} darajasi. Unitni tanlang:",
        "unit_menu_title": "{level}, Unit {unit}. Darsni tanlang:",
        "lesson_not_added": "Bu darsga hali uy vazifasi qo'shilmagan.",
        "lesson_content_header": "📄 Uy vazifasi:",
        "lesson_title": "{level}, Unit {unit}, Lesson {lesson}",
        "draft_start_prompt": (
            "Ushbu darsning uy vazifasi uchun bitta yoki bir nechta xabar "
            "(matn, foto, video, hujjat yoki havola) yuboring.\n"
            "Tugatgach — «{save}» tugmasini bosing."
        ),
        "draft_added": "Qoralamaga qo'shildi ({count}).",
        "draft_saved": "✅ Uy vazifasi saqlandi.",
        "draft_cancelled": "❌ Qoralama bekor qilindi, o'zgarishlar saqlanmadi.",
        "draft_empty_error": "Qoralama bo'sh — saqlashga hech narsa yo'q. Kamida bitta xabar yuboring.",
        "choose_feedback_level_prompt": "Tekshirish uchun darajangizni tanlang:",
        "choose_writing_task_prompt": "Topshiriq turini tanlang:",
        "choose_speaking_part_prompt": "Imtihon qismini tanlang:",
        "writing_question_prompt": "Siz javob bergan savol/topshiriqni yuboring (matn ko'rinishida).",
        "speaking_question_prompt": "Siz javob bergan savol/topshiriqni yuboring (matn ko'rinishida).",
        "writing_prompt": "Endi insho matnini (yoki inshoning fotosini) yuboring.",
        "writing_received": "Ish qabul qilindi, AI yordamida tekshirilmoqda...",
        "writing_feedback_header": "📝 Writing bo'yicha fikr-mulohaza:",
        "speaking_prompt": "Endi ovozli yoki video xabar yuboring.",
        "speaking_received": "Yozuv qabul qilindi, AI yordamida tekshirilmoqda...",
        "speaking_feedback_header": "🗣 Speaking bo'yicha fikr-mulohaza:",
        "error_generic": "Xatolik yuz berdi. Qaytadan urinib ko'ring.",
        "error_ai_provider": "AI'dan javob olishning imkoni bo'lmadi. Birozdan so'ng qaytadan urinib ko'ring.",
        "error_file_too_large": "Fayl juda katta (maksimal {max_mb} MB). Kichikroq fayl yuboring.",
        "error_unsupported_format": "Fayl formati qo'llab-quvvatlanmaydi.",
        "error_use_buttons": "Iltimos, menyu tugmalaridan foydalaning.",
        "error_not_teacher": "Bu funksiya hozircha faqat o'qituvchi uchun mavjud.",
        "error_writing_needs_text_or_photo": "Iltimos, insho matnini yoki fotosini yuboring.",
        "error_question_needs_text_or_file": "Savol/topshiriqni matn, foto, PDF yoki .docx fayl ko'rinishida yuboring.",
        "error_unsupported_question_format": "Fayl formati qo'llab-quvvatlanmaydi. Matn, foto, PDF yoki .docx yuboring.",
        "error_speaking_needs_media": "Iltimos, ovozli yoki video xabar yuboring.",
        "feedback_document_caption": "📄 Fidbek tayyor — fayl yuqorida.",
        "batch_next_hint": "Shu savolga keyingi javobni yuboring — yoki tugatish uchun «{back}» tugmasini bosing.",
        "main_menu_prompt": "Asosiy menyu:",
        "back_to_main": "Asosiy menyuga qaytdingiz.",
        "choose_language_prompt": "🌐 Tilni tanlang / Выберите язык интерфейса / Choose language:",
    },
    "en": {
        "btn_beginner": "Beginner",
        "btn_elementary": "Elementary",
        "btn_pre_intermediate": "Pre-Intermediate",
        "btn_intermediate": "Intermediate",
        "btn_writing": "Writing",
        "btn_speaking": "Speaking",
        "btn_add_hw": "➕ Add Homework",
        "btn_edit_hw": "✏️ Edit Homework",
        "btn_back": "⬅️ Back",
        "btn_save": "✅ Save",
        "btn_cancel": "❌ Cancel",
        "unit_button": "Unit {n}",
        "lesson_button": "Lesson {n}",
        "start_role_greeting": "Hello, {name}! Choose a section:",
        "choose_role_prompt": "Who are you?",
        "btn_role_student": "🎓 I'm a student",
        "btn_role_teacher": "🧑‍🏫 I'm a teacher",
        "role_label_student": "Student",
        "role_label_teacher": "Teacher",
        "access_pending": (
            "Your access request has been sent to the admin.\n"
            "Once they approve it, you'll get access."
        ),
        "access_approved_notice": "✅ You've been granted access to the bot's materials!",
        "access_rejected_notice": "❌ You have not been granted access to the bot's materials.",
        "teacher_new_request": (
            "🔔 New access request.\n"
            "Name: {name}\n"
            "Telegram ID: {telegram_id}\n"
            "Role: {role}\n\n"
            "Grant access?"
        ),
        "btn_approve": "✅ Approve",
        "btn_reject": "❌ Reject",
        "access_already_handled": "This request has already been handled.",
        "level_menu_title": "{level} level. Choose a unit:",
        "unit_menu_title": "{level}, Unit {unit}. Choose a lesson:",
        "lesson_not_added": "Homework for this lesson hasn't been added yet.",
        "lesson_content_header": "📄 Homework:",
        "lesson_title": "{level}, Unit {unit}, Lesson {lesson}",
        "draft_start_prompt": (
            "Send one or several messages (text, photo, video, document or link) "
            "for this lesson's homework.\n"
            "When you're done — press \"{save}\"."
        ),
        "draft_added": "Added to draft ({count}).",
        "draft_saved": "✅ Homework saved.",
        "draft_cancelled": "❌ Draft cancelled, changes were not saved.",
        "draft_empty_error": "The draft is empty — nothing to save. Send at least one message.",
        "choose_feedback_level_prompt": "Choose your level for the review:",
        "choose_writing_task_prompt": "Choose the task type:",
        "choose_speaking_part_prompt": "Choose the exam part:",
        "writing_question_prompt": "Send the question/prompt you were responding to (as text).",
        "speaking_question_prompt": "Send the question/prompt you were responding to (as text).",
        "writing_prompt": "Now send the essay text (or a photo of the essay).",
        "writing_received": "Work received, checking with AI...",
        "writing_feedback_header": "📝 Writing feedback:",
        "speaking_prompt": "Now send a voice or video message.",
        "speaking_received": "Recording received, checking with AI...",
        "speaking_feedback_header": "🗣 Speaking feedback:",
        "error_generic": "Something went wrong. Please try again.",
        "error_ai_provider": "Couldn't get a response from the AI. Please try again later.",
        "error_file_too_large": "The file is too large (maximum {max_mb} MB). Please send a smaller file.",
        "error_unsupported_format": "Unsupported file format.",
        "error_use_buttons": "Please use the menu buttons.",
        "error_not_teacher": "This feature is currently only available to the teacher.",
        "error_writing_needs_text_or_photo": "Please send the essay text or a photo of it.",
        "error_question_needs_text_or_file": "Please send the question/prompt as text, a photo, a PDF, or a .docx file.",
        "error_unsupported_question_format": "Unsupported file format. Please send text, a photo, a PDF, or a .docx file.",
        "error_speaking_needs_media": "Please send a voice or video message.",
        "feedback_document_caption": "📄 Feedback is ready — see the file above.",
        "batch_next_hint": "Send the next answer to this same question — or press \"{back}\" to finish.",
        "main_menu_prompt": "Main menu:",
        "back_to_main": "You're back in the main menu.",
        "choose_language_prompt": "🌐 Choose language / Выберите язык интерфейса / Tilni tanlang:",
    },
}


def t(key: str, lang: str | None, **kwargs) -> str:
    """
    Возвращает локализованную строку по ключу.
    Если язык неизвестен — используется DEFAULT_LANG.
    Если ключ не найден ни в одном словаре — возвращается сам ключ (чтобы не падать).
    """
    lang_dict = LOCALES.get(lang or DEFAULT_LANG, LOCALES[DEFAULT_LANG])
    template = lang_dict.get(key, LOCALES[DEFAULT_LANG].get(key, key))
    return template.format(**kwargs) if kwargs else template


# ---------------------------------------------------------------------------
# LABEL_TO_ACTION — единый словарь «подпись кнопки → действие», собранный
# сразу для всех трёх языков. Хендлеры сверяются только с ним, никогда —
# с сырыми строками напрямую.
# ---------------------------------------------------------------------------

ACTION_WRITING = "writing"
ACTION_SPEAKING = "speaking"
ACTION_BACK = "back"
ACTION_ADD_HW = "add_hw"
ACTION_EDIT_HW = "edit_hw"

_LEVEL_ACTION_KEY = {
    "btn_beginner": "beginner",
    "btn_elementary": "elementary",
    "btn_pre_intermediate": "pre_intermediate",
    "btn_intermediate": "intermediate",
}

_SERVICE_ACTION_KEY = {
    "btn_writing": ACTION_WRITING,
    "btn_speaking": ACTION_SPEAKING,
    "btn_back": ACTION_BACK,
    "btn_add_hw": ACTION_ADD_HW,
    "btn_edit_hw": ACTION_EDIT_HW,
}


def _build_label_to_action() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for lang_dict in LOCALES.values():
        for locale_key, action in {**_LEVEL_ACTION_KEY, **_SERVICE_ACTION_KEY}.items():
            label = lang_dict[locale_key]
            mapping[label] = action
    return mapping


LABEL_TO_ACTION: dict[str, str] = _build_label_to_action()

assert set(LEVELS) == set(_LEVEL_ACTION_KEY.values())


def labels_for_action(action: str) -> set[str]:
    """Обратный поиск по LABEL_TO_ACTION: все подписи кнопки (на всех языках) для действия."""
    return {label for label, act in LABEL_TO_ACTION.items() if act == action}
