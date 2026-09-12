# Test Registry

This registry maps every core system feature to its automated verification suite, tracking current test status and coverage targets.

| Feature / Component | Test Suite File | Status | Coverage Target | Verification Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Medclaim EDI Batch Generation** | `switch_adapters/tests.py` | Pass (4/4) | `generate_medclaim_edi`, `validate_medclaim_edi`, `SwitchTransport` | Segment formatting, trailer checksums, loopback ACK parsing |
| **Claim Scrubbing Engine** | `claims/tests_scrubbing.py` | Pass (3/3) | `ClaimScrubber`, `GenderDiagnosisMatchRule`, `AgeTariffMatchRule` | Clinical rules: pediatric age limits and gender ICD-10 validation |
| **EDI Pipeline & Submission** | `claims/tests_edi_pipeline.py` | Pass (4/4) | `batch_claims_edi`, `claim_edi_submit`, `EdiLogListView` | End-to-end batching, scrubbing block, view redirects, audit log rendering |
| **AI Ward Note Extraction** | `claims/tests_ai_extractor.py` | Pass (4/4) | `extract_claim_from_image`, `ReviewExtractedClaimView` | Gemini schema parsing, line item draft creation |
| **Offline Ward Sync REST API** | `api/tests.py` | Pass (5/5) | `ClaimSyncAPIView`, `Idempotency-Key`, RFC 7807 | Duplicate request suppression, validation error structures |
| **Patient Statements & Liability** | `billing_collections/tests.py` | Pass (2/2) | `PatientStatement`, `BureauInvoice` | Patient liability calculations, 2% commission ledger billing |
| **Currency & Session Security** | `core/tests.py` | Pass (6/6) | `rands`, `percentage`, MFA Session Verification | South African currency formatting, TOTP verification session state |
| **Remittance Auto-Reconciliation** | `reconciliation/tests.py` | Pass (4/4) | `AutoMatcher`, `RemittanceFile` | Atomic line matching, multi-pass matching, balance reconciliation |
| **UI End-to-End Browser Automation** | `e2e/test_browser_workflows.py` | Pass (7/7 steps) | MFA, Dashboard, Practices, Claims EDI, EDI Logs, Financials, Reconciliation, OCR | Automated Playwright browser verification against live server |
