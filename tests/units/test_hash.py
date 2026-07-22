import pytest
from source.core.security import hash_password, verify_password



@pytest.mark.parametrize(
    "password, password2, result",
    [
        ("mypassword", "mypassword", True),
        ("qwerty123", "fdvfbgfb", False),
        ("", "mypassword", False),
        ("gjkdhbvnfdv", "", False),
        ("verysupresecret1625password^34&5^#$%&*^", "verysupresecret1625password^34&5^#$%&*^", True),
    ]
)
def test_hash_and_verify(password, password2, result):
    hash = hash_password(password)
    assert hash != password
    assert verify_password(password2, hash) == result
    