"""
Unit tests for security utilities.
"""

import pytest
from datetime import timedelta

from app.core.security import (
    create_access_token,
    create_refresh_token,
    create_token_pair,
    decode_token,
    get_password_hash,
    verify_password,
    verify_token,
)


class TestPasswordHashing:
    def test_password_hashing(self):
        password = "test_password_123"
        hashed = get_password_hash(password)
        assert hashed != password
        assert verify_password(password, hashed) is True
        assert verify_password("wrong_password", hashed) is False


class TestJWTTokens:
    def test_access_token_creation_and_verification(self):
        data = {"sub": "user-123", "email": "test@example.com"}
        token = create_access_token(data)
        assert token is not None

        decoded = decode_token(token)
        assert decoded is not None
        assert decoded["sub"] == "user-123"
        assert decoded["email"] == "test@example.com"
        assert decoded["type"] == "access"

    def test_refresh_token_creation(self):
        data = {"sub": "user-123"}
        token = create_refresh_token(data)
        assert token is not None

        decoded = decode_token(token)
        assert decoded["type"] == "refresh"

    def test_token_pair_creation(self):
        data = {"sub": "user-123", "email": "test@example.com"}
        access, refresh = create_token_pair(data)
        assert access is not None
        assert refresh is not None
        assert access != refresh

    def test_token_verification(self):
        data = {"sub": "user-123"}
        access = create_access_token(data)
        refresh = create_refresh_token(data)

        assert verify_token(access, "access") is not None
        assert verify_token(refresh, "refresh") is not None
        assert verify_token(access, "refresh") is None  # Wrong type
        assert verify_token("invalid_token", "access") is None

    def test_expired_token(self):
        data = {"sub": "user-123"}
        # Create token that expires immediately
        token = create_access_token(data, expires_delta=timedelta(seconds=-1))
        decoded = decode_token(token)
        assert decoded is None  # Should fail verification due to expiry
