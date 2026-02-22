import pytest
from openpurse.validator import Validator

def test_mt_validation_success():
    # A valid-looking MT103
    valid_mt = (
        "{1:F01BANKUS33AXXX0000000000}{2:I103RECVGB22XXXXN}{4:\n"
        ":20:MSG12345\n"
        ":32A:231024USD1000,50\n"
        "-}"
    ).encode("utf-8")
    
    report = Validator.validate_schema(valid_mt)
    assert report.is_valid is True
    assert len(report.errors) == 0

def test_mt_validation_invalid_32a_date():
    invalid_date = (
        "{1:F01BANKUS33AXXX0000000000}{2:I103RECVGB22XXXXN}{4:\n"
        ":20:MSG12345\n"
        ":32A:231324USD1000,50\n"  # 13 is invalid month
        "-}"
    ).encode("utf-8")
    
    report = Validator.validate_schema(invalid_date)
    assert report.is_valid is False
    assert any("Invalid date in Field 32A" in err for err in report.errors)

def test_mt_validation_invalid_32a_currency():
    invalid_ccy = (
        "{1:F01BANKUS33AXXX0000000000}{2:I103RECVGB22XXXXN}{4:\n"
        ":20:MSG12345\n"
        ":32A:231024US11000,50\n"  # US1 is invalid ccy
        "-}"
    ).encode("utf-8")
    
    report = Validator.validate_schema(invalid_ccy)
    assert report.is_valid is False
    assert any("Invalid currency in Field 32A" in err for err in report.errors)

def test_mt_validation_invalid_32a_amount():
    invalid_amt = (
        "{1:F01BANKUS33AXXX0000000000}{2:I103RECVGB22XXXXN}{4:\n"
        ":20:MSG12345\n"
        ":32A:231024USDAABC,50\n"  # AABC is invalid amount
        "-}"
    ).encode("utf-8")
    
    report = Validator.validate_schema(invalid_amt)
    assert report.is_valid is False
    assert any("Invalid amount format in Field 32A" in err for err in report.errors)

def test_mt_validation_missing_field_20():
    missing_20 = (
        "{1:F01BANKUS33AXXX0000000000}{2:I103RECVGB22XXXXN}{4:\n"
        ":32A:231024USD1000,50\n"
        "-}"
    ).encode("utf-8")
    
    report = Validator.validate_schema(missing_20)
    assert report.is_valid is False
    assert any("Mandatory Field :20: (Sender's Reference) missing" in err for err in report.errors)

def test_mt_validation_invalid_header_bic():
    bad_bic = (
        "{1:F01BAD!BIC!AXXX0000000000}{2:I103RECVGB22XXXXN}{4:\n"
        ":20:MSG1\n"
        "-}"
    ).encode("utf-8")
    
    report = Validator.validate_schema(bad_bic)
    assert report.is_valid is False
    assert any("Invalid BIC format in Block 1" in err for err in report.errors)

def test_mt_validation_malformed_blocks():
    malformed = b"{1:F01}{2:I103}{4: -}"
    report = Validator.validate_schema(malformed)
    assert report.is_valid is False
    assert any(" structure" in err for err in report.errors)
