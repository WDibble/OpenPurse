import os
import glob
import pytest
from openpurse.parser import OpenPurseParser
from openpurse.models import (
    Camt054Message, Pacs008Message, Camt004Message, Camt052Message,
    Camt053Message, Pain001Message, Pain008Message, Pain002Message, PaymentMessage
)

# Path to example messages folder
EXAMPLES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'example_messages')
EXAMPLE_FILES = glob.glob(os.path.join(EXAMPLES_DIR, '*.xml'))

@pytest.mark.parametrize("filepath", EXAMPLE_FILES)
def test_parse_real_examples(filepath):
    """
    Ensure the parser can read and flatten real example messages without crashing.
    """
    with open(filepath, 'rb') as f:
        xml_data = f.read()

    parser = OpenPurseParser(xml_data)
    result = parser.flatten()

    # Verify that flattening returns a dictionary
    assert isinstance(result, dict)
    
    # Check that standard keys are present (even if values are None)
    expected_keys = {
        "message_id",
        "end_to_end_id",
        "amount",
        "currency",
        "sender_bic",
        "receiver_bic",
        "debtor_name",
        "creditor_name"
    }
    assert expected_keys.issubset(set(result.keys()))

@pytest.mark.parametrize("filepath", EXAMPLE_FILES)
def test_parse_detailed_real_examples(filepath):
    """
    Ensure the parser correctly dynamically identifies all 5 new and 3 existing examples 
    and instantiates their extreme detailed dataclass models correctly.
    """
    with open(filepath, 'rb') as f:
        xml_data = f.read()

    parser = OpenPurseParser(xml_data)
    result = parser.parse_detailed()

    filename = filepath.lower()

    if "camt_052" in filename or "camt.052" in filename:
        assert isinstance(result, Camt052Message)
    elif "camt_053" in filename or "camt053" in filename:
        assert isinstance(result, Camt053Message)
    elif "camt_054" in filename or "camt.054" in filename:
        assert isinstance(result, Camt054Message)
    elif "pain_001" in filename or "pain.001" in filename:
        assert isinstance(result, Pain001Message)
    elif "pain_002" in filename or "pain.002" in filename or "pain.002" in filename:
        assert isinstance(result, Pain002Message)
    elif "pain_008" in filename or "pain.008" in filename:
        assert isinstance(result, Pain008Message)
    elif "pacs.008" in filename or "pacs_008" in filename:
        assert isinstance(result, Pacs008Message)
    else:
        # Default fallback
        assert isinstance(result, PaymentMessage)
