from telegram.constants import ParseMode
from telegram.ext import CallbackContext
from telegram.helpers import escape_markdown

from db.redis_config import redis_conn
from handlers.constants import DEVELOPER_CHAT_ID, cron_title, REDIS_ALL_OPENAI_KEY
from openkey.openai_key import validate_openai_key, OpenaiKey
from logger.logger_config import setup_logger

logger = setup_logger('cron')


async def cron_validate_openkey(context: CallbackContext):
    token = redis_conn.srandmember(REDIS_ALL_OPENAI_KEY)
    if token is None:
        logger.info(f'No OpenKey in redis.')
        await context.bot.send_message(chat_id=DEVELOPER_CHAT_ID,
                                       text=f'{cron_title}No OpenKey in redis.',
                                       parse_mode=ParseMode.MARKDOWN_V2)
        return
    logger.info(f'Begin to validate OpenKey: {token}')
    res = validate_openai_key(token)
    if res:
        logger.info(f'OpenKey: {token} is valid.')
    else:
        msg = f'{cron_title}*{token}* is invalid and removed.'
        redis_conn.srem(REDIS_ALL_OPENAI_KEY, token)
        await context.bot.send_message(chat_id=DEVELOPER_CHAT_ID, text=msg, parse_mode=ParseMode.MARKDOWN_V2)
        logger.info(f'OpenKey: {token} is invalid and removed.')


async def cron_request_openkey(context: CallbackContext):
    logger.info('Cron job request open key start. ')
    openai_key = OpenaiKey()
    try:
        tokens = openai_key.hack_openai_token(1)
        msg = f'\nNew tokens: {tokens}'
    except Exception as e:
        logger.error(e)
        msg = f'Cron job error! \nError: {e}'
    msg = f'{cron_title}{escape_markdown(msg, 2)}'
    await context.bot.send_message(chat_id=DEVELOPER_CHAT_ID, text=msg, parse_mode=ParseMode.MARKDOWN_V2)
    logger.info('Cron job request open key end. ')
