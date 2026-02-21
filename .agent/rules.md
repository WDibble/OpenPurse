ANTIGRAVITY AGENT RULES FOR "OPENPURSE"

1. Tech Stack & Dependencies

Language: Python 3.10+

XML Parsing: MUST use lxml. It is faster and safer for financial data.

Testing: MUST use pytest.

Zero Bloat: Do not add heavy dependencies like pandas or pydantic unless absolutely necessary. The goal is a lightweight package.

2. Code Quality & Style

Use strictly PEP 8 formatting.

Provide Type Hints for all function arguments and return types.

Include Docstrings (Google style) for all classes and public methods.

3. Financial Data Handling Rules

Namespaces: ISO 20022 XMLs rely heavily on namespaces (e.g., urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08). Your XPath queries MUST account for these dynamically or via a robust namespace map.

Currency: Always extract the currency attribute when extracting an amount (e.g., <InstdAmt Ccy="USD">100.00</InstdAmt>).

Graceful Degradation: Financial XMLs vary wildly. If an XPath query fails to find a node because it is optional in the SWIFT schema, catch the IndexError or AttributeError and return None. Do not crash the parser.

4. Workflow (Test-Driven)

Write the pytest file first with a mock XML string.

Run the test (it will fail).

Write the parsing logic in openpurse/.

Run the test again.

Fix errors autonomously based on the terminal output until green.