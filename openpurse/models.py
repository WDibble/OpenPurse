from dataclasses import dataclass, asdict
from typing import Optional

@dataclass
class PaymentMessage:
    """
    Structured representation of a parsed financial payment message.
    
    This schema unifies extracted fields from deeply nested ISO 20022 XML messages 
    (e.g., pacs, camt, pain) and legacy SWIFT MT formats (e.g., MT103, MT202) into 
    a standardized, lightweight format.

    Attributes:
        message_id (Optional[str]): 
            The primary unique identifier for the message block (e.g., GrpHdr/MsgId in XML, or Block 4 :20: in MT).
        end_to_end_id (Optional[str]): 
            The End-to-End unique identification assigned by the initiating party. 
            Commonly maps to EndToEndId in XML. Often None in basic MT.
        amount (Optional[str]): 
            The principal monetary value linked to the transaction. 
            Kept as a string to preserve exact decimal precision out of the raw document.
        currency (Optional[str]): 
            The 3-letter active or historic currency code (e.g., 'USD', 'EUR').
        sender_bic (Optional[str]): 
            The Bank Identifier Code (BIC) of the party initiating or sending the message.
        receiver_bic (Optional[str]): 
            The Bank Identifier Code (BIC) of the destination or receiving servicing institution.
        debtor_name (Optional[str]): 
            The name or identification of the ordering customer or debtor party.
        creditor_name (Optional[str]): 
            The name or identification of the beneficiary or creditor party.
    """
    message_id: Optional[str] = None
    end_to_end_id: Optional[str] = None
    amount: Optional[str] = None
    currency: Optional[str] = None
    sender_bic: Optional[str] = None
    receiver_bic: Optional[str] = None
    debtor_name: Optional[str] = None
    creditor_name: Optional[str] = None
    
    def to_dict(self) -> dict:
        """
        Converts the parsed dataclass into a standard Python dictionary.
        Returns:
            dict: The flat dictionary representation of the message fields.
        """
        return asdict(self)
