import pytest
from openpurse.models import PaymentMessage
from openpurse.translator import Translator
from openpurse.parser import OpenPurseParser

def test_translate_to_mt():
    msg = PaymentMessage(
        message_id="TRANSLATEST",
        amount="500.50",
        currency="USD",
        sender_bic="BANKUS33XXX",
        receiver_bic="BANKGB22XXX",
        debtor_name="Alice",
        creditor_name="Bob"
    )
    
    mt_bytes = Translator.to_mt(msg, "103")
    assert b"{1:F01BANKUS33XXXX" in mt_bytes
    assert b"{2:I103BANKGB22XXXX" in mt_bytes
    assert b":20:TRANSLATEST" in mt_bytes
    assert b"USD500,50" in mt_bytes
    
    # Verify Parser can cleanly round-trip the generated translation!
    parser = OpenPurseParser(mt_bytes)
    roundtrip = parser.parse()
    
    assert roundtrip.message_id == "TRANSLATEST"
    assert roundtrip.amount == "500.50"
    assert roundtrip.currency == "USD"
    assert "Alice" in roundtrip.debtor_name

def test_translate_to_mx():
    msg = PaymentMessage(
        message_id="XMLTEST",
        end_to_end_id="E2E123",
        amount="750.00",
        currency="EUR",
        sender_bic="XMLUS33",
        receiver_bic="XMLGB22",
        debtor_name="Charlie",
        creditor_name="Dave"
    )
    
    mx_bytes = Translator.to_mx(msg, "pacs.008")
    assert b"<MsgId>XMLTEST</MsgId>" in mx_bytes
    assert b'Ccy="EUR">750.00</IntrBkSttlmAmt>' in mx_bytes
    
    # Verify Parser can cleanly round-trip the generated translation!
    parser = OpenPurseParser(mx_bytes)
    roundtrip = parser.parse()
    
    assert roundtrip.message_id == "XMLTEST"
    assert roundtrip.amount == "750.00"
    assert roundtrip.currency == "EUR"
    assert roundtrip.sender_bic == "XMLUS33"
    assert roundtrip.creditor_name == "Dave"

def test_unsupported_translations():
    msg = PaymentMessage()
    with pytest.raises(NotImplementedError):
        Translator.to_mt(msg, "999")
    with pytest.raises(NotImplementedError):
        Translator.to_mx(msg, "unknown.schema")
