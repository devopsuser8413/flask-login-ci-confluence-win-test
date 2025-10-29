import os
import smtplib
from email.message import EmailMessage
from urllib.parse import quote

# ----------------------------
# Load environment variables
# ----------------------------
SMTP_HOST = os.environ.get('SMTP_HOST')
SMTP_PORT = int(os.environ.get('SMTP_PORT'))
SMTP_USER = os.environ.get('SMTP_USER')
SMTP_PASS = os.environ.get('SMTP_PASS')
TO_EMAIL = os.environ.get('REPORT_TO')
FROM_EMAIL = os.environ.get('REPORT_FROM')
REPORT_PATH = os.environ.get('REPORT_PATH', 'report/report.html')
REPORT_DIR = os.path.dirname(REPORT_PATH)
REPORT_BASENAME = 'test_result_report'
WORKSPACE_URL = os.environ.get('WORKSPACE_URL', '')  # Optional Jenkins workspace URL
VERSION_FILE = os.path.join(REPORT_DIR, "version.txt")

# ----------------------------
# Version tracker
# ----------------------------
def get_next_version():
    """Read, increment, and persist shared report version."""
    os.makedirs(REPORT_DIR, exist_ok=True)
    version = 1
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE, "r") as f:
            content = f.read().strip()
            if content.isdigit():
                version = int(content) + 1
    with open(VERSION_FILE, "w") as f:
        f.write(str(version))
    return version

# ----------------------------
# Email sender
# ----------------------------
def send_email():
    version_number = get_next_version()
    new_report_path = os.path.join(REPORT_DIR, f"{REPORT_BASENAME}_v{version_number}.html")

    if not os.path.exists(REPORT_PATH):
        raise SystemExit(f"❌ Report not found: {REPORT_PATH}")

    # Copy report to incremental version
    with open(REPORT_PATH, 'rb') as src, open(new_report_path, 'wb') as dest:
        report_bytes = src.read()
        dest.write(report_bytes)

    print(f"📄 Created new report: {new_report_path} (v{version_number})")

    # Email setup
    msg = EmailMessage()
    msg['Subject'] = f"CI Test Report (v{version_number})"
    msg['From'] = FROM_EMAIL
    msg['To'] = TO_EMAIL

    file_name = os.path.basename(new_report_path)
    download_link = ""
    if WORKSPACE_URL:
        encoded = quote(file_name)
        download_link = f"<p><b>Download full HTML report:</b> <a href='{WORKSPACE_URL}/{encoded}'>Click here (v{version_number})</a></p><hr>"

    html_body = f"""
    <html>
    <body>
        <h2>CI Test Report (v{version_number})</h2>
        {download_link}
        <p>The detailed HTML test report is attached and viewable inline below.</p>
        <hr>
        {report_bytes.decode('utf-8')}
    </body>
    </html>
    """

    msg.set_content(f"Please find attached CI Test Report (v{version_number}).")
    msg.add_alternative(html_body, subtype='html')
    msg.add_attachment(report_bytes, maintype='text', subtype='html', filename=file_name)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.ehlo()
        if SMTP_PORT == 587:
            s.starttls()
        if SMTP_USER and SMTP_PASS:
            try:
                s.login(SMTP_USER, SMTP_PASS)
            except smtplib.SMTPNotSupportedError:
                print("⚠️ SMTP AUTH not supported — continuing without login.")
        s.send_message(msg)

    print(f"✅ Email sent successfully with report version v{version_number}")

if __name__ == '__main__':
    send_email()
