import pytest
from source.core.security import create_jwt_token, decode_token
from source.core.security import create_access_token, create_refresh_token, RoleEnum, TokenTypeEnum
from datetime import timedelta
import jwt
from uuid import uuid4




class TestToken:
    
    @pytest.mark.parametrize(
        "data, keys",
        [
            ({"id": 999}, ["id"]),
            ({"x": 20.5, "value": 0}, ["x", "value"]),
            ({"name": "qwerty", "numbers": [1,2,3]}, ["name", "numbers"]),
            ({}, [])
        ]
    )
    def test_create_and_decode_token(self, data, keys, time=timedelta(minutes=10)):
        token = create_jwt_token(data, time)
        payload = decode_token(token)
        
        assert payload is not None
        assert "exp" in payload
        for key in keys:
            assert payload.get(key) == data.get(key)
        

    @pytest.mark.parametrize(
        "time, result",
        [
            (timedelta(minutes=1), True),
            (timedelta(minutes=-1), False)
        ]
    )
    def test_expire_token(self, time, result):
        data = {"param": 100}
        token = create_jwt_token(data, time)
        payload = decode_token(token)
        
        assert isinstance(payload, dict) == result
        
    def test_decode_invalid_token(self):
        assert decode_token("random-invalid-token") is None
        
        payload = {"sub": "123"}
        bad_token = jwt.encode(payload, "Wrong secret key", algorithm="HS256")
        assert decode_token(bad_token) is None
        
    def test_access_and_refresh_token(self):
        user_id = uuid4()
        
        # access
        access_token = create_access_token(user_id, role=RoleEnum.USER)
        access_payload = decode_token(access_token)
        assert access_payload["sub"] == str(user_id)
        assert access_payload["type"] == TokenTypeEnum.ACCESS
        
        # refresh
        refresh_token = create_refresh_token(user_id)
        refresh_payload = decode_token(refresh_token)
        assert refresh_payload["sub"] == str(user_id)
        assert refresh_payload["type"] == TokenTypeEnum.REFRESH

