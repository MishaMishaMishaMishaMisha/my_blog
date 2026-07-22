from source.models.user import UserModel
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient
from sqlalchemy import select, text, delete
from uuid import UUID
import pytest


@pytest.mark.asyncio(loop_scope="session")
class TestUser:

    @pytest.mark.parametrize(
        "user_data, respnonse_status_code",
        [
            (["username123", "userpochta@gmail.com", "secretpassword123", "user", "true"], 200),
            (["username123", "newpochta@gmail.com", "secretpassword123", "user", "true"], 400),
            (["newusername", "userpochta@gmail.com", "secretpassword123", "user", "true"], 400),
            (["username345", "userpochta2@gmail.com", "secretpassword345", "admin", "true"], 200),
            (["username123", "userpochta1@gmail.com", "secretpassword123", "god", "true"], 422),
            (["q", "userpochta2@gmail.com", "secretpassword123", "user", "true"], 422),
            (["username567", "userpochgmail.com", "secretpassword123", "user", "true"], 422),
            (["username789", "userpochta5@gmail.com", "w", "user", "true"], 422),
            (["", "userpochta1@gmail.com", "secretpassword123", "user", "true"], 422),
            (["username432", "userpochta8@gmail.com", "", "user", "true"], 422),
        ]
    )
    async def test_register_user(self, 
                                db_session: AsyncSession, 
                                async_client: AsyncClient, 
                                user_data, respnonse_status_code,
                                mock_email_service):
        
        keys = ["username", "email", "password", "role", "is_active"]
        user = dict(zip(keys, user_data))
        
        response = await async_client.post("/users/register", json=user)

        assert response.status_code == respnonse_status_code
        
        if respnonse_status_code == 200:
            # проверяем что пользователь добавлен в базу
            data = response.json()
            res = await db_session.execute(select(UserModel).where(UserModel.id==data["id"]))
            user_model = res.scalar_one()
            assert user_model is not None
            
            # Проверяем, что метод sendEmail был действительно вызван 1 раз
            assert mock_email_service.call_count == 1

    async def test_get_user(self,
                            one_user,
                            async_client: AsyncClient):
        
        
        response = await async_client.get(f"/users/{one_user.id}")
        assert response.status_code == 200
        user_json = response.json()
        assert one_user.id == UUID(user_json["id"])
        assert one_user.username == user_json["username"]
        assert one_user.email == user_json["email"]
        assert one_user.role == user_json["role"]
        assert one_user.is_active == user_json["is_active"]
        
        # get user with wrong id
        response = await async_client.get(f"/users/{UUID(int=0)}")
        assert response.status_code == 404

    @pytest.mark.parametrize(
        "limit, offset, response_status_code, result_len",
        [
            (None, None, 200, 10),
            (50, None, 200, 50),
            (30, 50, 200, 30),
            (150, None, 422, 1),
        ]
    )
    async def test_get_users(self,
                             limit, offset, response_status_code, result_len,
                             prepared_100_users,
                             db_session: AsyncSession,
                             async_client: AsyncClient):
        
        if not limit and not offset:
            response = await async_client.get("/users/")
        elif limit and offset:
            response = await async_client.get(f"/users/?limit={limit}&offset={offset}")
        elif limit:
            response = await async_client.get(f"/users/?limit={limit}")
        else:
            response = await async_client.get(f"/users/?offset={offset}")

        assert response.status_code == response_status_code
        assert len(response.json()) == result_len
           
    async def test_delete_user(self,
                               one_user,
                               db_session: AsyncSession,
                               async_client: AsyncClient):
        
        response = await async_client.delete(f"/users/{one_user.id}")
        assert response.status_code == 200
        
        res = await db_session.execute(select(UserModel).where(UserModel.id==one_user.id))
        deleted_user = res.scalar_one_or_none()
        assert deleted_user is None
        
        # delete user with wrong id
        response = await async_client.delete(f"/users/{UUID(int=0)}")
        assert response.status_code == 404
        
    @pytest.mark.parametrize(
        "patch_user_data, updated_keys",
        [
            ({"username": "newusername"}, 
             ["username"]),
            ({"password": "newsecretpassword"}, 
             ["password"]),
            ({"email": "newmail@gmail.com"}, 
             ["email"]),
            ({"username": "newusernameagain", "password": "rekgjlntgkblrn"}, 
             ["username", "password"]),
            ({"username": "hkvblnbgb", "password": "ekjgvnlgreg", "email": "mymail@gmail.com"},
             ["username", "password", "email"]),
            ({}, [])
        ]
    )
    async def test_update_user(self,
                               patch_user_data,
                               updated_keys,
                               prepared_1_user,
                               async_client: AsyncClient):
        
        
        response = await async_client.patch(f"/users/{prepared_1_user.id}", json=patch_user_data)
        assert response.status_code == 200
        updated_user = response.json()
        for key in updated_keys:
            if key != "password": # пароль не возвращается в ответе
                assert patch_user_data[key] == updated_user[key]
        
        # update user with wrong id
        response = await async_client.patch(f"/users/{UUID(int=0)}", json={})
        assert response.status_code == 404

    @pytest.mark.parametrize(
        "query_params, expected_status, result_len", 
        [
            ("", 422, None),
            ("?username=qwe", 422, None),
            ("?name=", 422, None),
            ("?name=q", 422, None),
            ("?name=qwertyuiopadfghjklqwe", 422, None),
            ("?name=qwerty", 200, 0),
            ("?name=knight", 200, 1),
            ("?name=hunter", 200, 2),
            ("?name=hunter", 200, 2),
            ("?name=HUNTER", 200, 2),
            ("?name=dark knight", 200, 1),
            ("?name=_", 422, None),
            ("?name=   knight    ", 200, 0),
        ])
    async def test_find_user(self,
                             query_params,
                             expected_status,
                             result_len,
                             prepared_3_users,
                             async_client: AsyncClient):
        
        response = await async_client.get(f"/users/search{query_params}")
        assert response.status_code == expected_status
        if result_len:
            assert len(response.json()) == result_len