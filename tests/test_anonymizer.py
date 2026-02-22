import pytest
from openpurse.anonymizer import Anonymizer
from openpurse.validator import Validator
from openpurse.builder import MessageBuilder
from openpurse.parser import OpenPurseParser

def test_anonymize_xml_names_and_iban():
    xml = b"""<?xml version="1.0" encoding="UTF-8"?>
    <Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08">
        <FIToFICstmrCdtTrf>
            <CdtTrfTxInf>
                <Dbtr><Nm>John Doe</Nm></Dbtr>
                <Cdtr><Nm>Jane Smith</Nm></Cdtr>
                <DbtrAcct><Id><IBAN>GB90MIDL40051522334455</IBAN></Id></DbtrAcct>
            </CdtTrfTxInf>
        </FIToFICstmrCdtTrf>
    </Document>"""
    
    anonymizer = Anonymizer()
    anon_xml = anonymizer.anonymize_xml(xml)
    
    # 1. Verify names are changed
    assert b"John Doe" not in anon_xml
    assert b"CUST_" in anon_xml
    
    # 2. Parse the anonymized XML and validate the new IBAN
    parser = OpenPurseParser(anon_xml)
    msg = parser.parse()
    
    assert msg.debtor_name != "John Doe"
    assert msg.debtor_account != "GB90MIDL40051522334455"
    
    # 3. Checksum should be valid!
    report = Validator.validate(msg)
    assert report.is_valid is True

def test_anonymize_mt_names_and_iban():
    mt = b"{1:F01BANKUS33XXX0000000000}{4:\n:20:MSG123\n:50K:/GB90MIDL40051522334455\nJOHN DOE\n123 STREET\n:59:JANE SMITH\n-}"
    
    anonymizer = Anonymizer()
    anon_mt = anonymizer.anonymize_mt(mt)
    
    assert b"JOHN DOE" not in anon_mt
    assert b"123 STREET" not in anon_mt
    assert b"PARTY_" in anon_mt
    
    # Parse and validate IBAN
    parser = OpenPurseParser(anon_mt)
    msg = parser.parse()
    
    assert msg.debtor_account != "GB90MIDL40051522334455"
    report = Validator.validate(msg)
    assert report.is_valid is True

def test_determinism():
    anonymizer = Anonymizer(salt="steady")
    name = "Secret Agent"
    
    alias1 = anonymizer._get_alias(name)
    alias2 = anonymizer._get_alias(name)
    
    assert alias1 == alias2
    
    # Different salt should produce different alias
    anonymizer2 = Anonymizer(salt="different")
    alias3 = anonymizer2._get_alias(name)
    assert alias1 != alias3
