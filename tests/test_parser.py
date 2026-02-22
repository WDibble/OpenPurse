import pytest
from openpurse.parser import OpenPurseParser
from openpurse.models import PaymentMessage

MOCK_PACS008 = b"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08">
    <FIToFICstmrCdtTrf>
        <GrpHdr>
            <MsgId>MSG12345</MsgId>
            <InstgAgt>
                <FinInstnId>
                    <BICFI>SENDERUS33</BICFI>
                </FinInstnId>
            </InstgAgt>
            <InstdAgt>
                <FinInstnId>
                    <BICFI>RECVGB22</BICFI>
                </FinInstnId>
            </InstdAgt>
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

MOCK_CAMT052 = b"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.052.001.13">
    <BkToCstmrAcctRpt>
        <GrpHdr>
            <MsgId>RPT98765</MsgId>
        </GrpHdr>
        <Rpt>
            <Acct>
                <Svcr>
                    <FinInstnId>
                        <BICFI>SERVUS44</BICFI>
                    </FinInstnId>
                </Svcr>
            </Acct>
            <Ntry>
                <Amt Ccy="USD">500.50</Amt>
                <NtryDtls>
                    <TxDtls>
                        <RltdPties>
                            <Dbtr>
                                <Nm>Acme Corp</Nm>
                            </Dbtr>
                        </RltdPties>
                    </TxDtls>
                </NtryDtls>
            </Ntry>
        </Rpt>
    </BkToCstmrAcctRpt>
</Document>
"""

MOCK_MISSING_OPTIONAL = b"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08">
    <FIToFICstmrCdtTrf>
        <GrpHdr>
            <MsgId>MSG999</MsgId>
        </GrpHdr>
        <!-- Missing amounts, debtors, creditors -->
    </FIToFICstmrCdtTrf>
</Document>
"""

def test_pacs008_flattening():
    parser = OpenPurseParser(MOCK_PACS008)
    result = parser.flatten()
    
    assert result.get("message_id") == "MSG12345"
    assert result.get("end_to_end_id") == "E2E98765"
    assert result.get("amount") == "1500.00"
    assert result.get("currency") == "EUR"
    assert result.get("debtor_name") == "John Doe"
    assert result.get("creditor_name") == "Jane Smith"
    assert result.get("sender_bic") == "SENDERUS33"
    assert result.get("receiver_bic") == "RECVGB22"

def test_camt052_flattening():
    parser = OpenPurseParser(MOCK_CAMT052)
    result = parser.flatten()
    
    assert result.get("message_id") == "RPT98765"
    assert result.get("amount") == "500.50"
    assert result.get("currency") == "USD"
    assert result.get("debtor_name") == "Acme Corp"
    assert result.get("creditor_name") is None

def test_missing_optional_fields():
    parser = OpenPurseParser(MOCK_MISSING_OPTIONAL)
    result = parser.flatten()
    
    assert result.get("message_id") == "MSG999"
    assert result.get("amount") is None
    assert result.get("currency") is None
    assert result.get("debtor_name") is None
    assert result.get("creditor_name") is None

def test_parse_returns_payment_message():
    parser = OpenPurseParser(MOCK_PACS008)
    msg = parser.parse()
    
    assert isinstance(msg, PaymentMessage)
    assert msg.message_id == "MSG12345"
    assert msg.end_to_end_id == "E2E98765"
    assert msg.amount == "1500.00"
    assert msg.currency == "EUR"
    assert msg.debtor_name == "John Doe"
    assert msg.creditor_name == "Jane Smith"
    assert msg.sender_bic == "SENDERUS33"
    assert msg.receiver_bic == "RECVGB22"
    
    # Verify to_dict matches flatten perfectly
    assert msg.to_dict() == parser.flatten()