import pytest
from lxml import etree

from openpurse.models import Pacs008Message, Pain001Message, PostalAddress
from openpurse.parser import OpenPurseParser
from openpurse.writer import XMLWriter


def test_writer_pacs008_roundtrip():
    """
    Tests that a Pacs008Message can be generated into ISO XML and structurally parsed back
    yielding the exact same attribute values.
    """
    original = Pacs008Message(
        message_id="MSG-123",
        number_of_transactions=1,
        settlement_method="INDA",
        sender_bic="BANKUS33",
        receiver_bic="BANKGB22",
        end_to_end_id="E2E-456",
        uetr="550e8400-e29b-41d4-a716-446655440000",
        amount="5000.50",
        currency="USD",
        debtor_name="Acme Corp",
        debtor_address=PostalAddress(
            country="US",
            town_name="New York",
            post_code="10005",
            street_name="Wall Street",
            building_number="100"
        ),
        creditor_name="Globex Inc"
    )

    writer = XMLWriter(schema="pacs.008.001.08")
    xml_bytes = writer.to_xml(original)

    # Validate output has root and namespaces
    assert b"<Document" in xml_bytes
    assert b"xmlns=\"urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08\"" in xml_bytes
    assert b"<MsgId>MSG-123</MsgId>" in xml_bytes
    assert b"<EndToEndId>E2E-456</EndToEndId>" in xml_bytes

    # Parse back and map cleanly
    parser = OpenPurseParser(xml_bytes)
    roundtrip = parser.parse_detailed()

    assert isinstance(roundtrip, Pacs008Message)
    assert roundtrip.message_id == original.message_id
    assert roundtrip.number_of_transactions == original.number_of_transactions
    assert roundtrip.settlement_method == original.settlement_method
    assert roundtrip.sender_bic == original.sender_bic
    assert roundtrip.receiver_bic == original.receiver_bic
    
    # Check the first transaction mapped back
    assert len(roundtrip.transactions) == 1
    tx = roundtrip.transactions[0]
    
    assert tx["end_to_end_id"] == original.end_to_end_id
    assert roundtrip.uetr == original.uetr
    assert roundtrip.amount == original.amount
    assert roundtrip.currency == original.currency
    assert tx["debtor_name"] == original.debtor_name
    assert tx["creditor_name"] == original.creditor_name


def test_writer_pain001_roundtrip():
    """
    Tests that a Pain001Message generates valid structural ISO XML and equates backwards.
    """
    original = Pain001Message(
        message_id="INIT-777",
        number_of_transactions=2,
        control_sum="15000.00",
        initiating_party="Startup LLC",
        end_to_end_id="INB-999",
        debtor_name="Startup LLC",
        debtor_account="US1234567890",
        sender_bic="STARTUS33",
        amount="7500.00",
        currency="EUR",
        receiver_bic="VENDORGE22",
        creditor_name="Supplier GmbH",
        creditor_account="GE0987654321"
    )

    writer = XMLWriter(schema="pain.001.001.09")
    xml_bytes = writer.to_xml(original)

    assert b"<Document" in xml_bytes
    assert b"xmlns=\"urn:iso:std:iso:20022:tech:xsd:pain.001.001.09\"" in xml_bytes

    parser = OpenPurseParser(xml_bytes)
    roundtrip = parser.parse_detailed()
    
    # We map back specifically
    assert isinstance(roundtrip, Pain001Message)
    assert roundtrip.message_id == original.message_id
    
    # OpenPurse parser natively extracts pain amounts mostly flattening so we test via dict
    flat = parser.flatten()
    assert flat.get("message_id") == original.message_id
    assert flat.get("amount") == original.amount
    assert flat.get("currency") == original.currency
    assert flat.get("debtor_name") == original.debtor_name
    assert flat.get("creditor_name") == original.creditor_name
    assert flat.get("sender_bic") == original.sender_bic
    assert flat.get("receiver_bic") == original.receiver_bic
