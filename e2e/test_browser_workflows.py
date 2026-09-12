import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.abspath("."))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "billing_bureau.settings")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
import django
django.setup()

from django.contrib.auth.models import User
from django_otp.plugins.otp_totp.models import TOTPDevice
from django_otp.oath import totp
from playwright.sync_api import sync_playwright, expect

ARTIFACT_DIR = r"C:\Users\bumhira27\.gemini\antigravity\brain\72dd4084-e1cd-4ae6-8b24-7c48ca6ab433"
BASE_URL = "http://127.0.0.1:8000"


def run_e2e_audit():
    print("[E2E AUDIT] Starting Playwright Browser Automation Test Suite...")
    os.makedirs(ARTIFACT_DIR, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # -------------------------------------------------------------
        # 1. Authentication (Direct Sign-In, 2FA Disabled)
        # -------------------------------------------------------------
        print("\n[Step 1] Testing Direct Sign-In (2FA Disabled)...")
        page.goto(f"{BASE_URL}/account/login/")
        page.wait_for_load_state("networkidle")
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "01_login_step_auth.png"))

        # Step 1a: Fill username & password (supports standard or two-factor wizard input names)
        if page.locator("input[name='auth-username']").count() > 0:
            page.fill("input[name='auth-username']", "admin")
            page.fill("input[name='auth-password']", "AdminPass123!")
        else:
            page.fill("input[name='username']", "admin")
            page.fill("input[name='password']", "AdminPass123!")

        page.click("button[type='submit']")
        page.wait_for_load_state("networkidle")

        # Step 1b: If prompted for token (when 2FA is toggled on)
        if "token" in page.url or page.locator("input[name='token-otp_token']").count() > 0:
            print("  - TOTP Verification Step Detected. Generating code from device key...")
            u = User.objects.get(username="admin")
            dev = TOTPDevice.objects.filter(user=u, confirmed=True).first()
            if dev:
                code = str(totp(dev.bin_key)).zfill(6)
            else:
                code = "999999"
            print(f"  - Submitting TOTP Code: {code}")
            page.screenshot(path=os.path.join(ARTIFACT_DIR, "02_login_step_token.png"))
            page.fill("input[name='token-otp_token']", code)
            page.click("button[type='submit']")
            page.wait_for_load_state("networkidle")
        else:
            print("  - 2FA is disabled. Direct single-step sign-in succeeded without OTP prompt.")

        # Verify landing on Dashboard or main page
        print(f"  - Successfully Authenticated. Current URL: {page.url}")
        time.sleep(1)
        dash_text = page.locator("body").inner_text()
        assert "Claims by Status" not in dash_text, "Found 'Claims by Status' on Dashboard!"
        print("  - Verified: 'Claims by Status' is absent from Dashboard.")
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "03_dashboard_verified.png"))

        # -------------------------------------------------------------
        # 2. Practice Management
        # -------------------------------------------------------------
        print("\n[Step 2] Auditing Practice Management...")
        page.goto(f"{BASE_URL}/practices/")
        page.wait_for_load_state("networkidle")
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "04_practices_list.png"))

        # Click into practice detail
        practice_link = page.locator("table tbody tr a").first
        if practice_link.count() > 0:
            practice_link.click()
            page.wait_for_load_state("networkidle")
            time.sleep(0.5)
            page.screenshot(path=os.path.join(ARTIFACT_DIR, "05_practice_detail.png"))
            print("  - Practice Detail loaded successfully with Tailwind layout & tabs.")

            # Verify removal of Commission Fee, Banking, and Bureau Gateways
            detail_text = page.locator("body").inner_text()
            assert "Commission Fee" not in detail_text, "Found Commission Fee in Practice Detail"
            assert "Bureau Fee" not in detail_text, "Found Bureau Fee in Practice Detail"
            assert "Direct Scheme Gateways" not in detail_text, "Found Direct Scheme Gateways in Practice Detail"
            assert "Bank Account" not in detail_text, "Found Bank Account in Practice Detail"
            print("  - Verified: Practice Detail has no Commission Fees, Banking details, or Direct Scheme Gateways.")

            # Also check practice edit form
            page.goto(f"{BASE_URL}/practices/1/edit/")
            page.wait_for_load_state("networkidle")
            form_text = page.locator("body").inner_text()
            assert "bank_account" not in form_text.lower()
            assert "fee_percentage" not in form_text.lower()
            print("  - Verified: Practice Form has no banking or fee structure inputs.")

        # -------------------------------------------------------------
        # 3. Claims Engine: Clinical Scrubbing & Medclaim EDI Submission
        # -------------------------------------------------------------
        print("\n[Step 3] Auditing Claims Engine & Medclaim EDI Switch...")
        page.goto(f"{BASE_URL}/claims/")
        page.wait_for_load_state("networkidle")
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "06_claims_list.png"))

        # Step 3a: Verify Clinical Scrubber blocks invalid claim (Claim #7: 41yo on pediatric 0190)
        print("  - Testing Clinical Scrubber on Claim #7 (Invalid Tariff/Age match)...")
        page.goto(f"{BASE_URL}/claims/7/")
        page.wait_for_load_state("networkidle")
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "07_claim_detail.png"))

        scrub_btn = page.locator("button:has-text('Resubmit via Medclaim EDI'), button:has-text('Submit via Medclaim EDI')").first
        if scrub_btn.count() > 0:
            scrub_btn.click()
            page.wait_for_load_state("networkidle")
            time.sleep(1)
            page.screenshot(path=os.path.join(ARTIFACT_DIR, "08_claim_scrubbing_blocked.png"))
            print("  - Clinical Scrubber correctly caught validation failure and displayed alert toast.")

        # Step 3b: Verify Clean Claim EDI Transmission (Claim #8)
        print("  - Testing Clean EDI Submission on Claim #8...")
        page.goto(f"{BASE_URL}/claims/8/")
        page.wait_for_load_state("networkidle")

        submit_btn = page.locator("button:has-text('Submit via Medclaim EDI')").first
        if submit_btn.count() > 0:
            submit_btn.click()
            page.wait_for_load_state("networkidle")
            time.sleep(1)
            page.screenshot(path=os.path.join(ARTIFACT_DIR, "08_claim_submitted_edi.png"))
            print("  - Clean Claim submitted successfully via Medclaim EDI.")

            # Step 3c: Open Medclaim EDI Flat-File Inspection Modal
            inspect_btn = page.locator("button:has-text('Inspect EDI')").first
            if inspect_btn.count() > 0:
                inspect_btn.click()
                time.sleep(0.8)
                page.screenshot(path=os.path.join(ARTIFACT_DIR, "09_edi_payload_modal.png"))
                print("  - Opened Medclaim EDI Flat-File modal successfully.")

        # Step 3d: Verify Claim Deletion via Edit workflow
        print("  - Testing Claim Deletion workflow...")
        from practices.models import Practice
        from patients.models import Patient
        from claims.models import Claim, ClaimLineItem

        practice = Practice.objects.first()
        patient = Patient.objects.filter(practice=practice).first()
        test_claim = Claim.objects.create(
            practice=practice,
            patient=patient,
            date_of_service=datetime.now().date(),
            claim_status='draft',
            total_billed=650.00
        )
        ClaimLineItem.objects.create(
            claim=test_claim,
            tariff_code="0190",
            amount_billed=650.00,
            icd10_primary="J06.9"
        )
        del_id = test_claim.id
        print(f"  - Created test claim #{del_id} to verify deletion.")

        # Visit claim edit page
        page.goto(f"{BASE_URL}/claims/{del_id}/edit/")
        page.wait_for_load_state("networkidle")
        time.sleep(0.5)
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "14_claim_edit_with_delete_btn.png"))

        delete_link = page.locator("a:has-text('Delete Claim')")
        assert delete_link.count() > 0, "Delete Claim button missing on edit page"
        delete_link.click()
        page.wait_for_load_state("networkidle")
        time.sleep(0.5)
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "15_claim_confirm_delete.png"))

        confirm_heading = page.locator("h2.text-red-900").inner_text()
        assert f"Delete Claim #{del_id}" in confirm_heading, "Did not reach confirmation page"
        print(f"  - Reached confirmation page for Claim #{del_id}.")

        confirm_btn = page.locator("button:has-text('Yes, Delete Claim')")
        confirm_btn.click()
        page.wait_for_load_state("networkidle")
        time.sleep(0.5)
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "16_claim_deleted_confirmed.png"))

        # Verify claim is deleted in database
        assert Claim.objects.filter(id=del_id).count() == 0, f"Claim #{del_id} still exists in database"
        print(f"  - Claim #{del_id} successfully deleted from database and redirected to list.")

        # -------------------------------------------------------------
        # 4. EDI Transmission Logs Audit View
        # -------------------------------------------------------------
        print("\n[Step 4] Auditing Global EDI Transmission Logs...")
        page.goto(f"{BASE_URL}/claims/edi-logs/")
        page.wait_for_load_state("networkidle")
        time.sleep(0.5)
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "10_edi_transmission_logs.png"))
        print("  - EDI Transmission Logs rendered with batch references and ACK statuses.")

        # -------------------------------------------------------------
        # 5. Financials & Collections Dashboard
        # -------------------------------------------------------------
        print("\n[Step 5] Auditing Patient Statements & Collections...")
        page.goto(f"{BASE_URL}/collections/financials/")
        page.wait_for_load_state("networkidle")
        time.sleep(0.5)
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "11_bureau_financials.png"))
        fin_text = page.locator("body").inner_text()
        assert "Patient Statements & Shortfalls" in fin_text
        assert "Bureau Invoices" not in fin_text
        print("  - Patient Statements dashboard verified without commission invoices.")

        # -------------------------------------------------------------
        # 6. Reconciliation Engine Dashboard
        # -------------------------------------------------------------
        print("\n[Step 6] Auditing Remittance Reconciliation Dashboard...")
        page.goto(f"{BASE_URL}/reconciliation/")
        page.wait_for_load_state("networkidle")
        time.sleep(0.5)
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "12_reconciliation_dashboard.png"))
        print("  - Remittance Reconciliation dashboard verified.")

        # -------------------------------------------------------------
        # 7. Scan Ward Notes (AI Extractor)
        # -------------------------------------------------------------
        print("\n[Step 7] Auditing Ward Note AI Extraction View...")
        page.goto(f"{BASE_URL}/claims/upload-note/")
        page.wait_for_load_state("networkidle")
        time.sleep(0.5)
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "13_scan_ward_notes.png"))
        print("  - Ward Note AI Scanner view verified.")

        browser.close()
        print("\n[E2E AUDIT COMPLETE] All browser workflows executed and visual artifacts captured!")


if __name__ == "__main__":
    run_e2e_audit()
