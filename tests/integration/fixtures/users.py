import pytest
import pytest_asyncio
from source.models.user import UserModel
from source.core.types import RoleEnum
from source.core.utils import get_random_string
from source.database.db_connect import async_session_factory


@pytest.fixture
def user_json():
    return {
        "username": get_random_string(10),
        "email": f"{get_random_string(10)}@gmail.com",
        "password": get_random_string(15),
    }
    

# просто отдает UserModel
# можно создать user или admin
# использование
# user = user_factory()
# admin = user_factory(role=RoleEnum.ADMIN, username="admin")
@pytest.fixture
def user_factory():

    def factory(**kwargs):

        defaults = {
            "username": get_random_string(10),
            "email": f"{get_random_string(10)}@gmail.com",
            "password_hash": get_random_string(20),
        }

        defaults.update(kwargs)

        return UserModel(**defaults)

    return factory



# создает count пользователей и добавляет их в таблицу и возвращает список моделей
# использование
#users = await users_factory(5)
#admins = await users_factory(count=3, role=RoleEnum.ADMIN)
@pytest_asyncio.fixture
async def users_factory(db_session, user_factory):
    async def factory(count: int = 1, **kwargs):
        users = [user_factory(**kwargs) for _ in range(count)]

        db_session.add_all(users)
        await db_session.commit()

        for user in users:
            await db_session.refresh(user)

        return users

    return factory


# создает в таблице только одного пользователя и возвращает модель
# ипсользование. добавлеям как параметр в тесте и можно сразу использовать
@pytest_asyncio.fixture
async def one_user(users_factory):

    return (await users_factory())[0]



#############################################

# данные для параметризации в тестах (scope=class/module/session)

# вспомогательная функция (не фикстура)
async def create_users(count: int = 1, **kwargs) -> list[UserModel]:
    
    users = []
    for _ in range(count):
        user_model = {
            "username": get_random_string(10),
            "email": f"{get_random_string(10)}@gmail.com",
            "password_hash": get_random_string(20),
            "role": RoleEnum.USER}

        # если были переданы другие значения для полей
        user_model.update(kwargs)

        users.append(UserModel(**user_model))
    
    # добавляем в таблицу 
    async with async_session_factory() as session:
        session.add_all(users)
        await session.commit()
        for user in users:
            await session.refresh(user)
        return users
        

@pytest_asyncio.fixture(scope="module")
async def prepared_100_users():
    return await create_users(100)

@pytest_asyncio.fixture(scope="module")
async def prepared_3_users():
    user1 = await create_users(1, username="black_hunter")
    user2 = await create_users(1, username="dark knight")
    user3 = await create_users(1, username="white_hunter")
    return [user1[0], user2[0], user3[0]]

@pytest_asyncio.fixture(scope="module")
async def prepared_1_user():
    user = await create_users(1)
    return user[0]