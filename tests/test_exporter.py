import pytest
import json
from openpurse.exporter import Exporter
from openpurse import models

def test_generate_schema_basic():
    schema = Exporter.generate_schema(models.PostalAddress)
    assert schema["type"] == "object"
    assert "country" in schema["properties"]
    assert schema["properties"]["country"]["type"] == "string"
    assert schema["properties"]["country"]["nullable"] is True

def test_generate_schema_inheritance():
    # Pacs008Message inherits from PaymentMessage
    schema = Exporter.generate_schema(models.Pacs008Message)
    assert schema["type"] == "object"
    assert "settlement_method" in schema["properties"]
    # It should also contain fields from PaymentMessage
    assert "message_id" in schema["properties"]
    assert "amount" in schema["properties"]

def test_to_openapi_structure():
    spec = Exporter.to_openapi()
    assert spec["openapi"] == "3.0.0"
    assert "components" in spec
    assert "schemas" in spec["components"]
    assert "PaymentMessage" in spec["components"]["schemas"]
    assert "PostalAddress" in spec["components"]["schemas"]
    assert "ValidationReport" in spec["components"]["schemas"]

def test_export_json(tmp_path):
    path = tmp_path / "openapi.json"
    Exporter.export_json(str(path))
    assert path.exists()
    content = json.loads(path.read_text())
    assert content["openapi"] == "3.0.0"
