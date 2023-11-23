import io
import time

import requests
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CallbackContext
from telegram.helpers import escape_markdown

from config import config
from config.config import configInstance
from db.redis_util import redis_conn
from handlers.constants import *
from openkey.openai_key import validate_openai_key, OpenaiKey
from logger.logger_config import setup_logger

logger = setup_logger('cron')

# cron
custom_scheduler = AsyncIOScheduler()


async def cron_validate_openkey(application):
    logger.info('Cron job validate open key start. ')
    try:
        expire_tokens = list_keys_from_cf(configInstance.cf_account_id,
                                          configInstance.cf_namespace_id, configInstance.cf_api_key, 'sk')
        logger.info(f'Expire tokens: {expire_tokens}')
    except Exception as e:
        logger.error('List expire tokens failed:', e)
        expire_tokens = []
    count = 0
    # 随机获取一个 OpenKey 进行验证
    token = None
    while True:
        # 防止死循环，基本不可能到 20 次
        if count > 20:
            break
        count += 1
        token = redis_conn.get_random_token()
        if token not in expire_tokens:
            break

    if token is not None:
        try:
            validate_res = validate_openai_key(token)
            if not validate_res:
                expire_tokens.append(token)
        except Exception as e:
            logger.error(f'Validate token {token} failed: {e}')
    if len(expire_tokens) > 0:
        expire_str = '\n'.join(expire_tokens)
        msg = f'{cron_title}*{escape_markdown(expire_str, 2)}*\nis invalid and removed'
        redis_conn.remove_token(*expire_tokens)
        delete_keys_from_cf(expire_tokens, configInstance.cf_account_id,
                            configInstance.cf_namespace_id, configInstance.cf_api_key)
        await application.bot.send_message(chat_id=DEVELOPER_CHAT_ID, text=msg, parse_mode=ParseMode.MARKDOWN_V2)
        logger.info(f'OpenKey: {expire_tokens} is invalid and removed.')


async def cron_request_openkey(application):
    logger.info('Cron job request open key start. ')
    openai_key = OpenaiKey()
    try:
        tokens = openai_key.hack_openai_token(1)
        msg = f'\nRequest new tokens: {tokens}'
    except Exception as e:
        logger.error(e)
        msg = f'Cron job [request_openkey] error! \nError: {e}'
    msg = f'{cron_title}{escape_markdown(msg, 2)}'
    await application.bot.send_message(chat_id=DEVELOPER_CHAT_ID, text=msg, parse_mode=ParseMode.MARKDOWN_V2)
    logger.info('Cron job request open key end. ')


async def cron_hack_openkey(application):
    logger.info('Cron job hack open key start. ')
    openai_key = OpenaiKey()
    try:
        tokens = openai_key.hack_openai_token_via_plus_gmail(1)
        msg = f'\nHack new tokens: {tokens}'
    except Exception as e:
        logger.error(e)
        msg = f'Cron job [hack_openkey] error! \nError: {e}'
    msg = f'{cron_title}{escape_markdown(msg, 2)}'
    await application.bot.send_message(chat_id=DEVELOPER_CHAT_ID, text=msg, parse_mode=ParseMode.MARKDOWN_V2)
    logger.info('Cron job hack open key end. ')


async def cron_sync_kv(application):
    logger.info('Cron job sync kv start. ')
    now = time.time()
    start = now - TOKEN_EXPIRE
    end = now - TOKEN_REQ_INTERVAL * 2
    tokens = redis_conn.get_all_tokens(start, end)
    logger.info(f'Size of {REDIS_ALL_OPENAI_KEY} from {start} to {end}: {len(tokens)}')
    if not tokens:
        msg = f'No OpenKey in {REDIS_ALL_OPENAI_KEY}, res: {tokens}'
        await application.bot.send_message(chat_id=DEVELOPER_CHAT_ID,
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
        await application.bot.send_message(chat_id=DEVELOPER_CHAT_ID,
                                           text=text,
                                           parse_mode=ParseMode.MARKDOWN_V2)
    logger.info('Cron job sync kv end. ')


async def cron_update(update: Update, context: CallbackContext):
    options = [CRON_REQUEST_OPENKEY, CRON_HACK_OPENKEY, CRON_VALIDATE_OPENKEY, CRON_SYNC_KV]
    if len(context.args) != 6 or context.args[0] not in options:
        msg = f"💡Please input 6 parameters: \n\neg: {CRON_REQUEST_OPENKEY} 30 * * * *\n\nThe first parameter has following options: \n{CRON_REQUEST_OPENKEY}\n{CRON_HACK_OPENKEY}\n{CRON_VALIDATE_OPENKEY}\n{CRON_SYNC_KV}"
        await update.message.reply_text(msg)
        token = context.args[0]
    cron_expression = ' '.join(context.args[1:])
    try:
        job = update_cron(context.args[0], cron_expression)
        msg = f'Update cron job {context.args[0]} to {cron_expression} success!\nNext run time: {job.next_run_time}'
    except Exception as e:
        msg = f'Update cron job {context.args[0]} to {cron_expression} failed! Error: {e}'
    msg = f'{cron_title}{escape_markdown(msg, 2)}'
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)


