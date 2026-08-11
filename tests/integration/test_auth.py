from httpx import AsyncClient
import pytest
import asyncio

from sqlalchemy import select

from source.models.user import UserModel
from source.repositories.user import UserRepository
from source.cache.redis_backend import redis_backend
from source.services.verify_user import VerifyUserService


@pytest.mark.asyncio(loop_scope="session")
class TestAuth:

    async def test_login_user(self, 
                              async_client: AsyncClient, 
                              user_json):
        
        # register
        response = await async_client.post("/users/register", json=user_json)
        assert response.status_code == 200
        
        # login using username
        response = await async_client.post("/auth/login", data={"username": user_json["username"],
                                                                "password": user_json["password"]})
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("access_token", None) is not None
        assert response.cookies.get("refresh_token", None) is not None
        
        # login using email
        response = await async_client.post("/auth/login", data={"username": user_json["email"],
                                                                "password": user_json["password"]})
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("access_token", None) is not None
        assert response.cookies.get("refresh_token", None) is not None
        
        # wrong login
        response = await async_client.post("/auth/login", data={"username": "aaaaaaaaaaaaaa",
                                                                "password": user_json["password"]})
        assert response.status_code == 401
        data = response.json()
        assert data.get("access_token", None) is None
        assert response.cookies.get("refresh_token", None) is None
        
        # wrong password
        response = await async_client.post("/auth/login", data={"username": user_json["username"],
                                                                "password": "qqqqqqqqqqqqq"})
        assert response.status_code == 401
        data = response.json()
        assert data.get("access_token", None) is None
        assert response.cookies.get("refresh_token", None) is None
    
    async def test_logout_user(self, 
                               async_client: AsyncClient, 
                               authenticated_user):
        
        refresh_token = authenticated_user["refresh_token"]
        assert refresh_token is not None
        
        response = await async_client.post("/auth/logout",
                                          cookies={"refresh_token": refresh_token})
        
        assert response.status_code == 200
        assert response.cookies.get("refresh_token", None) is None
        
        # logout without refresh token
        response = await async_client.post("/auth/logout")
        assert response.status_code == 200
        assert response.cookies.get("refresh_token", None) is None
        
    async def test_update_refresh_token(self, 
                                        async_client: AsyncClient, 
                                        user_json):
        
        # register
        response = await async_client.post("/users/register", json=user_json)
        assert response.status_code == 200
        
        # login and save tokens
        response = await async_client.post("/auth/login", data={"username": user_json["email"],
                                                                "password": user_json["password"]})
        
        access_token = response.json().get("access_token", None)
        refresh_token = response.cookies.get("refresh_token", None)
        assert access_token is not None
        assert refresh_token is not None
        
        # Ждем 1 секунду, чтобы сменился timestamp для JWT
        await asyncio.sleep(1)
        
        # refresh tokens
        response = await async_client.post("/auth/refresh", cookies={"refresh_token": refresh_token})
        assert response.status_code == 200
        data = response.json()
        assert data.get("access_token", None) is not None
        assert response.cookies.get("refresh_token", None) is not None
        assert data.get("access_token", None) != access_token
        assert response.cookies.get("refresh_token", None) != refresh_token
        
    async def test_resend_verify_email(self,
                                       async_client: AsyncClient,
                                       authenticated_notVerified_user,
                                       authenticated_user,
                                       mock_email_service): 

        response = await async_client.post(
                "/auth/resend-verification-email",
                headers={"Authorization": f"Bearer {authenticated_notVerified_user["access_token"]}"})
        assert response.status_code == 200
        # должен быть вызван сервис по отвравке письма
        assert mock_email_service.call_count == 1
        
        response = await async_client.post(
                "/auth/resend-verification-email",
                headers={"Authorization": f"Bearer {authenticated_user["access_token"]}"})
        assert response.status_code == 200
        # письмо не должно быть отправлено
        assert mock_email_service.call_count == 1

    async def test_verify_email(self,
                                       async_client: AsyncClient,
                                       db_session,
                                       authenticated_notVerified_user,
                                       mock_email_service): 
        
        user_id = authenticated_notVerified_user["user"].id
        access_token = authenticated_notVerified_user["access_token"]

        verify_service = VerifyUserService(UserRepository(db_session), redis_backend)
        
        verify_link = await verify_service.create_verify_link(user_id)        
        
        token = verify_link.split("=")[1]
        response = await async_client.get("/auth/verify-email?token=" + token)
        assert response.status_code == 200
        
        # check user verify
        response = await async_client.post(
                "/auth/resend-verification-email",
                headers={"Authorization": f"Bearer {access_token}"})
        assert response.status_code == 200
        # письмо не должно быть отправлено
        assert mock_email_service.call_count == 0
        assert response.json()["message"] == "your account already verified"
        
        # try to verify again
        response = await async_client.get("/auth/verify-email?token=" + token)
        assert response.status_code == 401

    async def test_forgot_password_email(self,
                                       async_client: AsyncClient,
                                       authenticated_user,
                                       mock_email_service): 

        email = authenticated_user["user"].email

        response = await async_client.post("/auth/forgot-password", json={"user_email": email})
        assert response.status_code == 200
        # должен быть вызван сервис по отвравке письма
        assert mock_email_service.call_count == 1
        
        # повторный вызов
        response = await async_client.post("/auth/forgot-password", json={"user_email": email})
        assert response.status_code == 400
        # должен быть вызван сервис по отвравке письма
        assert mock_email_service.call_count == 1

    async def test_reset_password(self,
                                       async_client: AsyncClient,
                                       db_session,
                                       authenticated_user,
                                       mock_email_service): 
        
        user_id = authenticated_user["user"].id
        username = authenticated_user["user"].username
        access_token = authenticated_user["access_token"]
        
        new_password = "qwerty12345"

        verify_service = VerifyUserService(UserRepository(db_session), redis_backend)
        
        resetting_link = await verify_service.create_resetPassword_link(user_id)        
        
        token = resetting_link.split("=")[1]
        response = await async_client.post("/auth/reset-password", 
                                          json={"token": token, "new_password": new_password})
        assert response.status_code == 200
        
        # try to reset again
        response = await async_client.post("/auth/reset-password", 
                                          json={"token": token, "new_password": "fblnkgbegkgbgn"})
        assert response.status_code == 401
        
        # check new password
        response = await async_client.post("/auth/login", data={"username": username,
                                                                "password": new_password})
        assert response.status_code == 200
        

