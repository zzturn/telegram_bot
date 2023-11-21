from telegram import Update, InlineKeyboardButton, ForceReply, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import CallbackContext
from telegram.helpers import escape_markdown

from db.redis_config import redis_conn
from handlers.constants import *
from handlers.constants import DEVELOPER_CHAT_ID, operation_title, REDIS_ALL_OPENAI_KEY, ADD_TOKEN, REMOVE_TOKEN, \
    SET_CACHE, REMOVE_CACHE, HACK_TOKEN
from logger.logger_config import setup_logger
from openkey.openai_key import OpenaiKey, validate_openai_key, validate_openai_key_with_res

logger = setup_logger(__name__)

async def remove_a_openai_token(update: Update, context: CallbackContext) -> None:
    key = context.args[0]
    res = redis_conn.srem(REDIS_ALL_OPENAI_KEY, key)
    data = f"{operation_title}Remove token {escape_markdown(key, 2)}\nres:\n{escape_markdown(str(res) if res else 'No Message', 2)}"
    await update.message.reply_text(data, parse_mode=ParseMode.MARKDOWN_V2)


async def add_a_openai_token(update: Update, context: CallbackContext) -> None:
    key = context.args[0]
    res = redis_conn.sadd(REDIS_ALL_OPENAI_KEY, key)
    data = f"{operation_title}Add token {escape_markdown(key, 2)}\nres:\n{escape_markdown(str(res) if res else 'No Message', 2)}"
    await update.message.reply_text(data, parse_mode=ParseMode.MARKDOWN_V2)


async def remove_a_cache(update: Update, context: CallbackContext) -> None:
    key = context.args[0]
    res = redis_conn.delete(key)
    data = f"{operation_title}Remove cache {escape_markdown(key, 2)}\nres: {escape_markdown(str(res) if res else 'No Message', 2)}"
    await update.message.reply_text(data, parse_mode=ParseMode.MARKDOWN_V2)


async def set_a_cache(update: Update, context: CallbackContext) -> None:
    key = context.args[0]
    expire = context.args[1]
    value = context.args[2]
    data = redis_conn.setex(key, value, expire)
    data = f"{operation_title}Set cache {escape_markdown(key, 2)} with expire {escape_markdown(expire, 2)} and value {escape_markdown(value, 2)}\nres: {escape_markdown(str(res) if data else 'No Message', 2)}"
    await update.message.reply_text(data, parse_mode=ParseMode.MARKDOWN_V2)


async def openKey_addToken(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("⏪️Back", callback_data=CALLBACK_OPENKEY)]
    ]
    message = await context.bot.send_message(chat_id=update.effective_chat.id,
                                             text='Please reply to this message with the token you want to add:\neg: sk-123',
                                             reply_markup=ForceReply(selective=True))
    context.user_data['message_id'] = message.message_id
    context.user_data['action'] = ADD_TOKEN


async def openKey_removeToken(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("⏪️Back", callback_data=CALLBACK_OPENKEY)]
    ]
    message = await context.bot.send_message(chat_id=update.effective_chat.id,
                                             text='Please reply to this message with the token you want to remove:\neg: sk-123',
                                             reply_markup=ForceReply(selective=True))
    context.user_data['message_id'] = message.message_id
    context.user_data['action'] = REMOVE_TOKEN


async def openKey_setCache(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("⏪️Back", callback_data=CALLBACK_OPENKEY)]
    ]
    message = await context.bot.send_message(chat_id=update.effective_chat.id,
                                             text='Please reply to this message with the key, value and expire you want to set:\neg: key 10 value',
                                             reply_markup=ForceReply(selective=True))
    context.user_data['message_id'] = message.message_id
    context.user_data['action'] = SET_CACHE


async def openKey_removeCache(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("⏪️Back", callback_data=CALLBACK_OPENKEY)]
    ]
    message = await context.bot.send_message(chat_id=update.effective_chat.id,
                                             text='Please reply to this message with the key you want to remove:\neg: key1',
                                             reply_markup=ForceReply(selective=True))
    context.user_data['message_id'] = message.message_id
    context.user_data['action'] = REMOVE_CACHE


async def openKey_random(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [InlineKeyboardButton("⏪️Back", callback_data=CALLBACK_OPENKEY)]
    ]
    data = operation_title
    res = redis_conn.srandmember(REDIS_ALL_OPENAI_KEY)
    if data is None:
        data += 'No token found\\!'
    else:
        data += escape_markdown(res, 2)
    await update.callback_query.edit_message_text(data, reply_markup=InlineKeyboardMarkup(keyboard),
                                                  parse_mode=ParseMode.MARKDOWN_V2)


async def openKey_listAllTokens(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("⏪️Back", callback_data=CALLBACK_OPENKEY)]
    ]
    tokens_set = redis_conn.smembers(REDIS_ALL_OPENAI_KEY)
    tokens = list(tokens_set)
    await update.callback_query.edit_message_text(f'Totally {len(tokens)}, random 5 keys:\n{tokens[:5]}',
                                                  reply_markup=InlineKeyboardMarkup(keyboard))


