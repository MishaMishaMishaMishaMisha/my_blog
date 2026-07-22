from httpx import AsyncClient
import pytest
import asyncio


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
                                      user_json):
        
        # register user and admin
        user = user_json.copy()
        admin = user_json.copy()
        user["username"] = "randomusername"
        user["email"] = "randommefe324@gmail.com"
        admin["role"] = "admin"
        
        response_user = await async_client.post("/users/register", json=user)
        response_admin = await async_client.post("/users/register", json=admin)
        assert response_user.status_code == 200
        assert response_admin.status_code == 200
        
        # login and save tokens
        response_user = await async_client.post("/auth/login", data={"username": user["email"],
                                                                     "password": user["password"]})
        access_token_user = response_user.json().get("access_token", None)
        
        response_admin = await async_client.post("/auth/login", data={"username": admin["email"],
                                                                      "password": admin["password"]})
        access_token_admin = response_admin.json().get("access_token", None)
        
        # try to get security page
        response_user = await async_client.get("/users/securitypage", 
                                               headers={"Authorization": f"Bearer {access_token_user}"})
        assert response_user.status_code == 403
        
        response_admin = await async_client.get("/users/securitypage", 
                                                headers={"Authorization": f"Bearer {access_token_admin}"})
        assert response_admin.status_code == 200
        
        # try to get page with role admin but with incorrect token
        response = await async_client.get("/users/securitypage", 
                                          headers={"Authorization": f"Bearer {12345}"})
        assert response.status_code == 401