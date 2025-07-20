#!/usr/bin/env python3
"""
Authentication Service - JWT Token Management and User Authorization
Enhanced version that supports both WebSocket connections and existing functionality
"""

import jwt
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass
from flask import Flask

try:
    from ..models.mission_control_project import MissionControlProject
    from ..models.base import db
except ImportError:
    try:
        from models.mission_control_project import MissionControlProject
        from models.base import db
    except ImportError:
        # For testing without database models
        MissionControlProject = None
        db = None


logger = logging.getLogger(__name__)


@dataclass
class UserPermissions:
    """Enhanced user permissions with backward compatibility"""
    user_id: str
    username: Optional[str] = None
    email: Optional[str] = None
    project_ids: Set[str] = None
    roles: Set[str] = None
    is_admin: bool = False
    expires_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.project_ids is None:
            self.project_ids = set()
        if self.roles is None:
            self.roles = set()
    
    def has_project_access(self, project_id: str) -> bool:
        """Check if user has access to a specific project"""
        return self.is_admin or project_id in self.project_ids
    
    def has_role(self, role: str) -> bool:
        """Check if user has a specific role"""
        return self.is_admin or role in self.roles
    
    def is_expired(self) -> bool:
        """Check if permissions are expired"""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    # Backward compatibility properties
    @property
    def projects(self) -> Set[str]:
        """Backward compatibility for existing code"""
        return self.project_ids


