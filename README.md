<p align="center">
  <img src="https://raw.githubusercontent.com/WDibble/OpenPurse/main/assets/logo.png" width="180" alt="OpenPurse Logo">
</p>

<h1 align="center">OpenPurse</h1>

<p align="center">
  <strong>The Ultra-Lightweight, Production-Grade Engine for ISO 20022 and SWIFT MT Financial Messaging.</strong>
</p>

<p align="center">
  <a href="https://pypi.org/project/openpurse/"><img src="https://img.shields.io/pypi/v/openpurse?color=7C3AED&style=for-the-badge" alt="PyPI version"></a>
  <a href="https://github.com/WDibble/OpenPurse/blob/main/LICENSE"><img src="https://img.shields.io/pypi/l/openpurse?color=06B6D4&style=for-the-badge" alt="License"></a>
  <img src="https://img.shields.io/pypi/pyversions/openpurse?color=8B5CF6&style=for-the-badge" alt="Python Versions">
  <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="Ruff"></a>
</p>

---

## ⚡️ The OpenPurse Mission

Financial messaging is transitioning from archaic, line-based **SWIFT MT** to deeply nested, namespace-heavy **ISO 20022 (MX)** XML. Engineers are often caught in the middle, forced to deal with massive XML schemas, fragmented versions, and complex reconciliation logic.

**OpenPurse** solves this by providing a unified, zero-bloat API that flattens this complexity into clean, structured Python objects.

- **🚀 Performance-First**: Built with C-optimized `lxml` for lightning-fast parsing even under heavy load.
- **🛡️ Production-Hardened**: Strict validation for IBANs (Modulo-97) and BICs (ISO 9362).
- **🔌 Schema-Dynamic**: Not just one version. OpenPurse dynamically detects and supports **770+ ISO namespaces** across Cash Management, Payments Initiation, and Securities.
- **📦 Zero-Dependency Core**: No `pandas`, no `pydantic`. Just pure, native Python `@dataclasses`.

---

## 🏗️ Technical Philosophy: The @dataclass Way

Most financial libraries overwhelm you with nested dictionaries or heavy ORM-like objects. OpenPurse uses the **Uniform Data Model** (UDM) philosophy:

1. **Flattening**: We extract only the most critical fields needed for reconciliation and payment processing.
2. **Immutability**: Once parsed, messages are stored in lightweight, typed `@dataclasses`.
3. **Lossless-Ready**: While we flatten for convenience, we preserve raw data integrity (e.g., keeping amounts as `str` to avoid floating-point errors).

---

## 🛠️ Feature Deep Dive

### 1. The Unified Parser

One caller to rule them all. Whether your file starts with `<?xml` or `{1:`, the `OpenPurseParser` handles the routing.

```python
import openpurse

# Parses MT103, MT202, pacs.008, camt.053, pain.001, etc.
raw_data = get_incoming_payload()
parser = openpurse.OpenPurseParser(raw_data)
msg = parser.parse()

print(f"Ref: {msg.message_id} | Amt: {msg.amount} {msg.currency}")
```

#### The Uniform Data Model (UDM)

Every parsed message returns a `PaymentMessage` object (or an extended subclass like `Pacs008Message`) with these standardized attributes:

| Attribute                             | Description                                        |
| :------------------------------------ | :------------------------------------------------- |
| `message_id`                          | Unique ID from Group Header (:20: in MT)           |
| `end_to_end_id`                       | Original e2e reference (EndToEndId)                |
| `amount`                              | Transaction value (stored as string for precision) |
| `currency`                            | ISO 3-letter currency code (e.g. USD, EUR)         |
| `sender_bic` / `receiver_bic`         | Validated 8/11 char BIC codes                      |
| `debtor_name` / `creditor_name`       | Party names                                        |
| `debtor_account` / `creditor_account` | IBAN or local account identifiers                  |
| `uetr`                                | SWIFT gpi Unique Transaction Reference             |

### 2. Bidirectional Translator

Move between MX (ISO 20022) and MT legacy formats without losing precision.

```python
from openpurse.translator import Translator

# Convert a parsed message object to a legacy MT103 block
mt_payload = Translator.to_mt(msg, mt_type="103")
```

