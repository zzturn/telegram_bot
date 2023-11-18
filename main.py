import re

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import MenuButton
from telegram.ext import CommandHandler, CallbackQueryHandler, ApplicationBuilder, \
    ConversationHandler, MessageHandler, filters, JobQueue
from dotenv import load_dotenv

from config.config import configInstance
from handlers.bot_handler import start, log_update, error_handler, help_command
from handlers.constants import *
from handlers.cron_handler import cron_validate_openkey, cron_request_openkey, cron_sync_kv, cron_hack_openkey, \
    custom_scheduler, cron_info, cron_update
from handlers.openkey_handler import *
from handlers.redis_handler import start_redis, end_redis_mode, handleRedis
from handlers.openkey_handler import handle_callback_input
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
        ],
        states={
            REDIS_MODE: [MessageHandler(filters.TEXT & ~filters.COMMAND & custom_filter & ~filters.REPLY, handleRedis)],
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

    application.add_handler(CallbackQueryHandler(openKey_listAllTokens, CALLBACK_OPENKEY_LISTTOKENS))
    application.add_handler(CallbackQueryHandler(openKey_random, CALLBACK_OPENKEY_RANDOM))
    application.add_handler(CallbackQueryHandler(openKey_addToken, CALLBACK_OPENKEY_ADDTOKEN))
    application.add_handler(CallbackQueryHandler(openKey_removeToken, CALLBACK_OPENKEY_REMOVETOKEN))
    application.add_handler(CallbackQueryHandler(openKey_setCache, CALLBACK_OPENKEY_SETCACHE))
    application.add_handler(CallbackQueryHandler(openKey_removeCache, CALLBACK_OPENKEY_REMOVECACHE))
    application.add_handler(CallbackQueryHandler(openKey_listAllKeys, CALLBACK_OPENKEY_LISTKEYS))
    application.add_handler(CallbackQueryHandler(openKey_hackToken, CALLBACK_OPENKEY_HACKTOKEN))

    # conversation, need to be added before following message handler handle_callback_input
    application.add_handler(conv_handler)

    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND & custom_filter, handle_callback_input))


    # button operation callback
    application.add_handler(
        CommandHandler(filters=custom_filter, command=COMMAND_REMTOKEN, callback=remove_a_openai_token))
    application.add_handler(
        CommandHandler(filters=custom_filter, command=COMMAND_ADDTOKEN, callback=add_a_openai_token))
    application.add_handler(CommandHandler(filters=custom_filter, command=COMMAND_REMKEY, callback=remove_a_cache))
    application.add_handler(CommandHandler(filters=custom_filter, command=COMMAND_ADDKEY, callback=set_a_cache))
    application.add_handler(CommandHandler(filters=custom_filter, command=COMMAND_HACK, callback=hack_openkey))
    application.add_handler(CommandHandler(filters=custom_filter, command=COMMAND_VALIDATE, callback=validate_openkey))
    application.add_handler(CommandHandler(filters=custom_filter, command=COMMAND_CRON_INFO, callback=cron_info))
    application.add_handler(CommandHandler(filters=custom_filter, command=COMMAND_CRON_UPDATE, callback=cron_update))

    application.add_handler(CommandHandler(filters=custom_filter, command=COMMAND_HELP, callback=help_command))



    # Add the cron job
    custom_scheduler.add_job(cron_request_openkey, CronTrigger.from_crontab(configInstance.cron_request_openkey), args=[application], id=CRON_REQUEST_OPENKEY)
    custom_scheduler.add_job(cron_hack_openkey, CronTrigger.from_crontab(configInstance.cron_hack_openkey), args=[application], id=CRON_HACK_OPENKEY)
    custom_scheduler.add_job(cron_validate_openkey, CronTrigger.from_crontab(configInstance.cron_validate_openkey), args=[application], id=CRON_VALIDATE_OPENKEY)
    custom_scheduler.add_job(cron_sync_kv, CronTrigger.from_crontab(configInstance.cron_sync_kv), args=[application], id=CRON_SYNC_KV)
    custom_scheduler.start()

    logger.info('-------------Bot started-------------')
    application.run_polling()


if __name__ == '__main__':
    main()
