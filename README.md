# OpenPurse

OpenPurse is a lightweight, open-source Python package that parses and flattens deeply nested ISO 20022 XML financial messages into highly usable, flat Python dictionaries (which can be easily dumped to JSON).

## Features

- **Universal Support**: Dynamically determines the message format. It fully supports both XML-based ISO 20022 schemas and legacy block-based SWIFT MT formats (like MT103 and MT202).
- **Structured Schema**: Extracts all major variables into a standard Python `PaymentMessage` `@dataclass` (with robust `flatten()` dictionary dumps available as well).
- **Robust and Fast Parsing**: Built on top of `lxml` with robust error handling, regular expressions for non-XML data, and graceful degradation for missing optional fields.
- **Zero Bloat**: Only requires `lxml`. No heavy dependencies like pandas or pydantic are needed.

## Installation

OpenPurse is published on PyPI. You can install it directly via pip:

```bash
pip install openpurse
```

### Publishing to PyPI (Maintainers Only)

To publish a new version of OpenPurse to PyPI:

1. Ensure your `pyproject.toml` has the correct version number.
2. Build the distribution packages:
   ```bash
   python -m build
   ```
3. Upload to PyPI:
   ```bash
   python -m twine upload dist/*
   ```
   You will be prompted for your PyPI API token.

### Updating to a New Version

When you make changes to OpenPurse and want to publish an update:

1. Open `pyproject.toml` and increment the `version` (e.g. `"0.1.1"`).
2. Delete the old build artifacts in the `dist/` directory:
   ```bash
   rm -rf dist/
   ```
3. Rebuild and upload:
   ```bash
   python -m build
   python -m twine upload dist/*
   ```

To install development dependencies (for running tests):

```bash
pip install -e .[dev]
```

## Usage

You can import the main classes directly from the `openpurse` package to parse raw XML or MT bytes:

```python
import openpurse

# Your raw ISO 20022 XML data (or MT bytes)
xml_data = b'''<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08">
    <FIToFICstmrCdtTrf>
        <GrpHdr>
            <MsgId>MSG12345</MsgId>
            ...
        </GrpHdr>
        <CdtTrfTxInf>
            <IntrBkSttlmAmt Ccy="USD">1000.50</IntrBkSttlmAmt>
        </CdtTrfTxInf>
    </FIToFICstmrCdtTrf>
</Document>'''

# Initialize the parser
parser = openpurse.OpenPurseParser(xml_data)

# 1. Parse into a structured PaymentMessage dataclass (Recommended)
msg_struct = parser.parse()
print(f"ID is {msg_struct.message_id} sending {msg_struct.amount} {msg_struct.currency}")

# 2. Flatten directly into a dictionary
flat_dict = parser.flatten()
print(flat_dict)
# Output:
# {
#     "message_id": "MSG12345",
#     "end_to_end_id": None,
#     "amount": "1000.50",
#     "currency": "USD",
#     "sender_bic": None,
#     "receiver_bic": None,
#     "debtor_name": None,
#     "creditor_name": None
# }

# Or parse legacy SWIFT MT formats without changing any logic!
mt_data = b'''{1:F01BANKUS33AXXX0000000000}{2:I103BANKGB22XXXXN}{4:
:20:MT103MSG
:32A:231024EUR50000,00
-}'''

parser = openpurse.OpenPurseParser(mt_data)
# Output: {"message_id": "MT103MSG", "amount": "50000.00", "currency": "EUR"... }

# 3. Translate between MT and MX formats
msg_struct = parser.parse()

# Convert to MT103 byte string
mt_bytes = openpurse.Translator.to_mt(msg_struct, "103")

# Convert to ISO 20022 XML (e.g. pacs.008, camt.004)
mx_bytes = openpurse.Translator.to_mx(msg_struct, "camt.004")
```

## Supported Fields

Whether you call `.parse()` (which yields a `PaymentMessage` dataclass instance) or `.flatten()` (which yields a `dict`), the parser standardizes the following fields across all schemas:

- `message_id`: GrpHdr/MsgId (XML) or Block 4 :20: (MT)
- `end_to_end_id`: EndToEndId (XML)
- `amount`: Extracted value preserving decimal notation
- `currency`: 3-Letter currency code
- `sender_bic`: InstgAgt/BICFI (XML) or Header Block 1 (MT)
- `receiver_bic`: InstdAgt/BICFI (XML) or Header Block 2 (MT)
- `debtor_name`: Dbtr/Nm (XML) or :50K: tags (MT)
- `creditor_name`: Cdtr/Nm (XML) or :59: tags (MT)

Missing or optional fields gracefully return `None`.

## Tests

Testing is done using `pytest`. Currently, coverage includes mock definitions for basic `pacs` and `camt` schemas, validating graceful degradation when schemas don't provide creditor/debtor names.

```bash
pytest tests/
```
