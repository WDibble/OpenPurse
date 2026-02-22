from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from openpurse.models import (
    PaymentMessage,
    PostalAddress,
    Pacs008Message,
    Pain001Message,
    Camt054Message,
    Camt004Message,
)


class PydanticPostalAddress(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    country: Optional[str] = None
    town_name: Optional[str] = None
    post_code: Optional[str] = None
    street_name: Optional[str] = None
    building_number: Optional[str] = None
    address_lines: Optional[List[str]] = None


class PydanticPaymentMessage(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message_id: Optional[str] = None
    end_to_end_id: Optional[str] = None
    amount: Optional[str] = None
    currency: Optional[str] = None
    sender_bic: Optional[str] = None
    receiver_bic: Optional[str] = None
    debtor_name: Optional[str] = None
    creditor_name: Optional[str] = None
    debtor_address: Optional[PydanticPostalAddress] = None
    creditor_address: Optional[PydanticPostalAddress] = None
    debtor_account: Optional[str] = None
    creditor_account: Optional[str] = None
    uetr: Optional[str] = None


class PydanticPacs008(PydanticPaymentMessage):
    settlement_method: Optional[str] = None
    clearing_system: Optional[str] = None
    number_of_transactions: Optional[int] = None
    settlement_amount: Optional[str] = None
    settlement_currency: Optional[str] = None
    transactions: Optional[List[Dict[str, Any]]] = None


class PydanticPain001(PydanticPaymentMessage):
    creation_date_time: Optional[str] = None
    number_of_transactions: Optional[int] = None
    control_sum: Optional[str] = None
    initiating_party: Optional[str] = None


class PydanticCamt054(PydanticPaymentMessage):
    creation_date_time: Optional[str] = None
    notification_id: Optional[str] = None
    account_id: Optional[str] = None
    account_currency: Optional[str] = None
    account_owner: Optional[str] = None
    account_servicer: Optional[str] = None
    total_credit_entries: Optional[int] = None
    total_credit_amount: Optional[str] = None
    total_debit_entries: Optional[int] = None
    total_debit_amount: Optional[str] = None
    entries: Optional[List[Dict[str, Any]]] = None


class PydanticCamt004(PydanticPaymentMessage):
    creation_date_time: Optional[str] = None
    original_business_query: Optional[str] = None
    account_id: Optional[str] = None
    account_owner: Optional[str] = None
    account_servicer: Optional[str] = None
    account_status: Optional[str] = None
    account_currency: Optional[str] = None


def from_dataclass(msg: PaymentMessage) -> PydanticPaymentMessage:
    """
    Converts a core OpenPurse dataclass into its Pydantic equivalent.
    """
    if isinstance(msg, Pacs008Message):
        return PydanticPacs008.model_validate(msg)
    if isinstance(msg, Pain001Message):
        return PydanticPain001.model_validate(msg)
    if isinstance(msg, Camt054Message):
        return PydanticCamt054.model_validate(msg)
    if isinstance(msg, Camt004Message):
        return PydanticCamt004.model_validate(msg)
    
    return PydanticPaymentMessage.model_validate(msg)
