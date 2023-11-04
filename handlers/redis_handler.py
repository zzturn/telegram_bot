from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CallbackContext, ConversationHandler, ContextTypes

from db.redis_config import redis_conn
from handlers.constants import REDIS_MODE, ADD_TOKEN, WAIT_SINGLE_INPUT, REMOVE_TOKEN, SET_CACHE, REMOVE_CACHE
from handlers.constants import status_title, operation_title, REDIS_ALL_OPENAI_KEY
from logger.logger_config import setup_logger

logger = setup_logger('redis')


async def start_redis(update: Update, context: CallbackContext):
    msg = status_title + 'You are now in Redis mode. Use /closeredis to exit.'
    if update.callback_query:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=msg, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
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
    msg = status_title + 'Redis mode timed out.'
    job = context.job
    await context.bot.send_message(job.chat_id, text=msg, parse_mode=ParseMode.MARKDOWN)
    await end_redis_mode(None, context)


async def end_redis_mode(update: Update, context: CallbackContext) -> int:
    if update is not None:
        chat_id = update.effective_chat.id
    else:
        chat_id = context.job.chat_id
    job_removed = remove_job_if_exists(str(chat_id), context)
    logger.info(f'Redis mode timer removed: {job_removed}')
    msg = status_title + 'You have exited Redis mode.'
    await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode=ParseMode.MARKDOWN)
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
            msg = operation_title + f"[{' '.join(command_line)}]\nCommand executed with no result."
        else:
            msg = operation_title + f"[{' '.join(command_line)}]\nCommand executed with result: {result}"
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
        reset_timer(update, context)
    except Exception as e:
        msg = operation_title + f"Command execute with error: {e}"
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
    return REDIS_MODE


async def handle_redis_operation_input(update: Update, context: CallbackContext):
    if update.message.reply_to_message and update.message.reply_to_message.message_id == context.user_data.get(
            'message_id'):
        inputs = update.message.text.split()
        action = context.user_data.get('action')
        if action == ADD_TOKEN:
            if len(inputs) != 1:
                await update.message.reply_text('Please reply with right format.')
                return WAIT_SINGLE_INPUT
            res = redis_conn.sadd(REDIS_ALL_OPENAI_KEY, inputs[0])
            await update.message.reply_text(f'You add token: {inputs[0]}, res: {res}')
        elif action == REMOVE_TOKEN:
            if len(inputs) != 1:
                await update.message.reply_text('Please reply with right format.')
                return WAIT_SINGLE_INPUT
            res = redis_conn.srem(REDIS_ALL_OPENAI_KEY, inputs[0])
            await update.message.reply_text(f'You remove token: {inputs[0]}, res: {res}')
        elif action == SET_CACHE:
            if len(inputs) != 3:
                await update.message.reply_text('Please reply with right format.')
                return WAIT_SINGLE_INPUT
            res = redis_conn.setex(inputs[0], inputs[2], inputs[1])
            await update.message.reply_text(
                f'You set cache: {inputs[0]}, value: {inputs[2]}, expire in {inputs[1]}, res: {res}')
        elif action == REMOVE_CACHE:
            if len(inputs) != 1:
                await update.message.reply_text('Please reply with right format.')
                return WAIT_SINGLE_INPUT
            res = redis_conn.delete(inputs[0])
            await update.message.reply_text(f'You remove cache: {inputs[0]}, res: {res}')
        return ConversationHandler.END
    else:
        await update.message.reply_text('Please reply to the correct message.')
        return WAIT_SINGLE_INPUT
