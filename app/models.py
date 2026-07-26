import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, Numeric, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy import text

from app.database import Base


class Account(Base):
    __tablename__ = "accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    version = Column(Integer, nullable=False, server_default=text("0"))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    ledger_entries = relationship("LedgerEntry", back_populates="account")


class Transfer(Base):
    __tablename__ = "transfers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    idempotency_key = Column(String, unique=True, nullable=False)
    from_account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    to_account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    amount = Column(Numeric(18, 2), nullable=False)
    status = Column(String, nullable=False, default="pending")  # pending | completed | failed
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    ledger_entries = relationship("LedgerEntry", back_populates="transfer")


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    transfer_id = Column(UUID(as_uuid=True), ForeignKey("transfers.id"), nullable=True)
    direction = Column(String, nullable=False)  # "debit" | "credit"
    amount = Column(Numeric(18, 2), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    account = relationship("Account", back_populates="ledger_entries")
    transfer = relationship("Transfer", back_populates="ledger_entries")