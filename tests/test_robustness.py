import pytest
import lxml.etree
from openpurse.parser import OpenPurseParser
from openpurse.validator import Validator
from openpurse.reconciler import Reconciler
from openpurse.builder import MessageBuilder
from openpurse.models import PaymentMessage, Pain002Message

# --- 1. Parser Resilience: Malformed Input ---

def test_parser_malformed_xml():
    malformed_xml = b"<Document><MsgId>Broken" # Unclosed
    parser = OpenPurseParser(malformed_xml)
    # The parser should not crash, it should return an empty PaymentMessage or handle lxml errors
    msg = parser.parse()
    assert isinstance(msg, PaymentMessage)
    assert msg.message_id is None

def test_parser_malformed_mt():
    malformed_mt = b"{1:F01BANKUS33AXXX0000000000}{4:\n:20:TRUNCATED" # Missing closing -}
    parser = OpenPurseParser(malformed_mt)
    msg = parser.parse()
    assert isinstance(msg, PaymentMessage)
    # If it fails to find :20: due to truncation, it should be None, not crash
    assert msg.message_id == "TRUNCATED" 

# --- 2. Parser Resilience: Unicode ---

def test_parser_unicode_names():
    # Cyrillic and Emojis in names
    xml = b"""<?xml version="1.0" encoding="UTF-8"?>
    <Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08">
        <FIToFICstmrCdtTrf>
            <GrpHdr><MsgId>ID123</MsgId></GrpHdr>
            <CdtTrfTxInf>
                <InstdAgt><FinInstnId><BICFI>BANKRU</BICFI></FinInstnId></InstdAgt>
                <Dbtr><Nm>\xd0\x98\xd0\xb2\xd0\xb0\xd0\xbd \xd0\x9f\xd0\xb5\xd1\x82\xd1\x80\xd0\xbe\xd0\xb2 \xf0\x9f\x92\xb0</Nm></Dbtr>
                <Cdtr><Nm>Beneficiary \xe4\xb8\xad\xe6\x96\x87</Nm></Cdtr>
            </CdtTrfTxInf>
        </FIToFICstmrCdtTrf>
    </Document>"""
    parser = OpenPurseParser(xml)
    msg = parser.parse()
    assert "Иван Петров" in msg.debtor_name # Ivan Petrov
    assert "💰" in msg.debtor_name # Money bag emoji
    assert "中文" in msg.creditor_name # Chinese

# --- 3. Validator Robustness ---

def test_validator_iban_sanitization():
    # IBAN with dots and hyphens and mixed case
    # GB90 MIDL 4005 1522 3344 55
    dirty_iban = "gb90.midl-40051522.3344-55"
    msg = MessageBuilder.build("pacs.008", debtor_account=dirty_iban)
    report = Validator.validate(msg)
    assert report.is_valid is True # Should be sanitized and valid

def test_validator_empty_fields():
    msg = PaymentMessage(sender_bic=None, debtor_account=None)
    report = Validator.validate(msg)
    assert report.is_valid is True # Empty fields are not "invalid", just not present

# --- 4. Reconciler Cycle Handling ---

def test_reconciler_infinite_loop_protection():
    msg_a = MessageBuilder.build("pacs.008", message_id="A", end_to_end_id="X")
    msg_b = MessageBuilder.build("pacs.008", message_id="B", end_to_end_id="X")
    
    # These match each other. trace_lifecycle should handle this.
    timeline = Reconciler.trace_lifecycle(msg_a, [msg_a, msg_b])
    assert len(timeline) == 2
    assert msg_a in timeline
    assert msg_b in timeline

# --- 5. Boundary Amounts ---

def test_boundary_amounts():
    # Extremely large amount and many decimals
    large_amount = "999999999999999.9999999999"
    msg = MessageBuilder.build("pacs.008", amount=large_amount)
    assert msg.amount == large_amount # Should preserve as string

def test_parser_large_mt_amount():
    mt = b"{1:F01SENDERUS33AXXX0000000000}{4:\n:32A:231024USD999999999999,99\n-}"
    parser = OpenPurseParser(mt)
    msg = parser.parse()
    assert msg.amount == "999999999999.99"
    assert msg.currency == "USD"

def test_parser_non_iso_xml():
    # Plain XML without ISO namespace
    xml = b"<Root><Id>PLAIN_ID</Id><Amt currency='EUR'>50.00</Amt></Root>"
    parser = OpenPurseParser(xml)
    msg = parser.parse()
    # Should still extract if simple mapping fallback exists
    # Currently parser expects 'ns:' prefix in _get_text for ISO.
    # Let's see if it handles it.
    assert msg.message_id is None # No MsgId tag, should be None, not crash

def test_reconciler_fuzzy_amount():
    # 100 EUR initiation, 99.50 EUR notification (0.5% fee)
    msg1 = MessageBuilder.build("pacs.008", end_to_end_id="FEETX", amount="100.00", currency="EUR")
    msg2 = MessageBuilder.build("camt.054", end_to_end_id="FEETX", amount="99.50", currency="EUR")
    
    # Exact match fails
    assert Reconciler.is_match(msg1, msg2, fuzzy_amount=False) is False
    # Fuzzy match (1%) passes
    assert Reconciler.is_match(msg1, msg2, fuzzy_amount=True) is True
