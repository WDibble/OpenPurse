import pytest
from openpurse.parser import OpenPurseParser

def test_bah_unwrapping_and_extraction():
    """
    Verifies that the parser correctly unwraps a Document from a BusMsg/AppHdr wrapper
    and merges routing information from the Business Application Header.
    """
    bah_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
    <BusMsg xmlns="urn:iso:std:iso:20022:tech:xsd:head.001.001.01">
        <AppHdr>
            <Fr>
                <FIId>
                    <FinInstnId>
                        <BICFI>SENDERBAH</BICFI>
                    </FinInstnId>
                </FIId>
            </Fr>
            <To>
                <FIId>
                    <FinInstnId>
                        <BICFI>RECEIVERBAH</BICFI>
                    </FinInstnId>
                </FIId>
            </To>
            <BizMsgIdr>BAH-MESSAGE-ID-999</BizMsgIdr>
        </AppHdr>
        <Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08">
            <FIToFICstmrCdtTrf>
                <GrpHdr>
                    <MsgId>DOC-MSG-123</MsgId>
                </GrpHdr>
                <CdtTrfTxInf>
                    <PmtId>
                        <EndToEndId>E2E-456</EndToEndId>
                    </PmtId>
                    <IntrBkSttlmAmt Ccy="GBP">2500.00</IntrBkSttlmAmt>
                </CdtTrfTxInf>
            </FIToFICstmrCdtTrf>
        </Document>
    </BusMsg>
    """
    
    parser = OpenPurseParser(bah_xml)
    parsed = parser.parse()
    
    # 1. Routing info from BAH
    assert parsed.sender_bic == "SENDERBAH"
    assert parsed.receiver_bic == "RECEIVERBAH"
    
    # 2. MsgId from Document (precedence check)
    assert parsed.message_id == "DOC-MSG-123"
    
    # 3. Core transaction data from Document
    assert parsed.amount == "2500.00"
    assert parsed.currency == "GBP"
    assert parsed.end_to_end_id == "E2E-456"

def test_bah_only_id_and_missing_document_msg_id():
    """
    Verifies that the BizMsgIdr from BAH is used when the inner Document lacks a MsgId.
    """
    bah_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
    <BusMsg xmlns="urn:iso:std:iso:20022:tech:xsd:head.001.001.01">
        <AppHdr>
            <BizMsgIdr>ONLY-IN-BAH</BizMsgIdr>
        </AppHdr>
        <Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08">
            <FIToFICstmrCdtTrf>
                <CdtTrfTxInf>
                    <IntrBkSttlmAmt Ccy="EUR">75.50</IntrBkSttlmAmt>
                </CdtTrfTxInf>
            </FIToFICstmrCdtTrf>
        </Document>
    </BusMsg>
    """
    parser = OpenPurseParser(bah_xml)
    parsed = parser.parse()
    
    assert parsed.message_id == "ONLY-IN-BAH"
    assert parsed.amount == "75.50"
    assert parsed.currency == "EUR"

def test_direct_app_hdr_root():
    """
    Verifies support for messages where AppHdr is the root (less common but possible).
    """
    app_hdr_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
    <AppHdr xmlns="urn:iso:std:iso:20022:tech:xsd:head.001.001.01">
        <Fr><FIId><FinInstnId><BICFI>DIRECTSEN</BICFI></FinInstnId></FIId></Fr>
        <BizMsgIdr>DIRECT-ID</BizMsgIdr>
    </AppHdr>
    """
    parser = OpenPurseParser(app_hdr_xml)
    parsed = parser.parse()
    
    assert parsed.sender_bic == "DIRECTSEN"
    assert parsed.message_id == "DIRECT-ID"
