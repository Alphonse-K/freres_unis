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
    admin_role = db.query(Role).filter_by(name="SUPER_ADMIN")
    if not admin_role:
        admin_role = Role(name="SUPER_ADMIN")
        db.add(admin_role)
        db.commit()
        db.refresh(admin_role)
    all_permissions = db.query(Permission).all()
    admin_role.permissions = all_permissions
    db.commit()

def seed_default_client_role_and_permissions(db: Session):
    from src.core.permissions import Permissions
    from src.models.permission import Permission
    from src.models.role import Role

    default_permissions = [
        Permissions.READ_POS,
        Permissions.CREATE_ORDER,
        Permissions.READ_ORDER,
        Permissions.CANCEL_ORDER,
        Permissions.UPDATE_ORDER,
        Permissions.RETURN_ORDER
    ]
    for perm_name in default_permissions:
        perm = db.query(Permission).filter_by(name=perm_name).first()
        if not perm:
            perm = Permission(name=perm_name)
            db.add(perm)
        db.commit()
    
    client_role = db.query(Role).filter_by(name="CLIENT_BASIC").first()
    if not client_role:
        client_role = Role(name="CLIENT_BASIC")
        db.add(client_role)
        db.commit()
        db.refresh(client_role)
    client_role.permissions = db.query(Permission).filter(Permission.name.in_(default_permissions)).all()
    db.commit()