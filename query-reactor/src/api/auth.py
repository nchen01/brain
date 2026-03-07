"""Authentication and authorization for QueryReactor API."""

from typing import Optional, Dict, Any
from uuid import UUID, uuid4
import time
import jwt
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

from ..config.loader import config_loader

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer(auto_error=False)


class User:
    """User model for authentication."""
    
    def __init__(self, user_id: UUID, username: str, roles: list = None):
        self.user_id = user_id
        self.username = username
        self.roles = roles or ["user"]
        self.created_at = int(time.time())
    
    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        return role in self.roles
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "user_id": str(self.user_id),
            "username": self.username,
            "roles": self.roles,
            "created_at": self.created_at
        }


class AuthManager:
    """Manages authentication and authorization."""
    
    def __init__(self):
        self.secret_key = config_loader.get_env("SECRET_KEY", "dev-secret-key")
        self.algorithm = "HS256"
        self.token_expire_hours = 24
        
        # In-memory user store for V1.0 (use database in production)
        self.users: Dict[str, User] = {}
        self._create_default_users()
    
    def _create_default_users(self) -> None:
        """Create default users for development."""
        # Create a default user for testing
        default_user = User(
            user_id=uuid4(),
            username="default_user",
            roles=["user"]
        )
        self.users["default_user"] = default_user
        
        # Create an admin user
        admin_user = User(
            user_id=uuid4(),
            username="admin",
            roles=["user", "admin"]
        )
        self.users["admin"] = admin_user
    
    def create_token(self, user: User) -> str:
        """Create JWT token for user."""
        payload = {
            "user_id": str(user.user_id),
            "username": user.username,
            "roles": user.roles,
            "exp": int(time.time()) + (self.token_expire_hours * 3600),
            "iat": int(time.time())
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Optional[User]:
        """Verify JWT token and return user."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            user_id = UUID(payload["user_id"])
            username = payload["username"]
            roles = payload.get("roles", ["user"])
            
            # In production, you'd fetch user from database
            # For V1.0, create user from token payload
            return User(user_id=user_id, username=username, roles=roles)
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        return self.users.get(username)
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user with username/password."""
        # V1.0: Simple authentication (use proper password hashing in production)
        user = self.get_user_by_username(username)
        
        if user and password == "password":  # Placeholder password check
            return user
        
        return None


# Global auth manager
auth_manager = AuthManager()


async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[User]:
    """Get current authenticated user from token."""
    
    # For V1.0, authentication is optional
    # In production, you might want to make it required
    
    if not credentials:
        # Return anonymous user for development
        return User(
            user_id=uuid4(),
            username="anonymous",
            roles=["user"]
        )
    
    user = auth_manager.verify_token(credentials.credentials)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user (required authentication)."""
    
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    return current_user


def require_role(required_role: str):
    """Decorator to require specific role."""
    
    def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if not current_user.has_role(required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required"
            )
        return current_user
    
    return role_checker


# Convenience functions for common roles
require_admin = require_role("admin")
require_user = require_role("user")


class RateLimiter:
    """Simple rate limiter for API endpoints."""
    
    def __init__(self, max_requests: int = 100, window_minutes: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_minutes * 60
        self.requests: Dict[str, list] = {}
    
    def is_allowed(self, identifier: str) -> bool:
        """Check if request is allowed for identifier."""
        current_time = time.time()
        
        # Clean old requests
        if identifier in self.requests:
            self.requests[identifier] = [
                req_time for req_time in self.requests[identifier]
                if current_time - req_time < self.window_seconds
            ]
        else:
            self.requests[identifier] = []
        
        # Check limit
        if len(self.requests[identifier]) >= self.max_requests:
            return False
        
        # Add current request
        self.requests[identifier].append(current_time)
        return True
    
    def get_remaining_requests(self, identifier: str) -> int:
        """Get remaining requests for identifier."""
        current_count = len(self.requests.get(identifier, []))
        return max(0, self.max_requests - current_count)


# Global rate limiter
rate_limiter = RateLimiter(max_requests=100, window_minutes=60)


async def check_rate_limit(current_user: User = Depends(get_current_user)) -> None:
    """Check rate limit for current user."""
    
    identifier = str(current_user.user_id) if current_user else "anonymous"
    
    if not rate_limiter.is_allowed(identifier):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later."
        )