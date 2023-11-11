import re

from telegram import MenuButton
from telegram.ext import CommandHandler, CallbackQueryHandler, ApplicationBuilder, \
    ConversationHandler, MessageHandler, filters, JobQueue
from dotenv import load_dotenv

from config.config import configInstance
from handlers.bot_handler import start, log_update, error_handler
from handlers.constants import REDIS_MODE, WAIT_SINGLE_INPUT, CALLBACK_OPENKEY_ADDTOKEN, CALLBACK_OPENKEY_REMOVETOKEN, \
    CALLBACK_OPENKEY_SETCACHE, CALLBACK_OPENKEY_REMOVECACHE, CALLBACK_START_REDIS, COMMAND_REMTOKEN, COMMAND_ADDTOKEN, \
    COMMAND_REMKEY, COMMAND_ADDKEY, CALLBACK_OPENKEY_LISTALL, CALLBACK_OPENKEY_RANDOM, COMMAND_CLOSEREDIS, \
    COMMAND_REDIS, CALLBACK_START, CALLBACK_OPENKEY, COMMAND_SUMMARIZE, COMMAND_BACKUP, COMMAND_START
from handlers.cron_handler import cron_validate_openkey, cron_request_openkey
from handlers.openkey_handler import remove_a_openai_token, add_a_openai_token, remove_a_cache, set_a_cache, \
    openKey_addToken, openKey_removeToken, openKey_setCache, openKey_removeCache, openKey_random, openKey_listAll, \
    openKey
from handlers.redis_handler import start_redis, end_redis_mode, handleRedis, handle_redis_operation_input
from handlers.url_handler import summarize_url_text, save_url
from logger.logger_config import setup_logger

logger = setup_logger('main')

TELEGRAM_BOT_TOKEN = configInstance.telegram_bot_token


def main() -> None:
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN) \
        .base_url(configInstance.telegram_bot_api_base) \
        .job_queue(JobQueue()) \
        .build()

    # log and error
    application.add_handler(MessageHandler(filters.ALL, log_update), group=1)
    application.add_error_handler(error_handler)

    # all command should be authorized
    # custom_filter = filters.SenderChat(chat_id=configInstance.developer_chat_id)
    custom_filter = filters.User(user_id=configInstance.developer_chat_id)
    # conversation needs user input
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler(command=COMMAND_REDIS, callback=start_redis, filters=custom_filter),
            CallbackQueryHandler(start_redis, CALLBACK_START_REDIS),
            CallbackQueryHandler(openKey_addToken, CALLBACK_OPENKEY_ADDTOKEN),
            CallbackQueryHandler(openKey_removeToken, CALLBACK_OPENKEY_REMOVETOKEN),
            CallbackQueryHandler(openKey_setCache, CALLBACK_OPENKEY_SETCACHE),
            CallbackQueryHandler(openKey_removeCache, CALLBACK_OPENKEY_REMOVECACHE)
        ],
        states={
            REDIS_MODE: [MessageHandler(filters.TEXT & ~filters.COMMAND & custom_filter, handleRedis)],
            WAIT_SINGLE_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & custom_filter, handle_redis_operation_input)],
        },
        fallbacks=[CommandHandler(COMMAND_CLOSEREDIS, end_redis_mode)],
        map_to_parent={
            ConversationHandler.END: ConversationHandler.END,
        },
        conversation_timeout=120,
    )

    # start
    application.add_handler(CommandHandler(command=COMMAND_START, callback=start, filters=custom_filter))

    # openkey or redis
    application.add_handler(CallbackQueryHandler(start, pattern='^' + CALLBACK_START + '$'))
    application.add_handler(CallbackQueryHandler(openKey, pattern='^' + CALLBACK_OPENKEY + '$'))

    # summarize
    application.add_handler(
        CommandHandler(command=COMMAND_SUMMARIZE, callback=summarize_url_text, filters=custom_filter))
    application.add_handler(
        CommandHandler(command=COMMAND_BACKUP, callback=save_url, filters=custom_filter))

    # conversation
    application.add_handler(conv_handler)

    # button operation callback
    application.add_handler(
        CommandHandler(filters=custom_filter, command=COMMAND_REMTOKEN, callback=remove_a_openai_token))
    application.add_handler(
        CommandHandler(filters=custom_filter, command=COMMAND_ADDTOKEN, callback=add_a_openai_token))
    application.add_handler(CommandHandler(filters=custom_filter, command=COMMAND_REMKEY, callback=remove_a_cache))
    application.add_handler(CommandHandler(filters=custom_filter, command=COMMAND_ADDKEY, callback=set_a_cache))

    application.add_handler(CallbackQueryHandler(openKey_listAll, CALLBACK_OPENKEY_LISTALL))
    application.add_handler(CallbackQueryHandler(openKey_random, CALLBACK_OPENKEY_RANDOM))

    # cron
    job1 = application.job_queue.run_repeating(cron_request_openkey, interval=60 * 60 * 2, first=5, name='cron_request')
    job2 = application.job_queue.run_repeating(cron_validate_openkey, interval=60 * 30, first=60, name='cron_validate')

    logger.info('-------------Bot started-------------')
    application.run_polling()


if __name__ == '__main__':
    main()
