import random
import string

from fastapi import Depends, HTTPException, Request, Response, status
from fastapi_limiter.depends import RateLimiter


# обработчик ограничителя запросов
async def custom_rate_limit_callback(request: Request, response: Response, pexpire: int) -> None:
    """pexpire — это оставшееся время блокировки в миллисекундах"""
    # Переводим миллисекунды в секунды для заголовка Retry-After
    expire_seconds = max(1, pexpire // 1000) if pexpire else 60

    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={
            "error": "Too Many Requests",
            "message": f"Лимит запросов превышен. Попробуйте через {expire_seconds} сек.",
            "retry_after": expire_seconds,
        },
        headers={"Retry-After": str(expire_seconds)},
    )


def get_random_string(length: int = 10) -> str:
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))





if __name__ == "__main__":
    print("utils file")
    

    
    
    