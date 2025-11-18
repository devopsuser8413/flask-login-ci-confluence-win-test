import os
import smtplib
from email.message import EmailMessage
import re

SMTP_HOST = os.getenv('SMTP_HOST')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USER = os.getenv('SMTP_USER')
SMTP_PASS = os.getenv('SMTP_PASS')

TO_RAW  = os.getenv('REPORT_TO', '')
CC_RAW  = os.getenv('REPORT_CC', '')
BCC_RAW = os.getenv('REPORT_BCC', '')
FROM_EMAIL = os.getenv('REPORT_FROM')

CONFLUENCE_PAGE_URL_ENV = os.getenv("CONFLUENCE_PAGE_URL", "")
CONF_LINK_FILE = "report/confluence_url.txt"

REPORT_DIR   = 'report'
VERSION_FILE = os.path.join(REPORT_DIR, 'version.txt')
BASE_NAME    = 'test_result_report'
PYTEST_LOG   = os.path.join(REPORT_DIR, 'pytest_output.txt')


def parse_recipients(raw):
    if not raw:
        return []
    parts = re.split(r'[;,]', raw)
    return [p.strip() for p in parts if p.strip()]


def read_confluence_url():
    if CONFLUENCE_PAGE_URL_ENV:
        return CONFLUENCE_PAGE_URL_ENV
    if os.path.exists(CONF_LINK_FILE):
        with open(CONF_LINK_FILE, "r") as f:
            return f.read().strip()
    return ""


def read_version():
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE) as f:
            try:
                return int(f.read().strip())
            except ValueError:
                return 1
    return 1


def extract_test_status():
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
    rate = (passed / total * 100) if total else 0.0

    status = "PASS" if failed == 0 and errors == 0 else "FAIL"
    emoji = "✅" if status == "PASS" else "❌"

    summary = (
        f"{emoji} {passed} passed, ❌ {failed} failed, "
        f"⚠️ {errors} errors, ⏭ {skipped} skipped — Pass rate: {rate:.1f}%"
    )
    return status, summary


def send_single_email(recipient, cc_list, bcc_list, pdf_report_path, version, status, summary, confluence_url):
    emoji = "✅" if status == "PASS" else "❌"
    color = "green" if status == "PASS" else "red"

    msg = EmailMessage()
    msg["Subject"] = f"{emoji} Test Result {status} (v{version})"
    msg["From"] = FROM_EMAIL
    msg["To"] = recipient

    if cc_list:
        msg["Cc"] = ", ".join(cc_list)

    all_recipients = [recipient] + cc_list + bcc_list

    msg.set_content(f"""
Test Status: {status}
Summary: {summary}

Confluence Report:
{confluence_url or 'N/A'}

The PDF test report (v{version}) is attached.

Regards,
QA Automation System
""")

    msg.add_alternative(f"""
    <html>
        <body style="font-family:Arial,sans-serif;">
            <h2>{emoji} Test Result:
                <span style="color:{color}">{status}</span> (v{version})
            </h2>
            <p><b>Summary:</b> {summary}</p>
            <h3>📄 Confluence Report</h3>
            <p>
                {'<a href="' + confluence_url + '" target="_blank">View the full report in Confluence</a>' if confluence_url else 'No Confluence URL available.'}
            </p>
            <p>The PDF report is attached.</p>
            <p>Regards,<br><b>QA Automation System</b></p>
        </body>
    </html>
    """, subtype="html")

    with open(pdf_report_path, "rb") as f:
        msg.add_attachment(
            f.read(),
            maintype="application",
            subtype="pdf",
            filename=os.path.basename(pdf_report_path),
        )

    print(f"📤 Sending email to {recipient} (CC={cc_list}, BCC hidden)...")

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.ehlo()
        if SMTP_PORT == 587:
            s.starttls()
        if SMTP_USER and SMTP_PASS:
            s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg, to_addrs=all_recipients)

    print(f"✅ Email sent to: {recipient}")


def main():
    version = read_version()
    pdf_report_path = os.path.join(REPORT_DIR, f"{BASE_NAME}_v{version}.pdf")

    if not os.path.exists(pdf_report_path):
        raise SystemExit(f"❌ PDF report not found: {pdf_report_path}")

    status, summary = extract_test_status()
    confluence_url = read_confluence_url()

    to_list  = parse_recipients(TO_RAW)
    cc_list  = parse_recipients(CC_RAW)
    bcc_list = parse_recipients(BCC_RAW)

    if not to_list:
        raise SystemExit("❌ REPORT_TO has no valid recipients.")

    print("📧 Email Distribution:")
    print(" TO :", to_list)
    print(" CC :", cc_list)
    print(" BCC:", "[hidden]" if bcc_list else "None")
    print(" 🔗 Confluence:", confluence_url or "N/A")

    for r in to_list:
        send_single_email(r, cc_list, bcc_list, pdf_report_path, version, status, summary, confluence_url)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Email failed: {e}")
        raise
