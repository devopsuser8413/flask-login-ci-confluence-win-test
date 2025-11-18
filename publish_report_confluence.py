import os
import sys
import time
import datetime
import smtplib
from email.message import EmailMessage
import json
import re

import requests
from requests.auth import HTTPBasicAuth

# ----------------------------
# Environment Variables
# ----------------------------
CONFLUENCE_BASE  = os.getenv('CONFLUENCE_BASE', '').rstrip('/')  # e.g. https://your-org.atlassian.net/wiki
CONFLUENCE_USER  = os.getenv('CONFLUENCE_USER')
CONFLUENCE_TOKEN = os.getenv('CONFLUENCE_TOKEN')
CONFLUENCE_SPACE = os.getenv('CONFLUENCE_SPACE')  # e.g. "ENG"
CONFLUENCE_TITLE = os.getenv('CONFLUENCE_TITLE', 'Automated Test Report')

SMTP_HOST   = os.getenv('SMTP_HOST')
SMTP_PORT   = int(os.getenv('SMTP_PORT', '587'))
SMTP_USER   = os.getenv('SMTP_USER')
SMTP_PASS   = os.getenv('SMTP_PASS')
EMAIL_FROM  = os.getenv('REPORT_FROM')
EMAIL_TO    = os.getenv('REPORT_TO')

REPORT_DIR   = 'report'
VERSION_FILE = os.path.join(REPORT_DIR, 'version.txt')
BASE_NAME    = 'test_result_report'

auth    = HTTPBasicAuth(CONFLUENCE_USER, CONFLUENCE_TOKEN)
headers = {
    "Content-Type": "application/json",
    "X-Atlassian-Token": "no-check"
}

# ----------------------------
# Helpers
# ----------------------------
def validate_env():
    missing = []
    for key, value in {
        "CONFLUENCE_BASE": CONFLUENCE_BASE,
        "CONFLUENCE_USER": CONFLUENCE_USER,
        "CONFLUENCE_TOKEN": CONFLUENCE_TOKEN,
        "CONFLUENCE_SPACE": CONFLUENCE_SPACE,
        "SMTP_HOST": SMTP_HOST,
        "REPORT_FROM": EMAIL_FROM,
        "REPORT_TO": EMAIL_TO,
    }.items():
        if not value:
            missing.append(key)

    if missing:
        sys.exit(f"❌ Missing required environment variables: {', '.join(missing)}")

    # Basic sanity check for Confluence Cloud base URL
    if '/rest/api' in CONFLUENCE_BASE:
        sys.exit("❌ CONFLUENCE_BASE should NOT include '/rest/api'. Use something like 'https://your-org.atlassian.net/wiki'.")


def read_version():
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE) as f:
            try:
                return int(f.read().strip())
            except ValueError:
                return 1
    return 1


def extract_test_summary():
    """Extract pass/fail summary from pytest_output.txt with robust detection."""
    pytest_output = os.path.join(REPORT_DIR, "pytest_output.txt")
    if not os.path.exists(pytest_output):
        return "No test summary available.", "UNKNOWN"

    with open(pytest_output, encoding="utf-8", errors="ignore") as f:
        text = f.read()

    passed = failed = errors = skipped = 0

    if m := re.search(r"(\d+)\s+passed", text, re.IGNORECASE):
        passed = int(m.group(1))
    if m := re.search(r"(\d+)\s+failed", text, re.IGNORECASE):
        failed = int(m.group(1))
    if m := re.search(r"(\d+)\s+errors?", text, re.IGNORECASE):
        errors = int(m.group(1))
    if m := re.search(r"(\d+)\s+skipped", text, re.IGNORECASE):
        skipped = int(m.group(1))

    if "FAILED" in text.upper() and failed == 0:
        failed = 1

    total = passed + failed + errors + skipped
    rate = (passed / total * 100) if total else 0

    status = "PASS" if failed == 0 and errors == 0 else "FAIL"
    emoji = "✅" if status == "PASS" else "❌"
    summary = (
        f"{emoji} {passed} passed, ❌ {failed} failed, ⚠️ {errors} errors, "
        f"⏭ {skipped} skipped — Pass rate: {rate:.1f}%"
    )

    return summary, status


