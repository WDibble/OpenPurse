
from openpurse.parser import OpenPurseParser
from openpurse.models import Camt086Message

MOCK_CAMT_086 = b"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.086.001.05">
    <BkSrvcsBllgStmt>
        <RptHdr>
            <RptId>RPT-12345</RptId>
        </RptHdr>
        <BllgStmtGrp>
            <GrpId>GRP-54321</GrpId>
            <BllgStmt>
                <StmtId>STMT-999</StmtId>
                <CreDtTm>2023-11-20T10:00:00Z</CreDtTm>
                <Sts>ORGN</Sts>
            </BllgStmt>
        </BllgStmtGrp>
    </BkSrvcsBllgStmt>
</Document>"""

def test_parse_detailed_camt_086():
    parser = OpenPurseParser(MOCK_CAMT_086)
    msg = parser.parse_detailed()

    assert isinstance(msg, Camt086Message)
    assert msg.report_id == "RPT-12345"
    assert msg.group_id == "GRP-54321"
    assert msg.statement_id == "STMT-999"
    assert msg.creation_date_time == "2023-11-20T10:00:00Z"
    assert msg.statement_status == "ORGN"

def test_parse_detailed_camt_086_edge_cases():
    # Missing optional fields like GrpId and Sts
    mock_missing = b"""<?xml version="1.0" encoding="UTF-8"?>
    <Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.086.001.05">
        <BkSrvcsBllgStmt>
            <RptHdr>
            </RptHdr>
            <BllgStmtGrp>
                <BllgStmt>
                    <StmtId>STMT-ONLY</StmtId>
                </BllgStmt>
            </BllgStmtGrp>
        </BkSrvcsBllgStmt>
    </Document>"""
    parser = OpenPurseParser(mock_missing)
    msg = parser.parse_detailed()
    
    assert isinstance(msg, Camt086Message)
    assert msg.report_id is None
    assert msg.group_id is None
    assert msg.statement_id == "STMT-ONLY"
    assert msg.creation_date_time is None
    assert msg.statement_status is None

    # Empty document
    empty_doc = b"<Document xmlns=\"urn:iso:std:iso:20022:tech:xsd:camt.086.001.05\"></Document>"
    parser_empty = OpenPurseParser(empty_doc)
    msg_empty = parser_empty.parse_detailed()
    assert isinstance(msg_empty, Camt086Message)
    assert msg_empty.report_id is None

if __name__ == "__main__":
    test_parse_detailed_camt_086()
    test_parse_detailed_camt_086_edge_cases()
    print("CAMT.086 Tests passed! 🚀")
