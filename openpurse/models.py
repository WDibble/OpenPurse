from dataclasses import dataclass, asdict
from typing import Optional, List

@dataclass
class PostalAddress:
    """
    Standardized representation of an ISO 20022 PstlAdr (Postal Address).
    """
    country: Optional[str] = None
    town_name: Optional[str] = None
    post_code: Optional[str] = None
    street_name: Optional[str] = None
    building_number: Optional[str] = None
    address_lines: Optional[List[str]] = None

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
        debtor_address (Optional[PostalAddress]):
            The structured geographic and postal location of the debtor.
        creditor_address (Optional[PostalAddress]):
            The structured geographic and postal location of the creditor.
    """
    message_id: Optional[str] = None
    end_to_end_id: Optional[str] = None
    amount: Optional[str] = None
    currency: Optional[str] = None
    sender_bic: Optional[str] = None
    receiver_bic: Optional[str] = None
    debtor_name: Optional[str] = None
    creditor_name: Optional[str] = None
    debtor_address: Optional[PostalAddress] = None
    creditor_address: Optional[PostalAddress] = None
    
    def to_dict(self) -> dict:
        """
        Converts the parsed dataclass into a standard Python dictionary.
        Returns:
            dict: The flat dictionary representation of the message fields.
        """
        data = asdict(self)
        if self.debtor_address:
            data['debtor_address'] = asdict(self.debtor_address)
        if self.creditor_address:
            data['creditor_address'] = asdict(self.creditor_address)
        return data

@dataclass
class Camt054Message(PaymentMessage):
    """
    Detailed schema for CAMT.054 Bank to Customer Debit/Credit Notification.
    Provides deep extraction of notification details and entries.
    """
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
    entries: Optional[list] = None

@dataclass
class Pacs008Message(PaymentMessage):
    """
    Detailed schema for PACS.008 FI to FI Customer Credit Transfer.
    Provides deep extraction of settlement info and distinct credit transactions.
    """
    settlement_method: Optional[str] = None
    clearing_system: Optional[str] = None
    number_of_transactions: Optional[int] = None
    settlement_amount: Optional[str] = None
    settlement_currency: Optional[str] = None
    transactions: Optional[list] = None

@dataclass
class Camt004Message(PaymentMessage):
    """
    Detailed schema for CAMT.004 Return Account.
    Provides deep extraction of account details, balances, limits, and errors.
    """
    creation_date_time: Optional[str] = None
    original_business_query: Optional[str] = None
    account_id: Optional[str] = None
    account_owner: Optional[str] = None
    account_servicer: Optional[str] = None
    account_status: Optional[str] = None
    account_currency: Optional[str] = None
    balances: Optional[list] = None
    limits: Optional[list] = None
    number_of_payments: Optional[str] = None
    business_errors: Optional[list] = None

@dataclass
class Camt052Message(PaymentMessage):
    """
    Detailed schema for CAMT.052 Bank to Customer Account Report.
    Extracts high-level report information, account details, and entries.
    """
    creation_date_time: Optional[str] = None
    report_id: Optional[str] = None
    account_id: Optional[str] = None
    account_currency: Optional[str] = None
    account_owner: Optional[str] = None
    account_servicer: Optional[str] = None
    total_credit_entries: Optional[int] = None
    total_credit_amount: Optional[str] = None
    total_debit_entries: Optional[int] = None
    total_debit_amount: Optional[str] = None
    entries: Optional[list] = None

@dataclass
class Camt053Message(PaymentMessage):
    """
    Detailed schema for CAMT.053 Bank to Customer Statement.
    Extracts high-level statement details, balances, and distinct entries.
    """
    creation_date_time: Optional[str] = None
    statement_id: Optional[str] = None
    account_id: Optional[str] = None
    account_currency: Optional[str] = None
    account_owner: Optional[str] = None
    account_servicer: Optional[str] = None
    balances: Optional[list] = None
    total_credit_entries: Optional[int] = None
    total_credit_amount: Optional[str] = None
    total_debit_entries: Optional[int] = None
    total_debit_amount: Optional[str] = None
    entries: Optional[list] = None

@dataclass
class Pain001Message(PaymentMessage):
    """
    Detailed schema for PAIN.001 Customer Credit Transfer Initiation.
    Extracts the initiating party and standard payment information blocks containing individual transfers.
    """
    creation_date_time: Optional[str] = None
    number_of_transactions: Optional[int] = None
    control_sum: Optional[str] = None
    initiating_party: Optional[str] = None
    payment_information: Optional[list] = None

@dataclass
class Pain008Message(PaymentMessage):
    """
    Detailed schema for PAIN.008 Customer Direct Debit Initiation.
    Extracts the initiating party and standard payment information blocks containing direct debit instructions.
    """
    creation_date_time: Optional[str] = None
    number_of_transactions: Optional[int] = None
    control_sum: Optional[str] = None
    initiating_party: Optional[str] = None
    payment_information: Optional[list] = None

@dataclass
class Pain002Message(PaymentMessage):
    """
    Detailed schema for PAIN.002 Customer Payment Status Report.
    Extracts original group info, statuses, returning transactions and reasons.
    """
    creation_date_time: Optional[str] = None
    initiating_party: Optional[str] = None
    original_message_id: Optional[str] = None
    original_message_name_id: Optional[str] = None
    group_status: Optional[str] = None
    transactions_status: Optional[list] = None
