#!/usr/bin/env python3
import os
import sys
import time
import datetime
import json
import re
import requests
from requests.auth import HTTPBasicAuth

# =============================================================
# Environment Variables
# =============================================================
CONFLUENCE_BASE  = os.getenv('CONFLUENCE_BASE', '').rstrip('/')
CONFLUENCE_USER  = os.getenv('CONFLUENCE_USER')
CONFLUENCE_TOKEN = os.getenv('CONFLUENCE_TOKEN')
CONFLUENCE_SPACE = os.getenv('CONFLUENCE_SPACE')      # e.g., DEMO
CONFLUENCE_TITLE = os.getenv('CONFLUENCE_TITLE', 'Test Result Report')

REPORT_DIR   = 'report'
VERSION_FILE = os.path.join(REPORT_DIR, 'version.txt')
BASE_NAME    = 'test_result_report'
PYTEST_LOG   = os.path.join(REPORT_DIR, 'pytest_output.txt')

auth = HTTPBasicAuth(CONFLUENCE_USER, CONFLUENCE_TOKEN)
headers = {
    "Content-Type": "application/json",
    "X-Atlassian-Token": "no-check"
}


# =============================================================
# Validation
# =============================================================
def validate_env():
    missing = []
    for key, value in {
        "CONFLUENCE_BASE": CONFLUENCE_BASE,
        "CONFLUENCE_USER": CONFLUENCE_USER,
        "CONFLUENCE_TOKEN": CONFLUENCE_TOKEN,
        "CONFLUENCE_SPACE": CONFLUENCE_SPACE
    }.items():
        if not value:
            missing.append(key)
    if missing:
        sys.exit(f"❌ Missing required environment variables: {', '.join(missing)}")

    if "/rest/api" in CONFLUENCE_BASE:
        sys.exit("❌ CONFLUENCE_BASE must NOT contain '/rest/api'. "
                 "Use the base URL: https://your-org.atlassian.net/wiki")


# =============================================================
# Read version
# =============================================================
def read_version():
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE) as f:
            try:
                return int(f.read().strip())
            except ValueError:
                return 1
    return 1


# =============================================================
# Extract test summary
# =============================================================
def extract_test_summary():
    if not os.path.exists(PYTEST_LOG):
        return "No test summary available.", "UNKNOWN"

    with open(PYTEST_LOG, encoding="utf-8", errors="ignore") as f:
        text = f.read()

    passed = failed = errors = skipped = 0

    if m := re.search(r"(\d+)\s+passed", text, re.I):  passed = int(m.group(1))
    if m := re.search(r"(\d+)\s+failed", text, re.I):  failed = int(m.group(1))
    if m := re.search(r"(\d+)\s+errors?", text, re.I): errors = int(m.group(1))
    if m := re.search(r"(\d+)\s+skipped", text, re.I): skipped = int(m.group(1))

    total = passed + failed + errors + skipped
    rate = (passed / total * 100) if total else 0

    status = "PASS" if failed == 0 and errors == 0 else "FAIL"
    emoji = "✅" if status == "PASS" else "❌"

    summary = (
        f"{emoji} {passed} passed, ❌ {failed} failed, "
        f"⚠️ {errors} errors, ⏭ {skipped} skipped — Pass rate: {rate:.1f}%"
    )

    return summary, status


# =============================================================
# Create Confluence Page
# =============================================================
def create_confluence_page(title, html_body):
    url = f"{CONFLUENCE_BASE}/rest/api/content"
    payload = {
        "type": "page",
        "title": title,
        "space": {"key": CONFLUENCE_SPACE},
        "body": {
            "storage": {
                "value": html_body,
                "representation": "storage"
            }
        }
    }

    print(f"🌐 Creating Confluence page: {title}")
    res = requests.post(url, headers=headers, json=payload, auth=auth)

    if not res.ok:
        print(f"❌ Failed to create page: HTTP {res.status_code}")
        try:
            print(json.dumps(res.json(), indent=2))
        except:
            print(res.text)
        res.raise_for_status()

    data = res.json()
    return data["id"]


