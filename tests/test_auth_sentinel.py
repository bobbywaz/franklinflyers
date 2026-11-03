import pytest
from app.main import get_password_hash, verify_password

def test_password_hash_format():
    hash_str = get_password_hash("test_password")
    assert hash_str.startswith("pbkdf2:sha256:100000$")
    assert len(hash_str.split("$")) == 3

def test_verify_password_correct():
    hash_str = get_password_hash("test_password")
    assert verify_password("test_password", hash_str) is True

def test_verify_password_incorrect():
    hash_str = get_password_hash("test_password")
    assert verify_password("wrong_password", hash_str) is False

def test_verify_password_legacy_plaintext():
    assert verify_password("plaintext", "plaintext") is True
    assert verify_password("wrong", "plaintext") is False
