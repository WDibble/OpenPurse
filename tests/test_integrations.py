import pytest
import json
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from openpurse.models import Pacs008Message, PostalAddress
from openpurse.integrations.pydantic import from_dataclass, PydanticPacs008
from openpurse.integrations.fastapi import get_openpurse_message

def test_dataclass_to_pydantic_conversion():
    """
    Verifies that a Pacs008Message dataclass converts correctly to PydanticPacs008.
    """
    addr = PostalAddress(town_name="New York", country="US")
    msg = Pacs008Message(
        message_id="MSG_001",
        amount="100.50",
        currency="USD",
        debtor_name="John Doe",
        debtor_address=addr,
        settlement_method="INDA"
    )
    
    p_msg = from_dataclass(msg)
    
    assert isinstance(p_msg, PydanticPacs008)
    assert p_msg.message_id == "MSG_001"
    assert p_msg.amount == "100.50"
    assert p_msg.debtor_address.town_name == "New York"
    assert p_msg.settlement_method == "INDA"
    
    # Verify JSON serialization
    json_data = p_msg.model_dump_json()
    parsed_json = json.loads(json_data)
    assert parsed_json["message_id"] == "MSG_001"
    assert parsed_json["debtor_address"]["town_name"] == "New York"

# FastAPI Integration Test
app = FastAPI()

@app.post("/test-parse")
async def route_test_endpoint(msg=Depends(get_openpurse_message)):
    return {"status": "success", "msg_id": msg.message_id, "type": type(msg).__name__}

def test_fastapi_dependency_parsing():
    """
    Verifies that the FastAPI dependency correctly parses XML into a Pydantic model.
    """
    client = TestClient(app)
    
    valid_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.13">
    <FIToFICstmrCdtTrf>
        <GrpHdr>
            <MsgId>MSG_FASTAPI_001</MsgId>
            <CreDtTm>2026-02-22T22:00:00</CreDtTm>
            <NbOfTxs>1</NbOfTxs>
            <SttlmInf>
                <SttlmMtd>INDA</SttlmMtd>
            </SttlmInf>
        </GrpHdr>
        <CdtTrfTxInf>
            <PmtId>
                <EndToEndId>E2E_123</EndToEndId>
            </PmtId>
            <IntrBkSttlmAmt Ccy="USD">500.25</IntrBkSttlmAmt>
            <ChrgBr>SLEV</ChrgBr>
            <Dbtr>
                <Nm>John FastAPI</Nm>
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
                <Nm>Jane smith</Nm>
            </Cdtr>
        </CdtTrfTxInf>
    </FIToFICstmrCdtTrf>
</Document>
"""
    response = client.post("/test-parse", content=valid_xml)
    assert response.status_code == 200
    assert response.json() == {
        "status": "success", 
        "msg_id": "MSG_FASTAPI_001", 
        "type": "PydanticPacs008"
    }

def test_fastapi_dependency_failure_invalid_xml():
    """
    Verifies that the FastAPI dependency returns 422 on schema validation failure.
    """
    client = TestClient(app)
    
    # Missing mandatory CreDtTm
    invalid_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.13">
    <FIToFICstmrCdtTrf>
        <GrpHdr>
            <MsgId>MSG_FAIL</MsgId>
        </GrpHdr>
    </FIToFICstmrCdtTrf>
</Document>
"""
    response = client.post("/test-parse", content=invalid_xml)
    assert response.status_code == 422
    assert "Schema validation failed" in response.json()["detail"]["message"]
