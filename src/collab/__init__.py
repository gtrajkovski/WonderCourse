"""Collaboration and role-based access control module.

Provides Role and Collaborator models, permission definitions,
invitation management, and helper functions for checking user permissions on courses.
"""

from src.collab.permissions import (
    PERMISSIONS,
    ROLE_TEMPLATES,
    has_permission,
    get_user_permissions,
    get_user_role,
    seed_permissions,
)
from src.collab.models import Role, Collaborator
from src.collab.invitations import (
    Invitation,
    generate_invitation_token,
    validate_invitation_token,
    accept_invitation,
)
from src.collab.decorators import (
    require_permission,
    require_any_permission,
    require_collaborator,
    ensure_owner_collaborator,
)

__all__ = [
    "Role",
    "Collaborator",
    "PERMISSIONS",
    "ROLE_TEMPLATES",
    "has_permission",
    "get_user_permissions",
    "get_user_role",
    "seed_permissions",
    "Invitation",
    "generate_invitation_token",
    "validate_invitation_token",
    "accept_invitation",
    "require_permission",
    "require_any_permission",
    "require_collaborator",
    "ensure_owner_collaborator",
]