async def cron_info(update: Update, context: CallbackContext):
    msg = get_cron_info()
    msg = f'{cron_title}{escape_markdown(msg, 2)}'
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)


def get_cron_info():
    jobs = custom_scheduler.get_jobs()
    cron_info_str = '\n\n'.join(
        [f'{job.id}:\n{get_cron_str(job.trigger)}\n{job.next_run_time.strftime("%Y-%m-%d %H:%M:%S")}' for job in jobs])
    return cron_info_str


def get_cron_str(trigger):
    if isinstance(trigger, CronTrigger):
        return f'{trigger.fields[6]} {trigger.fields[5]} {trigger.fields[2]} {trigger.fields[1]} {trigger.fields[4]}'
    else:
        return 'None'


def update_cron(job_id, cron_expression):
    job = custom_scheduler.get_job(job_id)
    job.reschedule(CronTrigger.from_crontab(cron_expression))
    logger.info(f'Update cron job {job_id} to {cron_expression}, next run time: {job.next_run_time}')
    return job


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


def list_keys_from_cf(account_id, namespace_id, cf_api_key, prefix=''):
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/storage/kv/namespaces/{namespace_id}/keys?prefix={prefix}"
    headers = {
        'Authorization': f'Bearer {cf_api_key}',
    }
    response = requests.get(url, headers=headers)
    logger.info(f"List keys from Cloudflare KV with parameter: '{prefix}' res: {response.text}")
    response.raise_for_status()
    res = response.json()
    if res['success']:
        return [x['name'] for x in res['result']]
    else:
        raise Exception(f"List expire key from Cloudflare KV failed")


def delete_keys_from_cf(keys, account_id, namespace_id, cf_api_key):
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/storage/kv/namespaces/{namespace_id}/bulk"
    headers = {
        'Authorization': f'Bearer {cf_api_key}',
    }
    response = requests.delete(url, headers=headers, json=keys)
    logger.info(f"Delete keys from Cloudflare KV: {keys}, res: {response.text}")


def test_list_keys_from_cf():
    keys = list_keys_from_cf(configInstance.cf_account_id,
                             configInstance.cf_namespace_id,
                             configInstance.cf_api_key, 'sk')
    logger.info(f"List keys from Cloudflare KV: {keys}")


def test_cron_info():
    custom_scheduler.add_job(cron_request_openkey, CronTrigger.from_crontab("0 0 * * *"), args=['j'],
                             id=CRON_REQUEST_OPENKEY)
    custom_scheduler.add_job(cron_request_openkey, CronTrigger.from_crontab("10 10 * * *"), args=['j'],
                             id='abc')
    custom_scheduler.start()
    s = get_cron_info()
    print(s)


if __name__ == '__main__':
    test_cron_info()
    test_list_keys_from_cf()
    tokens = redis_conn.get_all_tokens()
    logger.info(f'{REDIS_ALL_OPENAI_KEY}: {tokens}')
    # 使用列表推导解码每个字节字符串
    normal_strings = [byte_string.decode('utf-8') if isinstance(byte_string, bytes) else byte_string for byte_string in
                      tokens]

    # 将列表转为用逗号分隔的字符串
    concat = ','.join(normal_strings)
    put_kv_to_cf(REDIS_ALL_OPENAI_KEY, concat, cf_api_key=configInstance.cf_api_key,
                 account_id=configInstance.cf_account_id, namespace_id=configInstance.cf_namespace_id)
