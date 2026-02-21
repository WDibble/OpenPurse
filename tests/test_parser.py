import pytest
from openpurse.parser import OpenPurseParser

# The agent will expand this file, but this gives it the necessary starting structure.

MOCK_PACS008 = b"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08">
    <FIToFICstmrCdtTrf>
        <GrpHdr>
            <MsgId>MSG12345</MsgId>
        </GrpHdr>
        <CdtTrfTxInf>
            <PmtId>
                <EndToEndId>E2E98765</EndToEndId>
            </PmtId>
            <IntrBkSttlmAmt Ccy="EUR">1500.00</IntrBkSttlmAmt>
            <Dbtr>
                <Nm>John Doe</Nm>
            </Dbtr>
            <Cdtr>
                <Nm>Jane Smith</Nm>
            </Cdtr>
        </CdtTrfTxInf>
    </FIToFICstmrCdtTrf>
</Document>
"""

def test_pacs008_flattening():
    parser = OpenPurseParser(MOCK_PACS008)
    result = parser.flatten()
    
    assert result["message_id"] == "MSG12345"
    assert result["end_to_end_id"] == "E2E98765"
    assert result["amount"] == 1500.00
    assert result["currency"] == "EUR"
    assert result["debtor_name"] == "John Doe"
    assert result["creditor_name"] == "Jane Smith"