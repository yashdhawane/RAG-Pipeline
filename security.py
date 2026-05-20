"""
security.py
-----------
Role-Based Access Control (RBAC) engine.

Responsibilities:
  - Load user-role mappings and access policies
  - Determine what a user is allowed to see
  - Build ChromaDB metadata filters for retrieval
  - Validate access decisions before LLM is ever called
"""

import json
import os
from typing import Optional


# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────

USER_ROLE_FILE = os.path.join("data", "user_roles", "user_role_mapping.json")
ACCESS_POLICY_FILE = os.path.join("data", "access_policies", "access_policies.json")
DEPT_PERMISSIONS_FILE = os.path.join("data", "access_policies", "department_permissions.json")


# ─────────────────────────────────────────────
# Loaders
# ─────────────────────────────────────────────

def _load_json(path: str) -> dict:
    """Load a JSON file; raise a clear error if missing."""
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Required file not found: {path}\n"
            "Run `python dataset_generator.py` first."
        )
    with open(path) as f:
        return json.load(f)


def load_user_roles() -> dict[str, str]:
    """Return {username: role} mapping."""
    return _load_json(USER_ROLE_FILE)


def load_access_policies() -> dict[str, list[str]]:
    """Return {role: [allowed_tags]} mapping."""
    return _load_json(ACCESS_POLICY_FILE)


def load_department_permissions() -> dict[str, dict]:
    """Return fine-grained per-role permission details."""
    return _load_json(DEPT_PERMISSIONS_FILE)


# ─────────────────────────────────────────────
# Role Resolution
# ─────────────────────────────────────────────

def get_user_role(username: str) -> Optional[str]:
    """
    Look up a user's role.
    Returns None if the user is not found (access denied by default).
    """
    roles = load_user_roles()
    return roles.get(username.lower())


def get_all_users() -> list[str]:
    """Return a sorted list of all known usernames."""
    return sorted(load_user_roles().keys())


# ─────────────────────────────────────────────
# Access Policy Resolution
# ─────────────────────────────────────────────

def get_allowed_tags(role: str) -> list[str]:
    """
    Return the list of department/keyword tags allowed for a given role.
    Admin gets a wildcard ["*"].
    """
    policies = load_access_policies()
    return policies.get(role, [])


def is_admin(role: str) -> bool:
    """Return True if the role has wildcard (Admin) access."""
    tags = get_allowed_tags(role)
    return "*" in tags


# ─────────────────────────────────────────────
# ChromaDB Filter Builder
# ─────────────────────────────────────────────

def build_chroma_filter(role: str) -> Optional[dict]:
    """
    Build a ChromaDB `where` filter dict for the given role.

    ChromaDB filter format for metadata matching:
      {"department": {"$in": ["finance", "hr"]}}

    Admin receives None → no filter applied → sees everything.

    IMPORTANT:
      This filter is applied BEFORE any document chunk reaches the LLM.
      Unauthorized chunks NEVER enter the retrieval pipeline.
    """
    if is_admin(role):
        # Admin → no filtering, access all departments
        return None

    # Map role → allowed department tag(s) stored in chunk metadata
    role_to_departments: dict[str, list[str]] = {
        "HR": ["hr"],
        "Finance": ["finance"],
        "Security": ["security"],
    }

    allowed_depts = role_to_departments.get(role)

    if not allowed_depts:
        # Unknown role → deny everything by returning an impossible filter
        return {"department": {"$eq": "__DENY_ALL__"}}

    if len(allowed_depts) == 1:
        # Single department → use equality check
        return {"department": {"$eq": allowed_depts[0]}}

    # Multiple departments → use $in operator
    return {"department": {"$in": allowed_depts}}


# ─────────────────────────────────────────────
# Access Decision Helper
# ─────────────────────────────────────────────

def check_access(username: str) -> tuple[bool, str, str]:
    """
    Validate whether a user can query the system.

    Returns:
        (is_allowed: bool, role: str, message: str)
    """
    role = get_user_role(username)

    if not role:
        return False, "", f"User '{username}' not found. Access denied."

    allowed_tags = get_allowed_tags(role)
    if not allowed_tags:
        return False, role, f"Role '{role}' has no permissions configured."

    return True, role, f"Access granted. Role: {role}"


# ─────────────────────────────────────────────
# Utility — human-readable policy summary
# ─────────────────────────────────────────────

def get_role_summary(role: str) -> dict:
    """Return a UI-friendly summary of what a role can access."""
    dept_perms = load_department_permissions()
    tags = get_allowed_tags(role)
    perms = dept_perms.get(role, {})

    return {
        "role": role,
        "allowed_tags": tags,
        "allowed_sources": perms.get("allowed_sources", []),
        "allowed_classifications": perms.get("allowed_classifications", []),
        "can_export": perms.get("can_export", False),
        "can_edit": perms.get("can_edit", False),
        "is_admin": is_admin(role),
    }