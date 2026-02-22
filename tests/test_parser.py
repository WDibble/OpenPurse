import pytest
from openpurse.parser import OpenPurseParser
from openpurse.models import PaymentMessage, Camt054Message, Pacs008Message, Camt004Message

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

MOCK_ADDRESS_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08">
    <FIToFICstmrCdtTrf>
        <GrpHdr>
            <MsgId>ADDR_TEST</MsgId>
        </GrpHdr>
        <CdtTrfTxInf>
            <Dbtr>
                <Nm>Debtor Name</Nm>
                <PstlAdr>
                    <StrtNm>Wall Street</StrtNm>
                    <BldgNb>101</BldgNb>
                    <PstCd>10005</PstCd>
                    <TwnNm>New York</TwnNm>
                    <Ctry>US</Ctry>
                    <AdrLine>Floor 42</AdrLine>
                    <AdrLine>Suite B</AdrLine>
                </PstlAdr>
            </Dbtr>
            <Cdtr>
                <Nm>Creditor Name</Nm>
                <!-- Missing PstlAdr to ensure it safely resolves to None -->
            </Cdtr>
        </CdtTrfTxInf>
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

def test_empty_input():
    parser = OpenPurseParser(b"")
    msg = parser.parse()
    assert msg.message_id is None
    
def test_address_parsing():
    parser = OpenPurseParser(MOCK_ADDRESS_XML)
    msg = parser.parse()
    
    assert msg.debtor_name == "Debtor Name"
    assert msg.debtor_address is not None
    assert msg.debtor_address.street_name == "Wall Street"
    assert msg.debtor_address.building_number == "101"
    assert msg.debtor_address.post_code == "10005"
    assert msg.debtor_address.town_name == "New York"
    assert msg.debtor_address.country == "US"
    assert len(msg.debtor_address.address_lines) == 2
    assert msg.debtor_address.address_lines[0] == "Floor 42"
    
    assert msg.creditor_name == "Creditor Name"
    assert msg.creditor_address is None

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

MOCK_CAMT054 = b"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.054.001.02">
    <BkToCstmrDbtCdtNtfctn>
        <GrpHdr>
            <MsgId>MSG_CAMT054</MsgId>
        </GrpHdr>
        <Ntfctn>
            <Id>NTF123</Id>
            <Acct>
                <Id><IBAN>SE123456</IBAN></Id>
            </Acct>
            <Ntry>
                <NtryRef>REF001</NtryRef>
                <Amt Ccy="SEK">100.00</Amt>
                <CdtDbtInd>CRDT</CdtDbtInd>
                <Sts>BOOK</Sts>
                <BookgDt><Dt>2023-10-24</Dt></BookgDt>
            </Ntry>
        </Ntfctn>
    </BkToCstmrDbtCdtNtfctn>
</Document>
"""

MOCK_PACS008_DETAILED = b"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08">
    <FIToFICstmrCdtTrf>
        <GrpHdr>
            <MsgId>PACS_008_MSG</MsgId>
            <SttlmInf><SttlmMtd>CLRG</SttlmMtd></SttlmInf>
        </GrpHdr>
        <CdtTrfTxInf>
            <PmtId>
                <InstrId>INSTR_999</InstrId>
                <EndToEndId>E2E_999</EndToEndId>
            </PmtId>
            <InstdAmt Ccy="EUR">250.00</InstdAmt>
            <Dbtr><Nm>Global Corp</Nm></Dbtr>
            <Cdtr><Nm>Local Shop</Nm></Cdtr>
            <RmtInf><Ustrd>Invoice 12345</Ustrd></RmtInf>
        </CdtTrfTxInf>
    </FIToFICstmrCdtTrf>
</Document>
"""

def test_parse_detailed_camt054():
    parser = OpenPurseParser(MOCK_CAMT054)
    msg = parser.parse_detailed()

    assert isinstance(msg, Camt054Message)
    assert msg.message_id == "MSG_CAMT054"
    assert msg.notification_id == "NTF123"
    assert msg.account_id == "SE123456"
    assert len(msg.entries) == 1
    assert msg.entries[0]["reference"] == "REF001"
    assert msg.entries[0]["amount"] == "100.00"
    assert msg.entries[0]["currency"] == "SEK"
    assert msg.entries[0]["status"] == "BOOK"
    assert msg.entries[0]["booking_date"] == "2023-10-24"

