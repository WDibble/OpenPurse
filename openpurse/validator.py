import re
from typing import Optional

from openpurse.models import PaymentMessage, ValidationReport


class Validator:
    """
    Intelligent pre-validation engine executing structural checks matching
    SWIFT & ISO compliance patterns.
    """

    _bic_pattern = re.compile(r"\A[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?\Z")
    _iban_clean_pattern = re.compile(r"[^A-Z0-9]")
    _iban_format_pattern = re.compile(r"\A[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}\Z")
    _uuid4_pattern = re.compile(
        r"\A[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\Z", re.I
    )

    @staticmethod
    def _validate_uetr(uetr: Optional[str]) -> Optional[str]:
        """
        Validates that a SWIFT gpi UETR matches the strict UUIDv4 specification.
        """
        if not uetr:
            return None

        if not Validator._uuid4_pattern.match(uetr):
            return f"Invalid UETR format: '{uetr}'. Must be a valid UUIDv4 string."

        return None

    @staticmethod
    def _validate_bic(bic: Optional[str]) -> Optional[str]:
        """
        Validates ISO 9362 BIC formatting strictly mapping to 8 or 11
        alphanumeric constraints.
        """
        if not bic:
            return None

        if not Validator._bic_pattern.match(bic):
            return (
                f"Invalid BIC format: '{bic}'. Must securely match ISO 9362 "
                "standard 8 or 11 characters."
            )

        return None

    @staticmethod
    def _is_likely_iban(iban: str) -> bool:
        """
        Heuristic check to determine if an account string *looks*
        like an IBAN. An IBAN typically starts with a 2-letter country
        code followed by 2 check digits, and is between 15-34 characters.
        """
        if not iban:
            return False
            
        # For the heuristic check ONLY, we strip out everything to see if it even remotely 
        # resembles an IBAN in its core alphanumeric structure. We do this so that malicious 
        # formatting (like newlines) doesn't bypass validation by tricking the engine into 
        # thinking it's not an IBAN account field at all.
        clean_iban = Validator._iban_clean_pattern.sub("", iban.upper())
        prefix_match = re.match(r"\A[A-Z]{2}[0-9]{2}", clean_iban)
        return bool(prefix_match)

    @staticmethod
    def _validate_iban_checksum(iban: str) -> Optional[str]:
        """
        Validates an International Bank Account Number (IBAN) using the
        Modulo-97 algorithm.
        Returns None if valid, or an error string if invalid.
        """
        if not iban:
            return None

        # Pre-check: Reject excessively long strings immediately
        if len(iban) > 100:
             return f"Invalid IBAN structure: excessively long string rejected."

        # 1. Sanitize only standard formatting characters (spaces, hyphens, and dots)
        cleaner_pattern = re.compile(r"[ \-\.]")
        formatted_iban = cleaner_pattern.sub("", iban.strip().upper())

        # 2. Strict ISO 13616 Format check on the resulting alphanumeric string
        # This catches injections, null bytes, special characters, and invalid lengths
        if not Validator._iban_format_pattern.match(formatted_iban) or "\n" in formatted_iban or "\r" in formatted_iban:
             return f"Invalid IBAN format: '{iban.strip()}' does not meet ISO 13616 standards or contains illegal characters."

        # 3. Rearrange: move the first four characters to the end
        rearranged = formatted_iban[4:] + formatted_iban[:4]

        # 2. Convert: replace letters with digits (A=10, B=11... Z=35)
        numeric_iban = "".join(
            str(ord(char) - 55) if char.isalpha() else char for char in rearranged
        )

        # 3. Modulo 97 check: the integer modulo 97 must equal 1
        # Python handles arbitrarily large integers, so we can cast and
        # modulo directly without chunking.
        try:
            if int(numeric_iban) % 97 != 1:
                return (
                    f"Invalid IBAN checksum: '{formatted_iban}'. Failed international "
                    "Modulo-97 algorithm."
                )
        except ValueError:
            return f"Invalid IBAN structure: '{formatted_iban}'. Could not evaluate checksum."

        return None

    @staticmethod
    def _validate_mt_bic(bic: str, block_name: str) -> Optional[str]:
        """
        Validates BIC format specifically for SWIFT MT headers (12 chars expected in blocks).
        """
        if not bic or len(bic) < 8:
            return f"Invalid BIC in {block_name}: too short."
        # Standard BIC is 8 or 11. headers often have 'X' padding or branch codes.
        if not Validator._bic_pattern.match(bic[:8] + (bic[8:11] if len(bic) >= 11 else "")):
            return f"Invalid BIC format in {block_name}: '{bic}'."
        return None

    @staticmethod
    def _validate_mt_32a(content: str) -> Optional[str]:
        """
        Validates Field 32A: :32A:YYMMDDCurrencyAmount
        """
        if len(content) < 10:  # 6 (date) + 3 (ccy) + 1 (min amt)
            return "Field 32A too short."
        
        date_part = content[:6]
        ccy_part = content[6:9]
        amount_part = content[9:].replace(",", ".")

        # Date check
        try:
            from datetime import datetime
            datetime.strptime(date_part, "%y%m%d")
        except ValueError:
            return f"Invalid date in Field 32A: '{date_part}'. Expected YYMMDD."

        # Currency check
        if not (len(ccy_part) == 3 and ccy_part.isalpha()):
            return f"Invalid currency in Field 32A: '{ccy_part}'."

        # Amount check
        try:
            float(amount_part)
        except ValueError:
            return f"Invalid amount format in Field 32A: '{amount_part}'."

        return None

    @staticmethod
    def validate_schema(raw_data: bytes) -> ValidationReport:
        """
        Executes a deep structural validation against the raw byte string.
        For XML (ISO 20022), validates against rigorous XSD definitions.
        For SWIFT MT, validates strictly against Block 1-5 structural rules.
        """
        from openpurse.parser import OpenPurseParser

        text_data = raw_data.decode("utf-8", errors="ignore").strip()

        # 1. XML Routing
        if text_data.startswith("<?xml") or text_data.startswith("<"):
            parser = OpenPurseParser(raw_data)
            return parser.validate_schema()

        # 2. SWIFT MT Routing
        if text_data.startswith("{1:"):
            errors = []
            
            # Block 1 Check: Basic Header {1:F01[BIC12]xxxx......}
            b1_match = re.search(r"\{1:([A-Z0-9]{3})([A-Z0-9]{12})([0-9]{10})\}", text_data)
            if not b1_match:
                errors.append("Invalid or missing Block 1 (Basic Header) structure.")
            else:
                bic = b1_match.group(2)[:11].strip()
                err = Validator._validate_mt_bic(bic, "Block 1")
                if err: errors.append(err)

            # Block 2 Check: Application Header {2:I103[BIC12]XXXXN...}
            b2_match = re.search(r"\{2:([IO])([0-9]{3})([A-Z0-9]{12})([A-Z0-9]*)?\}", text_data)
            if not b2_match:
                errors.append("Invalid or missing Block 2 (Application Header) structure.")
            else:
                bic = b2_match.group(3)[:11].strip()
                err = Validator._validate_mt_bic(bic, "Block 2")
                if err: errors.append(err)

            # Block 4 Check: Message Body
            block4_match = re.search(r"\{4:\r?\n(.+?)\r?\n-\}", text_data, re.DOTALL)
            if not block4_match:
                errors.append("Invalid or missing Block 4 (Message Body). Must cleanly terminate with '-}'.")
            else:
                body = block4_match.group(1)
                # Field 20 is mandatory in almost all messages
                if ":20:" not in body:
                    errors.append("Mandatory Field :20: (Sender's Reference) missing in Block 4.")
                
                # Check 32A if present
                if ":32A:" in body:
                    match_32a = re.search(r":32A:([A-Z0-9,.]+)", body)
                    if match_32a:
                        err = Validator._validate_mt_32a(match_32a.group(1))
                        if err: errors.append(err)

            if errors:
                return ValidationReport(is_valid=False, errors=errors)
            return ValidationReport(is_valid=True, errors=[])

        return ValidationReport(
            is_valid=False,
            errors=["Unrecognized message format. Payload does not match XML or SWIFT MT structures."],
        )

    @staticmethod
    def validate(message: PaymentMessage) -> ValidationReport:
        """
        Executes the full suite of validation rules against a parsed
        PaymentMessage.
        Returns a structured ValidationReport containing analytical results.
        """
        errors = []

        # 1. Core routing constraints mapped against generic properties
        sender_err = Validator._validate_bic(message.sender_bic)
        if sender_err:
            errors.append(f"[Sender] {sender_err}")

        receiver_err = Validator._validate_bic(message.receiver_bic)
        if receiver_err:
            errors.append(f"[Receiver] {receiver_err}")

        uetr_err = Validator._validate_uetr(message.uetr)
        if uetr_err:
            errors.append(f"[UETR] {uetr_err}")

        if message.end_to_end_id is not None and str(message.end_to_end_id).strip() == "":
            errors.append("end_to_end_id is present but is an empty string.")

        if message.amount is not None:
            amt_str = str(message.amount).strip()
            if amt_str == "":
                errors.append("amount is present but is an empty string.")

        if message.currency is not None:
            curr_str = str(message.currency).strip()
            if curr_str == "":
                errors.append("currency is present but is an empty string.")
            elif len(curr_str) != 3 or not curr_str.isalpha():
                errors.append(f"currency must be exactly 3 alphabetical characters, found: '{curr_str}'")
        # 2. Dynamic specific attribute IBAN extraction checks
        # Pacs008, Pain001, Pain008, etc. inherently provide debtor/creditor
        # explicit elements if loaded fully
        if hasattr(message, "debtor_account"):
            debtor_acct = getattr(message, "debtor_account")
            if debtor_acct and Validator._is_likely_iban(debtor_acct):
                iban_err = Validator._validate_iban_checksum(debtor_acct)
                if iban_err:
                    errors.append(f"[Debtor Account] {iban_err}")

        if hasattr(message, "creditor_account"):
            creditor_acct = getattr(message, "creditor_account")
            if creditor_acct and Validator._is_likely_iban(creditor_acct):
                iban_err = Validator._validate_iban_checksum(creditor_acct)
                if iban_err:
                    errors.append(f"[Creditor Account] {iban_err}")

        # Expanded nested mappings across multi-transaction messages
        # In detailed models like Pacs008Message, we also want to check nested
        # transactions if possible, but the base Validator aims for surface
        # level validation first.
        # Future enhancement: iterate entries/transactions.
        if hasattr(message, "transactions") and isinstance(getattr(message, "transactions"), list):
            for i, tx in enumerate(getattr(message, "transactions")):
                if isinstance(tx, dict):
                    if "debtor_account" in tx:
                        tx_db_acct = tx["debtor_account"]
                        if tx_db_acct and Validator._is_likely_iban(tx_db_acct):
                            err = Validator._validate_iban_checksum(tx_db_acct)
                            if err:
                                errors.append(f"[Transaction {i} Debtor Account] {err}")
                    if "creditor_account" in tx:
                        tx_cr_acct = tx["creditor_account"]
                        if tx_cr_acct and Validator._is_likely_iban(tx_cr_acct):
                            err = Validator._validate_iban_checksum(tx_cr_acct)
                            if err:
                                errors.append(f"[Transaction {i} Creditor Account] {err}")

        is_valid = len(errors) == 0
        return ValidationReport(is_valid=is_valid, errors=errors)
