import os
import glob
import pytest
from openpurse.parser import OpenPurseParser

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
