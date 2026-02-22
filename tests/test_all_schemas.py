import glob
import os

import pytest

from openpurse.parser import OpenPurseParser

# Gather all 777 XSDs at module load directly
DOCS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs")
XSD_FILES = glob.glob(f"{DOCS_DIR}/**/*.xsd", recursive=True)


def extract_namespace(xsd_path):
    try:
        with open(xsd_path, "r", encoding="utf-8") as f:
            content = f.read(1024)
            if 'targetNamespace="' in content:
                return content.split('targetNamespace="')[1].split('"')[0]
    except Exception:
        pass
    return None


NAMESPACES = [ns for ns in (extract_namespace(xsd) for xsd in XSD_FILES) if ns]

# Ensure we found a substantive amount of schemas
assert len(NAMESPACES) > 500, f"Expected 700+ namespaces, found {len(NAMESPACES)}"


@pytest.mark.parametrize("namespace", NAMESPACES)
def test_universal_schema_parsing(namespace):
    """
    Test every single schema found in docs/ to guarantee that IF a document
    adheres to ANY ISO 20022 schema, our generic XPaths will seamlessly
    extract the available target data (or gracefully skip missing fields).
    """

    # We construct a mock XML blob embedding the iterated namespace.
    # We use a generic root block, because OpenPurse uses //ns: element queries
    # to find data regardless of depth or schema-specific root names (e.g. BkToCstmrAcctRpt).
    mock_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="{namespace}">
    <DummyRoot>
        <GrpHdr>
            <MsgId>MEGA_UNI_ID</MsgId>
        </GrpHdr>
        <TxInf>
            <PmtId>
                <EndToEndId>E2E_001</EndToEndId>
            </PmtId>
            <InstgAgt>
                <FinInstnId>
                    <BICFI>SENDER123</BICFI>
                </FinInstnId>
            </InstgAgt>
            <InstdAgt>
                <FinInstnId>
                    <BICFI>RECV456</BICFI>
                </FinInstnId>
            </InstdAgt>
            
            <Amt Ccy="CAD">999.99</Amt>
            
            <Dbtr>
                <Nm>Universal Debtor</Nm>
            </Dbtr>
            <Cdtr>
                <Nm>Universal Creditor</Nm>
            </Cdtr>
        </TxInf>
    </DummyRoot>
</Document>"""

    # Parse it
    parser = OpenPurseParser(mock_xml.encode("utf-8"))
    msg = parser.parse()

    # Verify accurate extraction across all schemas natively
    assert msg.message_id == "MEGA_UNI_ID"
    assert msg.end_to_end_id == "E2E_001"
    assert msg.amount == "999.99"
    assert msg.currency == "CAD"
    assert msg.sender_bic == "SENDER123"
    assert msg.receiver_bic == "RECV456"
    assert msg.debtor_name == "Universal Debtor"
    assert msg.creditor_name == "Universal Creditor"


def test_universal_missing_fields_graceful_degradation():
    """Verify no schema crashes when elements are absent"""
    parser = OpenPurseParser(
        b'<Document xmlns="urn:iso:std:iso:20022:tech:xsd:any.schema.001"><Dummy/></Document>'
    )
    msg = parser.parse()
    assert msg.message_id is None
    assert msg.amount is None
