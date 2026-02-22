import pytest
from openpurse.validator import Validator
from openpurse.parser import OpenPurseParser

def test_pacs008_v13_xsd_validation_success():
    """
    Tests that a valid pacs.008.001.13 XML passes strict XSD validation.
    """
    valid_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.13">
    <FIToFICstmrCdtTrf>
        <GrpHdr>
            <MsgId>MSG123</MsgId>
            <CreDtTm>2026-02-22T22:00:00</CreDtTm>
            <NbOfTxs>1</NbOfTxs>
            <SttlmInf>
                <SttlmMtd>INDA</SttlmMtd>
            </SttlmInf>
        </GrpHdr>
        <CdtTrfTxInf>
            <PmtId>
                <EndToEndId>E2E123</EndToEndId>
            </PmtId>
            <IntrBkSttlmAmt Ccy="USD">100.00</IntrBkSttlmAmt>
            <ChrgBr>SLEV</ChrgBr>
            <Dbtr>
                <Nm>John Doe</Nm>
            </Dbtr>
            <DbtrAgt>
                <FinInstnId>
                    <BICFI>BANKUS33XXX</BICFI>
                </FinInstnId>
            </DbtrAgt>
            <CdtrAgt>
                <FinInstnId>
                    <BICFI>BANKGB22XXX</BICFI>
                </FinInstnId>
            </CdtrAgt>
            <Cdtr>
                <Nm>Jane Smith</Nm>
            </Cdtr>
        </CdtTrfTxInf>
    </FIToFICstmrCdtTrf>
</Document>
"""
    report = Validator.validate_schema(valid_xml)
    assert report.is_valid is True, f"Validation failed with errors: {report.errors}"

def test_pacs008_v13_xsd_validation_failure_missing_element():
    """
    Tests that a pacs.008.001.13 XML missing a mandatory element fails strict XSD validation.
    """
    # Missing <CreDtTm> in <GrpHdr> which is mandatory in pacs.008
    invalid_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.13">
    <FIToFICstmrCdtTrf>
        <GrpHdr>
            <MsgId>MSG123</MsgId>
            <NbOfTxs>1</NbOfTxs>
            <SttlmInf>
                <SttlmMtd>INDA</SttlmMtd>
            </SttlmInf>
        </GrpHdr>
        <CdtTrfTxInf>
            <PmtId>
                <EndToEndId>E2E123</EndToEndId>
            </PmtId>
            <IntrBkSttlmAmt Ccy="USD">100.00</IntrBkSttlmAmt>
            <ChrgBr>SLEV</ChrgBr>
            <Dbtr>
                <Nm>John Doe</Nm>
            </Dbtr>
            <DbtrAgt>
                <FinInstnId>
                    <BICFI>BANKUS33XXX</BICFI>
                </FinInstnId>
            </DbtrAgt>
            <CdtrAgt>
                <FinInstnId>
                    <BICFI>BANKGB22XXX</BICFI>
                </FinInstnId>
            </CdtrAgt>
            <Cdtr>
                <Nm>Jane Smith</Nm>
            </Cdtr>
        </CdtTrfTxInf>
    </FIToFICstmrCdtTrf>
</Document>
"""
    report = Validator.validate_schema(invalid_xml)
    assert report.is_valid is False
    assert any("CreDtTm" in err for err in report.errors)

def test_unsupported_namespace():
    """
    Tests that a document with an unknown namespace returns an error in strict validation.
    """
    xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:unknown.001.001.01">
</Document>
"""
    report = Validator.validate_schema(xml)
    assert report.is_valid is False
    assert "Unsupported namespace" in report.errors[0]
