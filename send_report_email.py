import os
import smtplib
from email.message import EmailMessage
import re

# ----------------------------
# Environment Variables
# ----------------------------
SMTP_HOST = os.getenv('SMTP_HOST')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USER = os.getenv('SMTP_USER')
SMTP_PASS = os.getenv('SMTP_PASS')
TO_EMAIL = os.getenv('REPORT_TO')
FROM_EMAIL = os.getenv('REPORT_FROM')

REPORT_DIR = 'report'
VERSION_FILE = os.path.join(REPORT_DIR, 'version.txt')
BASE_NAME = 'test_result_report'
PYTEST_LOG = os.path.join(REPORT_DIR, 'pytest_output.txt')

# ----------------------------
# Helpers
# ----------------------------
def read_version():
    """Read latest report version number."""
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE) as f:
            return int(f.read().strip())
    return 1


def extract_test_status():
    """Detect PASS / FAIL from pytest_output.txt."""
    if not os.path.exists(PYTEST_LOG):
        return "UNKNOWN", "⚪ No pytest_output.txt found."

    with open(PYTEST_LOG, encoding="utf-8", errors="ignore") as f:
        text = f.read()

    passed = failed = errors = skipped = 0
    if m := re.search(r"(\d+)\s+passed", text, re.IGNORECASE): passed = int(m.group(1))
    if m := re.search(r"(\d+)\s+failed", text, re.IGNORECASE): failed = int(m.group(1))
    if m := re.search(r"(\d+)\s+errors?", text, re.IGNORECASE): errors = int(m.group(1))
    if m := re.search(r"(\d+)\s+skipped", text, re.IGNORECASE): skipped = int(m.group(1))
    total = passed + failed + errors + skipped
    rate = (passed / total * 100) if total else 0

    status = "PASS" if failed == 0 and errors == 0 else "FAIL"
    emoji = "✅" if status == "PASS" else "❌"
    summary = f"{emoji} {passed} passed, ❌ {failed} failed, ⚠️ {errors} errors, ⏭ {skipped} skipped — Pass rate: {rate:.1f}%"
    return status, summary


# ----------------------------
# Main Logic
# ----------------------------
def send_email():
    version = read_version()
    pdf_report_path = os.path.join(REPORT_DIR, f"{BASE_NAME}_v{version}.pdf")

    if not os.path.exists(pdf_report_path):
        raise SystemExit(f"❌ PDF report not found: {pdf_report_path}")

    status, summary = extract_test_status()
    emoji = "✅" if status == "PASS" else "❌"

    # Email setup
    msg = EmailMessage()
    msg['Subject'] = f"{emoji} Test Result {status} (v{version})"
    msg['From'] = FROM_EMAIL
    msg['To'] = TO_EMAIL

    # Plain text
    msg.set_content(f"""
Test execution status: {status}
Summary: {summary}

Please find attached the detailed PDF test report (v{version}).

Regards,
Automated QA System
""")

    # HTML version
    msg.add_alternative(f"""
    <html>
        <body>
            <h2>{emoji} Test Result: <span style="color:{'green' if status=='PASS' else 'red'}">{status}</span> (v{version})</h2>
            <p><b>Summary:</b> {summary}</p>
            <p>The full PDF report is attached below.</p>
            <p>Regards,<br><b>Automated QA System</b></p>
        </body>
    </html>
    """, subtype='html')

    # Attach report
    with open(pdf_report_path, 'rb') as f:
        msg.add_attachment(f.read(), maintype='application', subtype='pdf',
                           filename=os.path.basename(pdf_report_path))

    # Send
    print(f"📤 Sending email to {TO_EMAIL} via {SMTP_HOST}:{SMTP_PORT} ...")
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.ehlo()
        if SMTP_PORT == 587:
            s.starttls()
        if SMTP_USER and SMTP_PASS:
            s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)

    print(f"{emoji} Email sent successfully ({status}) with report v{version} attached.")


# ----------------------------
# Entry Point
# ----------------------------
if __name__ == '__main__':
    try:
        send_email()
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        raise
