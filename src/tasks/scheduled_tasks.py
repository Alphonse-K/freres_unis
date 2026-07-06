from datetime import date, datetime, timezone

from src.core.celery import celery_app
from src.core.database import SessionLocal
from src.core.audit import logger


@celery_app.task(name="src.tasks.scheduled_tasks.increment_partner_balances")
def increment_partner_balances():
    db = SessionLocal()
    try:
        from src.models.clients import Client, LedgerEntry
        from src.core.audit import audit_log

        clients = db.query(Client).filter(
            Client.type == "PARTNER_CLIENT",
            Client.magnetic_card_status == "HELD_VALID"
        ).all()

        print("Here are the corresponding clients", clients)

        updated = 0
        for client in clients:
            if not client.approval or not client.approval.company:
                logger.warning(f"[scheduler] Client {client.id} has no company — skipping")
                continue
            if not client.card_opening_balance:
                continue
            client.card_opening_balance -= client.approval.company.card_amount
            balance_before = client.current_balance
            client.current_balance += client.approval.company.card_amount
            audit_log("Balance increment", "client", client.id, None)
            db.add(LedgerEntry(
                client_id=client.id,
                amount=client.approval.company.card_amount,
                entry_type="card validation",
                card_validation_count=1,
                balance_before=balance_before,
                balance_after=client.current_balance,
                reason="Card validation",
                reference_id=f"{client.id}-{datetime.now(timezone.utc)}",
            ))
            updated += 1
            client.card_validation_count += 1
        db.commit()
        logger.info(f"[scheduler] Balance increment done | updated={updated} clients")

    except Exception as e:
        db.rollback()
        logger.error(f"[scheduler] Balance increment failed | error={e}", exc_info=True)
    finally:
        db.close()