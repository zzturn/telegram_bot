from telegram import Update, InlineKeyboardButton, ForceReply, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import CallbackContext

from db.redis_config import redis_conn
from handlers.constants import ADD_TOKEN, WAIT_SINGLE_INPUT, REMOVE_TOKEN, SET_CACHE, \
    REMOVE_CACHE, CALLBACK_OPENKEY_LISTALL, CALLBACK_OPENKEY_RANDOM, CALLBACK_OPENKEY_ADDTOKEN, \
    CALLBACK_OPENKEY_REMOVETOKEN, CALLBACK_OPENKEY_SETCACHE, CALLBACK_OPENKEY_REMOVECACHE, CALLBACK_OPENKEY, \
    CALLBACK_START
from handlers.constants import DEVELOPER_CHAT_ID, operation_title, REDIS_ALL_OPENAI_KEY


async def remove_a_openai_token(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    if user_id != DEVELOPER_CHAT_ID:
        return
    key = context.args[0]
    data = f"{operation_title}Remove token {key}\nres: {redis_conn.srem(REDIS_ALL_OPENAI_KEY, key)}"
    await update.message.reply_text(data, parse_mode=ParseMode.MARKDOWN)


async def add_a_openai_token(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    if user_id != DEVELOPER_CHAT_ID:
        return
    key = context.args[0]
    data = f"{operation_title}Add token {key}\nres: {redis_conn.sadd(REDIS_ALL_OPENAI_KEY, key)}"
    await update.message.reply_text(data, parse_mode=ParseMode.MARKDOWN)


async def remove_a_cache(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    if user_id != DEVELOPER_CHAT_ID:
        return
    key = context.args[0]
    data = f"{operation_title}Remove cache {key}\nres: {redis_conn.delete(key)}"
    await update.message.reply_text(data, parse_mode=ParseMode.MARKDOWN)


async def set_a_cache(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    if user_id != DEVELOPER_CHAT_ID:
        return
    key = context.args[0]
    expire = context.args[1]
    value = context.args[2]
    data = redis_conn.setex(key, value, expire)
    data = f"{operation_title}Set cache {key} with expire {expire} and value {value}\nres: {data}"
    await update.message.reply_text(data, parse_mode=ParseMode.MARKDOWN)


async def openKey_addToken(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("⏪️Back", callback_data=CALLBACK_OPENKEY)]
    ]
    message = await context.bot.send_message(chat_id=update.effective_chat.id,
                                             text='Please reply to this message with the token you want to add:\neg: sk-123',
                                             reply_markup=ForceReply(selective=True))
    context.user_data['message_id'] = message.message_id
    context.user_data['action'] = ADD_TOKEN
    return WAIT_SINGLE_INPUT


async def openKey_removeToken(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("⏪️Back", callback_data=CALLBACK_OPENKEY)]
    ]
    message = await context.bot.send_message(chat_id=update.effective_chat.id,
                                             text='Please reply to this message with the token you want to remove:\neg: sk-123',
                                             reply_markup=ForceReply(selective=True))
    context.user_data['message_id'] = message.message_id
    context.user_data['action'] = REMOVE_TOKEN
    return WAIT_SINGLE_INPUT


async def openKey_setCache(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("⏪️Back", callback_data=CALLBACK_OPENKEY)]
    ]
    message = await context.bot.send_message(chat_id=update.effective_chat.id,
                                             text='Please reply to this message with the key, value and expire you want to set:\neg: key 10 value',
                                             reply_markup=ForceReply(selective=True))
    context.user_data['message_id'] = message.message_id
    context.user_data['action'] = SET_CACHE
    return WAIT_SINGLE_INPUT


async def openKey_removeCache(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("⏪️Back", callback_data=CALLBACK_OPENKEY)]
    ]
    message = await context.bot.send_message(chat_id=update.effective_chat.id,
                                             text='Please reply to this message with the key you want to remove:\neg: key1',
                                             reply_markup=ForceReply(selective=True))
    context.user_data['message_id'] = message.message_id
    context.user_data['action'] = REMOVE_CACHE
    return WAIT_SINGLE_INPUT


async def openKey_random(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [InlineKeyboardButton("⏪️Back", callback_data=CALLBACK_OPENKEY)]
    ]
    data = operation_title
    res = redis_conn.srandmember(REDIS_ALL_OPENAI_KEY)
    if data is None:
        data += 'No token found!'
    else:
        data += res
    await update.callback_query.edit_message_text(data, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)


async def openKey_listAll(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("⏪️Back", callback_data=CALLBACK_OPENKEY)]
    ]
    tokens_set = redis_conn.smembers(REDIS_ALL_OPENAI_KEY)
    tokens = list(tokens_set)
    await update.callback_query.edit_message_text(f'Totally {len(tokens)}, random 5 keys:\n {tokens[:5]}',
                                                  reply_markup=InlineKeyboardMarkup(keyboard))


async def openKey(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("📜List All", callback_data=CALLBACK_OPENKEY_LISTALL),
         InlineKeyboardButton("🔑Get One", callback_data=CALLBACK_OPENKEY_RANDOM)],
        [InlineKeyboardButton("➕Add One", callback_data=CALLBACK_OPENKEY_ADDTOKEN),
         InlineKeyboardButton("➖Remove One", callback_data=CALLBACK_OPENKEY_REMOVETOKEN)],
        [InlineKeyboardButton("📥Set Cache", callback_data=CALLBACK_OPENKEY_SETCACHE),
         InlineKeyboardButton("📤Remove Cache", callback_data=CALLBACK_OPENKEY_REMOVECACHE)],
        [InlineKeyboardButton("⏪️Back", callback_data=CALLBACK_START)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(text='Okay, choose one:',
                                                  reply_markup=reply_markup)
