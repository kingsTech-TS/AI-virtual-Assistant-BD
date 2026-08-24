from enum import Enum
from typing import Dict


class UserRole(str, Enum):
    STUDENT = "student"
    STAFF = "staff"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


ROLE_HIERARCHY: Dict[UserRole, int] = {
    UserRole.STUDENT: 1,
    UserRole.STAFF: 2,
    UserRole.ADMIN: 3,
    UserRole.SUPER_ADMIN: 4,
}


def has_min_role(user_role: UserRole, required_role: UserRole) -> bool:
    user_level = ROLE_HIERARCHY.get(user_role, 0)
    required_level = ROLE_HIERARCHY.get(required_role, 0)
    return user_level >= required_level
