import pytest_asyncio


@pytest_asyncio.fixture(scope="session", autouse=True)
def check_env_file():
    
    from source.core.config import settings
    assert settings.MODE == "TEST"
    
    # from source.core.logger import default_logger
    # import logging
    # # логи ставим на INFO
    # default_logger.setLevel(logging._nameToLevel["INFO"])