import pytest

from openpurse.models import PaymentMessage
from openpurse.parser import OpenPurseParser
from openpurse.translator import Translator
from openpurse.validator import Validator


def test_uetr_generation_and_extraction():
    msg = PaymentMessage(
        message_id="UETR_TEST",
        amount="123.45",
        currency="USD",
        sender_bic="BANKUS33XXX",
        receiver_bic="BANKGB22XXX",
    )

    # Translator should generate a UETR for MT103
    mt_bytes = Translator.to_mt(msg, "103")
    assert b"{3:{121:" in mt_bytes

    # Parse it back
    parser = OpenPurseParser(mt_bytes)
    roundtrip_msg = parser.parse()

    # In MT, the receiver/sender BICs are 12 chars (e.g. padded with X).
    # Since we need to test validation, let's just assert UETR here
    # and skip validating the auto-padded BICs which aren't always 11 chars.

    assert roundtrip_msg.uetr is not None
    assert len(roundtrip_msg.uetr) == 36  # UUIDv4 length

    # Verify the generated UETR is valid directly
    uetr_err = Validator._validate_uetr(roundtrip_msg.uetr)
    assert uetr_err is None


def test_uetr_xml_extraction():
    mx_bytes = b"""<?xml version="1.0" encoding="UTF-8"?>
    <Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08">
        <FIToFICstmrCdtTrf>
            <GrpHdr>
                <MsgId>XML_TEST</MsgId>
            </GrpHdr>
            <CdtTrfTxInf>
                <PmtId>
                    <UETR>550e8400-e29b-41d4-a716-446655440000</UETR>
                </PmtId>
            </CdtTrfTxInf>
        </FIToFICstmrCdtTrf>
    </Document>"""

    parser = OpenPurseParser(mx_bytes)
    msg = parser.parse()

    assert msg.uetr == "550e8400-e29b-41d4-a716-446655440000"


def test_uetr_validation_failure():
    msg = PaymentMessage(message_id="FAIL_TEST", uetr="not-a-uuid")

    report = Validator.validate(msg)
    assert report.is_valid is False
    assert any("Invalid UETR format" in err for err in report.errors)
