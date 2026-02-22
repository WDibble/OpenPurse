import re
import hashlib
from lxml import etree
from typing import Dict, Optional

class Anonymizer:
    """
    Utility to scrub Personally Identifiable Information (PII) from financial messages.
    Ensures structural and checksum validity for testing in non-prod environments.
    """

    def __init__(self, salt: str = "openpurse-default-salt"):
        self.salt = salt
        self._name_map: Dict[str, str] = {}
        self._account_map: Dict[str, str] = {}

    def _get_alias(self, original: str, prefix: str = "CUST") -> str:
        """
        Generates a deterministic alias for a given string using a hash.
        """
        if not original:
            return original
        
        # Deterministic hash based on original string and salt
        hash_val = hashlib.sha256((original + self.salt).encode()).hexdigest()[:8].upper()
        if not prefix:
            return hash_val
        return f"{prefix}_{hash_val}"

    def _mask_iban(self, iban: str) -> str:
        """
        Masks an IBAN while recalculating a valid Modulo-97 checksum.
        """
        if not iban:
            return iban
        
        # Clean the IBAN
        clean_iban = re.sub(r'[^A-Z0-9]', '', iban.upper())
        if len(clean_iban) < 15:
            return self._get_alias(clean_iban, "ACCT")

        country_code = clean_iban[:2]
        # Generate a dummy core account part (everything after the first 4 chars)
        core_len = len(clean_iban) - 4
        hash_seed = clean_iban[4:]
        hash_val = hashlib.sha256((hash_seed + self.salt).encode()).hexdigest()
        
        # Create a strictly numeric core of the correct length
        # Using a simple deterministic mapping from hash hex digits to dec digits
        mask_core = ""
        for i in range(core_len):
            digit_val = int(hash_val[i], 16) % 10
            mask_core += str(digit_val)
        
        # Now we need to find the 2 digits (pos 2,3) that make it valid
        # Rearranged: mask_core + country_code + "00"
        temp_rearranged = mask_core + country_code + "00"
        numeric_str = ""
        for char in temp_rearranged:
            if char.isalpha():
                numeric_str += str(ord(char) - 55)
            else:
                numeric_str += char
        
        mod = int(numeric_str) % 97
        check_digits = (98 - mod) % 97
        if check_digits == 0: check_digits = 97
        check_str = f"{check_digits:02d}"
        
        return f"{country_code}{check_str}{mask_core}"

    def anonymize_xml(self, xml_data: bytes) -> bytes:
        """
        Anonymizes PII in ISO 20022 XML data.
        """
        try:
            tree = etree.fromstring(xml_data)
        except Exception:
            return xml_data

        # PII tags to scrub
        # Names
        for nm in tree.xpath("//*[local-name()='Nm']"):
            if nm.text:
                nm.text = self._get_alias(nm.text)

        # Addresses
        for addr in tree.xpath("//*[local-name()='PstlAdr']"):
            for child in addr:
                tag = etree.QName(child).localname
                if tag in ['StrtNm', 'BldgNb', 'PstCd', 'TwnNm']:
                    child.text = "MASKED"
                elif tag == 'AdrLine':
                    child.text = "MASKED ADDRESS LINE"

        # Accounts (IBAN/BBAN)
        for acct in tree.xpath("//*[local-name()='IBAN']"):
            if acct.text:
                acct.text = self._mask_iban(acct.text)
        
        for id_tag in tree.xpath("//*[local-name()='Id']"):
            # Only scrub if it's inside a party context (Dbtr/Cdtr) and not a MsgId
            parent = id_tag.getparent()
            if parent is not None:
                p_tag = etree.QName(parent).localname
                if p_tag in ['Othr', 'PrvtId']:
                    if id_tag.text and len(id_tag.text) > 5:
                        id_tag.text = self._get_alias(id_tag.text, "ID")

        return etree.tostring(tree, encoding='UTF-8', xml_declaration=True)

    def anonymize_mt(self, mt_data: bytes) -> bytes:
        """
        Anonymizes PII in SWIFT MT data using regex.
        """
        text = mt_data.decode('utf-8', errors='ignore')

        # 1. Scrub :50K:, :50A:, :59:, :59A: (Parties)
        # These usually contain names and addresses on multiple lines
        def party_replacer(match):
            tag = match.group(1)
            content = match.group(2)
            # Mask the content lines
            lines = content.strip().split('\n')
            masked_lines = []
            for i, line in enumerate(lines):
                if i == 0 and line.startswith('/'): # Account line
                    masked_lines.append(f"/{self._mask_iban(line[1:])}")
                else:
                    masked_lines.append(self._get_alias(line, "PARTY"))
            return f"{tag}\n" + "\n".join(masked_lines)

        text = re.sub(r'(:50[AK]:|:59[A]?:)(.*?)(?=\n:[0-9A-Z]{2,3}:|\n-|\Z)', 
                      party_replacer, text, flags=re.DOTALL)

        return text.encode('utf-8')
