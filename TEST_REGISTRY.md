# Test Registry

| Feature/Component | Test File | Status | Coverage Target | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Claim Ingestion** | `claims/tests.py` | Pass | `Claim`, `ClaimLineItem` | Basic creation and state |
| **Pre-Scrubbing Rules** | `claims/tests_scrubbing.py` | Missing | `ClaimScrubber` | Need tests for age/gender rules |
| **POPIA Encryption** | `core/tests.py` | Missing | `EncryptedCharField` | Need tests for deterministic IV |
| **EDI Generation** | `switch_adapters/tests.py` | Pass | `generate_medclaim_edi` | Flat-file structure verified |
| **Patient Statements** | `billing_collections/tests.py` | Pass | `PatientStatement` | Calculation logic verified |
| **Bureau Commission** | `billing_collections/tests.py` | Pass | `BureauInvoice` | 2% fee calculation verified |
| **UI: EDI Logs** | UI E2E (Playwright) | Missing | `/claims/rpa-logs/` | Needs regression tests |
| **UI: Financials** | UI E2E (Playwright) | Missing | `/collections/financials/` | Needs regression tests |
