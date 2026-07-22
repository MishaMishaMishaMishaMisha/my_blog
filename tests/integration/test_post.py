from source.models.post import PostModel
from source.models.post_reaction import PostReactionModel
from source.models.tag import TagModel
from source.models.user import UserModel
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient
from sqlalchemy import select, text, delete
from sqlalchemy.orm import selectinload
from uuid import UUID
import pytest
from source.core.types import TypeReactionEnum
from source.core.types import FileTypeEnum



@pytest.mark.asyncio(loop_scope="session")
class TestPost:

    @pytest.mark.parametrize(
        "post_data",
        [
            (["my post", "bla bl bla.", ["tag_python"]]),
            (["post2", "nfdbgbgn eg", None]),
            (["post3", "regrth", ["tag_horror", "tag_python"]]),
            (["", "", []])
        ]
    )
    async def test_create_post_withoutAttachments(self, 
                               async_client: AsyncClient,
                               authenticated_user,
                               post_data):
        
        keys = ["title", "body", "tags"]
        post = dict(zip(keys, post_data))
        
        response = await async_client.post(
                            "/posts/", 
                            json=post, 
                            headers={"Authorization": f"Bearer {authenticated_user["access_token"]}"})

        assert response.status_code == 200
        
        # check response
        data = response.json()
        assert data["title"] == post["title"]
        assert data["body"] == post["body"]
        assert data["views_count"] == 0
        assert len(data["attachments"]) == 0
        if post["tags"] is not None:
            assert len(data["tags"]) == len(post["tags"])
            
    async def test_create_post_withAttachments(self, 
                               async_client: AsyncClient,
                               authenticated_user,
                               attachments_factory,
                               post_json):
        
        attachments = await attachments_factory(user=authenticated_user["user"], 
                                         count=1,
                                         filename="testfile.png")
        attachment = attachments[0]
        
        post_json["files_id"].append(str(attachment.id))
        
        response = await async_client.post(
                            "/posts/", 
                            json=post_json, 
                            headers={"Authorization": f"Bearer {authenticated_user["access_token"]}"})

        assert response.status_code == 200
        
        # check response
        data = response.json()
        assert data["title"] == post_json["title"]
        assert data["body"] == post_json["body"]
        assert data["views_count"] == 0
        assert len(data["attachments"]) == 1
        assert data["attachments"][0]["file_type"] == FileTypeEnum.IMAGE
        
    async def test_add_reaction(self,
                                authenticated_user,
                                posts_factory,
                                db_session,
                                async_client: AsyncClient):
        
        posts = await posts_factory(users=[authenticated_user["user"]], count=1)
        post = posts[0]
        
        # добавляем реакцию
        react_data = {"post_id": str(post.id),
                      "reaction_type": TypeReactionEnum.LIKE}
        response = await async_client.post(
                            "/posts/react", 
                            json=react_data, 
                            headers={"Authorization": f"Bearer {authenticated_user["access_token"]}"})
        
        assert response.status_code == 200
        
        # проверяем что реакция добавилась
        query = (select(PostModel)
                 .where(PostModel.id==post.id)
                 .options(selectinload(PostModel.reactions_list)))
        res = await db_session.execute(query)
        post = res.scalar()
        assert len(post.reactions) == 1
        assert post.reactions[TypeReactionEnum.LIKE] == 1
        
        # добавление реакции на несуществующий пост
        react_data["post_id"] = str(UUID(int=0))
        response = await async_client.post(
                            "/posts/react", 
                            json=react_data, 
                            headers={"Authorization": f"Bearer {authenticated_user["access_token"]}"})
        assert response.status_code == 404
        
    async def test_change_reaction(self,
                                authenticated_user,
                                posts_factory,
                                db_session,
                                async_client: AsyncClient):
        
        posts = await posts_factory(users=[authenticated_user["user"]], count=1)
        post = posts[0]
        
        # добавляем реакцию
        react_data = {"post_id": str(post.id),
                      "reaction_type": TypeReactionEnum.LIKE}
        response = await async_client.post(
                            "/posts/react", 
                            json=react_data, 
                            headers={"Authorization": f"Bearer {authenticated_user["access_token"]}"})
        
        assert response.status_code == 200
        
        # проверяем что реакция добавилась
        query = (select(PostModel)
                 .where(PostModel.id==post.id)
                 .options(selectinload(PostModel.reactions_list)))
        res = await db_session.execute(query)
        post = res.scalar()
        assert len(post.reactions) == 1
        assert post.reactions[TypeReactionEnum.LIKE] == 1
        
        # Меняем реакцию Like на  Dislike
        react_data["reaction_type"] = TypeReactionEnum.DISLIKE
        response = await async_client.post(
                            "/posts/react", 
                            json=react_data, 
                            headers={"Authorization": f"Bearer {authenticated_user["access_token"]}"})
        
        await db_session.refresh(post)
        # проверяем что реакция изменилась
        query = (select(PostModel)
                 .where(PostModel.id==post.id)
                 .options(selectinload(PostModel.reactions_list)))
        res = await db_session.execute(query)
        post = res.scalar()
        assert post.reactions.get(TypeReactionEnum.LIKE, None) == None 
        assert post.reactions.get(TypeReactionEnum.DISLIKE) == 1
        
        await db_session.refresh(post)
        # пробуем поставить ту же реакцию еще раз
        response = await async_client.post(
                            "/posts/react", 
                            json=react_data, 
                            headers={"Authorization": f"Bearer {authenticated_user["access_token"]}"})
        query = (select(PostModel)
                 .where(PostModel.id==post.id)
                 .options(selectinload(PostModel.reactions_list)))
        res = await db_session.execute(query)
        post = res.scalar()
        assert post.reactions.get(TypeReactionEnum.DISLIKE) == 1
        assert post.reactions.get(TypeReactionEnum.LIKE, None) == None
        
    async def test_get_all_existing_tags(self, db_session, async_client: AsyncClient):
        
        # очищаем старые теги
        await db_session.execute(delete(TagModel))
        await db_session.commit()
        
        # добавляем теги в базу
        # проверяем что реакция добавилась
        tags = ["tag1", "tag2", "tag3"]
        for tag in tags:
            db_session.add(TagModel(name=tag))
        await db_session.commit()
        
        # получаем теги
        response = await async_client.get("/posts/tags")
        assert response.status_code == 200
        assert len(tags) == len(response.json())   

    async def test_get_post_with_increment_views(self,
                                authenticated_user,
                                posts_factory,
                                db_session,
                                async_client: AsyncClient):
        
        posts = await posts_factory(users=[authenticated_user["user"]], count=1)
        post = posts[0]
        
        # получаем пост
        response = await async_client.get(f"/posts/{post.id}")
        assert response.status_code == 200
        
        post_response = response.json()
        assert post.title == post_response["title"]
        assert post.body == post_response["body"]
        assert str(post.author_id) == post_response["author_id"]
        assert len(post_response["tags"]) == 0
        assert len(post_response["reactions"]) == 0
        assert post_response["comments_count"] == 0
        # views_count сохранен в кеше и применится к бд через время
        #assert post_response["views_count"] == 1
        
        # get post with wrong id
        response = await async_client.get(f"/posts/{UUID(int=0)}")
        assert response.status_code == 404
        
    @pytest.mark.parametrize(
        "limit, offset, response_status_code, result_len",
        [
            (None, None, 200, 10),
            (50, None, 200, 50),
            (30, 50, 200, 30),
            (None, 50, 200, 10),
            (150, None, 422, 1),
        ]
    )
    async def test_get_posts(self,
                             limit, offset, response_status_code, result_len,
                             prepared_100_posts,
                             db_session: AsyncSession,
                             async_client: AsyncClient):
        
        if not limit and not offset:
            response = await async_client.get("/posts/")
        elif limit and offset:
            response = await async_client.get(f"/posts/?limit={limit}&offset={offset}")
        elif limit:
            response = await async_client.get(f"/posts/?limit={limit}")
        else:
            response = await async_client.get(f"/posts/?offset={offset}")

        assert response.status_code == response_status_code
        if response_status_code == 200:
            assert len(response.json()["posts"]) == result_len
        
    async def test_delete_post(self,
                            authenticated_user,
                            posts_factory,
                            db_session,
                            async_client: AsyncClient):
        
        posts = await posts_factory(users=[authenticated_user["user"]], count=1)
        post = posts[0]
        
        
        response = await async_client.delete(f"/posts/{post.id}",
                            headers={"Authorization": f"Bearer {authenticated_user["access_token"]}"})
        assert response.status_code == 200
        
        res = await db_session.execute(select(PostModel).where(PostModel.id==post.id))
        deleted_user = res.scalar_one_or_none()
        assert deleted_user is None
        
        # delete post with wrong id
        response = await async_client.delete(f"/posts/{UUID(int=0)}",
                            headers={"Authorization": f"Bearer {authenticated_user["access_token"]}"})
        assert response.status_code == 404
           
    @pytest.mark.parametrize(
        "patch_post_data, updated_keys",
        [
            ({"title": "ergrthytj"}, 
             ["title"]),
            ({"body": "kyujty"}, 
             ["body"]),
            ({"tags": ["tag1", "tag2"]}, 
             ["tags"]),
            ({"title": "hgtgtrh", "body": "ukjutyrth"}, 
             ["title", "body"]),
            ({"title": "new tttle", "body": "new body", "tags": ["python", "IT"]},
             ["title", "body", "tags"]),
            ({}, 
             [])
        ]
    )
    async def test_update_post_withoutAttachments(self,
                               authenticated_user,
                               posts_factory,
                               patch_post_data,
                               updated_keys,
                               db_session: AsyncSession,
                               async_client: AsyncClient):
        
        posts = await posts_factory(users=[authenticated_user["user"]], count=1)
        post = posts[0]
        
        response = await async_client.patch(f"/posts/{post.id}", json=patch_post_data,
                        headers={"Authorization": f"Bearer {authenticated_user["access_token"]}"})
        assert response.status_code == 200
        
        updated_post = response.json()
        for key in updated_keys:
            if key != "tags":
                assert patch_post_data[key] == updated_post[key]
            else: # сравниваем теги
                returned_tags = [tag["name"] for tag in updated_post[key]]
                assert returned_tags == patch_post_data[key]

        
        # update post with wrong id
        response = await async_client.patch(f"/posts/{UUID(int=0)}", json={},
                        headers={"Authorization": f"Bearer {authenticated_user["access_token"]}"})
        assert response.status_code == 404

    async def test_update_post_withAttachments(self,
                               authenticated_user,
                               posts_factory,
                               attachments_factory,
                               async_client: AsyncClient):
        
        # создаем пост с одним медиафайлом
        attachments = await attachments_factory(user=authenticated_user["user"], 
                                         count=1,
                                         filename="testfile.png")
        
        attachments_id = [str(attachments[0].id)]
        
        posts = await posts_factory(users=[authenticated_user["user"]], 
                                    count=1,
                                    attachments=attachments)
        post = posts[0]
        
        # добавим новый файл
        attachments_new = await attachments_factory(user=authenticated_user["user"], 
                                         count=1,
                                         filename="newtestfile.png")
        attachments_id.append(str(attachments_new[0].id))
        
        response = await async_client.patch(f"/posts/{post.id}", json={"files_id": attachments_id},
                        headers={"Authorization": f"Bearer {authenticated_user["access_token"]}"})
        
        assert response.status_code == 200
        updated_post = response.json()
        assert len(updated_post["attachments"]) == 2
        
        # удалим старый файл
        attachments_id.remove(attachments_id[0])
        response = await async_client.patch(f"/posts/{post.id}", json={"files_id": attachments_id},
                        headers={"Authorization": f"Bearer {authenticated_user["access_token"]}"})
        
        assert response.status_code == 200
        updated_post = response.json()
        assert len(updated_post["attachments"]) == 1
        
    async def test_get_post_reactions(self,
                            authenticated_user,
                            users_factory,
                            posts_factory,
                            db_session,
                            async_client: AsyncClient):
        
        posts = await posts_factory(users=[authenticated_user["user"]], count=1)
        post = posts[0]
        
        
        users_num = 50
        reactions = {TypeReactionEnum.LIKE: 25,
                     TypeReactionEnum.DISLIKE: 10,
                     TypeReactionEnum.FIRE: 5,
                     TypeReactionEnum.LAUGH: 8,
                     TypeReactionEnum.SHIT: 2}
        
        
        # добавляем реакции других пользователей
        users = await users_factory(users_num)
        users_id = [user.id for user in users]
        
        user_iter = iter(users_id)
        for reaction_type, count in reactions.items():
            for _ in range(count):
                db_session.add(
                    PostReactionModel(
                        user_id=next(user_iter),
                        post_id=post.id,
                        reaction_type=reaction_type))
        await db_session.commit()
        
        # получаем реакции поста
        response = await async_client.get(f"/posts/{post.id}/reactions")
        assert response.status_code == 200
        
        response_data = response.json()
        assert response_data == reactions
    
    async def test_get_post_tags(self,
                                authenticated_user,
                                posts_factory,
                                tags_factory,
                                async_client: AsyncClient):
        
        tags = await tags_factory(3)
        tags_names = [tag.name for tag in tags]
        # создаем пост
        posts = await posts_factory(users=[authenticated_user["user"]], count=1, tags=tags)
        post = posts[0]
        
        # получаем теги поста
        response = await async_client.get(f"/posts/{post.id}/tags")
        assert response.status_code == 200
        
        response_data = response.json()
        returned_tags = [tag["name"] for tag in response_data]
        assert returned_tags == tags_names
        
    @pytest.mark.parametrize(
            "query_params, expected_status, result_len", 
            [
                # === Твои базовые тесты ===
                ("", 422, None),
                ("?posttile=qwe", 422, None),
                ("?title=", 422, None),
                ("?title=q", 422, None),
                ("?title=qwerty", 200, 0), 
                ("?title=my favorite films", 200, 1),
                ("?title=game", 200, 3), # Изменил на 3, так как добавился "Super Game Max Pro"
                ("?title=2025", 200, 1),
                ("?title=HOW TO", 200, 1), 
                ("?title=_", 422, None),
                ("?title=   top five    ", 200, 1),

                # === НОВЫЕ ТЕСТЫ ===

                # 1. Опечатки (Fuzzy Search через триграммы)
                ("?title=prograaming", 200, 1),  # Опечатка "aa" -> найдет "how to learn programming"
                ("?title=filmz", 200, 1),        # Опечатка "z" -> найдет "my favorite films"
                ("?title=wither", 200, 1),       # Опечатка/пропуск буквы -> найдет "The Witcher 3..."

                # 2. Регистронезависимость и частичные совпадения (Разный регистр)
                ("?title=pYtHoN", 200, 2),       # Найдет "Разработка на Python..." и "Python для..."
                ("?title=LEARN", 200, 1),        # В верхнем регистре -> найдет "how to learn programming"

                # 3. Кириллица (Проверка работы триграмм/FTS со славянскими символами)
                ("?title=разработка", 200, 1),   # Точное совпадение на русском
                ("?title=питон", 200, 0),        # Ошибка/транслитерация не сработает, но "?title=питон" вернет 404
                ("?title=начинающих", 200, 1),   # Часть русской строки

                # 4. Специальные символы и цифры
                ("?title=Witcher 3", 200, 1),    # С цифрой
                ("?title=FastAPI vs", 200, 1),   # Со спецсимволом (двоеточия/слэши обычно режутся FTS, проверяем триграммы)

                # 5. Слишком сильные опечатки (??Должен быть 404, а не случайный пост)
                ("?title=programminggzz", 200, 1), 

                # 6. Несколько слов из разных постов (Проверка жадности поиска)
                # Если ввести "Python Django", FTS или триграммы могут найти оба поста (один про Python, другой про Django)
                ("?title=Python Django", 200, 3), # Найдет посты с Python (2 шт) + пост с Django (1 шт)
            ])
    async def test_find_posts(self,
                              query_params,
                              expected_status,
                              result_len,
                              prepared_10_posts,
                              async_client: AsyncClient):
        
        response = await async_client.get(f"/posts/search{query_params}")
        assert response.status_code == expected_status
        if result_len is not None:
            assert len(response.json()) == result_len
    
    @pytest.mark.parametrize(
        "query_params, expected_status, result_len", 
        [
            ("", 422, None),
            ("?tagname=qwe", 422, None),
            ("?name=", 422, None),
            ("?name=q", 422, None),
            ("?name=qwerty", 200, 0),
            ("?name=python", 200, 1),
            ("?name=fast", 200, 2),
            ("?name=api", 200, 2),
            ("?name=API", 200, 2),
            ("?name=fast api", 200, 1),
            ("?name=_", 422, None),
            ("?name=   python    ", 200, 0)
        ])
    async def test_find_tags(self,
                             query_params,
                             expected_status,
                             result_len,
                             prepared_3_tags,
                             async_client: AsyncClient):
        
        
        response = await async_client.get(f"/posts/tags/search{query_params}")
        assert response.status_code == expected_status
        if result_len:
            assert len(response.json()) == result_len
        