import re
from typing import List, Optional
from openpurse.models import PaymentMessage, ValidationReport

class Validator:
    """
    Intelligent pre-validation engine executing structural checks matching SWIFT & ISO compliance patterns.
    """

    @staticmethod
    def _validate_bic(bic: str) -> Optional[str]:
        """
        Validates ISO 9362 BIC formatting strictly mapping to 8 or 11 alphanumeric constraints.
        """
        if not bic:
            return None
            
        # Optional padding removal generated from parser extracts
        clean_bic = bic.strip()
        
        # Match standard BIC: 4 chars (bank code), 2 chars (country), 2 chars (location), optional 3 chars (branch)
        # Often SWIFT allows numbers in the country code or location code in testing, so we relax slightly
        pattern = re.compile(r"^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$")
        
        if not pattern.match(clean_bic):
            return f"Invalid BIC format: '{clean_bic}'. Must securely match ISO 9362 standard 8 or 11 characters."
            
        return None

    @staticmethod
    def _validate_iban(iban: str) -> Optional[str]:
        """
        Validates International Bank Account Numbers using the rigorous Modulo-97 checksum algorithm.
        """
        if not iban:
            return None
            
        clean_iban = iban.replace(" ", "").upper()
        
        # IBANs are strictly between 15 and 34 characters and begin with a 2-letter country code
        if not re.match(r"^[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}$", clean_iban):
            return None # Not an IBAN, safely ignore (could be a local BBAN/account number)
            
        # 1. Rearrange: move the first four characters to the end
        rearranged = clean_iban[4:] + clean_iban[:4]
        
        # 2. Convert: replace letters with digits (A=10, B=11... Z=35)
        numeric_iban = ""
        for char in rearranged:
            if char.isalpha():
                numeric_iban += str(ord(char) - 55) # 'A' is 65. 65 - 55 = 10.
            else:
                numeric_iban += char
                
        # 3. Modulo 97 check: the integer modulo 97 must equal 1
        try:
            if int(numeric_iban) % 97 != 1:
                return f"Invalid IBAN checksum: '{clean_iban}'. Failed international Modulo-97 algorithm."
        except ValueError:
            return f"Invalid IBAN structure: '{clean_iban}'. Could not evaluate checksum."
            
        return None

    @staticmethod
    def validate(message: PaymentMessage) -> ValidationReport:
        """
        Executes pre-flight banking compliance algorithms mapping fields dynamically to rigorous assertions.
        """
        errors = []
        
        # 1. Core routing constraints mapped against generic properties
        sender_err = Validator._validate_bic(message.sender_bic)
        if sender_err:
            errors.append(f"[Sender] {sender_err}")
            
        receiver_err = Validator._validate_bic(message.receiver_bic)
        if receiver_err:
            errors.append(f"[Receiver] {receiver_err}")

        # 2. Dynamic specific attribute IBAN extraction checks
        # Pacs008, Pain001, Pain008, etc. inherently provide debtor/creditor explicit elements if loaded fully
        if hasattr(message, 'debtor_account'):
            debtor_iban_err = Validator._validate_iban(getattr(message, 'debtor_account'))
            if debtor_iban_err:
                errors.append(f"[Debtor Account] {debtor_iban_err}")
                
        if hasattr(message, 'creditor_account'):
            creditor_iban_err = Validator._validate_iban(getattr(message, 'creditor_account'))
            if creditor_iban_err:
                errors.append(f"[Creditor Account] {creditor_iban_err}")

        # Expanded nested mappings across multi-transaction messages
        if hasattr(message, 'transactions') and isinstance(getattr(message, 'transactions'), list):
            for i, tx in enumerate(getattr(message, 'transactions')):
                if isinstance(tx, dict):
                    if 'debtor_account' in tx:
                        tx_db_err = Validator._validate_iban(tx['debtor_account'])
                        if tx_db_err:
                            errors.append(f"[Transaction {i} Debtor Account] {tx_db_err}")
                    if 'creditor_account' in tx:
                        tx_cr_err = Validator._validate_iban(tx['creditor_account'])
                        if tx_cr_err:
                            errors.append(f"[Transaction {i} Creditor Account] {tx_cr_err}")

        is_valid = len(errors) == 0
        return ValidationReport(is_valid=is_valid, errors=errors)