# ----------------------------
# Confluence Helpers
# ----------------------------
def create_confluence_page(title, html_body):
    """Create a new Confluence page."""
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
    print(f"🌐 Creating Confluence page at: {url}")
    print(f"🔎 Space: {CONFLUENCE_SPACE}, Title: {title}")

    res = requests.post(url, headers=headers, json=payload, auth=auth)
    if not res.ok:
        print(f"❌ Confluence create page failed: HTTP {res.status_code}")
        try:
            print("🧾 Response:", json.dumps(res.json(), indent=2))
        except Exception:
            print("🧾 Response text:", res.text)
        res.raise_for_status()

    data = res.json()
    page_id = data["id"]
    print(f"🧾 Created new Confluence page '{title}' (ID: {page_id})")
    return page_id


def upload_attachment(page_id, file_path):
    """Upload a file (PDF/HTML) to Confluence page."""
    if not os.path.exists(file_path):
        sys.exit(f"❌ Attachment file not found: {file_path}")

    file_name = os.path.basename(file_path)
    mime_type = "application/pdf" if file_name.endswith(".pdf") else "text/html"
    url = f"{CONFLUENCE_BASE}/rest/api/content/{page_id}/child/attachment"

    print(f"📤 Uploading attachment '{file_name}' to page {page_id}...")

    for attempt in range(1, 4):
        try:
            with open(file_path, "rb") as f:
                files = {"file": (file_name, f, mime_type)}
                res = requests.post(
                    url,
                    files=files,
                    auth=auth,
                    headers={"X-Atlassian-Token": "no-check"}
                )
            if res.status_code in (200, 201):
                data = res.json()
                attachment_id = data["results"][0]["id"]
                print(f"📎 Uploaded '{file_name}' (id: {attachment_id})")
                return file_name
            else:
                print(f"⚠️ Attempt {attempt} upload failed ({res.status_code})")
                try:
                    print("   Response:", res.json())
                except Exception:
                    print("   Response text:", res.text)
                time.sleep(2)
        except Exception as e:
            print(f"⚠️ Attempt {attempt} error: {e}")
            time.sleep(2)

    sys.exit(f"❌ Failed to upload attachment '{file_name}' after 3 attempts.")


def construct_download_link(page_id, file_name):
    # For Confluence Cloud typical pattern:
    # https://<base>/download/attachments/<pageId>/<file>?api=v2
    return f"{CONFLUENCE_BASE}/download/attachments/{page_id}/{file_name}?api=v2"


def get_page_version(page_id):
    """Fetch current page version from Confluence."""
    url = f"{CONFLUENCE_BASE}/rest/api/content/{page_id}?expand=version"
    res = requests.get(url, auth=auth)
    if not res.ok:
        print(f"❌ Failed to fetch page version: HTTP {res.status_code}")
        try:
            print("🧾 Response:", res.json())
        except Exception:
            print("🧾 Response text:", res.text)
        res.raise_for_status()
    data = res.json()
    return data["version"]["number"]


