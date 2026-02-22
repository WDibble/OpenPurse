# Contributing to OpenPurse

First off, thanks for taking the time to contribute! 🎉

OpenPurse is a community-driven project aiming to simplify financial messaging for everyone.

## How Can I Contribute?

### Reporting Bugs

- Use the GitHub Issue Tracker.
- Describe the exact steps for reproduction.
- Include a sample (anonymized!) message if possible.

### Suggesting Enhancements

- Open an issue titled "[Feature] Your Feature Name".
- Explain why this feature would be useful for all ISO 20022 or SWIFT MT users.

### Pull Requests

1. Fork the repo.
2. Create a branch: `feat/amazing-feature`.
3. Add tests for your changes.
4. Run `pytest` to ensure 100% pass rate.
5. Submit your PR!

## Development Setup

```bash
# Clone and setup
git clone https://github.com/WDibble/OpenPurse.git
pip install -e .[dev]

# Run tests
pytest tests/
```

## Code Style

- We follow PEP 8.
- Use Google-style docstrings for all public methods.
- Keep dependencies to a minimum.

---

Questions? Open an issue!
