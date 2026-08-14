import pytest
import pytest_asyncio

from sqlalchemy import delete

from source.models.tag import TagModel
from source.core.utils import get_random_string
from source.database.db_connect import async_session_factory


# создает три случайных имени для тегов
@pytest.fixture
def tag_names():

    return [
        get_random_string(8)
        for _ in range(3)
    ]


# создает модель тега и добавляет его в таблицу
# можно передать свое имя тега
@pytest.fixture
def tag_factory():

    def factory(**kwargs):

        defaults = {
            "name": get_random_string(10),
        }

        defaults.update(kwargs)

        return TagModel(**defaults)

    return factory


# создает count тегов и добавляет в таблицу. можно передать свои названия тегов
@pytest_asyncio.fixture
async def tags_factory(db_session, tag_factory):

    async def factory(
        count: int = 3,
        names: list[str] | None = None,
    ):

        if names is not None:
            tags = [
                tag_factory(name=name)
                for name in names
            ]
        else:
            tags = [
                tag_factory()
                for _ in range(count)
            ]

        db_session.add_all(tags)

        await db_session.commit()

        for tag in tags:
            await db_session.refresh(tag)

        return tags

    return factory




#############################################

# данные для параметризации в тестах (scope=class/module/session)

# вспомогательная функция (не фикстура)
async def create_tags(count: int = 1, **kwargs) -> list[TagModel]:
    
    tags = []
    for _ in range(count):
        tag_model = {"name": get_random_string(10)}

        # если были переданы другие значения для полей
        tag_model.update(kwargs)

        tags.append(TagModel(**tag_model))
    
    # добавляем в таблицу 
    async with async_session_factory() as session:
        session.add_all(tags)
        await session.commit()
        for tag in tags:
            await session.refresh(tag)
        return tags
        

@pytest_asyncio.fixture(scope="module")
async def prepared_3_tags():
    
    # очищаем все теги
    async with async_session_factory() as session:
        await session.execute(delete(TagModel))
        await session.commit()
    
    tag1 = await create_tags(1, name="fast api")
    tag2 = await create_tags(1, name="python")
    tag3 = await create_tags(1, name="fastAPI")
    return [tag1[0], tag2[0], tag3[0]]
