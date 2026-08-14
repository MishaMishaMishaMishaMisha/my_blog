import pytest

from uuid import UUID
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from source.models.post import PostModel
from source.models.comment_reaction import CommentReactionModel
from source.models.comment import CommentModel
from source.core.types import TypeReactionEnum
from source.core.utils import get_random_string


@pytest.mark.asyncio(loop_scope="session")
class TestComment:
    
    async def test_create_commentWithoutAttachments(self, 
                               db_session: AsyncSession, 
                               async_client: AsyncClient,
                               posts_factory,
                               authenticated_users):
        
        users = await authenticated_users(count=6, is_verified=True)
        
        comment_nums = 5
        
        posts = await posts_factory(users=[users[0]["user"]], count=1)
        post = posts[0]
        
        for i in range(1, comment_nums+1):
            comment = {
                        "post_id": str(post.id),
                        "parent_id": None,
                        "body": get_random_string(100)}
            
            response = await async_client.post(
                                f"/posts/{post.id}/comments", 
                                json=comment, 
                                headers={"Authorization": f"Bearer {users[i]["access_token"]}"})

            assert response.status_code == 200
            
            # check response
            data = response.json()
            assert data["post_id"] == comment["post_id"]
            assert data["body"] == comment["body"]
            assert data["author_id"] == str(users[i]["user"].id)
            assert data["parent_id"] == comment["parent_id"]
            assert len(data["attachments"]) == 0

        # проверяем что у поста появились комментарии
        res = await db_session.execute((select(PostModel)
                                  .where(PostModel.id==post.id)
                                  .options(selectinload(PostModel.comments))))
        post_db = res.scalar_one()
        assert len(post_db.comments) == comment_nums
        
    async def test_create_commentWithAttachments(self, 
                               async_client: AsyncClient,
                               posts_factory,
                               attachments_factory,
                               authenticated_users):
        
        users = await authenticated_users(count=2, is_verified=True)
        
        posts = await posts_factory(users=[users[0]["user"]], count=1)
        post = posts[0]
        
        attachments_user1 = await attachments_factory(user=users[0]["user"], count=1)
        attachments_user2 = await attachments_factory(user=users[1]["user"], count=5)
        
        attachments_id_user1 = []
        for attachment in attachments_user1:
            attachments_id_user1.append(str(attachment.id))
        attachments_id_user2 = []
        for attachment in attachments_user2:
            attachments_id_user2.append(str(attachment.id))

        comment = {
                    "post_id": str(post.id),
                    "parent_id": None,
                    "body": get_random_string(100),
                    "files_id": attachments_id_user1}
        
        response = await async_client.post(
                            f"/posts/{post.id}/comments", 
                            json=comment, 
                            headers={"Authorization": f"Bearer {users[0]["access_token"]}"})

        assert response.status_code == 200
        
        # check response
        data = response.json()
        assert data["post_id"] == comment["post_id"]
        assert data["body"] == comment["body"]
        assert data["author_id"] == str(users[0]["user"].id)
        assert data["parent_id"] == comment["parent_id"]
        assert len(data["attachments"]) == len(attachments_user1)
        
        # пробуем прикрепить к комментарию 5 файлов
        comment["files_id"] = attachments_id_user2
        response = await async_client.post(
                            f"/posts/{post.id}/comments", 
                            json=comment, 
                            headers={"Authorization": f"Bearer {users[0]["access_token"]}"})

        assert response.status_code == 403
        
    async def test_create_comment_replies(self, 
                               db_session: AsyncSession, 
                               async_client: AsyncClient,
                               posts_factory,
                               authenticated_users):
        
        comment_nums = 5
        users = await authenticated_users(count=comment_nums, is_verified=True)
        
        posts = await posts_factory(users=[users[0]["user"]], count=1)
        post = posts[0]
        
        # создаем несколько корневых комментриев
        comments_id = []
        for i in range(3):
            comment = {
                        "post_id": str(post.id),
                        "parent_id": None,
                        "body": get_random_string(100)}
            
            response = await async_client.post(
                                f"/posts/{post.id}/comments", 
                                json=comment, 
                                headers={"Authorization": f"Bearer {users[i]["access_token"]}"})
            
            comments_id.append(response.json()["id"])

        # добавляем ответы на комментарии
        for i in range(3, comment_nums):
            comment = {
                        "post_id": str(post.id),
                        "parent_id": str(comments_id[comment_nums-i]),
                        "body": get_random_string(100)}
            
            response = await async_client.post(
                                f"/posts/{post.id}/comments", 
                                json=comment, 
                                headers={"Authorization": f"Bearer {users[i]["access_token"]}"})

            assert response.status_code == 200
            
            # check response
            data = response.json()
            assert data["post_id"] == comment["post_id"]
            assert data["body"] == comment["body"]
            assert data["author_id"] == str(users[i]["user"].id)
            assert data["parent_id"] == comment["parent_id"]

        # считаем комментарии под постом
        res = await db_session.execute((select(PostModel)
                                  .where(PostModel.id==post.id)
                                  .options(selectinload(PostModel.comments))))
        post_db = res.scalar_one()
        assert len(post_db.comments) == comment_nums
        
        # добавляем ответ на не существующий комментарий
        comment = {
                    "post_id": str(post.id),
                    "parent_id": str(UUID(int=0)),
                    "body": get_random_string(100)}
        response = await async_client.post(
                            f"/posts/{post.id}/comments", 
                            json=comment, 
                            headers={"Authorization": f"Bearer {users[0]["access_token"]}"})
        assert response.status_code == 404
        
    async def test_get_root_comments_and_replies(self, 
                               async_client: AsyncClient,
                               posts_factory,
                               users_factory,
                               comments_tree):
        
        users = await users_factory(count=5)
        
        posts = await posts_factory(users=[users[0]], count=1)
        post = posts[0]
        
        # создадим 3 корневых комменатрия, 2 ответа на 1й комментрий, 1 ответ на 1й ответ 1го комментария
        comments = await comments_tree(post=post,
                                       users=users,
                                       count_roots=3,
                                       count_replies_level1=2,
                                       count_replies_level2=1)
        
        
        # тест корневых комментариев
        response = await async_client.get(f"/posts/{post.id}/comments")
        assert response.status_code == 200
        assert len(response.json()) == 3
        
        # тест ответов на 1й коммент
        response = await async_client.get(f"/comments/{comments["roots"][0].id}/replies")
        assert response.status_code == 200
        assert len(response.json()) == 2
        
        # тест ответов на первый ответ на 1й коммент
        response = await async_client.get(f"/comments/{comments["level1"][0].id}/replies")
        assert response.status_code == 200
        assert len(response.json()) == 1        
        
    async def test_add_reaction(self,
                                authenticated_users,
                                posts_factory,
                                comments_factory,
                                db_session,
                                async_client: AsyncClient):
        
        users = await authenticated_users(count=2, is_verified=True)
        
        posts = await posts_factory(users=[users[0]["user"]], count=1)
        post = posts[0]
        
        comments = await comments_factory(users=[users[0]["user"]], post=post)
        
        # добавляем реакцию
        react_data = {
                      "comment_id": str(comments[0].id),
                      "reaction_type": TypeReactionEnum.LIKE}
        response = await async_client.post(
                            "/comments/react", 
                            json=react_data, 
                            headers={"Authorization": f"Bearer {users[1]["access_token"]}"})
        
        assert response.status_code == 200
        
        # проверяем что реакция добавилась
        query = (select(CommentModel)
                 .where(CommentModel.id==comments[0].id)
                 .options(selectinload(CommentModel.reactions_list)))
        res = await db_session.execute(query)
        comment_model = res.scalar()
        assert comment_model.reactions[TypeReactionEnum.LIKE] == 1
        
        # добавление реакции на несуществующий комментарий
        react_data["comment_id"] = str(UUID(int=0))
        response = await async_client.post(
                            "/comments/react", 
                            json=react_data, 
                            headers={"Authorization": f"Bearer {users[1]["access_token"]}"})
        assert response.status_code == 404
        
        
        # Меняем реакцию
        react_data["comment_id"] = str(comments[0].id)
        react_data["reaction_type"] = TypeReactionEnum.DISLIKE
        response = await async_client.post(
                            "/comments/react", 
                            json=react_data, 
                            headers={"Authorization": f"Bearer {users[1]["access_token"]}"})
        
        await db_session.refresh(comment_model)
        # проверяем что реакция изменилась
        query = (select(CommentModel)
                 .where(CommentModel.id==comments[0].id)
                 .options(selectinload(CommentModel.reactions_list)))
        res = await db_session.execute(query)
        comment = res.scalar()
        assert comment.reactions.get(TypeReactionEnum.LIKE) == 0
        assert comment.reactions.get(TypeReactionEnum.DISLIKE) == 1
        
        
        await db_session.refresh(comment)
        # пробуем поставить ту же реакцию еще раз (удалить)
        response = await async_client.post(
                            "/comments/react", 
                            json=react_data, 
                            headers={"Authorization": f"Bearer {users[1]["access_token"]}"})
        query = (select(CommentModel)
                 .where(CommentModel.id==comments[0].id)
                 .options(selectinload(CommentModel.reactions_list)))
        res = await db_session.execute(query)
        post = res.scalar()
        assert post.reactions.get(TypeReactionEnum.DISLIKE) == 0
        assert post.reactions.get(TypeReactionEnum.LIKE) == 0
        
    async def test_delete_comment(self,
                                authenticated_users,
                                posts_factory,
                                comments_factory,
                                db_session,
                                async_client: AsyncClient):
        
        users = await authenticated_users(count=2, is_verified=True)
        
        posts = await posts_factory(users=[users[0]["user"]], count=1)
        post = posts[0]
        
        comments = await comments_factory(users=[users[0]["user"], users[1]["user"]], 
                                          post=post, count=2)
        
        # удаляем комментарий
        response = await async_client.delete(f"/comments/{comments[0].id}",
                            headers={"Authorization": f"Bearer {users[0]["access_token"]}"})
        assert response.status_code == 200
        # проверяем что его нету в базе
        res = await db_session.execute(select(CommentModel).where(CommentModel.id==comments[0].id))
        deleted_comment = res.scalar_one_or_none()
        assert deleted_comment is None
        
        # delete comment with wrong id
        response = await async_client.delete(f"/comments/{UUID(int=0)}",
                            headers={"Authorization": f"Bearer {users[0]["access_token"]}"})
        assert response.status_code == 404
        
        # delete other user' comment
        response = await async_client.delete(f"/comments/{comments[1].id}",
                            headers={"Authorization": f"Bearer {users[0]["access_token"]}"})
        assert response.status_code == 404

    async def test_get_comment_reactions(self,
                                         users_factory,
                                         posts_factory,
                                         comments_factory,
                                         db_session,
                                         async_client: AsyncClient):
        
        
        users_num = 50
        reactions = {TypeReactionEnum.LIKE: 25,
                     TypeReactionEnum.DISLIKE: 10,
                     TypeReactionEnum.FIRE: 5,
                     TypeReactionEnum.LAUGH: 8,
                     TypeReactionEnum.SHIT: 2}
        
        
        # создаем комментрий
        users = await users_factory(count=users_num)
        
        posts = await posts_factory(users=[users[0]], count=1)
        post = posts[0]
        
        comments = await comments_factory(users=[users[0]], 
                                          post=post, count=1)
        
        users_id = [user.id for user in users]
        user_iter = iter(users_id)
        for reaction_type, count in reactions.items():
            for _ in range(count):
                db_session.add(
                    CommentReactionModel(
                        user_id=next(user_iter),
                        comment_id=comments[0].id,
                        reaction_type=reaction_type))
        await db_session.commit()
        
        # получаем реакции поста
        response = await async_client.get(f"/comments/{comments[0].id}/reactions")
        assert response.status_code == 200
        
        response_data = response.json()
        assert response_data == reactions
    
    async def test_get_comment_byID(self,
                                users_factory,
                                         posts_factory,
                                         comments_factory,
                                         async_client: AsyncClient):
        
        # создаем комментрий
        users = await users_factory(count=1, is_verified=True)
        
        posts = await posts_factory(users=[users[0]], count=1)
        post = posts[0]
        
        comments = await comments_factory(users=[users[0]], 
                                          post=post, count=1)
        
        # получаем комментарий
        response = await async_client.get(f"/comments/{comments[0].id}")
        assert response.status_code == 200
        
        comment_response = response.json()
        assert str(users[0].id) == comment_response["author_id"]
        assert str(comments[0].post_id) == comment_response["post_id"]
        assert comments[0].parent_id == comment_response["parent_id"]
        assert comments[0].body == comment_response["body"]
        assert len(comment_response["attachments"]) == 0
        
        # get post with wrong id
        response = await async_client.get(f"/comments/{UUID(int=0)}")
        assert response.status_code == 404
            
    @pytest.mark.parametrize(
        "patch_comment_data, updated_keys",
        [
            ({"body": "new comment kfjbvf"}, ["body"]),
            ({}, [])
        ]
    )
    async def test_update_comment_WithoutAttachments(self,
                                patch_comment_data,
                                updated_keys,
                                async_client: AsyncClient,
                                authenticated_users,
                                posts_factory,
                                comments_factory):
        
        users = await authenticated_users(count=2, is_verified=True)
        
        posts = await posts_factory(users=[users[0]["user"]], count=1)
        post = posts[0]
        
        comments = await comments_factory(users=[users[0]["user"], users[1]["user"]], 
                                          post=post, count=2)
        
        
        # update comment
        response = await async_client.patch(f"/comments/{comments[0].id}", json=patch_comment_data,
                        headers={"Authorization": f"Bearer {users[0]["access_token"]}"})
        assert response.status_code == 200
        updated_post = response.json()
        for key in updated_keys:
            assert patch_comment_data[key] == updated_post[key]

        
        # update comment with wrong id
        response = await async_client.patch(f"/comments/{UUID(int=0)}", json={},
                        headers={"Authorization": f"Bearer {users[0]["access_token"]}"})
        assert response.status_code == 404
        
        # update other user' comment
        if patch_comment_data:
            response = await async_client.patch(f"/comments/{comments[1].id}", json=patch_comment_data,
                            headers={"Authorization": f"Bearer {users[0]["access_token"]}"})
            assert response.status_code == 404
               
    async def test_update_comment_withAttachments(self,
                            authenticated_user,
                            async_client: AsyncClient, 
                            posts_factory,
                            comments_factory,
                            attachments_factory):
        
        
        posts = await posts_factory(users=[authenticated_user["user"]])
        post = posts[0]
        
        # создаем комментарий с одним медиафайлом
        attachments = await attachments_factory(user=authenticated_user["user"], 
                                         count=1,
                                         filename="testfile.png")
        
        attachments_id = [str(attachments[0].id)]
        
        comments = await comments_factory(users=[authenticated_user["user"]], 
                                          post=post, count=1,
                                          attachments=attachments)
        
        # добавим новый файл
        attachments_new = await attachments_factory(user=authenticated_user["user"], 
                                         count=1,
                                         filename="newtestfile.png")
        attachments_id.append(str(attachments_new[0].id))
        
        response = await async_client.patch(f"/comments/{comments[0].id}", 
                        json={"files_id": attachments_id},
                        headers={"Authorization": f"Bearer {authenticated_user["access_token"]}"})
        
        assert response.status_code == 200
        updated_comment = response.json()
        assert len(updated_comment["attachments"]) == 2
        
        # удалим старый файл
        attachments_id.remove(attachments_id[0])
        response = await async_client.patch(f"/comments/{comments[0].id}", 
                        json={"files_id": attachments_id},
                        headers={"Authorization": f"Bearer {authenticated_user["access_token"]}"})
        
        assert response.status_code == 200
        updated_comment = response.json()
        assert len(updated_comment["attachments"]) == 1
        