import pytest
from openpurse.models import PaymentMessage, Camt053Message
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

def test_translate_202_pacs009():
    msg = PaymentMessage(
        message_id="BANK2BANK",
        amount="1000000.00",
        currency="USD",
        sender_bic="BBBBUS33",
        receiver_bic="CCCCGB22"
    )
    mt_bytes = Translator.to_mt(msg, "202")
    assert b"{2:I202CCCCGB22" in mt_bytes
    assert b":58A:/CCCCGB22" in mt_bytes
    assert b":50K:" not in mt_bytes # 202 omits ordering customer
    
    mx_bytes = Translator.to_mx(msg, "pacs.009")
    assert b"<FICdtTrf>" in mx_bytes
    assert b"<BICFI>BBBBUS33</BICFI>" in mx_bytes

def test_translate_900_910_camt054():
    msg = PaymentMessage(
        message_id="NOTIFYDEBIT",
        amount="-50.00",
        currency="EUR",
        sender_bic="BANKDEFF",
        receiver_bic="CUST1234",
        debtor_name="Alice (Debited)"
    )
    mt_bytes = Translator.to_mt(msg, "900")
    assert b"{2:I900CUST1234" in mt_bytes
    assert b":52A:/BANKDEFF" in mt_bytes
    assert b"Alice (Debited)" in mt_bytes
    assert b"-50,00" in mt_bytes

    mx_bytes = Translator.to_mx(msg, "camt.054")
    assert b"<CdtDbtInd>DBIT</CdtDbtInd>" in mx_bytes
    assert b'<Amt Ccy="EUR">50.0</Amt>' in mx_bytes # abs amt
    
    msg.amount = "100.00"
    msg.creditor_name = "Bob (Credited)"
    mt_bytes_910 = Translator.to_mt(msg, "910")
    assert b"{2:I910CUST1234" in mt_bytes_910
    
    mx_bytes_crdt = Translator.to_mx(msg, "camt.054")
    assert b"<CdtDbtInd>CRDT</CdtDbtInd>" in mx_bytes_crdt

def test_translate_940_camt053():
    msg = Camt053Message(
        message_id="STMT123",
        amount="1000.25",
        currency="GBP",
        sender_bic="BANKGB22",
        entries=[
            {
                "reference": "TXN001",
                "amount": "500.00",
                "credit_debit_indicator": "CRDT",
                "remittance": "Salary"
            },
            {
                "reference": "TXN002",
                "amount": "25.50",
                "credit_debit_indicator": "DBIT",
                "remittance": "Fee"
            }
        ]
    )
    mt_bytes = Translator.to_mt(msg, "940")
    assert b"{2:I940" in mt_bytes
    assert b":61:" in mt_bytes
    assert b"C500,00NTRFTXN001" in mt_bytes
    assert b":86:Salary" in mt_bytes
    assert b"D25,50NTRFTXN002" in mt_bytes
    
    mx_bytes = Translator.to_mx(msg, "camt.053")
    assert b"<BkToCstmrStmt>" in mx_bytes
    assert b"<NtryRef>TXN001</NtryRef>" in mx_bytes
    assert b"<CdtDbtInd>CRDT</CdtDbtInd>" in mx_bytes
    assert b"<CdtDbtInd>DBIT</CdtDbtInd>" in mx_bytes
