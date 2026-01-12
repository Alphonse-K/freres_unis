# src/core/audit.py
import logging

logger = logging.getLogger("audit")

def audit_log(
    action: str,
    entity: str,
    entity_id: int,
    actor_id: int | None,
    metadata: dict | None = None,
):
    logger.info(
        "AUDIT | %s | %s:%s | actor=%s | %s",
        action,
        entity,
        entity_id,
        actor_id,
        metadata or {},
    )
