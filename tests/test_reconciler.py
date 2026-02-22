import pytest
from openpurse.reconciler import Reconciler
from openpurse.builder import MessageBuilder
from openpurse.models import PaymentMessage, Pain002Message

def test_reconcile_by_end_to_end_id():
    # Two messages sharing the same EndToEndId
    msg1 = MessageBuilder.build("pacs.008", end_to_end_id="TX123", amount="100.00")
    msg2 = MessageBuilder.build("camt.054", end_to_end_id="TX123", amount="100.00")
    
    assert Reconciler.is_match(msg1, msg2) is True

def test_reconcile_pain002_status_report():
    # A pain.002 status report matching an original MsgId
    original_msg = MessageBuilder.build("pain.001", message_id="MSG001")
    status_report = MessageBuilder.build("pain.002", original_message_id="MSG001")
    
    assert Reconciler.is_match(original_msg, status_report) is True

def test_find_matches():
    primary = MessageBuilder.build("pain.001", end_to_end_id="E2E_001")
    candidates = [
        MessageBuilder.build("pain.002", end_to_end_id="E2E_001"), # Match
        MessageBuilder.build("camt.054", end_to_end_id="E2E_001"), # Match
        MessageBuilder.build("pacs.008", end_to_end_id="E2E_999"), # No match
    ]
    
    matches = Reconciler.find_matches(primary, candidates)
    assert len(matches) == 2
    assert matches[0].end_to_end_id == "E2E_001"
    assert matches[1].end_to_end_id == "E2E_001"

def test_trace_lifecycle():
    # Build a chain: pain.001 -> pain.002 (Init Status) -> camt.054 (Credit)
    initiation = MessageBuilder.build("pain.001", message_id="INIT_001", end_to_end_id="REF_001")
    status = MessageBuilder.build("pain.002", original_message_id="INIT_001", end_to_end_id="REF_001")
    notification = MessageBuilder.build("camt.054", end_to_end_id="REF_001")
    unrelated = MessageBuilder.build("pacs.008", end_to_end_id="REF_999")
    
    all_msgs = [initiation, status, notification, unrelated]
    
    timeline = Reconciler.trace_lifecycle(initiation, all_msgs)
    
    assert len(timeline) == 3
    assert initiation in timeline
    assert status in timeline
    assert notification in timeline
    assert unrelated not in timeline
