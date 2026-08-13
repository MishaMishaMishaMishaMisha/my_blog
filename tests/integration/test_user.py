from source.models.user import UserModel
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient
from sqlalchemy import select, text, delete
from uuid import UUID
import pytest
from source.core.security import hash_password, verify_password


@pytest.mark.asyncio(loop_scope="session")
class TestUser:

    @pytest.mark.parametrize(
        "user_data, respnonse_status_code",
        [
            (["username123", "userpochta@gmail.com", "secretpassword123"], 200),
            (["username123", "newpochta@gmail.com", "secretpassword123"], 400),
            (["newusername", "userpochta@gmail.com", "secretpassword123"], 400),
            (["username345", "userpochta2@gmail.com", "secretpassword345"], 200),
            (["username123", "userpochta1@gmail.com", "secretpassword123"], 400),
            (["q", "userpochta2@gmail.com", "secretpassword123"], 422),
            (["username567", "userpochgmail.com", "secretpassword123"], 422),
            (["username789", "userpochta5@gmail.com", "w"], 422),
            (["", "userpochta1@gmail.com", "secretpassword123"], 422),
            (["username432", "userpochta8@gmail.com", ""], 422),
        ]
    )
    async def test_register_user(self, 
                                db_session: AsyncSession, 
                                async_client: AsyncClient, 
                                user_data, respnonse_status_code,
                                mock_email_service):
        
        keys = ["username", "email", "password"]
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

    async def test_get_user_profile(self,
                            one_user,
                            async_client: AsyncClient):
        
        
        response = await async_client.get(f"/users/{one_user.username}")
        assert response.status_code == 200
        user_json = response.json()
        
        assert user_json["username"] == one_user.username
        assert user_json["is_verified"] == False
        assert user_json["posts_count"] == 0
        assert user_json["comments_count"] == 0
        assert user_json.get("created_at", None) != None
        assert user_json.get("last_seen", None) != None  
        
        # get user with wrong username
        response = await async_client.get(f"/users/notexistinguser1234")
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
                               authenticated_user,
                               db_session: AsyncSession,
                               async_client: AsyncClient):
        
        response = await async_client.delete(
                    "users/me",
                    headers={"Authorization": f"Bearer {authenticated_user["access_token"]}"})
        assert response.status_code == 200
        
        res = await db_session.execute(
                    select(UserModel).where(UserModel.id==authenticated_user["user"].id))
        deleted_user = res.scalar_one_or_none()
        assert deleted_user is None
        
    async def test_update_username(self,
                               users_factory,
                               authenticated_user,
                               async_client: AsyncClient):
        
        # пользователь с указанным никнеймом
        existing_usernme = "randomusername123"
        other_user = await users_factory(count=1, username=existing_usernme)
        
        data = {"username": "newnickname"}
        
        response = await async_client.patch(
                        "/users/me", 
                        json=data,
                        headers={"Authorization": f"Bearer {authenticated_user["access_token"]}"})
        
        assert response.status_code == 200
        updated_user = response.json()
        assert updated_user["username"] == "newnickname"
        
        # смена имени на уже сущестующее
        data["username"] = existing_usernme
        response = await async_client.patch(
                        "/users/me", 
                        json=data,
                        headers={"Authorization": f"Bearer {authenticated_user["access_token"]}"})
        
        assert response.status_code == 400
        

    async def test_update_email(self,
                               users_factory,
                               authenticated_users,
                               async_client: AsyncClient):
        
        # пользователь с указанной почтой
        existing_email = "randomemail3123213@gmail.com"
        other_user = await users_factory(count=1, email=existing_email)
        
        # тестируемый пользователь
        password = "12345678"
        hash = hash_password(password)
        user = (await authenticated_users(count=1, password_hash=hash))[0]
        
        data = {"confirm_password": password, "new_email": "newemail321@gmail.com"}
        
        response = await async_client.patch(
                        "/users/me/email", 
                        json=data,
                        headers={"Authorization": f"Bearer {user["access_token"]}"})
        
        assert response.status_code == 200
        
        # смена почты на уже сущестующее
        data["new_email"] = existing_email
        response = await async_client.patch(
                        "/users/me/email", 
                        json=data,
                        headers={"Authorization": f"Bearer {user["access_token"]}"})
        
        assert response.status_code == 400
    
    async def test_update_password(self,
                               authenticated_users,
                               db_session: AsyncSession, 
                               async_client: AsyncClient):
    

        password = "12345678"
        hash = hash_password(password)
        new_password = "qwerty12345"
        new_hash = hash_password(new_password)
        
        user = (await authenticated_users(count=1, password_hash=hash))[0]
        
        data = {"current_password": password, "new_password": new_password}
        
        response = await async_client.patch(
                        "/users/me/password", 
                        json=data,
                        headers={"Authorization": f"Bearer {user["access_token"]}"})
        
        assert response.status_code == 200
        
        # проверяем что пароль поменялся
        response = await async_client.post("/auth/login", data={"username": user["user"].username,
                                                                "password": new_password})
        assert response.status_code == 200
        
        # смена пароля с указанием неверного текущего
        data["current_password"] = "ghi45oyt94ogh48oth4goh"
        response = await async_client.patch(
                        "/users/me/password", 
                        json=data,
                        headers={"Authorization": f"Bearer {user["access_token"]}"})
        
        assert response.status_code == 401

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
            
    async def test_get_protected_page(self, 
                                      async_client: AsyncClient, 
                                      user_json):
        
        # register
        response = await async_client.post("/users/register", json=user_json)
        assert response.status_code == 200
        
        # try to get page without authenticate
        response = await async_client.get("/users/me")
        assert response.status_code == 401
        
        # try to get page with incorrect token
        response = await async_client.get("/users/me", headers={"Authorization": "Bearer 12345"})
        assert response.status_code == 401
        
        # login and save token
        response = await async_client.post("/auth/login", data={"username": user_json["email"],
                                                                "password": user_json["password"]})
        access_token = response.json().get("access_token", None)
        
        response = await async_client.get("/users/me", headers={"Authorization": f"Bearer {access_token}"})
        assert response.status_code == 200
        
    # client must have role admin to get page
    async def test_get_security_page(self, 
                                      async_client: AsyncClient,
                                      authenticated_admin,
                                      authenticated_user):
        
        access_token_user = authenticated_user["access_token"]
        access_token_admin = authenticated_admin["access_token"]
        
        # try to get security page
        response_user = await async_client.get("/users/securitypage", 
                                               headers={"Authorization": f"Bearer {access_token_user}"})
        assert response_user.status_code == 403
        
        response_admin = await async_client.get("/users/securitypage", 
                                                headers={"Authorization": f"Bearer {access_token_admin}"})
        assert response_admin.status_code == 200
        
        # try to get page with incorrect token
        response = await async_client.get("/users/securitypage", 
                                          headers={"Authorization": f"Bearer {12345}"})
        assert response.status_code == 401
    
    
    
    # get_user_posts in test_post.py
            
            
            