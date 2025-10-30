import os
import sys
import time
import datetime
import requests
from requests.auth import HTTPBasicAuth

# ----------------------------
# Environment Variables
# ----------------------------
CONFLUENCE_BASE = os.getenv('CONFLUENCE_BASE')
CONFLUENCE_USER = os.getenv('CONFLUENCE_USER')
CONFLUENCE_TOKEN = os.getenv('CONFLUENCE_TOKEN')
CONFLUENCE_SPACE = os.getenv('CONFLUENCE_SPACE')
CONFLUENCE_TITLE = os.getenv('CONFLUENCE_TITLE')

REPORT_DIR = 'report'
VERSION_FILE = os.path.join(REPORT_DIR, 'version.txt')
BASE_NAME = 'test_result_report'

auth = HTTPBasicAuth(CONFLUENCE_USER, CONFLUENCE_TOKEN)
headers = {"Content-Type": "application/json", "X-Atlassian-Token": "no-check"}


# ----------------------------
# Helpers
# ----------------------------
def read_version():
    """Read current version number."""
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE) as f:
            return int(f.read().strip())
    return 1


def extract_test_summary():
    """Extract summary from pytest_output.txt if available."""
    pytest_output = os.path.join(REPORT_DIR, "pytest_output.txt")
    if not os.path.exists(pytest_output):
        return "No test summary available."

    with open(pytest_output, encoding='utf-8', errors='ignore') as f:
        text = f.read()

    import re
    passed = failed = errors = skipped = 0
    if m := re.search(r"(\d+)\s+passed", text): passed = int(m.group(1))
    if m := re.search(r"(\d+)\s+failed", text): failed = int(m.group(1))
    if m := re.search(r"(\d+)\s+error", text): errors = int(m.group(1))
    if m := re.search(r"(\d+)\s+skipped", text): skipped = int(m.group(1))
    total = passed + failed + errors + skipped
    rate = (passed / total * 100) if total else 0

    return f"✅ {passed} passed, ❌ {failed} failed, ⚠️ {errors} errors, ⏭ {skipped} skipped — Pass rate: {rate:.1f}%"


def create_confluence_page(title, html_body):
    """Create a new Confluence page."""
    url = f"{CONFLUENCE_BASE}/rest/api/content"
    payload = {
        "type": "page",
        "title": title,
        "space": {"key": CONFLUENCE_SPACE},
        "body": {"storage": {"value": html_body, "representation": "storage"}}
    }
    res = requests.post(url, headers=headers, json=payload, auth=auth)
    if res.status_code == 403:
        sys.exit("❌ Forbidden: User lacks permission to create pages in this space.")
    res.raise_for_status()
    data = res.json()
    page_id = data["id"]
    print(f"🧾 Created new Confluence page: '{title}' (ID: {page_id})")
    return page_id


def upload_attachment(page_id, file_path):
    """Upload a file (PDF/HTML) as an attachment with retry."""
    file_name = os.path.basename(file_path)
    mime_type = "application/pdf" if file_name.endswith(".pdf") else "text/html"
    url = f"{CONFLUENCE_BASE}/rest/api/content/{page_id}/child/attachment"

    # Retry upload in case Confluence hasn't fully committed the new page
    for attempt in range(1, 4):
        try:
            with open(file_path, "rb") as f:
                files = {"file": (file_name, f, mime_type)}
                res = requests.post(url, files=files, auth=auth, headers={"X-Atlassian-Token": "no-check"})

            if res.status_code in (200, 201):
                data = res.json()
                attachment_id = data["results"][0]["id"]
                print(f"📎 Uploaded attachment '{file_name}' (id: {attachment_id})")
                return file_name
            else:
                print(f"⚠️ Attempt {attempt}: Upload failed ({res.status_code}) - retrying...")
                time.sleep(2)
        except Exception as e:
            print(f"⚠️ Attempt {attempt} error: {e}")
            time.sleep(2)

    sys.exit(f"❌ Failed to upload attachment '{file_name}' after 3 attempts.")


def construct_download_link(page_id, file_name):
    """Generate download link for uploaded attachment."""
    return f"{CONFLUENCE_BASE}/download/attachments/{page_id}/{file_name}?api=v2"


# ----------------------------
# Main Logic
# ----------------------------
def main():
    version = read_version()
    pdf_path = os.path.join(REPORT_DIR, f"{BASE_NAME}_v{version}.pdf")

    if not os.path.exists(pdf_path):
        sys.exit(f"❌ PDF report not found: {pdf_path}")

    # Summary and timestamp
    summary = extract_test_summary()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Page title and HTML
    page_title = f"{CONFLUENCE_TITLE} v{version}"
    body = f"""
        <h2>🚀 {CONFLUENCE_TITLE} (v{version})</h2>
        <p><b>Date:</b> {timestamp}</p>
        <p><b>Summary:</b> {summary}</p>
        <p>The full test result PDF report is attached below.</p>
    """

    # Create page
    page_id = create_confluence_page(page_title, body)

    # Upload PDF
    print("📤 Uploading PDF attachment...")
    pdf_name = upload_attachment(page_id, pdf_path)

    # Confirm attachment link
    pdf_link = construct_download_link(page_id, pdf_name)

    # Update page to include link
    updated_body = body + f"""
        <p><b>📎 Download:</b> <a href="{pdf_link}" target="_blank">{pdf_name}</a></p>
    """
    update_url = f"{CONFLUENCE_BASE}/rest/api/content/{page_id}"
    update_payload = {
        "id": page_id,
        "type": "page",
        "title": page_title,
        "version": {"number": 2},
        "body": {"storage": {"value": updated_body, "representation": "storage"}}
    }
    res = requests.put(update_url, headers=headers, json=update_payload, auth=auth)
    res.raise_for_status()

    print(f"✅ Successfully published v{version} to Confluence with PDF attached.")
    print(f"🔗 {pdf_link}")


# ----------------------------
# Entry Point
# ----------------------------
if __name__ == '__main__':
    try:
        main()
    except requests.exceptions.RequestException as e:
        print(f"❌ HTTP error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)
