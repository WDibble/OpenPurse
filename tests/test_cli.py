import subprocess
import sys
import os
import pytest
import json

EXAMPLES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "example_messages")

def run_cli(args):
    """Utility to run the OpenPurse CLI via subprocess."""
    result = subprocess.run(
        [sys.executable, "-m", "openpurse"] + args,
        capture_output=True,
        text=True
    )
    return result

def test_cli_validate_success():
    # Use a real example from the repo
    # Assuming pacs_008_example_sepa_direct_debit.xml is typical
    file_path = os.path.join(EXAMPLES_DIR, "pain_008_example_sepa_direct_debit.xml")
    if not os.path.exists(file_path):
        pytest.skip("Example file missing")
        
    result = run_cli(["validate", file_path])
    assert result.returncode == 0
    assert "Validation Successful" in result.stdout

def test_cli_parse_pacs008():
    file_path = os.path.join(EXAMPLES_DIR, "pain_008_example_sepa_direct_debit.xml")
    if not os.path.exists(file_path):
        pytest.skip("Example file missing")
        
    result = run_cli(["parse", file_path])
    assert result.returncode == 0
    # Verify it's valid JSON and contains expected keys
    data = json.loads(result.stdout)
    assert "message_id" in data

def test_cli_persist_sqlite(tmp_path):
    file_path = os.path.join(EXAMPLES_DIR, "pain_008_example_sepa_direct_debit.xml")
    db_file = tmp_path / "test_cli.db"
    db_url = f"sqlite:///{db_file}"
    
    result = run_cli(["persist", file_path, "--db-url", db_url])
    assert result.returncode == 0
    assert "Successfully persisted" in result.stdout
    assert os.path.exists(db_file)

def test_cli_invalid_command():
    result = run_cli(["garbage"])
    assert result.returncode != 0
    assert "invalid choice" in result.stderr
