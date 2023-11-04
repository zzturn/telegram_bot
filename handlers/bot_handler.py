import traceback

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import CallbackContext

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


def help_command(update: Update, context: CallbackContext):
    help_text = """
    Here are the commands you can use:
    /start - Start the bot
    /summarize - Summarize a web url
    /backup - Backup a web url
    /redis - Connect to Redis
    /closeredis - Close Redis connection
    /remtoken - Remove a token
    /addtoken - Add a token
    /remkey - Remove a key
    /addkey - Add a key
    """
    update.message.reply_text(help_text)


async def log_update(update: Update, context: CallbackContext) -> None:
    logger.debug(update)


async def error_handler(update: object, context: CallbackContext):
    # 获取异常对象
    exception = context.error

    # 在控制台中打印错误信息
    logger.error(f"An error occurred: {exception}")
    traceback_str = traceback.format_exc()
    logger.error(traceback_str)

    # 可以通知用户有错误发生
    msg = f"{error_title}{exception}\n{traceback_str}"
    await context.bot.send_message(chat_id=DEVELOPER_CHAT_ID, text=msg, parse_mode=ParseMode.MARKDOWN)
