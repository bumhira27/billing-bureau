# Billing Bureau: Project Roadmap

This document tracks the long-term strategic goals, legal requirements, and technical milestones for the Billing Bureau software.

## Phase 1: Core Construction (Completed)
- [x] Claim Ingestion & Reconciliation Engine (Atomic DB transactions)
- [x] Pre-Scrubbing Rules Engine (Gender/Age clinical validation)
- [x] POPIA/HIPAA Compliance (Database-level PHI encryption & read-access auditing)
- [x] Modular Architecture (Decoupled DTOs for switch plugin ecosystem)
- [x] Collections & Patient Invoicing (Patient liability statements, Bureau commission ledgers)
- [x] UI/UX Dashboards (Jazzmin admin, Tailwind frontend, Chart.js financials)
- [x] AI Ward Note Extraction (Gemini-powered ICD-10 extraction from scanned clinical notes)

## Phase 2: Security & Access Control (Completed)
- [x] Multi-Factor Authentication (MFA) via TOTP (django-otp + django-two-factor-auth)
- [x] Role-Based Access Control (RBAC) (Practice-scoped data isolation for PracticeUsers)
- [x] Dynamic sidebar redaction (Bureau-only links hidden for PracticeUsers)
- [x] Test suite updated for MFA-aware sessions

## Phase 3: Production Hardening & EDI Integration (In Progress)
- [x] Replace RPA web-scraping with BHF-accredited Medclaim EDI switch integration
- [x] Frontend cleanup: complete Bootstrap eradication and Tailwind CSS migration across 30+ templates
- [x] Login page redesign using Tailwind CSS and custom spring animations
- [x] Medclaim EDI Flat-File batch generation, validation, and staging
- [x] Clearinghouse Level 1 ACK/NAK response parsing and audit logging (`EdiTransmissionLog`)
- [ ] SFTP polling for inbound eRA files from MediSwitch/Healthbridge clearinghouse
- [ ] Cloud hosting & data sovereignty deployment (AWS Cape Town or Azure Johannesburg)

## Phase 4: Legal & Commercial Structuring (Pre-Launch)
- [ ] POPIA "Operator" Agreement template between Bureau and medical practices
- [ ] PAIA / POPIA Manual (public-facing data processing disclosure)
- [ ] BHF Bureau Registration (obtain official Bureau Practice Number)

## Phase 5: Expansion & Direct Switch Accreditation
- [ ] Credit bureau and debt collection agency integration
- [ ] Direct SFTP/EDI connection to Discovery Health and Medscheme
  - [ ] Apply for direct EDI testing credentials
  - [ ] Pass 50-100 sample claim test runs
  - [ ] Batch file drops onto Scheme SFTP servers
  - [ ] Native eRA file parsing directly from schemes
