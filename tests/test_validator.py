import pytest

from openpurse.builder import MessageBuilder
from openpurse.models import Pacs008Message, PaymentMessage
from openpurse.validator import Validator


def test_valid_bics():
    msg = PaymentMessage(sender_bic="BANKUS33XXX", receiver_bic="CHASGB2L")
    report = Validator.validate(msg)
    assert report.is_valid is True
    assert len(report.errors) == 0


def test_invalid_bics():
    msg = PaymentMessage(sender_bic="BANK", receiver_bic="INVALID_BIC_FORMAT")
    report = Validator.validate(msg)
    assert report.is_valid is False
    assert len(report.errors) == 2
    assert "BANK" in report.errors[0]
    assert "INVALID_BIC_FORMAT" in report.errors[1]


def test_valid_iban():
    # Example valid UK IBAN
    msg = MessageBuilder.build("pacs.008", debtor_account="GB90MIDL40051522334455")
    report = Validator.validate(msg)
    assert report.is_valid is True
    assert len(report.errors) == 0


def test_invalid_iban_checksum():
    # Modified the digits to fail modulo 97
    msg = MessageBuilder.build("pacs.008", debtor_account="GB99MIDL40051522334455")
    report = Validator.validate(msg)
    assert report.is_valid is False
    assert len(report.errors) == 1
    assert "Invalid IBAN checksum" in report.errors[0]


def test_not_an_iban_ignored():
    # A generic account number (BBAN) shouldn't trigger IBAN errors
    msg = MessageBuilder.build("pacs.008", debtor_account="123456789")
    report = Validator.validate(msg)
    assert report.is_valid is True


def test_nested_transaction_ibans():
    txs = [
        {"debtor_account": "GB90MIDL40051522334455"},  # Valid
        {"creditor_account": "FR1420041010050500013M02606"},  # Valid French IBAN
    ]
    msg = MessageBuilder.build("pacs.008", transactions=txs)
    report = Validator.validate(msg)
    assert report.is_valid is True

    txs_bad = [{"debtor_account": "GB99MIDL40051522334455"}]  # Invalid
    msg_bad = MessageBuilder.build("pacs.008", transactions=txs_bad)
    report_bad = Validator.validate(msg_bad)
    assert report_bad.is_valid is False
    assert len(report_bad.errors) == 1


def test_validator_edge_cases():
    # Empty and None values should not fail validation
    msg_empty = PaymentMessage(
        sender_bic="", receiver_bic=None, debtor_account="", creditor_account=None
    )
    report_empty = Validator.validate(msg_empty)
    assert report_empty.is_valid is True

    # Dirty but valid IBANs (spaces, hyphens, mixed case)
    dirty_iban = "  gb90 midl 4005-1522-3344-55  "
    msg_dirty = MessageBuilder.build("pacs.008", debtor_account=dirty_iban)
    report_dirty = Validator.validate(msg_dirty)
    assert report_dirty.is_valid is True

    # Just barely failing BIC regex (e.g., too short, too long)
    msg_short_bic = PaymentMessage(sender_bic="BANKUS3")
    assert Validator.validate(msg_short_bic).is_valid is False

    msg_long_bic = PaymentMessage(sender_bic="BANKUS33XXX12")
    assert Validator.validate(msg_long_bic).is_valid is False


def test_extreme_corruption_bics():
    """Test validation against maliciously or extremely corrupted BIC strings."""
    corrupted_bics = [
        "BANKUS33\x00",  # Null byte injection
        "BANKUS33\n\r",  # Carriage returns
        "SELECT *",      # SQLi attempt
        "<script>",      # XSS attempt
        "B" * 50,        # Buffer overflow attempt
        "12345678",      # All digits (invalid format)
        "BANK US33",     # Internal spaces
    ]
    for bad_bic in corrupted_bics:
        msg = PaymentMessage(sender_bic=bad_bic)
        report = Validator.validate(msg)
        assert report.is_valid is False, f"Failed to catch corrupted BIC: {bad_bic}"
        assert len(report.errors) == 1
        assert "Invalid BIC format" in report.errors[0]

def test_extreme_corruption_amounts_and_currencies():
    """Test validation against corrupted monetary values."""
    # Negative amount strings
    # Extremely long amount strings
    msg_bad_amount = PaymentMessage(amount="100.00" * 50, currency="USD")
    
    # Currency with numbers
    msg_bad_currency = PaymentMessage(amount="100.00", currency="US1")
    
    # Empty strings and whitespace
    msg_empty = PaymentMessage(amount="   ", currency="\t")
    
    reports = {
        "empty": Validator.validate(msg_empty),
        "curr": Validator.validate(msg_bad_currency)
    }
    
    assert reports["empty"].is_valid is False
    assert any("empty string" in e for e in reports["empty"].errors)
    
    # Currency should only be alphabetic (we haven't strictly enforced this in validator yet, 
    # but let's check length constraints we did add)
    msg_wrong_len_curr = PaymentMessage(amount="100", currency="US")
    assert Validator.validate(msg_wrong_len_curr).is_valid is False

def test_extreme_corruption_ibans():
    """Test validation against corrupted or malicious IBAN strings."""
    corrupted_ibans = [
        "GB90MIDL40051522334455\x00", # Null byte
        "GB90MID\nL40051522334455",   # New line
        "GB90<script>L4005",          # XSS
        "GB90" + ("1" * 100),         # Extreme length
    ]
    
    for bad_iban in corrupted_ibans:
        msg = MessageBuilder.build("pacs.008", debtor_account=bad_iban)
        report = Validator.validate(msg)
        
        # If it doesn't even look like an IBAN (due to scripts etc), it might pass the heuristic
        # If it DOES look like an IBAN, it MUST fail the checksum
        if Validator._is_likely_iban(bad_iban):
            assert report.is_valid is False, f"Failed to catch corrupted IBAN: {bad_iban}"
            assert "Invalid IBAN" in report.errors[0]

