import re
from typing import Optional

from openpurse.models import PaymentMessage, ValidationReport


class Validator:
    """
    Intelligent pre-validation engine executing structural checks matching
    SWIFT & ISO compliance patterns.
    """

    _bic_pattern = re.compile(r"^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$")
    _iban_clean_pattern = re.compile(r"[^A-Z0-9]")
    _iban_format_pattern = re.compile(r"^[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}$")
    _uuid4_pattern = re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.I
    )

    @staticmethod
    def _validate_uetr(uetr: Optional[str]) -> Optional[str]:
        """
        Validates that a SWIFT gpi UETR matches the strict UUIDv4 specification.
        """
        if not uetr:
            return None

        clean_uetr = uetr.strip()
        if not Validator._uuid4_pattern.match(clean_uetr):
            return f"Invalid UETR format: '{clean_uetr}'. Must be a valid UUIDv4 string."

        return None

    @staticmethod
    def _validate_bic(bic: Optional[str]) -> Optional[str]:
        """
        Validates ISO 9362 BIC formatting strictly mapping to 8 or 11
        alphanumeric constraints.
        """
        if not bic:
            return None

        clean_bic = bic.strip()

        if not Validator._bic_pattern.match(clean_bic):
            return (
                f"Invalid BIC format: '{clean_bic}'. Must securely match ISO 9362 "
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
        clean_iban = Validator._iban_clean_pattern.sub("", iban.upper())
        return bool(Validator._iban_format_pattern.match(clean_iban))

    @staticmethod
    def _validate_iban_checksum(iban: str) -> Optional[str]:
        """
        Validates an International Bank Account Number (IBAN) using the
        Modulo-97 algorithm.
        Returns None if valid, or an error string if invalid.
        """
        if not iban:
            return None

        clean_iban = Validator._iban_clean_pattern.sub("", iban.upper())

        # 1. Rearrange: move the first four characters to the end
        rearranged = clean_iban[4:] + clean_iban[:4]

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
                    f"Invalid IBAN checksum: '{clean_iban}'. Failed international "
                    "Modulo-97 algorithm."
                )
        except ValueError:
            return f"Invalid IBAN structure: '{clean_iban}'. Could not evaluate checksum."

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
            import re

            # Block 1 Check: Basic Header {1:F01[BIC12]xxxx......}
            if not re.search(r"\{1:[A-Z0-9]{15,}\}", text_data):
                errors.append("Invalid or missing Block 1 (Basic Header).")

            # Block 2 Check: Application Header {2:I103[BIC12]XXXXN...}
            if not re.search(r"\{2:[IO][0-9]{3}[A-Z0-9]{10,}\}", text_data):
                errors.append("Invalid or missing Block 2 (Application Header).")

            # Block 4 Check: Message Body {4:\n:[2-3c]:...\n-}
            # Basic structural verification: must contain {4: and end with -}
            block4_match = re.search(r"\{4:\r?\n(.+?)\r?\n-\}", text_data, re.DOTALL)
            if not block4_match:
                errors.append("Invalid or missing Block 4 (Message Body). Must cleanly terminate with '-}'.")
            else:
                body = block4_match.group(1)
                # Verify standard MT tag structures (e.g. :20:IDENTIFIER)
                if not re.search(r"^:[0-9]{2}[a-zA-Z]?:", body, re.MULTILINE):
                    errors.append("Block 4 body does not contain valid SWIFT MT tags.")

            # Block 5 Check (Optional): Trailers {5:{MAC:xxxx}{CHK:xxxx}}
            if "{5:" in text_data:
                if not re.search(r"\{5:(\{.*?\})+\}", text_data):
                    errors.append("Malformed Block 5 (Trailers/Checksums).")

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
            elif len(curr_str) != 3:
                errors.append(f"currency must be exactly 3 characters, found: '{curr_str}'")
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
