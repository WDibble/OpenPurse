"""
Integrations with third-party libraries like Pydantic and FastAPI.
"""

from .pydantic import from_dataclass, PydanticPaymentMessage
from .fastapi import get_openpurse_message

__all__ = ["from_dataclass", "PydanticPaymentMessage", "get_openpurse_message"]
