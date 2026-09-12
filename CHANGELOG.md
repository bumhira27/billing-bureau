# Changelog

All notable changes to the Billing Bureau project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0-rc.1] - 2026-09-12

### Added
* Medclaim EDI Flat-File Generation Engine (`switch_adapters/mediswitch_edi.py`) mapping claims to MediSwitch / Healthbridge batch specifications.
* Multi-pass eRA reconciliation pipeline in `reconciliation/matching.py` with exact, fuzzy-date, and manual queues.
* Database row-level locking (`select_for_update`) across line-item reconciliation to prevent race conditions during concurrent statement posting.
* Pre-submission clinical rules engine (`claims/scrubbing.py`) for automated diagnosis-gender and age-tariff validation.
* Offline Bedside Ward Sync REST API v1 (`/api/v1/claims/sync/`) with RFC 7807 problem details and mandatory `Idempotency-Key` tracking.
* Time-based One-Time Password (TOTP) Multi-Factor Authentication via `django-otp` and `django-two-factor-auth`.
* Enforced MFA middleware (`EnforceBureauAdminMFAMiddleware`) for administrative users.
* Practice-level Role-Based Access Control (`RBACQuerySetMixin`) isolating data access between `BureauAdmin` and `PracticeUser` groups.
* AI Clinical Note Extractor powered by Google GenAI SDK for extracting ICD-10 and tariff line items from photographed clinical day-sheets.
* Dynamic sidebar role redaction template filter (`has_group`) in `core/templatetags/role_tags.py`.

### Changed
* Migrated complete client presentation layer from Bootstrap 5 to Tailwind CSS and Alpine.js.
* Modernized layout templates (`base.html`, `sidebar.html`, `navbar.html`) incorporating Emil Kowalski spring animations.
* Replaced direct portal automation architecture with BHF-compliant EDI switch batching.
* Updated test suite to execute against MFA-aware session authentication and encrypted model fields.

### Fixed
* Resolved `OperationalError: no such table: django_otp_staticdevice` by registering static token plugin migrations.
* Resolved `NoReverseMatch` in administration sidebar on reference data routing.
* Corrected currency filter precision to render South African Rands consistently (`R 1,234.56`).

### Security
* Deterministic AES-256 field encryption (`EncryptedCharField`) for South African national identity numbers and medical aid membership credentials.
* `PHIReadLoggerMiddleware` capturing user context on read access to unmasked medical records.
* Secret rotation and environment configuration isolation via `django-environ`.
