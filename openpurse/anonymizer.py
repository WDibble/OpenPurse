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
        self.salt_bytes = self.salt.encode()
        self._name_map: Dict[str, str] = {}
        self._account_map: Dict[str, str] = {}
        
        # Pre-compile regexes for performance
        self._iban_clean_pattern = re.compile(r'[^A-Z0-9]')
        self._mt_party_pattern = re.compile(r'(:50[AK]:|:59[A]?:)(.*?)(?=\n:[0-9A-Z]{2,3}:|\n-|\Z)', re.DOTALL)

    def _get_alias(self, original: str, prefix: str = "CUST") -> str:
        """
        Generates a deterministic alias for a given string using a hash.
        """
        if not original:
            return original
        
        # Deterministic hash based on original string and salt
        hash_val = hashlib.sha256(original.encode() + self.salt_bytes).hexdigest()[:8].upper()
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
        clean_iban = self._iban_clean_pattern.sub('', iban.upper())
        if len(clean_iban) < 15:
            return self._get_alias(clean_iban, "ACCT")

        country_code = clean_iban[:2]
        # Generate a dummy core account part (everything after the first 4 chars)
        core_len = len(clean_iban) - 4
        hash_seed = clean_iban[4:].encode()
        hash_val = hashlib.sha256(hash_seed + self.salt_bytes).hexdigest()
        
        # Create a strictly numeric core of the correct length
        # Using a simple deterministic mapping from hash hex digits to dec digits
        mask_core = "".join(str(int(hash_val[i], 16) % 10) for i in range(core_len))
        
        # Now we need to find the 2 digits (pos 2,3) that make it valid
        # Rearranged: mask_core + country_code + "00"
        temp_rearranged = mask_core + country_code + "00"
        
        # Fast alphanumeric char conversion
        numeric_str = "".join(str(ord(c) - 55) if c.isalpha() else c for c in temp_rearranged)
        
        check_digits = (98 - (int(numeric_str) % 97)) % 97
        if check_digits == 0: 
            check_digits = 97
        
        # Using zfill is slightly faster and cleaner
        return f"{country_code}{str(check_digits).zfill(2)}{mask_core}"

    def anonymize_xml(self, xml_data: bytes) -> bytes:
        """
        Anonymizes PII in ISO 20022 XML data in a single optimized pass.
        """
        try:
            tree = etree.fromstring(xml_data)
        except Exception:
            return xml_data

        # Single pass over the XML tree using fast iteration
        for elem in tree.iter():
            tag = etree.QName(elem).localname
            
            if tag == 'Nm' and elem.text:
                elem.text = self._get_alias(elem.text)
            
            elif tag == 'PstlAdr':
                for child in elem:
                    c_tag = etree.QName(child).localname
                    if c_tag in ('StrtNm', 'BldgNb', 'PstCd', 'TwnNm'):
                        child.text = "MASKED"
                    elif c_tag == 'AdrLine':
                        child.text = "MASKED ADDRESS LINE"
            
            elif tag == 'IBAN' and elem.text:
                elem.text = self._mask_iban(elem.text)
                
            elif tag == 'Id' and elem.text and len(elem.text) > 5:
                # Only scrub if it's inside a party context (Dbtr/Cdtr) and not a MsgId
                parent = elem.getparent()
                if parent is not None:
                    p_tag = etree.QName(parent).localname
                    if p_tag in ('Othr', 'PrvtId'):
                        elem.text = self._get_alias(elem.text, "ID")

        return etree.tostring(tree, encoding='UTF-8', xml_declaration=True)

    def anonymize_mt(self, mt_data: bytes) -> bytes:
        """
        Anonymizes PII in SWIFT MT data using optimized regex.
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

        text = self._mt_party_pattern.sub(party_replacer, text)

        return text.encode('utf-8')
