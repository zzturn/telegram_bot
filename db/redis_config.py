import redis

from config.config import configInstance


class RedisClient:
    def __init__(self, host=configInstance.redis_host, port=configInstance.redis_port, db=0):
        self.client = redis.StrictRedis(host=host, port=port, db=db)

    def setex(self, key, value, time=5 * 60):
        self.client.setex(key, time, value)

    def get(self, key):
        return str(self.client.get(key), 'utf-8')

    def delete(self, key):
        return self.client.delete(key)

    def keys(self, pattern='*'):
        return self.client.keys(pattern)

    def sadd(self, key, value):
        return self.client.sadd(key, value)

    def srem(self, key, value):
        return self.client.srem(key, value)

    def smembers(self, key):
        return self.client.smembers(key)

    def srandmember(self, key):
        return str(self.client.srandmember(key), 'utf-8')

    def exists(self, key):
        return self.client.exists(key)


redis_conn = RedisClient()


if __name__ == "__main__":
    # 测试模块
    redis_instance = RedisClient()
    redis_instance.setex('example_key', 'example_value')
    result = redis_instance.get('example_key')
    print(f'Get result: {result}')
