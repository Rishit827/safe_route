from app.auth import get_password_hash, verify_password

def test_password_hash_round_trip():
    hashed = get_password_hash("example-password")
    assert hashed != "example-password"
    assert verify_password("example-password", hashed)
    assert not verify_password("wrong-password", hashed)
