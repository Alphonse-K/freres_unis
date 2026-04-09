from sqlalchemy import Column, String, Integer, Boolean, DateTime, func, Numeric
from sqlalchemy.orm import relationship
from src.core.database import Base  


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False, unique=True)
    email = Column(String(150), nullable=False, unique=True)
    phone = Column(String(50), nullable=True)
    card_amount = Column(Numeric(12, 3), nullable=False)
    address = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    clients = relationship("ClientApproval", back_populates="company")
    api_keys = relationship("APIKey", back_populates="company")
    



"""Add company relation, card fields, and order_code

Revision ID: your_revision_id
Revises: previous_revision_id
Create Date: 2026-04-09 00:00:00.000000
"""
# from sqlalchemy.orm import Session
# from ulid import ULID

# def generate_order_code():
#     """Generate a unique order code using ULID."""
#     return f"ORD{str(ULID())}"


# def upgrade() -> None:
#     """Upgrade schema."""
#     # -------------------------
#     # 1. Update client_approvals
#     # -------------------------
#     op.add_column(
#         'client_approvals',
#         sa.Column('magnetic_card_number', sa.String(length=120), nullable=True)
#     )
#     op.add_column(
#         'client_approvals',
#         sa.Column('company_id', sa.Integer(), nullable=True)
#     )
#     op.create_unique_constraint(
#         "uq_client_approvals_magnetic_card_number",
#         "client_approvals",
#         ["magnetic_card_number"]
#     )
#     # create foreign key safely
#     op.create_foreign_key(
#         "fk_client_approvals_company_id",
#         "client_approvals",
#         "companies",
#         ["company_id"],
#         ["id"],
#         ondelete="SET NULL"
#     )
#     op.drop_column('client_approvals', 'employee_id_number')

#     # -------------------------
#     # 2. Update companies
#     # -------------------------
#     op.add_column(
#         'companies',
#         sa.Column('card_amount', sa.Numeric(12, 3), nullable=False, server_default='0')
#     )

#     # -------------------------
#     # 3. Update orders
#     # -------------------------
#     # Add nullable column first
#     op.add_column(
#         'orders',
#         sa.Column('order_code', sa.String(length=255), nullable=True)
#     )

#     # Fill existing orders with unique codes
#     bind = op.get_bind()
#     session = Session(bind=bind)
#     orders = session.execute(sa.text("SELECT id FROM orders")).fetchall()
#     for order in orders:
#         session.execute(
#             sa.text("UPDATE orders SET order_code = :code WHERE id = :id"),
#             {"code": generate_order_code(), "id": order.id}
#         )
#     session.commit()

#     # Enforce NOT NULL and UNIQUE constraints
#     op.alter_column('orders', 'order_code', nullable=False)
#     op.create_unique_constraint(
#         "uq_orders_order_code",
#         "orders",
#         ["order_code"]
#     )


