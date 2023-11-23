import datetime
import random
import time

import redis

from config.config import configInstance
from handlers.constants import REDIS_ALL_OPENAI_KEY, TOKEN_EXPIRE


class RedisUtil:
    def __init__(self, host=configInstance.redis_host, port=configInstance.redis_port, db=0):
        self.client = redis.StrictRedis(host=host, port=port, db=db, decode_responses=True)

    def setex(self, key, value, time=5 * 60):
        self.client.setex(key, time, value)

    def get(self, key):
        return self.client.get(key)

    def delete(self, *key):
        return self.client.delete(*key)

    def keys(self, pattern='*'):
        return self.client.keys(pattern)

    def sadd(self, key, value):
        return self.client.sadd(key, value)

    def srem(self, key, *values):
        return self.client.srem(key, *values)

    def smembers(self, key):
        return self.client.smembers(key)

    def srandmember(self, key):
        return self.client.srandmember(key)

    def exists(self, key):
        return self.client.exists(key)


    # openkey
    def add_token(self, token, value=None):
        now = time.time()
        expire = TOKEN_EXPIRE
        if value is not None:
            expire -= int(now - value)
        else:
            value = now
        self.setex(token, value, expire)
        return self.client.zadd(REDIS_ALL_OPENAI_KEY, {token: int(value)})

    def remove_token(self, *token):
        self.delete(*token)
        return self.client.zrem(REDIS_ALL_OPENAI_KEY, *token)

    def get_random_token(self):
        tokens = self.get_all_tokens()
        return random.choice(tokens)

    def get_all_tokens(self, start=None, end=None):
        if end is None:
            end = '+inf'
        else:
            end = int(end)
        if start is None:
            start = time.time() - TOKEN_EXPIRE
        else:
            start = int(start)
        return self.client.zrangebyscore(REDIS_ALL_OPENAI_KEY, start, end)

    def is_member(self, token):
        return self.client.zscore(REDIS_ALL_OPENAI_KEY, token)


redis_conn = RedisUtil()


if __name__ == "__main__":
    # 测试模块
    redis_instance = RedisUtil('192.168.1.3', 6379)
    ts = datetime.datetime.now().timestamp()
    print(redis_instance.add_token('test'))
    print(redis_instance.add_token('test2'))
    print(redis_instance.get_all_tokens(start=ts))
    print(redis_instance.get_random_token())
    print(redis_instance.remove_token('test'))
    print(redis_instance.get_all_tokens(start=ts))
    print(redis_instance.get_random_token())
    ts = redis_instance.get_all_tokens()
    print(ts)
