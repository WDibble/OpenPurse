import pytest
from openpurse.parser import OpenPurseParser
from openpurse.reconciler import Reconciler
from openpurse.models import Camt056Message, Camt029Message, Pacs008Message

def test_exception_lifecycle_reconciliation():
    """
    Simulates a full investigation lifecycle:
    1. A Payment is sent (pacs.008)
    2. A Recall is requested (camt.056)
    3. A Resolution is received (camt.029)
    And verifies the reconciler can link them all.
    """
    # 1. Original Payment (pacs.008)
    pacs_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
    <Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08">
        <FIToFICstmrCdtTrf>
            <GrpHdr><MsgId>PAYMENT-101</MsgId></GrpHdr>
            <CdtTrfTxInf>
                <PmtId>
                    <EndToEndId>E2E-REF-001</EndToEndId>
                    <UETR>550e8400-e29b-41d4-a716-446655440000</UETR>
                </PmtId>
                <IntrBkSttlmAmt Ccy="USD">100.00</IntrBkSttlmAmt>
            </CdtTrfTxInf>
        </FIToFICstmrCdtTrf>
    </Document>
    """
    
    # 2. Recall Request (camt.056)
    recall_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
    <Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.056.001.08">
        <FIToFICstmrCdtTrfRcl>
            <Assgnmt><Id>ASS-99</Id></Assgnmt>
            <Case><Id>CASE-ABC</Id></Case>
            <OrgnlGrpInf>
                <OrgnlMsgId>PAYMENT-101</OrgnlMsgId>
                <OrgnlMsgNmId>pacs.008.001.08</OrgnlMsgNmId>
            </OrgnlGrpInf>
            <Undrlyg>
                <OrgnlEndToEndId>E2E-REF-001</OrgnlEndToEndId>
                <OrgnlUETR>550e8400-e29b-41d4-a716-446655440000</OrgnlUETR>
            </Undrlyg>
        </FIToFICstmrCdtTrfRcl>
    </Document>
    """
    
    # 3. Resolution (camt.029)
    resolution_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
    <Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.029.001.09">
        <RsltnOfInvstgtn>
            <Assgnmt><Id>ASS-100</Id></Assgnmt>
            <Case><Id>CASE-ABC</Id></Case>
            <Sts><Conf>Accepted</Conf></Sts>
            <CxlDtls>
                <OrgnlEndToEndId>E2E-REF-001</OrgnlEndToEndId>
                <OrgnlUETR>550e8400-e29b-41d4-a716-446655440000</OrgnlUETR>
                <TxCxlSts>Cancelled</TxCxlSts>
            </CxlDtls>
        </RsltnOfInvstgtn>
    </Document>
    """
    
    payment = OpenPurseParser(pacs_xml).parse_detailed()
    recall = OpenPurseParser(recall_xml).parse_detailed()
    resolution = OpenPurseParser(resolution_xml).parse_detailed()
    
    # Verification of Types
    assert isinstance(payment, Pacs008Message)
    assert isinstance(recall, Camt056Message)
    assert isinstance(resolution, Camt029Message)
    
    # Verification of Matching Logic
    # Recall matches Payment via OriginalMsgId
    assert Reconciler.is_match(recall, payment) is True
    
    # Recall matches Payment via UETR (Tier 1)
    assert recall.uetr == payment.uetr
    
    # Resolution matches Recall via Case ID
    assert Reconciler.is_match(resolution, recall) is True
    assert resolution.case_id == "CASE-ABC"
    
    # Full Timeline check
    history = Reconciler.trace_lifecycle(payment, [payment, recall, resolution])
    assert len(history) == 3
    assert payment in history
    assert recall in history
    assert resolution in history
    
    # Check specific details
    assert recall.recall_reason is None # Since we didn't specify one in the mock
    assert resolution.investigation_status == "Accepted"
