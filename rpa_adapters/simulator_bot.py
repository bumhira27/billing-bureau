import time
import random
from datetime import datetime
from playwright.sync_api import sync_playwright
from .base_bot import BasePortalBot, BotResult
from .dtos import ClaimDTO

class SimulatorPortalBot(BasePortalBot):
    """
    RPA bot that renders and automates a South African provider portal workflow
    via Playwright in headless Chromium, capturing visual proof of submission.
    """

    def submit_claim(self, claim_dto: ClaimDTO) -> BotResult:
        start_time = time.time()
        
        patient_name = claim_dto.patient.full_name
        membership_number = claim_dto.patient.membership_number
        
        # Take the first line for simplification in simulator display
        first_line = claim_dto.lines[0] if claim_dto.lines else None
        tariff_code = first_line.tariff_code if first_line else '0190'
        icd10 = first_line.icd10 if first_line else 'J06.9'
        
        amount = f"{claim_dto.total_amount:.2f}"
        practice_nr = claim_dto.practice.practice_number
        practice_name = claim_dto.practice.practice_name
        doctor_name = claim_dto.practice.provider_name
        bureau_user = claim_dto.bureau_username or self.username or 'BUR-MASTER'
        bureau_bhf = claim_dto.bureau_bhf or 'BUR-88921'
        scheme_name = claim_dto.patient.scheme_name

        ref_number = f"DIR-{datetime.now().strftime('%Y%m%d')}-{random.randint(10000, 99999)}"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{scheme_name} - Bureau Claims Portal</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <style>
                body {{ background-color: #f4f6f9; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 20px; }}
                .portal-header {{ background-color: #0b2545; color: white; padding: 15px 25px; border-radius: 8px 8px 0 0; }}
                .portal-box {{ background: white; border: 1px solid #dee2e6; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
                .badge-success {{ background-color: #198754; }}
            </style>
        </head>
        <body>
            <div class="container" style="max-width: 800px;">
                <div class="portal-box mb-4">
                    <div class="portal-header d-flex justify-content-between align-items-center">
                        <div>
                            <h4 class="mb-0">{scheme_name} Bureau Gateway</h4>
                            <small class="text-light opacity-75">Bureau Session: {bureau_user} ({bureau_bhf})</small>
                        </div>
                        <span class="badge bg-light text-dark">Practice: {practice_nr}</span>
                    </div>
                    <div class="p-4">
                        <div class="alert alert-success d-flex align-items-center" role="alert">
                            <div>
                                <h5 class="alert-heading mb-1">Direct Bureau Claim Adjudicated Successfully</h5>
                                <p class="mb-0">Zero-Switch Direct Submission Accepted. Intermediary fees bypassed.</p>
                            </div>
                        </div>

                        <div class="row g-3 mb-4">
                            <div class="col-md-6">
                                <label class="form-label text-muted small">Scheme Direct Reference</label>
                                <div class="fs-5 fw-bold font-monospace text-primary">{ref_number}</div>
                            </div>
                            <div class="col-md-6">
                                <label class="form-label text-muted small">Adjudication Status</label>
                                <div><span class="badge bg-success fs-6">APPROVED (100% Covered)</span></div>
                            </div>
                            <div class="col-md-6">
                                <label class="form-label text-muted small">Client Practice & Provider</label>
                                <div class="fw-bold">{practice_name}</div>
                                <div class="small text-muted">{doctor_name} (BHF: {practice_nr})</div>
                            </div>
                            <div class="col-md-6">
                                <label class="form-label text-muted small">Patient / Dependant</label>
                                <div class="fw-bold">{patient_name} (Mem: {membership_number})</div>
                            </div>
                        </div>

                        <table class="table table-bordered table-sm mb-3">
                            <thead class="table-light">
                                <tr>
                                    <th>Tariff Code</th>
                                    <th>ICD-10 Diagnosis</th>
                                    <th>Claimed Amount</th>
                                    <th>Scheme Approved</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td class="font-monospace fw-bold">{tariff_code}</td>
                                    <td class="font-monospace">{icd10}</td>
                                    <td class="text-end">R {amount}</td>
                                    <td class="text-end text-success fw-bold">R {amount}</td>
                                </tr>
                            </tbody>
                        </table>

                        <div class="border-top pt-3 text-muted small d-flex justify-content-between">
                            <span>Channel: Central Bureau Administrator Gateway (R0.00 Switch Fee)</span>
                            <span>Processed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span>
                        </div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        screenshot_bytes = None
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            page = browser.new_page(viewport={'width': 1024, 'height': 768})
            page.set_content(html_content)
            page.wait_for_timeout(500)
            screenshot_bytes = page.screenshot(full_page=True)
            browser.close()

        execution_time = round(time.time() - start_time, 2)
        return BotResult(
            success=True,
            reference_number=ref_number,
            message=f"Direct submission accepted on {scheme_name} portal.",
            screenshot_bytes=screenshot_bytes,
            execution_time=execution_time,
        )
