import pytest
import pytest_asyncio
from source.models.post import PostModel
from source.core.utils import get_random_string
from source.database.db_connect import async_session_factory


@pytest.fixture
def post_json():

    return {
        "title": get_random_string(20),
        "body": get_random_string(300),
        "tags": [],
        "files_id": [],
    }


@pytest.fixture
def post_factory():

    def factory(
        *,
        author_id,
        title=None,
        body=None,
        **kwargs,
    ):

        defaults = {
            "author_id": author_id,
            "title": title or get_random_string(20),
            "body": body or get_random_string(300),
        }

        defaults.update(kwargs)

        return PostModel(**defaults)

    return factory


@pytest_asyncio.fixture
async def posts_factory(
    db_session,
    post_factory,
):

    async def factory(
        *,
        users,
        count: int = 1,
        **kwargs,
    ):

        posts = []

        users_count = len(users)

        for i in range(count):

            posts.append(
                post_factory(
                    author_id=users[i % users_count].id,
                    **kwargs,
                )
            )

        db_session.add_all(posts)

        await db_session.commit()

        for post in posts:
            await db_session.refresh(post)

        return posts

    return factory


#############################################

# данные для параметризации в тестах (scope=class/module/session)

# вспомогательная функция (не фикстура)
async def create_posts(author_id: int, count: int = 1, **kwargs) -> list[PostModel]:
    
    posts = []
    for _ in range(count):
        post_model = {
                        "author_id": author_id,
                        "title": get_random_string(20),
                        "body": get_random_string(300),
                    }

        # если были переданы другие значения для полей
        post_model.update(kwargs)

        posts.append(PostModel(**post_model))
    
    # добавляем в таблицу 
    async with async_session_factory() as session:
        session.add_all(posts)
        await session.commit()
        for post in posts:
            await session.refresh(post)
        return posts
        

@pytest_asyncio.fixture(scope="module")
async def prepared_100_posts(prepared_1_user):
    return await create_posts(prepared_1_user.id, 100)

@pytest_asyncio.fixture(scope="module")
async def prepared_10_posts(prepared_1_user):

    post_titles = [
        "top five rpg games in 2025",   # 0
        "my favorite films",            # 1
        "how to learn programming",     # 2
        "game of the 2010",             # 3
        # ---- Новые посты для расширенных тестов ----
        "Разработка на Python и Go",    # 4 (Кириллица)
        "The Witcher 3: Wild Hunt",     # 5 (Спецсимволы, точный бренд)
        "FastAPI vs Django guide",      # 6 (Похожий на "programming")
        "Python для начинающих",        # 7 (Дублирование темы Python)
        "Super Game Max Pro",           # 8 (Для проверки ранжирования слова Game)
    ]
    
    posts = []
    for i in range(len(post_titles)):
        post = await create_posts(prepared_1_user.id, 1, title=post_titles[i])
        posts.append(post[0])
        
    return posts