# Changelog

All notable changes to the Billing Bureau project will be documented in this file.

## [Unreleased] - 2026-09-12

### Added
- **Claim Scrubbing Rules Engine**: `ClaimScrubber` registry that automatically validates claims for gender and age-tariff mismatches before RPA submission to fail fast.
- **POPIA/HIPAA Compliance**: Implemented `EncryptedCharField` using deterministic AES (Fernet) for database-level encryption of `Patient.id_number`, phone numbers, emails, and medical aid membership numbers.
- **Read Access Audit Logging**: Added `PHIReadLoggerMiddleware` and `PHIReadAudit` model to track when users view patient Patient Health Information (PHI).
- **Modular RPA Adapters**: Decoupled bot scripts from core Django by migrating RPA code into an isolated `rpa_adapters` package with a strict `BasePortalBot` interface.
- **Interoperability DTOs**: Standardized Claim payload structure using `ClaimDTO` (inspired by HL7 FHIR standard) to pass data to RPA bots, replacing rigid Django ORM object passing.

### Changed
- Refactored `claims.tasks.submit_claim_rpa` to utilize the new scrubbing engine and the modular DTO-driven bot adapters.
- Updated all test suites to accommodate encrypted fields, modular bot mocking, and scrubbing pipelines (33 passing tests).
