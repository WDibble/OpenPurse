import dataclasses
from typing import Any, Dict, List, Optional, Type, Union
from sqlalchemy import select
from sqlalchemy.orm import Session
from openpurse.models import PaymentMessage, Pacs008Message, Pain001Message, Camt054Message
from openpurse.database.models import (
    Base,
    PaymentMessageRecord,
    Pacs008Record,
    Pain001Record,
    Camt054Record,
)

class MessageRepository:
    """
    Repository layer for managing financial message persistence.
    """

    def __init__(self, session: Session):
        self.session = session

    def save(self, msg: PaymentMessage) -> PaymentMessageRecord:
        """
        Converts a PaymentMessage dataclass to a SQLAlchemy record and persists it.
        """
        record = self._to_record(msg)
        self.session.add(record)
        self.session.flush()  # Ensure ID is populated
        return record

    def get_by_message_id(self, message_id: str) -> Optional[PaymentMessageRecord]:
        """
        Retrieves a message record by its ISO/MT message ID.
        """
        stmt = select(PaymentMessageRecord).where(PaymentMessageRecord.message_id == message_id)
        return self.session.execute(stmt).scalars().first()

    def list_by_sender(self, sender_bic: str) -> List[PaymentMessageRecord]:
        """
        Lists all messages sent by a specific BIC.
        """
        stmt = select(PaymentMessageRecord).where(PaymentMessageRecord.sender_bic == sender_bic)
        return list(self.session.execute(stmt).scalars().all())

    def _to_record(self, msg: PaymentMessage) -> PaymentMessageRecord:
        """
        Internal mapping logic from dataclass to relational record.
        """
        data = dataclasses.asdict(msg)
        
        # Handle polymorphic identities
        if isinstance(msg, Pacs008Message):
            # Flatten or remove complex fields that handled separately in the model
            return Pacs008Record(**data)
        elif isinstance(msg, Pain001Message):
            return Pain001Record(**data)
        elif isinstance(msg, Camt054Message):
            return Camt054Record(**data)
        
        return PaymentMessageRecord(**data)

    @staticmethod
    def create_schema(engine) -> None:
        """
        Utility to create all defined tables in the target database.
        """
        Base.metadata.create_all(engine)
