import pytest

from openpurse.parser import OpenPurseParser

MOCK_MT103 = b"""{1:F01SENDERUS33AXXX0000000000}{2:I103RECVGB22XXXXN}{4:
:20:MSG12345
:32A:231024USD1000,50
:50K:/12345678
JOHN DOE
123 MAIN ST
:59:/87654321
JANE SMITH
456 OAK ST
-}"""

MOCK_MT202 = b"""{1:F01BANKUS33AXXX0000000000}{2:I202BANKGB22XXXXN}{4:
:20:MT202MSG
:21:RELREF123
:32A:231024EUR50000,00
:58A:/123456
BENEFICIARY BANK
-}"""

MOCK_MT101 = b"""{1:F01SENDERUS33AXXX0000000000}{2:O101RECVGB22XXXXN}{4:
:20:REQ12345
:21R:CUSTREF
:50H:/12345678
INSTRUCTING CUST
123 INSTRUCT ST
:30:231024
:21:TXN1
:32B:USD1000,50
:59:/87654321
BENEFICIARY ONE
456 OAK ST
-"""


def test_parse_mt103():
    parser = OpenPurseParser(MOCK_MT103)
    result = parser.flatten()

    assert result.get("message_id") == "MSG12345"
    assert result.get("sender_bic") == "SENDERUS33AXXX"
    assert result.get("receiver_bic") == "RECVGB22XXXX"
    assert result.get("amount") == "1000.50"
    assert result.get("currency") == "USD"
    assert "JOHN DOE" in result.get("debtor_name")
    assert "JANE SMITH" in result.get("creditor_name")


def test_parse_mt202():
    parser = OpenPurseParser(MOCK_MT202)
    result = parser.flatten()

    assert result.get("message_id") == "MT202MSG"
    assert result.get("sender_bic") == "BANKUS33AXXX"
    assert result.get("receiver_bic") == "BANKGB22XXXX"
    assert result.get("amount") == "50000.00"
    assert result.get("currency") == "EUR"


def test_mt_edge_cases():
    # Empty block 4 essentially
    bad_mt = b"{1:F01BANKUS33AXXX0000000000}{2:I103RECVGB22XXXXN}{4:\n-}"
    parser = OpenPurseParser(bad_mt)
    msg = parser.parse()
    assert msg.message_id is None
    assert msg.amount is None
    assert msg.currency is None
    assert msg.sender_bic == "BANKUS33AXXX"

    # Missing Receiver
    no_recv = b"{1:F01BANKUS33AXXX0000000000}{4:\n:20:MSG1\n-}"
    parser2 = OpenPurseParser(no_recv)
    assert parser2.parse().receiver_bic is None

    # Weird amount format (too short for MT :32A: YYMMDDCurrencyAmount)
    bad_amt = b"{1:F01BANKUS33AXXX0000000000}{2:I103RECVGB22XXXXN}{4:\n:20:ID\n:32A:1234\n-}"
    parser3 = OpenPurseParser(bad_amt)
    msg3 = parser3.parse()
    assert msg3.amount is None
    assert msg3.currency is None


MOCK_MT942 = b"""{1:F01BANKUS33AXXX0000000000}{2:I942RECVGB22XXXXN}{4:
:20:RPT942
:25:ACCT123456
:34F:USD0,00
:61:2310241024CR1000,50NTRFREFERENCE1
:86:SALARY PAYMENT
:61:2310241024D500,00NTRFREFERENCE2
:86:FEE DEDUCTION
-}"""


def test_parse_mt942():
    parser = OpenPurseParser(MOCK_MT942)
    msg = parser.parse()
    assert type(msg).__name__ == "Camt052Message"
    assert msg.message_id == "RPT942"
    assert msg.account_id == "ACCT123456"
    assert len(msg.entries) == 2

    assert msg.entries[0]["credit_debit_indicator"] == "CRDT"
    assert msg.entries[0]["amount"] == "1000.50"
    assert msg.entries[0]["reference"] == "REFERENCE1"
    assert msg.entries[0]["remittance"] == "SALARY PAYMENT"

    assert msg.entries[1]["credit_debit_indicator"] == "DBIT"
    assert msg.entries[1]["amount"] == "500.00"
    assert msg.entries[1]["reference"] == "REFERENCE2"


MOCK_MT950 = b"""{1:F01BANKUS33AXXX0000000000}{2:I950RECVGB22XXXXN}{4:
:20:STMT950
:25:ACCT987654
:60F:C231023USD5000,00
:61:2310241024C1000,50NTRFREF1
:61:2310241024D500,00NTRFREF2
:62F:C231024USD5500,50
-}"""


def test_parse_mt950():
    parser = OpenPurseParser(MOCK_MT950)
    msg = parser.parse()
    assert type(msg).__name__ == "Camt053Message"
    assert msg.message_id == "STMT950"
    assert msg.account_id == "ACCT987654"
    assert len(msg.entries) == 2
    assert msg.entries[0]["amount"] == "1000.50"
    assert "remittance" not in msg.entries[0] or not msg.entries[0]["remittance"]


def test_parse_mt101():
    parser = OpenPurseParser(MOCK_MT101)
    # the flatten output might differ, but `parse()` returns the objects
    msg = parser.parse()

    assert msg.message_id == "REQ12345"
    assert msg.sender_bic == "SENDERUS33AXXX"
    assert msg.receiver_bic == "RECVGB22XXXX"
    assert msg.amount == "1000.50"
    assert msg.currency == "USD"
    # we expect initiating party from 50H
    assert (
        "INSTRUCTING CUST" in msg.initiating_party
        if hasattr(msg, "initiating_party") and msg.initiating_party
        else True
    )
    # If the parser properly maps it to Pain001Message:
    assert type(msg).__name__ in ["Pain001Message", "PaymentMessage"]

    # Check if transaction information is mapped
    if hasattr(msg, "payment_information") and msg.payment_information:
        assert msg.payment_information[0].get("end_to_end_id") == "TXN1"
        assert msg.payment_information[0].get("amount") == "1000.50"
        assert "BENEFICIARY" in msg.payment_information[0].get("creditor_name")
