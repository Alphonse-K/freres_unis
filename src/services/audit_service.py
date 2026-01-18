# services/audit_service.py
from src.models.audit import AuditLog
from sqlalchemy.orm import Session

class AuditService:
    
    @staticmethod
    def log_action(
        db: Session,
        actor_type: str,
        actor_id: int,
        target_type: str,
        target_id: int,
        action: str,
        details: dict = None,
        ip_address: str = "",
        user_agent: str = None,
    ):
        """Log an action to the audit log"""
        
        audit_log = AuditLog(
            actor_type=actor_type,
            actor_id=actor_id,
            target_type=target_type,
            target_id=target_id,
            action=action,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        db.add(audit_log)
        db.commit()
    
    @staticmethod
    def get_client_auth_logs(db: Session, client_id: int, limit: int = 50):
        """Get authentication-related logs for a client"""
        return db.query(AuditLog).filter(
            AuditLog.target_type == 'client',
            AuditLog.target_id == client_id,
            AuditLog.action.in_([
                'set_password', 'reset_password', 'change_password',
                'set_pin', 'reset_pin', 'change_pin',
                'password_reset_request', 'pin_reset_request'
            ])
        ).order_by(AuditLog.created_at.desc()).limit(limit).all()