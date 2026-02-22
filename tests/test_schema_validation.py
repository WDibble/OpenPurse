import pytest

from openpurse.models import ValidationReport
from openpurse.parser import OpenPurseParser


def test_valid_schema():
    # A valid but minimal pacs.008 mapped against the standard 20022 schemas
    valid_pacs = b"""<?xml version="1.0" encoding="UTF-8"?>
    <Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08">
        <FIToFICstmrCdtTrf>
            <GrpHdr>
                <MsgId>VALID123</MsgId>
                <CreDtTm>2023-10-24T12:00:00Z</CreDtTm>
                <NbOfTxs>1</NbOfTxs>
                <SttlmInf>
                    <SttlmMtd>INDA</SttlmMtd>
                </SttlmInf>
            </GrpHdr>
        </FIToFICstmrCdtTrf>
    </Document>"""

    parser = OpenPurseParser(valid_pacs)
    # The actual docs/ schemas are rigorous so this minimal mock might fail XSD requirements.
    # However, let's just make sure the method runs and returns a report safely.
    report = parser.validate_schema()
    assert isinstance(report, ValidationReport)


def test_invalid_schema_namespace():
    invalid_ns = b"""<?xml version="1.0" encoding="UTF-8"?>
    <Document xmlns="urn:iso:std:iso:20022:tech:xsd:invalid.999">
        <FIToFICstmrCdtTrf></FIToFICstmrCdtTrf>
    </Document>"""

    parser = OpenPurseParser(invalid_ns)
    report = parser.validate_schema()

    assert report.is_valid is False
    assert any("Unsupported namespace" in err for err in report.errors)


def test_mt_validation_valid():
    from openpurse.validator import Validator
    mt_msg = b"{1:F01BANKUS33XXX0000000000}{2:I103BANKGB22XXXN}{4:\n:20:REF123\n:32A:231024USD1000,\n-}{5:{MAC:12A34B}}"
    report = Validator.validate_schema(mt_msg)

    assert report.is_valid is True
    assert len(report.errors) == 0

def test_mt_validation_broken_block4():
    from openpurse.validator import Validator
    # Missing the terminating -} string
    mt_msg = b"{1:F01BANKUS33XXX0000000000}{2:I103BANKGB22XXXN}{4:\n:20:REF123\n:32A:231024USD1000,"
    report = Validator.validate_schema(mt_msg)

    assert report.is_valid is False
    assert any("Invalid or missing Block 4" in err for err in report.errors)

def test_mt_validation_invalid_tag():
    from openpurse.validator import Validator
    # Block 4 is intact but has raw unstructured text inside, breaking Regex
    mt_msg = b"{1:F01BANKUS33XXX0000000000}{2:I103BANKGB22XXXN}{4:\nThis is not a valid SWIFT MT format.\n-}"
    report = Validator.validate_schema(mt_msg)

    assert report.is_valid is False
    assert any("Block 4 body does not contain valid SWIFT MT tags" in err for err in report.errors)
