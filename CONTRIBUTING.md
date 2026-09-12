# Contributing to Billing Bureau

This document outlines the standards, branch policies, formatting constraints, and verification requirements for contributing to the Billing Bureau platform.

## Code of Conduct & Medical Data Responsibility
Contributors handle sensitive healthcare software logic. All code touching Patient Health Information (PHI) must comply with the Protection of Personal Information Act (POPIA). Unencrypted logging of identity numbers, contact details, or clinical diagnoses in production loggers or unit test outputs is strictly prohibited.

## Development Environment Setup

### 1. Python Toolchain & Virtual Environment
* Target Python runtime: `3.12.10`
* Virtual environment path: `.venv` or `venv`

Install development tools:
```bash
pip install black flake8 isort pytest-django
```

### 2. Formatting & Linting Standards
All code committed to the repository must satisfy the automated linting checks. Run checks prior to opening pull requests.

#### Black (Code Formatting)
* Line length limit: 88 characters.
* Target version: Python 3.12.
```bash
black --check --line-length 88 .
```

#### Flake8 (Static Code Analysis)
* Configuration: exclude `.venv,venv,migrations`.
```bash
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
```

#### isort (Import Sorting)
* Profile: `black`.
```bash
isort --check-only --profile black .
```

## Branching Strategy

The repository follows a Trunk-Based Development model with short-lived feature branches:

1. **Main Branch (`main`)**: The production-ready trunk. All commits must pass CI verification. Direct commits to `main` are disabled.
2. **Feature Branches (`feat/<feature-name>`)**: Scoped branches for new functionality or integrations.
3. **Bugfix Branches (`fix/<bug-description>`)**: Scoped branches addressing specific defects or scrubbing rules.
4. **Chore & Docs Branches (`chore/<task>`, `docs/<topic>`)**: Tooling, maintenance, and documentation updates.

Branch lifespans should remain under 48 hours to minimize merge drift.

## Semantic Commit Guidelines

Commit messages must conform to the Conventional Commits 1.0.0 specification:

```
<type>(<optional scope>): <description>

[optional body]

[optional footer(s)]
```

### Allowed Types
* `feat`: A new user-facing or integration feature (e.g., Medclaim EDI line item batching).
* `fix`: A defect resolution in existing code.
* `docs`: Documentation alterations or additions.
* `refactor`: Code alterations that neither fix a bug nor introduce a feature.
* `test`: Adding missing unit, integration, or regression tests.
* `chore`: Toolchain, dependency, or configuration updates.
* `ci`: Continuous integration pipeline modifications.

### Examples
* `feat(edi): add Medclaim batch generation for MediSwitch`
* `fix(scrubber): prevent false positive on pediatric code 0101 for 11-year-olds`
* `security(auth): enforce TOTP setup for BureauAdmin roles`

## Pull Request Lifecycle & Merge Requirements

1. **Branch Naming**: Match the conventional naming format (`feat/`, `fix/`).
2. **Automated Test Suite**: All local unit tests must pass before opening a PR:
   ```bash
   python manage.py test
   ```
3. **No Database Migration Conflicts**: Verify migration sequences using:
   ```bash
   python manage.py makemigrations --check --dry-run
   ```
4. **Code Review**: Each pull request requires at least one approving review from a codeowner.
5. **Merge Method**: Use `Squash and merge` with a conventional commit message to preserve linear history on `main`.
