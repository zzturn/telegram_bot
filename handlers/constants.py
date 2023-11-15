from config.config import configInstance

DEVELOPER_CHAT_ID = configInstance.developer_chat_id

status_title = '🌐🌐*\[Status Notify\]*🌐🌐\n\n'
operation_title = '🟡🟡*\[Operation Notify\]*🟡🟡\n\n'
error_title = '‼️‼️*\[Error Notify\]*‼️‼️\n\n'
cron_title = '⏱️⏱️*\[Cron Notify\]*⏱️⏱️\n\n'

REDIS_ALL_OPENAI_KEY = 'all_openai_key'

REDIS_MODE, WAIT_SINGLE_INPUT = range(2)
ADD_TOKEN, REMOVE_TOKEN, SET_CACHE, REMOVE_CACHE, HACK_TOKEN = range(5)

CALLBACK_START = 'start'
CALLBACK_OPENKEY = 'openKey'
CALLBACK_START_REDIS = 'start_redis'
CALLBACK_OPENKEY_LISTTOKENS = 'openKey_listTokens'
CALLBACK_OPENKEY_LISTKEYS = 'openKey_listKeys'
CALLBACK_OPENKEY_HACKTOKEN = 'openKey_hackToken'
CALLBACK_OPENKEY_RANDOM = 'openKey_random'
CALLBACK_OPENKEY_ADDTOKEN = 'openKey_addToken'
CALLBACK_OPENKEY_REMOVETOKEN = 'openKey_removeToken'
CALLBACK_OPENKEY_SETCACHE = 'openKey_setCache'
CALLBACK_OPENKEY_REMOVECACHE = 'openKey_removeCache'


COMMAND_START = 'start'
COMMAND_REDIS = 'redis'
COMMAND_REMTOKEN = 'remtoken'
COMMAND_ADDTOKEN = 'addtoken'
COMMAND_REMKEY = 'remkey'
COMMAND_ADDKEY = 'addkey'
COMMAND_CLOSEREDIS = 'closeredis'
COMMAND_SUMMARIZE = 'summarize'
COMMAND_BACKUP = 'backup'
COMMAND_HACK = 'hack'