### 3. Smart PII Anonymizer

Essential for testing in staging environments with real data. OpenPurse scrubs names and addresses while keeping **IBAN checksums valid**, so your downstream systems don't reject the files.

```python
from openpurse.anonymizer import Anonymizer

anonymized_xml = Anonymizer().anonymize_xml(raw_xml_bytes)
```

### 4. Lifecycle Reconciler

The "Holy Grail" of treasury engineering: linking fragmented messages into a single payment lifecycle (e.g., linking a `pain.001` to its `pain.002` status report and final `camt.054` notification).

```python
from openpurse.reconciler import Reconciler

# Trace the entire life of a payment across your message history
timeline = Reconciler.trace_lifecycle(seed_msg, message_pool)
```

---

## 📊 Capability Matrix

| Format             | Category   | Supported Message Types                        |
| :----------------- | :--------- | :--------------------------------------------- |
| **ISO 20022 (MX)** | Payments   | `pacs.008`, `pacs.009`, `pacs.004`             |
|                    | Cash Mgmt  | `camt.052`, `camt.053`, `camt.054`, `camt.004` |
|                    | Initiation | `pain.001`, `pain.002`, `pain.008`             |
| **SWIFT MT**       | Customer   | `MT101`, `MT103`                               |
|                    | Financial  | `MT202`                                        |
|                    | Reporting  | `MT900`, `MT910`, `MT940`, `MT942`, `MT950`    |

---

## 🚦 Dual-Tier Validation Engine

OpenPurse doesn't just extract data; it actively defends your downstream systems against corrupted financial payloads using a two-tier validation engine.

### Tier 1: Deep Structural Validation

Instantly checks the raw payload syntax before you even attempt to parse it.

- **XML (MX)**: Automatically evaluates the raw bytes against the precise matching `lxml` compiled XSD definition from the 770+ ISO schemas in the library.
- **SWIFT MT**: Enforces rigorous Regex structural checks ensuring Block 1-5 definitions, proper `:tag:` spacing, and correct termination syntax are met.

```python
from openpurse.validator import Validator

raw_payload = b"{1:F01BANKUS33XXX0000000000}{2:I103BANKGB22XXXN}{4:\n:20:REF123\n-}"
report = Validator.validate_schema(raw_payload)
if not report.is_valid:
    print(report.errors) # Caught malformed block 4 before parsing
```

### Tier 2: Logical Field Validation

Validates the actual extracted business values of a parsed `PaymentMessage`.

- **IBAN**: Full Modulo-97 checksum execution across all supported country formats.
- **BIC**: Strict ISO 9362 8- or 11-character alphanumeric check for Senders/Receivers.
- **UETR**: Strict UUIDv4 checking for SWIFT gpi tracking strings.

```python
parsed_msg = parser.parse()
logic_report = Validator.validate(parsed_msg)
if not logic_report.is_valid:
    print(f"Critical Business Error: {logic_report.errors}")
```

---

## 🔍 Exporter: Automated API Specs

Instantly sync your internal financial models with your REST API documentation. `Exporter` generates OpenAPI 3.0 / JSON Schema definitions directly from the codebase.

```bash
# Generate openapi.json for your web team
python3 scripts/export_schema.py --output docs/api_spec.json
```

---

## ⚖️ Performance Benchmarks (Qualitative)

OpenPurse is optimized for high-throughput reconciliation pipelines. By leveraging `lxml`'s C-bindings for XML traversal and specialized RegEx engines for MT parsing, OpenPurse can process:

- **Small Messages**: ~0.001s / message.
- **Large Statements (CAMT.053/MT940)**: Typically < 0.05s for statement blocks with 5,000+ entries.

---

## 🤝 Contributing

OpenPurse is a community project for financial engineers. We welcome PRs for:

- New ISO version mappings.
- New MT block pattern regex improvements.
- Performance optimizations.

```bash
# Setup for development
pip install -e ".[dev]"
pytest tests/
```

---

## 📜 License

OpenPurse is released under the **MIT License**. Build something great.

<p align="center">
  Built with ❤️ for modern financial engineering by the OpenPurse team.
</p>
