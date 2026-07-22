import pytest_asyncio


@pytest_asyncio.fixture(scope="session", autouse=True)
def check_env_file():
    from source.core.config import settings
    print("checking env. MODE =", settings.MODE)
    assert settings.MODE == "TEST"