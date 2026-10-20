"""
Automated Browser Screenshot Capture Utility for Project Atlas.
Captures the 5 key evaluator walkthrough steps of the CodeIgniter 3 Portal.

Usage:
  1. Ensure the stack is running (docker compose up -d or local dev server)
  2. pip install playwright
  3. playwright install chromium
  4. python scripts/capture_screenshots.py
"""

import os
import sys
import time

def main():
    try:
        from playwright.sync_api import sync_playwright  # type: ignore[import-untyped,import-not-found]
    except ImportError:
        print("[!] Playwright is not installed.")
        print("    Install via: pip install playwright && playwright install chromium")
        sys.exit(1)

    output_dir = os.path.join(os.path.dirname(__file__), "..", "docs", "assets")
    os.makedirs(output_dir, exist_ok=True)

    base_url = os.environ.get("PORTAL_URL", "http://localhost:8080")
    print(f"[*] Capturing evaluator screenshots from {base_url}...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # Step 1: Portal Landing Page
        print("  -> Capturing Step 1: Portal Landing...")
        try:
            page.goto(f"{base_url}/preview.html", timeout=10000)
        except Exception:
            page.goto(f"{base_url}/index.php/chat", timeout=10000)
        page.wait_for_timeout(1000)
        page.screenshot(path=os.path.join(output_dir, "01_portal_landing.png"))

        # Step 2: Login Modal
        print("  -> Capturing Step 2: Login Modal...")
        login_btn = page.locator("button:has-text('Sign In'), button:has-text('Login'), a:has-text('Sign In')").first
        if login_btn.is_visible():
            login_btn.click()
            page.wait_for_timeout(800)
            page.screenshot(path=os.path.join(output_dir, "02_login_modal.png"))

        # Step 3: Fill Credentials and Authenticate
        print("  -> Capturing Step 3: Authenticated Entitlements Dashboard...")
        email_input = page.locator("input[type='email'], input[name='email']").first
        pass_input = page.locator("input[type='password'], input[name='password']").first
        if email_input.is_visible() and pass_input.is_visible():
            email_input.fill("ops@northwind.example.com")
            pass_input.fill("Password123!@#")
            submit_btn = page.locator("button[type='submit'], button:has-text('Log In')").first
            if submit_btn.is_visible():
                submit_btn.click()
                page.wait_for_timeout(1500)
        page.screenshot(path=os.path.join(output_dir, "03_client_entitlements.png"))

        # Step 4: Copilot Chat View
        print("  -> Capturing Step 4: Active Copilot Workspace...")
        chat_tab = page.locator("button:has-text('Atlas Access'), a:has-text('Atlas Access'), button:has-text('Copilot')").first
        if chat_tab.is_visible():
            chat_tab.click()
            page.wait_for_timeout(800)
        page.screenshot(path=os.path.join(output_dir, "04_copilot_chat.png"))

        # Step 5: Submit Query & Capture Response
        print("  -> Capturing Step 5: Response with In-Text Citations & Table Rendering...")
        # Select C-04 for water utility scenario
        client_select = page.locator("#loginClientSelect")
        if client_select.is_visible():
            page.select_option("#loginClientSelect", "C-04")
            login_btn = page.locator("#loginFormView .btn-auth-submit")
            if login_btn.is_visible():
                login_btn.click()
                page.wait_for_timeout(1000)

        query_input = page.locator("textarea, input[placeholder*='Ask']").first
        if query_input.is_visible():
            query_input.fill("What was the smart water meter market size in 2024?")
            send_btn = page.locator("#sendBtn, button:has-text('Send')").first
            if send_btn.is_visible():
                send_btn.click()
                try:
                    page.wait_for_selector(".answer-content table", timeout=25000)
                    page.wait_for_timeout(1000)
                    page.evaluate("() => { const tbl = document.querySelector('.answer-content table'); if (tbl) { tbl.scrollIntoView({block: 'center'}); const cs = document.getElementById('chatStream'); if (cs) cs.scrollTop = Math.max(0, cs.scrollTop - 85); } }")
                    page.wait_for_timeout(800)
                except Exception:
                    page.wait_for_timeout(4000)

        page.screenshot(path=os.path.join(output_dir, "05_query_response_citations.png"))

        browser.close()
        print(f"[OK] Successfully captured 5 evaluator screenshots to {output_dir}!")

if __name__ == "__main__":
    main()
