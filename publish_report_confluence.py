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
    """Extract pass/fail summary from pytest_output.txt if present."""
    pytest_output = os.path.join(REPORT_DIR, "pytest_output.txt")
    if not os.path.exists(pytest_output):
        return "No test summary available.", "UNKNOWN"

    with open(pytest_output, encoding="utf-8", errors="ignore") as f:
        text = f.read()

    import re
    passed = failed = errors = skipped = 0
    if m := re.search(r"(\d+)\s+passed", text): passed = int(m.group(1))
    if m := re.search(r"(\d+)\s+failed", text): failed = int(m.group(1))
    if m := re.search(r"(\d+)\s+error",  text): errors = int(m.group(1))
    if m := re.search(r"(\d+)\s+skipped", text): skipped = int(m.group(1))
    total = passed + failed + errors + skipped
    rate = (passed / total * 100) if total else 0

    status = "PASS" if failed == 0 and errors == 0 else "FAIL"
    summary = f"✅ {passed} passed, ❌ {failed} failed, ⚠️ {errors} errors, ⏭ {skipped} skipped — Pass rate: {rate:.1f}%"
    return summary, status


def create_confluence_page(title, html_body):
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


def send_email_notification(version, summary, status, pdf_link, html_link, pdf_path, html_path):
    """Send summary email and attach both reports."""
    msg = EmailMessage()
    emoji = "✅" if status == "PASS" else "❌"
    msg["Subject"] = f"{emoji} Test Result {status} (v{version}) - Confluence Report"
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO

    msg.set_content(f"""
Test run completed with status: {status}
Summary: {summary}

View reports:
HTML: {html_link}
PDF : {pdf_link}
""")

    msg.add_alternative(f"""
    <html><body>
        <h2>{emoji} Test Result: <span style="color:{'green' if status=='PASS' else 'red'}">{status}</span> (v{version})</h2>
        <p><b>Summary:</b> {summary}</p>
        <ul>
          <li><a href="{html_link}" target="_blank">View HTML Report</a></li>
          <li><a href="{pdf_link}" target="_blank">Download PDF Report</a></li>
        </ul>
        <p>This is an automated Jenkins notification.</p>
    </body></html>
    """, subtype="html")

    # Attach reports
    try:
        with open(pdf_path, "rb") as f:
            msg.add_attachment(f.read(), maintype="application", subtype="pdf",
                               filename=os.path.basename(pdf_path))
        with open(html_path, "rb") as f:
            msg.add_attachment(f.read(), maintype="text", subtype="html",
                               filename=os.path.basename(html_path))
    except Exception as e:
        print(f"⚠️ Could not attach files: {e}")

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

    page_title = f"{CONFLUENCE_TITLE} v{version} ({status})"
    body = f"""
        <h2>🚀 {CONFLUENCE_TITLE} (v{version})</h2>
        <p><b>Date:</b> {timestamp}</p>
        <p><b>Status:</b> {status}</p>
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
