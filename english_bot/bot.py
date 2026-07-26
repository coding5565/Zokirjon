"""
Точка входа: собирает Application, регистрирует хендлеры и запускает polling.

Порядок регистрации важен: ConversationHandler'ы (черновик Д.З., Writing,
Speaking) должны идти раньше общего MessageHandler навигации — иначе, пока
активен диалог, общий обработчик может перехватить сообщение раньше него
(python-telegram-bot проверяет хендлеры одной группы по порядку добавления).
"""

import logging

from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

import config
from database.db import init_db
from handlers import access, common, teacher

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def build_application() -> Application:
    application = Application.builder().token(config.BOT_TOKEN).build()

    application.add_handler(teacher.draft_conversation)
    application.add_handler(teacher.writing_conversation)
    application.add_handler(teacher.speaking_conversation)

    application.add_handler(CallbackQueryHandler(common.language_selected, pattern=r"^lang:"))
    application.add_handler(
        CallbackQueryHandler(access.handle_access_decision, pattern=r"^access_(approve|reject):\d+$")
    )
    application.add_handler(CommandHandler("start", common.start))

    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, teacher.handle_navigation_text)
    )

    return application


def main() -> None:
    config.validate()
    init_db()

    application = build_application()
    logger.info("Бот запускается (polling)...")
    application.run_polling(allowed_updates=None)


if __name__ == "__main__":
    main()
