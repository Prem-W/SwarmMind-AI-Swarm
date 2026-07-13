"""
Authentication Service

Handles OAuth2 + JWT authentication, user management,
and team-based access control.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.core.exceptions import AuthenticationException, AuthorizationException
from app.core.logging import get_logger
from app.core.security import create_token_pair, get_password_hash, verify_password, verify_token
from app.models.user import Team, TeamMember, TeamRole, User, UserRole

logger = get_logger(__name__)
settings = get_settings()


class AuthService:
    """Authentication and authorization service."""

    @staticmethod
    async def authenticate_user(email: str, password: str) -> Optional[User]:
        """Authenticate a user with email and password."""
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select

            result = await session.execute(
                select(User).where(User.email == email, User.is_active == True)
            )
            user = result.scalar_one_or_none()

            if not user or not user.hashed_password:
                return None

            if not verify_password(password, user.hashed_password):
                return None

            # Update last login
            user.last_login = datetime.now(timezone.utc)
            await session.commit()

            return user

    @staticmethod
    async def create_user(
        email: str,
        password: str,
        full_name: str,
        role: UserRole = UserRole.MEMBER,
    ) -> User:
        """Create a new user."""
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select

            # Check if user exists
            result = await session.execute(select(User).where(User.email == email))
            if result.scalar_one_or_none():
                raise AuthenticationException("Email already registered")

            user = User(
                email=email,
                hashed_password=get_password_hash(password),
                full_name=full_name,
                role=role,
                is_active=True,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

            logger.info("User created", user_id=str(user.id), email=email)
            return user

    @staticmethod
    async def get_user_by_id(user_id: uuid.UUID) -> Optional[User]:
        """Get user by ID."""
        async with AsyncSessionLocal() as session:
            return await session.get(User, user_id)

    @staticmethod
    async def create_team(name: str, slug: str, owner_id: uuid.UUID, description: str = None) -> Team:
        """Create a new team/workspace."""
        async with AsyncSessionLocal() as session:
            team = Team(
                name=name,
                slug=slug,
                description=description,
                is_active=True,
            )
            session.add(team)
            await session.flush()

            # Add owner as team member
            member = TeamMember(
                team_id=team.id,
                user_id=owner_id,
                role=TeamRole.OWNER,
            )
            session.add(member)
            await session.commit()
            await session.refresh(team)

            logger.info("Team created", team_id=str(team.id), name=name, owner=str(owner_id))
            return team

    @staticmethod
    async def add_team_member(
        team_id: uuid.UUID,
        user_id: uuid.UUID,
        role: TeamRole = TeamRole.MEMBER,
        invited_by: uuid.UUID = None,
    ) -> TeamMember:
        """Add a member to a team."""
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select

            # Check if already a member
            result = await session.execute(
                select(TeamMember).where(
                    TeamMember.team_id == team_id,
                    TeamMember.user_id == user_id,
                )
            )
            if result.scalar_one_or_none():
                raise AuthorizationException("User is already a team member")

            member = TeamMember(
                team_id=team_id,
                user_id=user_id,
                role=role,
            )
            session.add(member)
            await session.commit()
            await session.refresh(member)

            logger.info(
                "Team member added",
                team_id=str(team_id),
                user_id=str(user_id),
                role=role.value,
            )
            return member

    @staticmethod
    async def check_team_permission(
        user_id: uuid.UUID,
        team_id: uuid.UUID,
        required_role: TeamRole = TeamRole.MEMBER,
    ) -> bool:
        """Check if a user has the required role in a team."""
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select

            result = await session.execute(
                select(TeamMember).where(
                    TeamMember.team_id == team_id,
                    TeamMember.user_id == user_id,
                )
            )
            membership = result.scalar_one_or_none()

            if not membership:
                return False

            # Role hierarchy
            role_hierarchy = {
                TeamRole.OWNER: 4,
                TeamRole.ADMIN: 3,
                TeamRole.MEMBER: 2,
                TeamRole.VIEWER: 1,
            }

            return role_hierarchy.get(membership.role, 0) >= role_hierarchy.get(required_role, 0)

    @staticmethod
    def create_auth_tokens(user: User) -> dict:
        """Create JWT token pair for a user."""
        user_data = {
            "sub": str(user.id),
            "email": user.email,
            "name": user.full_name,
            "role": user.role.value,
        }
        access_token, refresh_token = create_token_pair(user_data)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.access_token_expire_minutes * 60,
        }

    @staticmethod
    async def get_user_teams(user_id: uuid.UUID):
        """Get all teams a user belongs to."""
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select

            result = await session.execute(
                select(TeamMember, Team)
                .join(Team, TeamMember.team_id == Team.id)
                .where(TeamMember.user_id == user_id, Team.is_active == True)
            )
            memberships = result.all()

            return [
                {
                    "team": {
                        "id": str(m.Team.id),
                        "name": m.Team.name,
                        "slug": m.Team.slug,
                        "description": m.Team.description,
                    },
                    "role": m.TeamMember.role.value,
                    "joined_at": m.TeamMember.joined_at.isoformat() if m.TeamMember.joined_at else None,
                }
                for m in memberships
            ]
