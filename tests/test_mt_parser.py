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
