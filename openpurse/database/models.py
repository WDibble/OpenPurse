from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, Table
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class PaymentMessageRecord(Base):
    """
    Main table for all financial messages. 
    Supports polymorphic storage for specific ISO message types.
    """
    __tablename__ = "payment_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    msg_type: Mapped[str] = mapped_column(String(50))  # e.g., 'pacs.008', 'pain.001'
    
    # Common core fields from PaymentMessage dataclass
    message_id: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    end_to_end_id: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    uetr: Mapped[Optional[str]] = mapped_column(String(36), index=True)
    
    amount: Mapped[Optional[str]] = mapped_column(String(50))
    currency: Mapped[Optional[str]] = mapped_column(String(3))
    
    sender_bic: Mapped[Optional[str]] = mapped_column(String(11), index=True)
    receiver_bic: Mapped[Optional[str]] = mapped_column(String(11), index=True)
    
    debtor_name: Mapped[Optional[str]] = mapped_column(String(255))
    creditor_name: Mapped[Optional[str]] = mapped_column(String(255))
    
    debtor_address: Mapped[Optional[dict]] = mapped_column(JSON)
    creditor_address: Mapped[Optional[dict]] = mapped_column(JSON)
    
    debtor_account: Mapped[Optional[str]] = mapped_column(String(255))
    creditor_account: Mapped[Optional[str]] = mapped_column(String(255))

    # Extended common fields
    transaction_id: Mapped[Optional[str]] = mapped_column(String(255))
    instruction_id: Mapped[Optional[str]] = mapped_column(String(255))
    requested_execution_date: Mapped[Optional[str]] = mapped_column(String(50))
    purpose: Mapped[Optional[str]] = mapped_column(String(50))
    remittance_info: Mapped[Optional[str]] = mapped_column(String(1000))

    # Audit trail
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    raw_payload_size: Mapped[Optional[int]] = mapped_column(Integer)

    # Polymorphic configuration
    __mapper_args__ = {
        "polymorphic_on": msg_type,
        "polymorphic_identity": "base",
    }

class Pacs008Record(PaymentMessageRecord):
    __tablename__ = "pacs008_messages"
    id: Mapped[int] = mapped_column(ForeignKey("payment_messages.id"), primary_key=True)
    
    settlement_method: Mapped[Optional[str]] = mapped_column(String(50))
    clearing_system: Mapped[Optional[str]] = mapped_column(String(50))
    number_of_transactions: Mapped[Optional[int]] = mapped_column(Integer)
    settlement_amount: Mapped[Optional[str]] = mapped_column(String(50))
    settlement_currency: Mapped[Optional[str]] = mapped_column(String(3))
    
    # Transaction level details stored as JSON
    transactions: Mapped[Optional[list]] = mapped_column(JSON)

    __mapper_args__ = {
        "polymorphic_identity": "pacs.008",
    }

class Pain001Record(PaymentMessageRecord):
    __tablename__ = "pain001_messages"
    id: Mapped[int] = mapped_column(ForeignKey("payment_messages.id"), primary_key=True)
    
    creation_date_time: Mapped[Optional[str]] = mapped_column(String(50))
    number_of_transactions: Mapped[Optional[int]] = mapped_column(Integer)
    control_sum: Mapped[Optional[str]] = mapped_column(String(50))
    initiating_party: Mapped[Optional[str]] = mapped_column(String(255))
    payment_information: Mapped[Optional[list]] = mapped_column(JSON)
    
    __mapper_args__ = {
        "polymorphic_identity": "pain.001",
    }

class Camt054Record(PaymentMessageRecord):
    __tablename__ = "camt054_messages"
    id: Mapped[int] = mapped_column(ForeignKey("payment_messages.id"), primary_key=True)
    
    creation_date_time: Mapped[Optional[str]] = mapped_column(String(50))
    notification_id: Mapped[Optional[str]] = mapped_column(String(255))
    account_id: Mapped[Optional[str]] = mapped_column(String(255))
    account_currency: Mapped[Optional[str]] = mapped_column(String(3))
    account_owner: Mapped[Optional[str]] = mapped_column(String(255))
    account_servicer: Mapped[Optional[str]] = mapped_column(String(255))
    total_credit_entries: Mapped[Optional[int]] = mapped_column(Integer)
    total_credit_amount: Mapped[Optional[str]] = mapped_column(String(50))
    total_debit_entries: Mapped[Optional[int]] = mapped_column(Integer)
    total_debit_amount: Mapped[Optional[str]] = mapped_column(String(50))
    
    entries: Mapped[Optional[list]] = mapped_column(JSON)

    __mapper_args__ = {
        "polymorphic_identity": "camt.054",
    }
