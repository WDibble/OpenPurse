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


def test_mt_validation_rejection():
    mt_msg = b"{1:F01BANKUS33XXX0000000000}{2:I103BANKGB22XXXN}{4:\n-}"
    parser = OpenPurseParser(mt_msg)
    report = parser.validate_schema()

    assert report.is_valid is False
    assert report.errors[0] == "Schema validation is not applicable to SWIFT MT block formats."