class AuthService:
    """Enhanced authentication service with WebSocket support"""

    def __init__(self, config, secret_key: Optional[str] = None):
        """
        Initialize the AuthService.
        
        Args:
            config: Flask app config object.
            secret_key: Optional secret key to override the one in config.
        """
        # Local import to prevent circular dependency
        try:
            from .distributed_cache import get_distributed_cache
            self.cache = get_distributed_cache()
        except ImportError:
            logger.warning("Distributed cache not available, using in-memory cache")
            self.cache = None

        self.secret_key = secret_key or config.get('SECRET_KEY', 'dev-secret-key')
        self.session_ttl = config.get('SESSION_TTL', 3600)
        
        # In-memory cache fallback for WebSocket functionality
        self._token_cache: Dict[str, UserPermissions] = {}
        self._cache_max_size = 1000
        
        if not self.cache:
            logger.warning("Using in-memory token cache instead of distributed cache")
        
        logger.info(f"AuthService initialized with session TTL: {self.session_ttl}s")

    def generate_token(self, user_id: str, project_ids: List[str] = None, 
                      username: str = None, email: str = None,
                      roles: List[str] = None, is_admin: bool = False, 
                      expires_in_hours: int = None) -> str:
        """Generate a JWT token with user permissions"""
        
        expires_delta = timedelta(hours=expires_in_hours or (self.session_ttl / 3600))
        expires_at = datetime.utcnow() + expires_delta
        
        payload = {
            'user_id': user_id,
            'username': username,
            'email': email,
            'projects': project_ids or [],  # Keep backward compatibility
            'project_ids': project_ids or [],  # New field name
            'roles': roles or [],
            'is_admin': is_admin,
            'exp': expires_at,
            'iat': datetime.utcnow()
        }
        
        try:
            token = jwt.encode(payload, self.secret_key, algorithm='HS256')
            logger.debug(f"Generated token for user {user_id}")
            return token
        except Exception as e:
            logger.error(f"Error generating token: {e}")
            raise

    def decode_token(self, token: str) -> Optional[UserPermissions]:
        """Decode and validate a JWT token, returning user permissions."""
        
        # Check in-memory cache first
        if token in self._token_cache:
            permissions = self._token_cache[token]
            if not permissions.is_expired():
                return permissions
            else:
                del self._token_cache[token]
        
        # Check distributed cache if available
        cached_permissions = None
        if self.cache:
            try:
                cached_permissions = self.cache.get(f"token:{token}")
                if cached_permissions and not cached_permissions.is_expired():
                    self._cache_token(token, cached_permissions)
                    return cached_permissions
                elif cached_permissions:
                    self.cache.delete(f"token:{token}")
            except Exception as e:
                logger.warning(f"Error accessing distributed cache: {e}")

        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            
            # Support both old and new field names
            project_ids = payload.get('project_ids') or payload.get('projects', [])
            
            permissions = UserPermissions(
                user_id=payload['user_id'],
                username=payload.get('username'),
                email=payload.get('email'),
                project_ids=set(project_ids),
                roles=set(payload.get('roles', [])),
                is_admin=payload.get('is_admin', False),
                expires_at=datetime.fromtimestamp(payload['exp'])
            )
            
            if permissions.is_expired():
                logger.warning(f"Expired token received for user {permissions.user_id}")
                return None

            # Cache the permissions
            self._cache_token(token, permissions)
            
            if self.cache:
                try:
                    ttl = (permissions.expires_at - datetime.utcnow()).total_seconds()
                    self.cache.set(f"token:{token}", permissions, ttl=ttl)
                except Exception as e:
                    logger.warning(f"Error caching to distributed cache: {e}")
            
            logger.debug(f"Decoded token for user {permissions.user_id}")
            return permissions
            
        except jwt.ExpiredSignatureError:
            logger.warning("Expired token signature")
            return None
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid token: {e}")
            return None

    def _cache_token(self, token: str, permissions: UserPermissions):
        """Cache token permissions with size limit"""
        if len(self._token_cache) >= self._cache_max_size:
            # Remove oldest entries (simple FIFO)
            oldest_tokens = list(self._token_cache.keys())[:100]
            for old_token in oldest_tokens:
                del self._token_cache[old_token]
        
        self._token_cache[token] = permissions

    def validate_project_access(self, token: str, project_id: str) -> bool:
        """Validate if a token grants access to a specific project."""
        permissions = self.decode_token(token)
        return permissions is not None and permissions.has_project_access(project_id)

    def get_user_projects(self, token: str) -> Set[str]:
        """Get list of projects user has access to"""
        permissions = self.decode_token(token)
        if not permissions:
            return set()
        
        if permissions.is_admin:
            # Admin has access to all projects
            try:
                if MissionControlProject is not None:
                    all_projects = MissionControlProject.query.all()
                    return {project.id for project in all_projects}
                else:
                    # In testing mode, return empty set for admin
                    return set()
            except Exception as e:
                logger.error(f"Failed to get all projects for admin: {e}")
                return set()
        
        return permissions.project_ids

    def refresh_token(self, token: str, extends_hours: int = None) -> Optional[str]:
        """Refresh a token, extending its expiry time."""
        permissions = self.decode_token(token)
        if not permissions:
            return None
        
        self.revoke_token(token)
        
        return self.generate_token(
            user_id=permissions.user_id,
            username=permissions.username,
            email=permissions.email,
            project_ids=list(permissions.project_ids),
            roles=list(permissions.roles),
            is_admin=permissions.is_admin,
            expires_in_hours=extends_hours
        )

    def revoke_token(self, token: str):
        """Revoke a token (remove from cache)"""
        if token in self._token_cache:
            del self._token_cache[token]
        
        if self.cache:
            try:
                self.cache.delete(f"token:{token}")
            except Exception as e:
                logger.warning(f"Error removing token from distributed cache: {e}")
        
        logger.info("Token revoked")

    def create_guest_token(self, project_ids: List[str] = None, 
                          expires_in_hours: int = 1) -> str:
        """Create a guest token with limited access"""
        guest_id = f"guest_{datetime.utcnow().timestamp()}"
        return self.generate_token(
            user_id=guest_id,
            project_ids=project_ids or [],
            roles=['guest'],
            expires_in_hours=expires_in_hours
        )
    
    def create_admin_token(self, user_id: str, username: str = None,
                          expires_in_hours: int = None) -> str:
        """Create an admin token with full access"""
        return self.generate_token(
            user_id=user_id,
            username=username,
            is_admin=True,
            roles=['admin'],
            expires_in_hours=expires_in_hours
        )

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get token cache statistics"""
        return {
            'cached_tokens': len(self._token_cache),
            'cache_max_size': self._cache_max_size,
            'cache_usage_percent': (len(self._token_cache) / self._cache_max_size) * 100,
            'distributed_cache_available': self.cache is not None
        }


# Global auth service instance
_auth_service: Optional[AuthService] = None


def init_auth_service(app: Flask):
    """
    Initialize the global auth service.
    This should be called once during application startup.
    """
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService(app.config)
        logger.info("Auth service initialized.")
    return _auth_service


def get_auth_service() -> Optional[AuthService]:
    """Get the global auth service instance. Must be called after init_auth_service."""
    if _auth_service is None:
        raise RuntimeError("AuthService has not been initialized. Call init_auth_service() in your app factory.")
    return _auth_service


# Convenience functions for WebSocket functionality
def decode_token(token: str) -> Optional[UserPermissions]:
    """Decode a JWT token using the global auth service"""
    return get_auth_service().decode_token(token)


def validate_project_access(token: str, project_id: str) -> bool:
    """Validate project access using the global auth service"""
    return get_auth_service().validate_project_access(token, project_id)


def get_user_projects(token: str) -> Set[str]:
    """Get user projects using the global auth service"""
    return get_auth_service().get_user_projects(token)