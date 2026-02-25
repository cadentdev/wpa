# Contributing to WPA

Thanks for your interest in contributing!

## Development Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pip install ruff
```

## Running Tests

```bash
pytest --cov=. --cov-report=term-missing
```

All changes must maintain 99% coverage. Tests use mocked HTTP calls — no real WordPress connection needed.

## Linting

```bash
ruff check .
ruff format --check .
```

Both checks run in CI and must pass before merge.

## Submitting Changes

1. Fork the repo and create a feature branch from `main`
2. Make your changes
3. Ensure tests pass and linting is clean
4. Open a pull request against `main`

CI must pass before merging. Branch protection requires the `test (ubuntu-latest, 3.12)` check.
