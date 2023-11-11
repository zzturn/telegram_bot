import requests
from telegram.constants import ParseMode
from telegram.ext import CallbackContext
from telegram.helpers import escape_markdown

from config import config
from config.config import configInstance
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
        msg = f'{cron_title}*{escape_markdown(token, 2)}* is invalid and removed.'
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
        msg = f'Cron job [request_openkey] error! \nError: {e}'
    msg = f'{cron_title}{escape_markdown(msg, 2)}'
    await context.bot.send_message(chat_id=DEVELOPER_CHAT_ID, text=msg, parse_mode=ParseMode.MARKDOWN_V2)
    logger.info('Cron job request open key end. ')


async def cron_sync_kv(context: CallbackContext):
    logger.info('Cron job sync kv start. ')
    tokens = redis_conn.smembers(REDIS_ALL_OPENAI_KEY)
    logger.info(f'{REDIS_ALL_OPENAI_KEY}: {tokens}')
    if not tokens:
        msg = f'No OpenKey in {REDIS_ALL_OPENAI_KEY}, res: {tokens}'
        await context.bot.send_message(chat_id=DEVELOPER_CHAT_ID,
                                       text=escape_markdown(msg, 2),
                                       parse_mode=ParseMode.MARKDOWN_V2)
        return
    # 使用列表推导解码每个字节字符串
    normal_strings = [byte_string.decode('utf-8') if isinstance(byte_string, bytes) else byte_string for byte_string in
                      tokens]

    # 将列表转为用逗号分隔的字符串
    concat = ','.join(normal_strings)
    try:
        put_kv_to_cf(REDIS_ALL_OPENAI_KEY, concat,
                     cf_api_key=configInstance.cf_api_key,
                     account_id=configInstance.cf_account_id,
                     namespace_id=configInstance.cf_namespace_id)
    except Exception as e:
        msg = f'Cron job [sync_kv] error! \nError: {e}'
        text = f'{cron_title}{escape_markdown(msg, 2)}'
        await context.bot.send_message(chat_id=DEVELOPER_CHAT_ID,
                                       text=text,
                                       parse_mode=ParseMode.MARKDOWN_V2)
    logger.info('Cron job sync kv end. ')


def put_kv_to_cf(key, value, account_id, namespace_id, cf_api_key):
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/storage/kv/namespaces/{namespace_id}/values/{key}"

    headers = {
        'Authorization': f'Bearer {cf_api_key}',
    }

    data = {
        'metadata': '{}',
        'value': value
    }

    response = requests.put(url, headers=headers, files=data)
    logger.info(f"Put {key} to Cloudflare KV: {response.text}")
    if response.status_code == 200 and response.json()['success']:
        return True
    else:
        raise Exception(f"Put {key} to Cloudflare KV failed: {response.text}")


if __name__ == '__main__':
    tokens = redis_conn.smembers(REDIS_ALL_OPENAI_KEY)
    logger.info(f'{REDIS_ALL_OPENAI_KEY}: {tokens}')
    # 使用列表推导解码每个字节字符串
    normal_strings = [byte_string.decode('utf-8') if isinstance(byte_string, bytes) else byte_string for byte_string in
                      tokens]

    # 将列表转为用逗号分隔的字符串
    concat = ','.join(normal_strings)
    put_kv_to_cf(REDIS_ALL_OPENAI_KEY, concat, cf_api_key=configInstance.cf_api_key,
                 account_id=configInstance.cf_account_id, namespace_id=configInstance.cf_namespace_id)
