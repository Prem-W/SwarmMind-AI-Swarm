"""
SwarmMind Custom Exceptions

Defines all application-specific exceptions with proper HTTP status codes
and error messages for consistent API error handling.
"""

from fastapi import HTTPException, status


class SwarmMindException(Exception):
    """Base exception for SwarmMind."""

    def __init__(self, message: str = "An error occurred", status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class AgentNotFoundException(SwarmMindException):
    """Raised when an agent is not found."""

    def __init__(self, agent_id: str = None):
        super().__init__(
            message=f"Agent '{agent_id}' not found" if agent_id else "Agent not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class TaskNotFoundException(SwarmMindException):
    """Raised when a task is not found."""

    def __init__(self, task_id: str = None):
        super().__init__(
            message=f"Task '{task_id}' not found" if task_id else "Task not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class WorkflowNotFoundException(SwarmMindException):
    """Raised when a workflow is not found."""

    def __init__(self, workflow_id: str = None):
        super().__init__(
            message=f"Workflow '{workflow_id}' not found" if workflow_id else "Workflow not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class AgentExecutionException(SwarmMindException):
    """Raised when an agent fails to execute a task."""

    def __init__(self, agent_id: str = None, task_id: str = None, detail: str = None):
        message = "Agent execution failed"
        if agent_id and task_id:
            message = f"Agent '{agent_id}' failed on task '{task_id}'"
        if detail:
            message += f": {detail}"
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class LLMProviderException(SwarmMindException):
    """Raised when LLM provider fails."""

    def __init__(self, provider: str = None, detail: str = None):
        message = f"LLM provider '{provider}' error" if provider else "LLM provider error"
        if detail:
            message += f": {detail}"
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


class AuthenticationException(SwarmMindException):
    """Raised for authentication failures."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class AuthorizationException(SwarmMindException):
    """Raised for authorization failures."""

    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
        )


class ValidationException(SwarmMindException):
    """Raised for validation errors."""

    def __init__(self, message: str = "Validation failed", errors: dict = None):
        self.errors = errors or {}
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


class SwarmOrchestrationException(SwarmMindException):
    """Raised when swarm orchestration fails."""

    def __init__(self, message: str = "Swarm orchestration failed"):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


def handle_swarm_exception(exc: SwarmMindException) -> HTTPException:
    """Convert SwarmMind exceptions to FastAPI HTTPException."""
    return HTTPException(
        status_code=exc.status_code,
        detail={"message": exc.message, "errors": getattr(exc, "errors", {})},
    )
