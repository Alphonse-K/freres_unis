from sqlalchemy.orm import Session
from src.models.permission import Permission
from src.core.permissions import Permissions
from src.models.role import Role

def seed_permissions(db: Session):
    """
    Sync database permissions with enum permissions
    Safe to run multiple time
    """
    # Get existing permissions in db
    existing_permission = {
        perm.name for perm in db.query(Permission).all()
    }
    enum_permission = {perm.value for perm in Permissions}

    for perm in enum_permission - existing_permission:
        db.add(Permission(name=perm))

    db.commit()

def seed_role(db: Session):
    """
    Create SUPER_ADMIN role if it doesn't exist and
    assign all permissions to it
    """
    admin_role = db.query(Role).filter_by(name="SUPER_ADMIN").first()
    if not admin_role:
        admin_role = Role(name="SUPER_ADMIN")
        db.add(admin_role)
        db.commit()
        db.refresh(admin_role)
    all_permissions = db.query(Permission).all()
    admin_role.permissions = all_permissions
    db.commit()
