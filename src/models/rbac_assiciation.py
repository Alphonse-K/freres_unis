from sqlalchemy import Table, Column, ForeignKey, Integer
from src.core.database import Base   # adjust import if needed

# Role ↔ Permission
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)

# User ↔ Role
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)

# Client ↔ Role
client_roles = Table(
    "client_roles",
    Base.metadata,
    Column("client_id", ForeignKey("clients.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)

# POSUser ↔ Role
posuser_roles = Table(
    "posuser_roles",
    Base.metadata,
    Column("posuser_id", ForeignKey("pos_user.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)


