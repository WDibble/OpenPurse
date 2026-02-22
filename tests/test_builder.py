import pytest
from openpurse.builder import MessageBuilder
from openpurse.models import Pacs008Message, Camt054Message, PaymentMessage

def test_builder_exact_match():
    # Valid explicit kwargs
    payload = {
        "message_id": "BLD123",
        "amount": "150.00",
        "currency": "USD",
        "settlement_method": "CLRG"
    }
    
    msg = MessageBuilder.build("pacs.008", **payload)
    
    assert isinstance(msg, Pacs008Message)
    assert msg.message_id == "BLD123"
    assert msg.amount == "150.00"
    assert msg.settlement_method == "CLRG"

def test_builder_filters_unknown_kwargs():
    # Dictionary with fields not present in Camt054
    payload = {
        "message_id": "BLD456",
        "amount": "200.00",
        "total_credit_entries": 5,
        "unknown_junk_field": "SHOULD_BE_DROPPED",
        "another_bad_field": 123
    }
    
    msg = MessageBuilder.build("camt.054", **payload)
    
    assert isinstance(msg, Camt054Message)
    assert msg.message_id == "BLD456"
    assert msg.total_credit_entries == 5
    
    # Prove the fields were rejected and didn't crash execution
    assert not hasattr(msg, "unknown_junk_field")
    assert not hasattr(msg, "another_bad_field")

def test_builder_fallback_base_message():
    payload = {
        "message_id": "FALLBACK",
        "amount": "99.99"
    }
    
    msg = MessageBuilder.build("unknown.schema.123", **payload)
    
    assert type(msg) is PaymentMessage
    assert msg.message_id == "FALLBACK"
    assert msg.amount == "99.99"

def test_builder_edge_cases():
    # Completely empty kwargs
    msg_empty = MessageBuilder.build("pacs.008")
    assert isinstance(msg_empty, Pacs008Message)
    assert msg_empty.message_id is None
    
    # Passing unexpected types (dataclass doesn't strictly enforce at runtime but should store them)
    msg_types = MessageBuilder.build("camt.054", amount=100.50, total_credit_entries="five")
    assert msg_types.amount == 100.50
    assert msg_types.total_credit_entries == "five"
