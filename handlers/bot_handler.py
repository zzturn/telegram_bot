import traceback

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import CallbackContext
from telegram.helpers import escape_markdown

from config.config import configInstance
from handlers.constants import DEVELOPER_CHAT_ID, error_title, CALLBACK_OPENKEY, CALLBACK_START_REDIS
from logger.logger_config import setup_logger

logger = setup_logger('bot')


async def start(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("OpenKey", callback_data=CALLBACK_OPENKEY),
         InlineKeyboardButton("Redis", callback_data=CALLBACK_START_REDIS)],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.edit_message_text('💡Hello, tell me what you want:', reply_markup=reply_markup)
    else:
        await update.message.reply_text('💡Hello, tell me what you want:', reply_markup=reply_markup)


async def help_command(update: Update, context: CallbackContext):
    help_text = """
Here are the commands you can use:
/start - Start the bot
/summarize - Summarize a web url
/backup - Backup a web url
/hack - Hack a token
/validate - Validate a token
/cron_info - Show cron info
/cron_update - Update cron info
/redis - Connect to Redis
/closeredis - Close Redis connection
/remtoken - Remove a token
/addtoken - Add a token
/remkey - Remove a key
/addkey - Add a key
/help - Show this help message
"""
    await update.message.reply_text(help_text)


async def log_update(update: Update, context: CallbackContext) -> None:
    logger.debug(update)


async def error_handler(update: object, context: CallbackContext):
    # logger.error(msg="Exception while handling an update:", exc_info=context.error)
    # 获取错误堆栈信息
    error_traceback = ''.join(traceback.format_tb(context.error.__traceback__))
    context_error = context.error
    if not context_error:
        context_error = 'No error'
    if not error_traceback:
        error_traceback = 'No error traceback'
    error_message = f"{error_title}An error occurred: {escape_markdown(str(context.error), 2)}"

    # 可以通知用户有错误发生
    await context.bot.send_message(chat_id=DEVELOPER_CHAT_ID, text=error_message, parse_mode=ParseMode.MARKDOWN_V2)