# =============================================================
# Upload Attachment
# =============================================================
def upload_attachment(page_id, file_path):
    if not os.path.exists(file_path):
        sys.exit(f"❌ Missing attachment: {file_path}")

    file_name = os.path.basename(file_path)
    mime_type = "application/pdf" if file_name.endswith(".pdf") else "text/html"

    url = (
        f"{CONFLUENCE_BASE}/rest/api/content/"
        f"{page_id}/child/attachment?allowDuplicated=true"
    )

    print(f"📤 Uploading: {file_name}")

    # REQUIRED DELAY (Confluence Cloud eventually consistency)
    time.sleep(2)

    for attempt in range(1, 4):
        try:
            with open(file_path, "rb") as f:
                files = {
                    "file": (file_name, f, mime_type)
                }

                headers = { "X-Atlassian-Token": "no-check" }

                res = requests.post(
                    url,
                    files=files,
                    headers=headers,
                    auth=auth,
                )

            if res.status_code in (200, 201):
                print(f"📎 Uploaded successfully: {file_name}")
                return file_name

            print(f"⚠️ Attempt {attempt} failed: HTTP {res.status_code}")
            try:
                print(res.json())
            except:
                print(res.text)

            time.sleep(2)

        except Exception as e:
            print(f"⚠️ Attempt {attempt} exception: {e}")
            time.sleep(2)

    sys.exit(f"❌ Failed to upload attachment after 3 attempts: {file_name}")

# =============================================================
# Get current page version
# =============================================================
def get_page_version(page_id):
    url = f"{CONFLUENCE_BASE}/rest/api/content/{page_id}?expand=version"
    res = requests.get(url, auth=auth)
    if not res.ok:
        print(f"❌ Unable to fetch page version: HTTP {res.status_code}")
        try:
            print(json.dumps(res.json(), indent=2))
        except:
            print(res.text)
        res.raise_for_status()

    return res.json()["version"]["number"]


# =============================================================
# Main Script
# =============================================================
def main():
    validate_env()

    version = read_version()

    pdf_path  = os.path.join(REPORT_DIR, f"{BASE_NAME}_v{version}.pdf")
    html_path = os.path.join(REPORT_DIR, f"{BASE_NAME}_v{version}.html")

    if not os.path.exists(pdf_path) or not os.path.exists(html_path):
        sys.exit("❌ Report files missing! Cannot publish to Confluence.")

    summary, status = extract_test_summary()

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    safe_timestamp = timestamp.replace(":", "-")          # prevent invalid title errors

    emoji = "✅" if status == "PASS" else "❌"
    color = "green" if status == "PASS" else "red"

    page_title = f"{CONFLUENCE_TITLE} v{version} ({status}) - {safe_timestamp}"

    body = f"""
        <h2>{emoji} {CONFLUENCE_TITLE} (v{version})</h2>
        <p><b>Date:</b> {timestamp}</p>
        <p><b>Status:</b> <span style="color:{color}; font-weight:bold;">{status}</span></p>
        <p><b>Summary:</b> {summary}</p>
        <p>Details available in attached PDF/HTML files.</p>
    """

    # Create page
    page_id = create_confluence_page(page_title, body)

    # Upload attachments
    pdf_name  = upload_attachment(page_id, pdf_path)
    html_name = upload_attachment(page_id, html_path)

    pdf_link  = f"{CONFLUENCE_BASE}/download/attachments/{page_id}/{pdf_name}?api=v2"
    html_link = f"{CONFLUENCE_BASE}/download/attachments/{page_id}/{html_name}?api=v2"

    # Update page with download links
    updated_body = body + f"""
        <h3>📎 Attachments</h3>
        <p><a href="{html_link}">{html_name}</a></p>
        <p><a href="{pdf_link}">{pdf_name}</a></p>
    """

    current_version = get_page_version(page_id)

    update_url = f"{CONFLUENCE_BASE}/rest/api/content/{page_id}"
    update_payload = {
        "id": page_id,
        "type": "page",
        "title": page_title,
        "version": {"number": current_version + 1},
        "body": {
            "storage": {
                "value": updated_body,
                "representation": "storage"
            }
        }
    }

    print(f"📝 Updating page {page_id} to v{current_version + 1}...")
    res = requests.put(update_url, headers=headers, json=update_payload, auth=auth)
    if not res.ok:
        print(f"❌ Page update failed: HTTP {res.status_code}")
        try:
            print(json.dumps(res.json(), indent=2))
        except:
            print(res.text)
        res.raise_for_status()

    page_url = f"{CONFLUENCE_BASE}/spaces/{CONFLUENCE_SPACE}/pages/{page_id}"
    print(f"✅ Published v{version} ({status}) to Confluence: {page_url}")
    print(f"🔗 PDF: {pdf_link}")
    print(f"🔗 HTML: {html_link}")

    # Save correct URL for email script
    os.makedirs(REPORT_DIR, exist_ok=True)
    conf_link_file = os.path.join(REPORT_DIR, "confluence_url.txt")
    with open(conf_link_file, "w") as f:
        f.write(page_url)

    print(f"🔗 Page URL saved → {page_url}")


# =============================================================
# Entry Point
# =============================================================
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