# ----------------------------
# Email Notification
# ----------------------------
def send_email_notification(version, summary, status, pdf_link, html_link, pdf_path, html_path):
    """Send summary email and attach both reports (clearly showing FAIL/PASS overview)."""
    msg = EmailMessage()
    emoji = "✅" if status == "PASS" else "❌"
    color = "green" if status == "PASS" else "red"

    msg["Subject"] = f"{emoji} Test Result {status} (v{version}) - Confluence Report"
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO

    # Extract numeric summary details
    passed = failed = errors = skipped = 0
    match = re.findall(r"(\d+)\s+(passed|failed|errors?|skipped)", summary, re.IGNORECASE)
    for count, label in match:
        count = int(count)
        label = label.lower()
        if "pass" in label:
            passed = count
        elif "fail" in label:
            failed = count
        elif "error" in label:
            errors = count
        elif "skip" in label:
            skipped = count

    total = passed + failed + errors + skipped
    pass_rate = round((passed / total * 100) if total else 0, 1)

    msg.set_content(f"""
Test Execution Report (v{version})
-----------------------------------
Status  : {status}
Summary : {summary}

View Reports:
HTML: {html_link}
PDF : {pdf_link}

This is an automated Jenkins notification.
""")

    msg.add_alternative(f"""
    <html>
    <body style="font-family:Arial, sans-serif; color:#222;">
        <h2>{emoji} Test Result:
            <span style="color:{color}; font-weight:bold;">{status}</span> (v{version})
        </h2>
        <p><b>Summary:</b> {summary}</p>

        <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse; margin-top:10px;">
            <tr style="background-color:#f2f2f2; text-align:center;">
                <th>✅ Passed</th>
                <th>❌ Failed</th>
                <th>⚠️ Errors</th>
                <th>⏭ Skipped</th>
                <th>Pass Rate</th>
            </tr>
            <tr style="text-align:center;">
                <td style="color:green;">{passed}</td>
                <td style="color:red;">{failed}</td>
                <td style="color:orange;">{errors}</td>
                <td>{skipped}</td>
                <td><b>{pass_rate}%</b></td>
            </tr>
        </table>

        <h3 style="margin-top:20px;">📎 View or Download Reports</h3>
        <ul>
          <li><a href="{html_link}" target="_blank">View HTML Report</a></li>
          <li><a href="{pdf_link}" target="_blank">Download PDF Report</a></li>
        </ul>

        <p style="margin-top:20px; font-size:0.9em; color:#777;">
            This is an automated Jenkins notification.<br>
            Generated on {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}.
        </p>
    </body>
    </html>
    """, subtype="html")

    # Attach both reports
    for path in (pdf_path, html_path):
        if os.path.exists(path):
            with open(path, "rb") as f:
                subtype = "pdf" if path.endswith(".pdf") else "html"
                maintype = "application" if subtype == "pdf" else "text"
                msg.add_attachment(
                    f.read(),
                    maintype=maintype,
                    subtype=subtype,
                    filename=os.path.basename(path)
                )

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
            s.ehlo()
            if SMTP_PORT == 587:
                s.starttls()
            if SMTP_USER and SMTP_PASS:
                s.login(SMTP_USER, SMTP_PASS)
            s.send_message(msg)
        print(f"📨 Email notification sent ({status}) to {EMAIL_TO}.")
    except Exception as e:
        print(f"⚠️ Failed to send email: {e}")


# ----------------------------
# Main Logic
# ----------------------------
def main():
    validate_env()

    version = read_version()
    pdf_path  = os.path.join(REPORT_DIR, f"{BASE_NAME}_v{version}.pdf")
    html_path = os.path.join(REPORT_DIR, f"{BASE_NAME}_v{version}.html")

    if not os.path.exists(pdf_path) or not os.path.exists(html_path):
        sys.exit(f"❌ Missing test report files: {pdf_path} or {html_path}")

    summary, status = extract_test_summary()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    color = "green" if status == "PASS" else "red"
    emoji = "✅" if status == "PASS" else "❌"

    # Mode B: new page every run (title includes version + status)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    page_title = f"{CONFLUENCE_TITLE} v{version} ({status}) - {timestamp}"


    body = f"""
        <h2>{emoji} {CONFLUENCE_TITLE} (v{version})</h2>
        <p><b>Date:</b> {timestamp}</p>
        <p><b>Status:</b> <span style="color:{color}; font-weight:bold;">{status}</span></p>
        <p><b>Summary:</b> {summary}</p>
        <p>See attachments below for detailed results.</p>
    """

    # 1) Create page
    page_id = create_confluence_page(page_title, body)

    # 2) Upload attachments
    print("📤 Uploading attachments...")
    pdf_name  = upload_attachment(page_id, pdf_path)
    html_name = upload_attachment(page_id, html_path)

    pdf_link  = construct_download_link(page_id, pdf_name)
    html_link = construct_download_link(page_id, html_name)

    # 3) Update the page body to include download links
    updated_body = body + f"""
        <p><b>📎 Downloads:</b>
            <br>➡️ <a href="{html_link}" target="_blank">{html_name}</a>
            <br>➡️ <a href="{pdf_link}" target="_blank">{pdf_name}</a>
        </p>
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

    print(f"📝 Updating page {page_id} to version {current_version + 1}...")
    res = requests.put(update_url, headers=headers, json=update_payload, auth=auth)
    if not res.ok:
        print(f"❌ Failed to update page: HTTP {res.status_code}")
        try:
            print("🧾 Response:", res.json())
        except Exception:
            print("🧾 Response text:", res.text)
        res.raise_for_status()

    print(f"✅ Published v{version} ({status}) to Confluence.")
    print(f"🔗 PDF: {pdf_link}")
    print(f"🔗 HTML: {html_link}")

    # 4) Send email notification
    send_email_notification(version, summary, status, pdf_link, html_link, pdf_path, html_path)


# ----------------------------
# Entry Point
# ----------------------------
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
