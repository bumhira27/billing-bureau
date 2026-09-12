# Billing Bureau: Project Roadmap

This document tracks the long-term strategic goals, legal requirements, and technical milestones for the Billing Bureau software.

## Phase 1: Core Construction (Completed)
- [x] **Claim Ingestion & Reconciliation Engine**: Atomic database transactions.
- [x] **Pre-Scrubbing Rules Engine**: Gender/Age clinical validation.
- [x] **POPIA/HIPAA Compliance**: Database-level PHI deterministic encryption & read-access auditing.
- [x] **Modular Architecture**: Decoupled Data Transfer Objects (DTOs) for the plugin ecosystem.
- [x] **RPA Submission Engine**: Playwright browser automation bots for Discovery and Medscheme.
- [x] **Automated eRA Fetching**: Background Celery tasks to scrape and download remittance files.
- [x] **Collections & Patient Invoicing**: Patient liability statements and Bureau commission ledgers.
- [x] **UI/UX Dashboards**: Jazzmin admin integration and visual tracking for claims, bot screenshots, and financials.

## Phase 2: Beta Launch Readiness (Up Next)
- [ ] **Multi-Factor Authentication (MFA)**: Secure bureau staff logins.
- [ ] **Role-Based Access Control (RBAC)**: Restrict staff access to specific practices/patients.
- [ ] **Cloud Hosting & Data Sovereignty**: Deploy to a secure, POPIA-compliant cloud provider (e.g., AWS Cape Town or Azure Johannesburg).

## Phase 3: Legal & Commercial Structuring (Pre-Launch)
- [ ] **The "Operator" Agreement**: Draft and implement legal contracts between the Bureau and medical practices to define POPIA liability.
- [ ] **PAIA / POPIA Manual**: Draft and publish a public manual detailing data processing, subjects, and security measures.
- [ ] **BHF Bureau Registration**: Register formally with the Board of Healthcare Funders (BHF) to receive an official Bureau Practice Number.

## Phase 4: Expansion & "True Switch" Accreditation
- [ ] **Expansion into Financial Services**: Integrate with credit bureaus and debt collection agencies.
- [ ] **Direct SFTP/EDI Connection (Building Your Own Switch)**:
  - [ ] Phase out RPA web scraping.
  - [ ] Apply to Discovery Health and Medscheme for direct EDI testing credentials.
  - [ ] Pass the 50-100 sample claim test runs.
  - [ ] Implement batch file drops directly onto Scheme SFTP servers.
  - [ ] Automatically receive and parse native electronic remittance advice (eRA) files directly from the schemes.
