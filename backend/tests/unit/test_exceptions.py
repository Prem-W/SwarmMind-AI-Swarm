"""
Unit tests for custom exceptions.
"""

import pytest
from fastapi import HTTPException, status

from app.core.exceptions import (
    AgentExecutionException,
    AgentNotFoundException,
    AuthenticationException,
    AuthorizationException,
    LLMProviderException,
    SwarmMindException,
    TaskNotFoundException,
    ValidationException,
    handle_swarm_exception,
)


class TestExceptions:
    def test_base_exception(self):
        exc = SwarmMindException("Test error", 500)
        assert exc.message == "Test error"
        assert exc.status_code == 500
        assert str(exc) == "Test error"

    def test_agent_not_found(self):
        exc = AgentNotFoundException("agent-123")
        assert exc.status_code == status.HTTP_404_NOT_FOUND
        assert "agent-123" in exc.message

    def test_task_not_found(self):
        exc = TaskNotFoundException("task-456")
        assert exc.status_code == status.HTTP_404_NOT_FOUND
        assert "task-456" in exc.message

    def test_agent_execution_error(self):
        exc = AgentExecutionException("agent-1", "task-1", "Timeout")
        assert exc.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "agent-1" in exc.message
        assert "task-1" in exc.message
        assert "Timeout" in exc.message

    def test_llm_provider_error(self):
        exc = LLMProviderException("openai", "Rate limited")
        assert exc.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "openai" in exc.message
        assert "Rate limited" in exc.message

    def test_authentication_error(self):
        exc = AuthenticationException("Invalid credentials")
        assert exc.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authorization_error(self):
        exc = AuthorizationException("Forbidden")
        assert exc.status_code == status.HTTP_403_FORBIDDEN

    def test_validation_error(self):
        exc = ValidationException("Invalid data", {"field": "required"})
        assert exc.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert exc.errors == {"field": "required"}

    def test_exception_handler(self):
        exc = AgentNotFoundException("test-agent")
        http_exc = handle_swarm_exception(exc)
        assert isinstance(http_exc, HTTPException)
        assert http_exc.status_code == status.HTTP_404_NOT_FOUND