async def openKey_listAllKeys(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("⏪️Back", callback_data=CALLBACK_OPENKEY)]
    ]
    keys_set = redis_conn.keys()
    tokens = list(keys_set)
    tokens_str = '\n'.join(tokens)
    await update.callback_query.edit_message_text(f'Totally {len(tokens)}:\n{tokens_str}',
                                                  reply_markup=InlineKeyboardMarkup(keyboard))


async def openKey_hackToken(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("⏪️Back", callback_data=CALLBACK_OPENKEY)]
    ]
    message = await context.bot.send_message(chat_id=update.effective_chat.id,
                                             text='Please reply to this message with the email you want to hack:\neg: abc@gmail.com',
                                             reply_markup=ForceReply(selective=True))
    context.user_data['message_id'] = message.message_id
    context.user_data['action'] = HACK_TOKEN


async def openKey(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("📜List Tokens", callback_data=CALLBACK_OPENKEY_LISTTOKENS),
         InlineKeyboardButton("🔑Get a Token", callback_data=CALLBACK_OPENKEY_RANDOM)],
        [InlineKeyboardButton("📋List Keys", callback_data=CALLBACK_OPENKEY_LISTKEYS),
         InlineKeyboardButton("🔨Hack Token", callback_data=CALLBACK_OPENKEY_HACKTOKEN)],
        [InlineKeyboardButton("➕Add One", callback_data=CALLBACK_OPENKEY_ADDTOKEN),
         InlineKeyboardButton("➖Remove One", callback_data=CALLBACK_OPENKEY_REMOVETOKEN)],
        [InlineKeyboardButton("📥Set Cache", callback_data=CALLBACK_OPENKEY_SETCACHE),
         InlineKeyboardButton("📤Remove Cache", callback_data=CALLBACK_OPENKEY_REMOVECACHE)],
        [InlineKeyboardButton("⏪️Back", callback_data=CALLBACK_START)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(text='Okay, choose one:',
                                                  reply_markup=reply_markup)

async def hack_openkey(update: Update, context: CallbackContext):
    openai_key = OpenaiKey()
    try:
        tokens = openai_key.hack_openai_token_via_plus_gmail(1)
        msg = f'\nNew tokens: {tokens}'
    except Exception as e:
        logger.error(e)
        msg = f'hack_openkey error! \nError: {e}'
    msg = f'{operation_title}{escape_markdown(msg, 2)}'
    await update.message.reply_text(text=msg, parse_mode=ParseMode.MARKDOWN_V2)


async def validate_openkey(update: Update, context: CallbackContext):
    token = context.args[0]
    response = validate_openai_key_with_res(token)
    res = response.text
    msg = f'{operation_title}{escape_markdown(res if res else "No response", 2)}'
    await update.message.reply_text(text=msg, parse_mode=ParseMode.MARKDOWN_V2)


async def handle_callback_input(update: Update, context: CallbackContext):
    if update.message.reply_to_message and update.message.reply_to_message.message_id == context.user_data.get(
            'message_id'):
        inputs = update.message.text.split()
        action = context.user_data.get('action')
        if action == ADD_TOKEN:
            if len(inputs) != 1:
                await update.message.reply_text('Please reply with right format.')
                return
            res = redis_conn.sadd(REDIS_ALL_OPENAI_KEY, inputs[0])
            await update.message.reply_text(f'You add token: {inputs[0]}, res: {res}')
            context.user_data['handled'] = True
        elif action == REMOVE_TOKEN:
            if len(inputs) != 1:
                await update.message.reply_text('Please reply with right format.')
                return
            res = redis_conn.srem(REDIS_ALL_OPENAI_KEY, inputs[0])
            await update.message.reply_text(f'You remove token: {inputs[0]}, res: {res}')
            context.user_data['handled'] = True
        elif action == SET_CACHE:
            if len(inputs) != 3:
                await update.message.reply_text('Please reply with right format.')
                return
            res = redis_conn.setex(inputs[0], inputs[2], inputs[1])
            await update.message.reply_text(
                f'You set cache: {inputs[0]}, value: {inputs[2]}, expire in {inputs[1]}, res: {res}')
            context.user_data['handled'] = True
        elif action == REMOVE_CACHE:
            if len(inputs) != 1:
                await update.message.reply_text('Please reply with right format.')
                return
            res = redis_conn.delete(inputs[0])
            await update.message.reply_text(f'You remove cache: {inputs[0]}, res: {res}')
            context.user_data['handled'] = True
        elif action == HACK_TOKEN:
            if len(inputs) != 1 and not (inputs[0].endswith('@gmail.com') or inputs[0].endswith('@icloud.com')):
                await update.message.reply_text('Please reply with right format.')
                return
            openai_key = OpenaiKey()
            res = openai_key.read_code_and_request_key(inputs[0])
            if isinstance(res, list):
                res = '\n'.join(res)
            await update.message.reply_text(f'Get token from {inputs[0]}, res:\n{res}')
            context.user_data['handled'] = True
    elif update.message.text == 'ping':
        await update.message.reply_text('pong')
