from dataclasses import fields
from typing import Any, Dict, Type
from openpurse.models import (
    PaymentMessage,
    Camt054Message,
    Pacs008Message,
    Camt004Message,
    Camt052Message,
    Camt053Message,
    Pain001Message,
    Pain008Message,
    Pain002Message
)

class MessageBuilder:
    """
    A factory for programmatically building typed OpenPurse payment messages.
    """

    _SCHEMA_MAP = {
        "pacs.008": Pacs008Message,
        "camt.054": Camt054Message,
        "camt.004": Camt004Message,
        "camt.052": Camt052Message,
        "camt.053": Camt053Message,
        "pain.001": Pain001Message,
        "pain.008": Pain008Message,
        "pain.002": Pain002Message
    }

    @staticmethod
    def build(schema: str, **kwargs: Any) -> PaymentMessage:
        """
        Dynamically constructs a typed PaymentMessage subclass based on the provided schema identifier.
        
        Args:
            schema (str): The target schema to build (e.g., "pacs.008", "camt.054"). If the schema 
                          is unknown, it falls back to the base PaymentMessage.
            **kwargs: The dictionary of string properties to assign to the message.
        
        Returns:
            PaymentMessage: The strictly-typed schema model instance.
            
        Note:
            Any kwargs provided that do not explicitly exist on the resolved schema's definition 
            will be safely discarded avoiding `TypeError` exceptions.
        """
        # Determine the target dataclass
        target_class: Type[PaymentMessage] = MessageBuilder._SCHEMA_MAP.get(schema, PaymentMessage)
        
        # Introspect the allowed fields from the dataclass
        valid_fields = {f.name for f in fields(target_class)}
        
        # Filter kwargs to only include valid fields
        filtered_kwargs = {k: v for k, v in kwargs.items() if k in valid_fields}
        
        return target_class(**filtered_kwargs)
