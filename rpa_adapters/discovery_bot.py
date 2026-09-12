import time
import random
from datetime import datetime
from playwright.sync_api import sync_playwright
from .base_bot import BasePortalBot, BotResult
from .dtos import ClaimDTO

class DiscoveryPortalBot(BasePortalBot):
    """
    RPA bot for Discovery Health Provider Portal.
    """
    DEFAULT_URL = "https://www.discovery.co.za/portal/provider"

    def submit_claim(self, claim_dto: ClaimDTO) -> BotResult:
        start_time = time.time()
        screenshot_bytes = None
        ref_number = ""

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            page = browser.new_page(viewport={'width': 1280, 'height': 800})
            
            try:
                # 1. Login
                page.goto(self.portal_url or self.DEFAULT_URL, timeout=60000)
                # Note: These selectors are speculative and must be updated with live HTML
                page.fill("input[name='username']", self.username)
                page.fill("input[name='password']", self.password)
                page.click("button[type='submit']")
                
                # Wait for dashboard to load (handling potential OTP prompts would go here)
                page.wait_for_selector(".dashboard-container", timeout=30000)

                # 2. Navigate to Claims Submission
                page.click("text='Submit a Claim'")
                page.wait_for_selector("#claim-form", timeout=15000)

                # 3. Fill Claim Data
                page.fill("#patient-membership", claim_dto.patient.membership_number)
                page.fill("#patient-dependent", claim_dto.patient.dependent_code)
                page.click("#verify-patient")
                page.wait_for_timeout(2000) # wait for AJAX

                page.fill("#date-of-service", claim_dto.date_of_service)
                page.fill("#practice-number", claim_dto.practice.practice_number)

                # Fill lines
                for line in claim_dto.lines:
                    page.click("#add-line-item")
                    page.fill(f".line-item:last-child .tariff-code", line.tariff_code)
                    page.fill(f".line-item:last-child .icd10-code", line.icd10)
                    page.fill(f".line-item:last-child .amount", str(line.amount))

                # 4. Submit
                if self.dry_run:
                    # In dry_run mode, we don't click submit. Just take a screenshot of the filled form.
                    page.wait_for_timeout(1000)
                    screenshot_bytes = page.screenshot(full_page=True)
                    ref_number = f"DRYRUN-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    message = "Dry Run: Claim form filled but not submitted."
                else:
                    page.click("#submit-final-claim")
                    page.wait_for_selector(".submission-success", timeout=30000)
                    ref_number = page.inner_text(".reference-number")
                    screenshot_bytes = page.screenshot(full_page=True)
                    message = "Claim submitted successfully."

                success = True

            except Exception as e:
                success = False
                message = f"RPA Error: {str(e)}"
                try:
                    screenshot_bytes = page.screenshot(full_page=True)
                except:
                    pass

            finally:
                browser.close()

        return BotResult(
            success=success,
            message=message,
            reference_number=ref_number,
            execution_time=round(time.time() - start_time, 2),
            screenshot_bytes=screenshot_bytes
        )

    def fetch_remittances(self, date_from: str, date_to: str) -> list[bytes]:
        """
        Navigates to the Remittance/Reports tab and downloads the eRA files.
        """
        files = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            page = browser.new_page(viewport={'width': 1280, 'height': 800})
            
            try:
                page.goto(self.portal_url or self.DEFAULT_URL, timeout=60000)
                page.fill("input[name='username']", self.username)
                page.fill("input[name='password']", self.password)
                page.click("button[type='submit']")
                page.wait_for_selector(".dashboard-container", timeout=30000)

                # Navigate to Reports
                page.click("text='Remittance Advice'")
                page.wait_for_selector("#date-from")
                
                page.fill("#date-from", date_from)
                page.fill("#date-to", date_to)
                page.click("#search-remittances")
                
                # Wait for download links
                page.wait_for_selector(".download-link", timeout=15000)
                
                # Download files
                links = page.query_selector_all(".download-link")
                for link in links:
                    with page.expect_download() as download_info:
                        link.click()
                    download = download_info.value
                    
                    # Read the downloaded file into bytes
                    path = download.path()
                    if path:
                        with open(path, "rb") as f:
                            files.append(f.read())
            except Exception as e:
                print(f"Error fetching remittances: {e}")
            finally:
                browser.close()
                
        return files
