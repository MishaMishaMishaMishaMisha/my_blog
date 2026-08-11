from redis.asyncio import Redis
import json
from source.core.config import settings
from typing import Any
from fastapi_limiter import FastAPILimiter


class RedisBackend:

    def __init__(self):
        self.redis = Redis.from_url(settings.redis.url, decode_responses=True)
        
    def pipeline(self, transaction: bool = True):
        return self.redis.pipeline(transaction=transaction)

    async def set(self, 
                  key: str, 
                  value: Any, 
                  ttl_seconds: int | None = None,
                  is_value_serialize: bool = True) -> None:
        if is_value_serialize:
            value = json.dumps(value)
        await self.redis.set(key, value, ex=ttl_seconds)

    async def get(self, key: str) -> Any | None:
        value = await self.redis.get(key)
        if value is None:
            return None
        return json.loads(value)

    async def delete(self, key: str) -> None:
        await self.redis.delete(key)
    
    # hincrby hash increment by
    # в redis hash это тип данных похожий на dict in python
    # key это ключ под которым хранится весь hash
    # field_name это поле внутри hash. 
    # значение этого поля будет увеличиваться на increment_value при каждом вызове
    async def hincrby(self, key: str, field_name: str, increment_value: int) -> None:
         await self.redis.hincrby(key, field_name, increment_value)

    # вернуть все поля hash
    async def hgetall(self, key: str) -> dict:
        return await self.redis.hgetall(key)
    
    async def hset(self, key: str, mapping: dict[str, Any]) -> None:
        await self.redis.hset(key, 
                              mapping={field: json.dumps(value) for field, value in mapping.items()})
        
    async def hget(self, key: str, field: str) -> Any | None:
        value = await self.redis.hget(key, field)
        return json.loads(value) if value is not None else None

    async def expire(self, key: str, ttl_seconds: int) -> bool:
        return await self.redis.expire(key, ttl_seconds)
    
    async def renameKey(self, key: str, new_key: str) -> None:
        await self.redis.rename(key, new_key)
        
    async def get_expire_key_time(self, key: str) -> int:
        return await self.redis.ttl(key)
        
    async def close(self):
        await self.redis.aclose()
        
    async def init_rate_limiter(self):
        await FastAPILimiter.init(self.redis)
        
        
# единственный экземпляр на приложение
redis_backend = RedisBackend()


# пример кеширования одного объекта. 
# нужно указать mode="json" чтобы UUID конвертировался в строку
# dto_post = PostDTO.model_validate(db_post)
# await redis.set(key=f"post:{db_post.id}", value=dto_post.model_dump(mode="json"), ttl_seconds=600)
# dto_post = PostDTO.model_validate(await redis.get(f"post:{post_id}"))

# пример кеширования списка объектов
# posts = [PostDTO.model_validate(post).model_dump(mode="json") for post in db_posts]
# await redis.set(key="latest_posts", value=posts)
# posts_dicts = await redis.get("latest_posts")
# posts = [PostDTO.model_validate(post_dict) for post in posts_dicts]




