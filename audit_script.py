import time
from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1280, 'height': 800})
        
        # 1. Login
        page.goto('http://localhost:8000/accounts/login/')
        page.screenshot(path='audit_login.png', full_page=True)
        
        page.fill('input[name="username"]', 'admin')
        page.fill('input[name="password"]', 'admin')  # Assuming default superuser
        page.click('button[type="submit"]')
        time.sleep(1)
        
        # 2. Dashboard
        page.goto('http://localhost:8000/')
        page.screenshot(path='audit_dashboard.png', full_page=True)
        
        # 3. Claims
        page.goto('http://localhost:8000/claims/')
        page.screenshot(path='audit_claims.png', full_page=True)
        
        # 4. Financials
        page.goto('http://localhost:8000/collections/financials/')
        page.screenshot(path='audit_financials.png', full_page=True)
        
        # 5. EDI Logs
        page.goto('http://localhost:8000/claims/rpa-logs/')
        page.screenshot(path='audit_edi_logs.png', full_page=True)
        
        browser.close()

if __name__ == '__main__':
    run()