def test_parse_detailed_pacs008():
    parser = OpenPurseParser(MOCK_PACS008_DETAILED)
    msg = parser.parse_detailed()

    assert isinstance(msg, Pacs008Message)
    assert msg.message_id == "PACS_008_MSG"
    assert msg.settlement_method == "CLRG"
    assert len(msg.transactions) == 1
    assert msg.transactions[0]["instruction_id"] == "INSTR_999"
    assert msg.transactions[0]["end_to_end_id"] == "E2E_999"
    assert msg.transactions[0]["instructed_amount"] == "250.00"
    assert msg.transactions[0]["instructed_currency"] == "EUR"
    assert msg.transactions[0]["debtor_name"] == "Global Corp"
    assert msg.transactions[0]["creditor_name"] == "Local Shop"
    assert msg.transactions[0]["remittance_info"] == "Invoice 12345"

MOCK_CAMT004 = b"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.004.001.10">
    <RtrAcct>
        <MsgHdr>
            <MsgId>MSG_CAMT004</MsgId>
            <CreDtTm>2023-10-24T12:00:00Z</CreDtTm>
            <OrgnlBizQry>
                <MsgId>QRY123</MsgId>
            </OrgnlBizQry>
        </MsgHdr>
        <RptOrErr>
            <AcctRpt>
                <AcctId>
                    <IBAN>GB123456789</IBAN>
                </AcctId>
                <AcctOrErr>
                    <Acct>
                        <Nm>Main Account</Nm>
                        <Ccy>GBP</Ccy>
                        <Ownr>
                            <Nm>Corporate Entity</Nm>
                        </Ownr>
                        <Svcr>
                            <FinInstnId>
                                <BICFI>BANKGB22</BICFI>
                            </FinInstnId>
                        </Svcr>
                        <Sts>ENAB</Sts>
                        <MulBal>
                            <Amt Ccy="GBP">50000.00</Amt>
                            <CdtDbtInd>CRDT</CdtDbtInd>
                            <Tp>
                                <Cd>CLAV</Cd>
                            </Tp>
                            <ValDt>
                                <Dt>2023-10-24</Dt>
                            </ValDt>
                        </MulBal>
                        <CurBilLmt>
                            <CtrPtyId>
                                <FinInstnId>
                                    <BICFI>BANKDEF</BICFI>
                                </FinInstnId>
                            </CtrPtyId>
                            <LmtAmt>
                                <AmtWthCcy Ccy="GBP">100000.00</AmtWthCcy>
                            </LmtAmt>
                            <CdtDbtInd>CRDT</CdtDbtInd>
                        </CurBilLmt>
                    </Acct>
                </AcctOrErr>
            </AcctRpt>
        </RptOrErr>
    </RtrAcct>
</Document>
"""

def test_parse_detailed_camt004():
    parser = OpenPurseParser(MOCK_CAMT004)
    msg = parser.parse_detailed()

    assert isinstance(msg, Camt004Message)
    assert msg.message_id == "MSG_CAMT004"
    assert msg.creation_date_time == "2023-10-24T12:00:00Z"
    assert msg.original_business_query == "QRY123"
    assert msg.account_id == "GB123456789"
    assert msg.account_owner == "Corporate Entity"
    assert msg.account_servicer == "BANKGB22"
    assert msg.account_status == "ENAB"
    assert msg.account_currency == "GBP"
    
    assert len(msg.balances) == 1
    assert msg.balances[0]["amount"] == "50000.00"
    assert msg.balances[0]["currency"] == "GBP"
    assert msg.balances[0]["type"] == "CLAV"
    assert msg.balances[0]["credit_debit_indicator"] == "CRDT"
    assert msg.balances[0]["value_date"] == "2023-10-24"

    assert len(msg.limits) == 1
    assert msg.limits[0]["amount"] == "100000.00"
    assert msg.limits[0]["currency"] == "GBP"
    assert msg.limits[0]["credit_debit_indicator"] == "CRDT"