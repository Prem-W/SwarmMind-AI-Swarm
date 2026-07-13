"""
Integration tests for API endpoints.
"""

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_check(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "version" in data
            assert "environment" in data


class TestRootEndpoint:
    @pytest.mark.asyncio
    async def test_root(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/")
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "SwarmMind"
            assert "documentation" in data


class TestAuthEndpoints:
    @pytest.mark.asyncio
    async def test_login_without_user(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={"email": "nonexistent@test.com", "password": "wrong"},
            )
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_register_invalid_email(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/register",
                json={"email": "invalid-email", "password": "123", "full_name": "Test"},
            )
            assert response.status_code == 422
