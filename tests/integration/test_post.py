import pytest

from httpx import AsyncClient
from uuid import UUID
from typing import Any
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from source.models.post import PostModel
from source.models.post_reaction import PostReactionModel
from source.models.tag import TagModel
from source.core.types import TypeReactionEnum
from source.core.types import FileTypeEnum
from source.cache.redis_backend import redis_backend



@pytest.mark.asyncio(loop_scope="session")
class TestPost:

    async def test_create_post_withoutAttachments(self, 
                               async_client: AsyncClient,
                               authenticated_user):
        
        # without tags
        post: dict[str, Any] = {"title": "title1", "body": "body1"}
        response = await async_client.post(
                            "/api/v1/posts/", 
                            json=post, 
                            headers={"Authorization": f"Bearer {authenticated_user["access_token"]}"})
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == post["title"]
        assert data["body"] == post["body"]
        assert data["views_count"] == 0
        assert len(data["attachments"]) == 0
        assert len(data["tags"]) == 0
        
        # with new tag
        post = {"title": "title1", "body": "body1", "tags": [{"name": "tag1"}]}
        response = await async_client.post(
                            "/api/v1/posts/", 
                            json=post, 
                            headers={"Authorization": f"Bearer {authenticated_user["access_token"]}"})
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == post["title"]
        assert data["body"] == post["body"]
        assert data["views_count"] == 0
        assert len(data["attachments"]) == 0
        assert len(data["tags"]) == 1
        assert data["tags"][0]["name"] == "tag1"
        # save tag id
        tag_id = str(data["tags"][0]["id"])
        
        
        # with existing tag
        post = {"title": "title1", 
                "body": "body1", 
                "tags": [{"name": "new-tag"}, {"id": tag_id, "name": "tag1"}]}
        response = await async_client.post(
                            "/api/v1/posts/", 
                            json=post, 
                            headers={"Authorization": f"Bearer {authenticated_user["access_token"]}"})
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == post["title"]
        assert data["body"] == post["body"]
        assert data["views_count"] == 0
        assert len(data["attachments"]) == 0
        assert len(data["tags"]) == 2
            
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
                            "/api/v1/posts/", 
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
                            "/api/v1/posts/react", 
                            json=react_data, 
                            headers={"Authorization": f"Bearer {authenticated_user["access_token"]}"})
        
        assert response.status_code == 200
        
        # проверяем что реакция добавилась
        query = (select(PostModel)
                 .where(PostModel.id==post.id)
                 .options(selectinload(PostModel.reactions_list)))
        res = await db_session.execute(query)
        post = res.scalar()
        assert post.reactions[TypeReactionEnum.LIKE] == 1
        
        # добавление реакции на несуществующий пост
        react_data["post_id"] = str(UUID(int=0))
        response = await async_client.post(
                            "/api/v1/posts/react", 
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
                            "/api/v1/posts/react", 
                            json=react_data, 
                            headers={"Authorization": f"Bearer {authenticated_user["access_token"]}"})
        
        assert response.status_code == 200
        
        # проверяем что реакция добавилась
        query = (select(PostModel)
                 .where(PostModel.id==post.id)
                 .options(selectinload(PostModel.reactions_list)))
        res = await db_session.execute(query)
        post = res.scalar()
        assert post.reactions[TypeReactionEnum.LIKE] == 1
        
        # Меняем реакцию Like на  Dislike
        react_data["reaction_type"] = TypeReactionEnum.DISLIKE
        response = await async_client.post(
                            "/api/v1/posts/react", 
                            json=react_data, 
                            headers={"Authorization": f"Bearer {authenticated_user["access_token"]}"})
        
        await db_session.refresh(post)
        # проверяем что реакция изменилась
        query = (select(PostModel)
                 .where(PostModel.id==post.id)
                 .options(selectinload(PostModel.reactions_list)))
        res = await db_session.execute(query)
        post = res.scalar()
        assert post.reactions.get(TypeReactionEnum.LIKE) == 0 
        assert post.reactions.get(TypeReactionEnum.DISLIKE) == 1
        
        await db_session.refresh(post)
        # пробуем поставить ту же реакцию еще раз (удалить реакцию)
        response = await async_client.post(
                            "/api/v1/posts/react", 
                            json=react_data, 
                            headers={"Authorization": f"Bearer {authenticated_user["access_token"]}"})
        query = (select(PostModel)
                 .where(PostModel.id==post.id)
                 .options(selectinload(PostModel.reactions_list)))
        res = await db_session.execute(query)
        post = res.scalar()
        assert post.reactions.get(TypeReactionEnum.DISLIKE) == 0
        assert post.reactions.get(TypeReactionEnum.LIKE) == 0
        
    async def test_get_all_existing_tags(self, 
                                         db_session, 
                                         async_client: AsyncClient):
        
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
        response = await async_client.get("/api/v1/posts/tags")
        assert response.status_code == 200
        assert len(tags) == len(response.json())   

    async def test_get_post_with_increment_views(self,
                                authenticated_user,
                                posts_factory,
                                async_client: AsyncClient):
        
        posts = await posts_factory(users=[authenticated_user["user"]], count=1)
        post = posts[0]
        
        # получаем пост
        response = await async_client.get(f"/api/v1/posts/{post.id}")
        assert response.status_code == 200
        
        post_response = response.json()
        assert post.title == post_response["title"]
        assert post.body == post_response["body"]
        assert str(post.author_id) == post_response["author_id"]
        assert len(post_response["tags"]) == 0
        assert post_response["comments_count"] == 0
        
        # views count должен увеличится в кеше
        redis_views = await redis_backend.hget("post_views", str(post.id))
        redis_views == 1
        
        # get post with wrong id
        response = await async_client.get(f"/api/v1/posts/{UUID(int=0)}")
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
                             async_client: AsyncClient):
        
        if not limit and not offset:
            response = await async_client.get("/api/v1/posts/")
        elif limit and offset:
            response = await async_client.get(f"/api/v1/posts/?limit={limit}&offset={offset}")
        elif limit:
            response = await async_client.get(f"/api/v1/posts/?limit={limit}")
        else:
            response = await async_client.get(f"/api/v1/posts/?offset={offset}")

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
        
        
        response = await async_client.delete(f"/api/v1/posts/{post.id}",
                            headers={"Authorization": f"Bearer {authenticated_user["access_token"]}"})
        assert response.status_code == 200
        
        res = await db_session.execute(select(PostModel).where(PostModel.id==post.id))
        deleted_user = res.scalar_one_or_none()
        assert deleted_user is None
        
        # delete post with wrong id
        response = await async_client.delete(f"/api/v1/posts/{UUID(int=0)}",
                            headers={"Authorization": f"Bearer {authenticated_user["access_token"]}"})
        assert response.status_code == 404
           
    @pytest.mark.parametrize(
        "patch_post_data, updated_keys",
        [
            ({"title": "ergrthytj"}, 
             ["title"]),
            ({"body": "kyujty"}, 
             ["body"]),
            ({"tags": [{"name": "tagggg1"}, {"name": "taggggg2"}]}, 
             ["tags"]),
            ({"title": "hgtgtrh", "body": "ukjutyrth"}, 
             ["title", "body"]),
            ({"title": "new tttle", "body": "new body", "tags": [{"name": "python"}, 
                                                                 {"name": "IT"}]},
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
                               async_client: AsyncClient):
        
        posts = await posts_factory(users=[authenticated_user["user"]], count=1)
        post = posts[0]
        
        response = await async_client.put(f"/api/v1/posts/{post.id}", json=patch_post_data,
                        headers={"Authorization": f"Bearer {authenticated_user["access_token"]}"})
        assert response.status_code == 200
        
        updated_post = response.json()
        for key in updated_keys:
            if key != "tags":
                assert patch_post_data[key] == updated_post[key]
            else: # сравниваем теги
                returned_tags = [tag["name"] for tag in updated_post[key]]
                patched_tags = [tag["name"] for tag in patch_post_data[key]]
                assert returned_tags == patched_tags

        
        # update post with wrong id
        response = await async_client.put(f"/api/v1/posts/{UUID(int=0)}", json={},
                        headers={"Authorization": f"Bearer {authenticated_user["access_token"]}"})
        assert response.status_code == 404
        
    async def test_update_post_add_existing_tag(self,
                               authenticated_user,
                               posts_factory,
                               tag_factory,
                               async_client: AsyncClient):
        
        posts = await posts_factory(users=[authenticated_user["user"]], count=1)
        post = posts[0]
        
        tag = tag_factory()
        
        patch_post_data = {"tags": [{"id": tag.id, "name": tag.name},
                                    {"name": "new----tag"}]}
        
        response = await async_client.put(f"/api/v1/posts/{post.id}", json=patch_post_data,
                        headers={"Authorization": f"Bearer {authenticated_user["access_token"]}"})
        assert response.status_code == 200

        updated_post = response.json()
        assert len(patch_post_data["tags"]) == len(updated_post["tags"])
        assert patch_post_data["tags"][0]["name"] == updated_post["tags"][0]["name"]
        assert patch_post_data["tags"][1]["name"] == updated_post["tags"][1]["name"]

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
        
        response = await async_client.put(f"/api/v1/posts/{post.id}", json={"files_id": attachments_id},
                        headers={"Authorization": f"Bearer {authenticated_user["access_token"]}"})
        
        assert response.status_code == 200
        updated_post = response.json()
        assert len(updated_post["attachments"]) == 2
        
        # удалим старый файл
        attachments_id.remove(attachments_id[0])
        response = await async_client.put(f"/api/v1/posts/{post.id}", json={"files_id": attachments_id},
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
        response = await async_client.get(f"/api/v1/posts/{post.id}/reactions")
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
        response = await async_client.get(f"/api/v1/posts/{post.id}/tags")
        assert response.status_code == 200
        
        response_data = response.json()
        returned_tags = [tag["name"] for tag in response_data]
        assert returned_tags == tags_names
        
    @pytest.mark.parametrize(
            "query_params, expected_status, result_len", 
            [
                ("", 422, None),
                ("?posttile=qwe", 422, None),
                ("?title=", 422, None),
                ("?title=q", 422, None),
                ("?title=qwerty", 200, 0), 
                ("?title=my favorite films", 200, 1),
                ("?title=game", 200, 3),
                ("?title=2025", 200, 1),
                ("?title=HOW TO", 200, 1), 
                ("?title=_", 422, None),
                ("?title=   top five    ", 200, 1),
                ("?title=prograaming", 200, 1),  # Опечатка "aa" -> найдет "how to learn programming"
                ("?title=filmz", 200, 1),        # Опечатка "z" -> найдет "my favorite films"
                ("?title=wither", 200, 1),       # Опечатка/пропуск буквы -> найдет "The Witcher 3..."
                ("?title=pYtHoN", 200, 2),       # Найдет "Разработка на Python..." и "Python для..."
                ("?title=LEARN", 200, 1),        # В верхнем регистре -> найдет "how to learn programming"
                ("?title=разработка", 200, 1),   # Точное совпадение на русском
                ("?title=питон", 200, 0),        # Ошибка/транслитерация не сработает, но "?title=питон" вернет 404
                ("?title=начинающих", 200, 1),   # Часть русской строки
                ("?title=Witcher 3", 200, 1),    # С цифрой
                ("?title=FastAPI vs", 200, 1),   # Со спецсимволом (двоеточия/слэши обычно режутся FTS, проверяем триграммы)
                ("?title=programminggzz", 200, 1), 
                ("?title=Python Django", 200, 3), # Найдет посты с Python (2 шт) + пост с Django (1 шт)
            ])
    async def test_find_posts(self,
                              query_params,
                              expected_status,
                              result_len,
                              prepared_10_posts,
                              async_client: AsyncClient):
        
        response = await async_client.get(f"/api/v1/posts/search{query_params}")
        assert response.status_code == expected_status
        if result_len is not None:
            assert len(response.json()["posts"]) == result_len
    
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
        
        
        response = await async_client.get(f"/api/v1/posts/tags/search{query_params}")
        assert response.status_code == expected_status
        if result_len:
            assert len(response.json()) == result_len

    async def test_get_user_posts(self,
                                users_factory,
                                posts_factory,
                                async_client: AsyncClient):
        
        users = await users_factory(count=2, is_verified=True)
        
        posts_user1 = await posts_factory(users=[users[0]], count=3)
        posts_user2 = await posts_factory(users=[users[1]], count=5)


        response = await async_client.get(f"/api/v1/users/{users[0].username}/posts")
        assert response.status_code == 200
        res1 = response.json()
        assert res1["total_count"] == len(posts_user1)
        for i in range(len(posts_user1)):
            assert posts_user1[i].title == res1["posts"][i]["title"]
            
        response = await async_client.get(f"/api/v1/users/{users[1].username}/posts")
        assert response.status_code == 200
        res2 = response.json()
        assert res2["total_count"] == len(posts_user2)
        for i in range(len(posts_user2)):
            assert posts_user2[i].title == res2["posts"][i]["title"]
        
    async def test_get_posts_with_tag(self,
                                authenticated_user,
                                tags_factory,
                                posts_factory,
                                async_client: AsyncClient):
        
        tagsname = ["first-tag", "second-tag"]
        tags = await tags_factory(2, tagsname)
        
        user = authenticated_user["user"]
        
        posts_without_tags = await posts_factory(users=[user], count=3)
        posts_with_1tag = await posts_factory(users=[user], count=2, tags=[tags[0]])
        posts_with_2tag = await posts_factory(users=[user], count=4, tags=[tags[1]])
        posts_with_1and2tag = await posts_factory(users=[user], count=1, tags=[tags[0], tags[1]])
        
        
        response1 = await async_client.get(f"/api/v1/posts/search-with-tag?tag={tagsname[0]}")
        assert response1.status_code == 200
        res1 = response1.json()
        assert res1["total_count"] == len(posts_with_1tag) + len(posts_with_1and2tag)
        for p in res1["posts"]:
            if p["tags"][0]["name"] != tagsname[0]:
                assert p["tags"][1]["name"] == tagsname[0]
            else:
                assert p["tags"][0]["name"] == tagsname[0]
        
        response2 = await async_client.get(f"/api/v1/posts/search-with-tag?tag={tagsname[1]}")
        assert response2.status_code == 200
        res2 = response2.json()
        assert res2["total_count"] == len(posts_with_2tag) + len(posts_with_1and2tag)
        for p in res2["posts"]:
            if p["tags"][0]["name"] != tagsname[1]:
                assert p["tags"][1]["name"] == tagsname[1]
            else:
                assert p["tags"][0]["name"] == tagsname[1]

        
        
        
        
        