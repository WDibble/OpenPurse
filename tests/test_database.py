import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from openpurse.models import Pacs008Message, PostalAddress, Pain001Message
from openpurse.database.models import Base, Pacs008Record, Pain001Record
from openpurse.database.repository import MessageRepository

@pytest.fixture
def db_session():
    """
    Provides an in-memory SQLite database session for testing.
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_save_pacs008_to_db(db_session):
    repo = MessageRepository(db_session)
    
    # Create a complex Pacs008Message
    addr = PostalAddress(town_name="London", country="GB")
    msg = Pacs008Message(
        message_id="MSG_DB_001",
        uetr="550e8400-e29b-41d4-a716-446655440000",
        amount="5000.00",
        currency="GBP",
        sender_bic="BANKGB22XXX",
        receiver_bic="BANKUS33XXX",
        debtor_name="Company A",
        debtor_address=addr,
        settlement_method="INDA",
        transactions=[{"id": "TX1", "amt": "1000"}]
    )
    
    # Save to DB
    record = repo.save(msg)
    assert record.id is not None
    assert isinstance(record, Pacs008Record)
    
    # Retrieve and verify
    retrieved = repo.get_by_message_id("MSG_DB_001")
    assert retrieved is not None
    assert retrieved.uetr == "550e8400-e29b-41d4-a716-446655440000"
    assert retrieved.amount == "5000.00"
    assert retrieved.transactions[0]["id"] == "TX1"
    assert retrieved.debtor_address["town_name"] == "London"

def test_list_by_sender(db_session):
    repo = MessageRepository(db_session)
    
    msg1 = Pacs008Message(message_id="ID1", sender_bic="SENDER1", amount="100")
    msg2 = Pain001Message(message_id="ID2", sender_bic="SENDER1", amount="200")
    msg3 = Pacs008Message(message_id="ID3", sender_bic="SENDER2", amount="300")
    
    repo.save(msg1)
    repo.save(msg2)
    repo.save(msg3)
    
    sender1_msgs = repo.list_by_sender("SENDER1")
    assert len(sender1_msgs) == 2
    ids = [m.message_id for m in sender1_msgs]
    assert "ID1" in ids
    assert "ID2" in ids
    
    # Verify polymorphic identities (Pain001Record vs Pacs008Record)
    pain_rec = next(m for m in sender1_msgs if m.message_id == "ID2")
    assert isinstance(pain_rec, Pain001Record)
