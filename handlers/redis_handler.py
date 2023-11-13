from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CallbackContext, ConversationHandler, ContextTypes
from telegram.helpers import escape_markdown

from db.redis_config import redis_conn
from handlers.constants import REDIS_MODE
from handlers.constants import status_title, operation_title
from logger.logger_config import setup_logger

logger = setup_logger('redis')


async def start_redis(update: Update, context: CallbackContext):
    msg = status_title + escape_markdown('You are now in Redis mode. Use /closeredis to exit.', 2)
    if update.callback_query:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=msg, parse_mode=ParseMode.MARKDOWN_V2)
    else:
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)
    reset_timer(update, context)
    logger.info('Redis mode timer started.')
    return REDIS_MODE


def reset_timer(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    job_removed = remove_job_if_exists(str(chat_id), context)
    due = 120
    chat_id = update.effective_chat.id
    context.job_queue.run_once(timeout, due, chat_id=chat_id, name=str(chat_id), data=due)
    logger.info(f'Redis mode timer reset')


async def timeout(context: CallbackContext) -> None:
    msg = status_title + escape_markdown('Redis mode timed out.', 2)
    job = context.job
    await context.bot.send_message(job.chat_id, text=msg, parse_mode=ParseMode.MARKDOWN_V2)
    await end_redis_mode(None, context)


async def end_redis_mode(update: Update, context: CallbackContext) -> int:
    if update is not None:
        chat_id = update.effective_chat.id
    else:
        chat_id = context.job.chat_id
    job_removed = remove_job_if_exists(str(chat_id), context)
    logger.info(f'Redis mode timer removed: {job_removed}')
    msg = status_title + escape_markdown('You have exited Redis mode.', 2)
    await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode=ParseMode.MARKDOWN_V2)
    return ConversationHandler.END


def remove_job_if_exists(name: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Remove job with given name. Returns whether job was removed."""
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True


async def handleRedis(update: Update, context: CallbackContext) -> int:
    logger.info('Received command: ' + update.message.text)
    try:
        command_line = update.message.text.split()
        command = command_line[0]
        args = command_line[1:]
        result = getattr(redis_conn.client, command)(*args)
        if result is None:
            msg = operation_title + escape_markdown(f"[{' '.join(command_line)}]\nCommand executed with no result.", 2)
        else:
            msg = operation_title + escape_markdown(
                f"[{' '.join(command_line)}]\nCommand executed with result: {result}", 2)
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)
        reset_timer(update, context)
    except Exception as e:
        msg = operation_title + f"Command execute with error: {escape_markdown(str(e), 2)}"
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)
    return REDIS_MODE


