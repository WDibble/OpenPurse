import pytest
from openpurse.parser import OpenPurseParser
from openpurse.models import Pacs004Message, Pacs009Message


def test_parse_pacs_004_payment_return():
    """Test extracting detailed fields from a PACS.004 Payment Return."""
    xml_data = b"""<?xml version="1.0" encoding="UTF-8"?>
    <Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.004.001.09">
        <PmtRtr>
            <GrpHdr>
                <CreDtTm>2023-11-20T10:00:00Z</CreDtTm>
            </GrpHdr>
            <OrgnlGrpInf>
                <OrgnlMsgId>MSG-9911</OrgnlMsgId>
                <OrgnlMsgNmId>pacs.008.001.08</OrgnlMsgNmId>
            </OrgnlGrpInf>
            <TxInf>
                <RtrId>RET-123</RtrId>
                <OrgnlEndToEndId>E2E-ORIG-456</OrgnlEndToEndId>
                <OrgnlTxId>TX-ORIG-789</OrgnlTxId>
                <OrgnlUETR>123e4567-e89b-12d3-a456-426614174000</OrgnlUETR>
                <RtrdIntrBkSttlmAmt Ccy="EUR">50000.00</RtrdIntrBkSttlmAmt>
                <RtrRsnInf>
                    <Rsn>
                        <Cd>AC03</Cd>
                    </Rsn>
                </RtrRsnInf>
            </TxInf>
        </PmtRtr>
    </Document>
    """
    
    parser = OpenPurseParser(xml_data)
    parsed = parser.parse_detailed()
    
    assert isinstance(parsed, Pacs004Message)
    assert parsed.creation_date_time == "2023-11-20T10:00:00Z"
    assert parsed.original_message_id == "MSG-9911"
    assert parsed.original_message_name_id == "pacs.008.001.08"
    assert parsed.uetr == "123e4567-e89b-12d3-a456-426614174000"
    
    assert len(parsed.transactions) == 1
    tx = parsed.transactions[0]
    assert tx["return_id"] == "RET-123"
    assert tx["original_end_to_end_id"] == "E2E-ORIG-456"
    assert tx["returned_amount"] == "50000.00"
    assert tx["returned_currency"] == "EUR"
    assert tx["return_reason"] == "AC03"


def test_parse_pacs_009_financial_institution_credit_transfer():
    """Test extracting detailed fields from a PACS.009 FI Credit Transfer."""
    xml_data = b"""<?xml version="1.0" encoding="UTF-8"?>
    <Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.009.001.08">
        <FICdtTrf>
            <GrpHdr>
                <CreDtTm>2023-11-21T14:30:00Z</CreDtTm>
                <SttlmInf>
                    <SttlmMtd>INDA</SttlmMtd>
                </SttlmInf>
            </GrpHdr>
            <CdtTrfTxInf>
                <PmtId>
                    <InstrId>INSTR-009</InstrId>
                    <EndToEndId>E2E-009-ABC</EndToEndId>
                    <TxId>TX-009-XYZ</TxId>
                    <UETR>987e6543-e21b-24d4-b654-426614174111</UETR>
                </PmtId>
                <IntrBkSttlmAmt Ccy="USD">1000000.00</IntrBkSttlmAmt>
                <Dbtr>
                    <BICFI>BOFUS33</BICFI>
                </Dbtr>
                <Cdtr>
                    <BICFI>CHASUS33</BICFI>
                </Cdtr>
            </CdtTrfTxInf>
        </FICdtTrf>
    </Document>
    """
    
    parser = OpenPurseParser(xml_data)
    parsed = parser.parse_detailed()
    
    assert isinstance(parsed, Pacs009Message)
    assert parsed.creation_date_time == "2023-11-21T14:30:00Z"
    assert parsed.settlement_method == "INDA"
    assert parsed.uetr == "987e6543-e21b-24d4-b654-426614174111"
    assert parsed.end_to_end_id == "E2E-009-ABC"
    
    assert len(parsed.transactions) == 1
    tx = parsed.transactions[0]
    assert tx["instruction_id"] == "INSTR-009"
    assert tx["amount"] == "1000000.00"
    assert tx["currency"] == "USD"
    assert tx["debtor"] == "BOFUS33"
    assert tx["creditor"] == "CHASUS33"
