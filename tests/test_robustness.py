import lxml.etree
import pytest
import os

from openpurse.builder import MessageBuilder
from openpurse.models import Pain002Message, PaymentMessage
from openpurse.parser import OpenPurseParser
from openpurse.reconciler import Reconciler
from openpurse.validator import Validator

# --- 1. Parser Resilience: Malformed Input ---


def test_parser_malformed_xml():
    malformed_xml = b"<Document><MsgId>Broken"  # Unclosed
    parser = OpenPurseParser(malformed_xml)
    # The parser should not crash, it should return an empty PaymentMessage or handle lxml errors
    msg = parser.parse()
    assert isinstance(msg, PaymentMessage)
    assert msg.message_id is None


def test_parser_malformed_mt():
    malformed_mt = b"{1:F01BANKUS33AXXX0000000000}{4:\n:20:TRUNCATED"  # Missing closing -}
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
    assert "Иван Петров" in msg.debtor_name  # Ivan Petrov
    assert "💰" in msg.debtor_name  # Money bag emoji
    assert "中文" in msg.creditor_name  # Chinese


# --- 3. Validator Robustness ---


def test_validator_iban_sanitization():
    # IBAN with dots and hyphens and mixed case
    # GB90 MIDL 4005 1522 3344 55
    dirty_iban = "gb90.midl-40051522.3344-55"
    msg = MessageBuilder.build("pacs.008", debtor_account=dirty_iban)
    report = Validator.validate(msg)
    assert report.is_valid is True  # Should be sanitized and valid


def test_validator_empty_fields():
    msg = PaymentMessage(sender_bic=None, debtor_account=None)
    report = Validator.validate(msg)
    assert report.is_valid is True  # Empty fields are not "invalid", just not present


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
    assert msg.amount == large_amount  # Should preserve as string


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
    # Verify parser handles missing mandatory tags gracefully.
    assert msg.message_id is None  # No MsgId tag, should be None, not crash


def test_reconciler_fuzzy_amount():
    # 100 EUR initiation, 99.50 EUR notification (0.5% fee)
    msg1 = MessageBuilder.build("pacs.008", end_to_end_id="FEETX", amount="100.00", currency="EUR")
    msg2 = MessageBuilder.build("camt.054", end_to_end_id="FEETX", amount="99.50", currency="EUR")

    # Exact match fails
    assert Reconciler.is_match(msg1, msg2, fuzzy_amount=False) is False
    # Fuzzy match (1%) passes
    assert Reconciler.is_match(msg1, msg2, fuzzy_amount=True) is True


# --- 6. Garbage & Malicious Input ---


def test_parser_pure_garbage_input():
    """Test that the parser doesn't crash with non-text binary garbage."""
    garbage = os.urandom(1024)
    parser = OpenPurseParser(garbage)
    msg = parser.parse()
    assert isinstance(msg, PaymentMessage)
    # Binary garbage shouldn't match startswith(b"{1:") or yield valid XML
    assert msg.message_id is None


def test_parser_deep_nesting_failures():
    """Test that partial or deeply nested missing elements don't cause crashes."""
    # pacs.008 with nested parts missing halfway
    xml = b"""<?xml version="1.0" encoding="UTF-8"?>
    <Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08">
        <FIToFICstmrCdtTrf>
            <CdtTrfTxInf>
                <PmtId>
                    <!-- EndToEndId missing here -->
                </PmtId>
                <InstdAgt>
                    <!-- FinInstnId missing here -->
                    <BranchId><Id>BRANCH123</Id></BranchId>
                </InstdAgt>
            </CdtTrfTxInf>
        </FIToFICstmrCdtTrf>
    </Document>"""
    parser = OpenPurseParser(xml)
    msg = parser.parse()
    assert msg.end_to_end_id is None  # Gracefully None
    assert msg.receiver_bic is None


def test_parser_unsupported_encoding():
    """Test handling of XML with non-UTF8 encoding declaration."""
    # ISO-8859-1 (Latin-1)
    xml = (
        '<?xml version="1.0" encoding="ISO-8859-1"?>'
        '<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08">'
        "<FIToFICstmrCdtTrf><GrpHdr><MsgId>LATIN_ID_\xe9</MsgId></GrpHdr></FIToFICstmrCdtTrf>"
        "</Document>"
    ).encode("iso-8859-1")

    parser = OpenPurseParser(xml)
    msg = parser.parse()
    # lxml handle encoding from the declaration usually
    assert "LATIN_ID" in msg.message_id
    assert msg.message_id.endswith("é")


def test_parser_huge_values():
    """Test parser with extremely long strings to check for buffer/slowdown issues."""
    huge_id = "A" * 100000  # 100KB string
    xml = f"""<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08">
        <FIToFICstmrCdtTrf><GrpHdr><MsgId>{huge_id}</MsgId></GrpHdr></FIToFICstmrCdtTrf>
    </Document>""".encode()
    parser = OpenPurseParser(xml)
    msg = parser.parse()
    assert msg.message_id == huge_id
