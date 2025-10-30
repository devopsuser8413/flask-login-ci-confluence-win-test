import os
import sys
import time
import datetime
import smtplib
from email.message import EmailMessage
import requests
from requests.auth import HTTPBasicAuth

# ----------------------------
# Environment Variables
# ----------------------------
CONFLUENCE_BASE  = os.getenv('CONFLUENCE_BASE')
CONFLUENCE_USER  = os.getenv('CONFLUENCE_USER')
CONFLUENCE_TOKEN = os.getenv('CONFLUENCE_TOKEN')
CONFLUENCE_SPACE = os.getenv('CONFLUENCE_SPACE')
CONFLUENCE_TITLE = os.getenv('CONFLUENCE_TITLE')

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
headers = {"Content-Type": "application/json", "X-Atlassian-Token": "no-check"}


# ----------------------------
# Helpers
# ----------------------------
def read_version():
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE) as f:
            return int(f.read().strip())
    return 1


def extract_test_summary():
    """Extract pass/fail summary from pytest_output.txt with robust detection."""
    pytest_output = os.path.join(REPORT_DIR, "pytest_output.txt")
    if not os.path.exists(pytest_output):
        return "No test summary available.", "UNKNOWN"

    with open(pytest_output, encoding="utf-8", errors="ignore") as f:
        text = f.read()

    import re
    passed = failed = errors = skipped = 0

    # Match case-insensitive to handle "FAILED", "errors", etc.
    if m := re.search(r"(\d+)\s+passed", text, re.IGNORECASE): 
        passed = int(m.group(1))
    if m := re.search(r"(\d+)\s+failed", text, re.IGNORECASE): 
        failed = int(m.group(1))
    if m := re.search(r"(\d+)\s+errors?", text, re.IGNORECASE): 
        errors = int(m.group(1))
    if m := re.search(r"(\d+)\s+skipped", text, re.IGNORECASE): 
        skipped = int(m.group(1))

    # Fallback detection (handles short summary lines like "FAILED tests/test_app.py")
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
    res.raise_for_status()
    data = res.json()
    page_id = data["id"]
    print(f"🧾 Created new Confluence page '{title}' (ID: {page_id})")
    return page_id


def upload_attachment(page_id, file_path):
    """Upload a file (PDF/HTML) to Confluence page."""
    file_name = os.path.basename(file_path)
    mime_type = "application/pdf" if file_name.endswith(".pdf") else "text/html"
    url = f"{CONFLUENCE_BASE}/rest/api/content/{page_id}/child/attachment"

    for attempt in range(1, 4):
        try:
            with open(file_path, "rb") as f:
                files = {"file": (file_name, f, mime_type)}
                res = requests.post(url, files=files, auth=auth, headers={"X-Atlassian-Token": "no-check"})
            if res.status_code in (200, 201):
                data = res.json()
                attachment_id = data["results"][0]["id"]
                print(f"📎 Uploaded '{file_name}' (id: {attachment_id})")
                return file_name
            print(f"⚠️ Attempt {attempt} upload failed ({res.status_code})")
            time.sleep(2)
        except Exception as e:
            print(f"⚠️ Attempt {attempt} error: {e}")
            time.sleep(2)
    sys.exit(f"❌ Failed to upload attachment '{file_name}' after 3 attempts.")


def construct_download_link(page_id, file_name):
    return f"{CONFLUENCE_BASE}/download/attachments/{page_id}/{file_name}?api=v2"


# ----------------------------
# Enhanced Email Notification
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
    import re
    passed = failed = errors = skipped = 0
    match = re.findall(r"(\d+)\s+(passed|failed|error|skipped)", summary)
    for count, label in match:
        count = int(count)
        if "pass" in label: passed = count
        elif "fail" in label: failed = count
        elif "error" in label: errors = count
        elif "skip" in label: skipped = count

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
                <td><b>{round((passed/(passed+failed+errors+skipped)*100) if (passed+failed+errors+skipped) else 0,1)}%</b></td>
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
                msg.add_attachment(f.read(),
                                   maintype="application" if subtype == "pdf" else "text",
                                   subtype=subtype,
                                   filename=os.path.basename(path))

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
    version = read_version()
    pdf_path  = os.path.join(REPORT_DIR, f"{BASE_NAME}_v{version}.pdf")
    html_path = os.path.join(REPORT_DIR, f"{BASE_NAME}_v{version}.html")

    if not os.path.exists(pdf_path) or not os.path.exists(html_path):
        sys.exit("❌ Missing test report files.")

    summary, status = extract_test_summary()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    color = "green" if status == "PASS" else "red"
    emoji = "✅" if status == "PASS" else "❌"

    page_title = f"{CONFLUENCE_TITLE} v{version} ({status})"
    body = f"""
        <h2>{emoji} {CONFLUENCE_TITLE} (v{version})</h2>
        <p><b>Date:</b> {timestamp}</p>
        <p><b>Status:</b> <span style="color:{color}; font-weight:bold;">{status}</span></p>
        <p><b>Summary:</b> {summary}</p>
        <p>See attachments below for detailed results.</p>
    """

    page_id = create_confluence_page(page_title, body)

    print("📤 Uploading attachments...")
    pdf_name  = upload_attachment(page_id, pdf_path)
    html_name = upload_attachment(page_id, html_path)

    pdf_link  = construct_download_link(page_id, pdf_name)
    html_link = construct_download_link(page_id, html_name)

    updated_body = body + f"""
        <p><b>📎 Downloads:</b>
            <br>➡️ <a href="{html_link}" target="_blank">{html_name}</a>
            <br>➡️ <a href="{pdf_link}" target="_blank">{pdf_name}</a>
        </p>
    """
    update_url = f"{CONFLUENCE_BASE}/rest/api/content/{page_id}"
    update_payload = {
        "id": page_id,
        "type": "page",
        "title": page_title,
        "version": {"number": 2},
        "body": {"storage": {"value": updated_body, "representation": "storage"}}
    }
    requests.put(update_url, headers=headers, json=update_payload, auth=auth).raise_for_status()

    print(f"✅ Published v{version} ({status}) to Confluence.")
    print(f"🔗 PDF: {pdf_link}")
    print(f"🔗 HTML: {html_link}")

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
