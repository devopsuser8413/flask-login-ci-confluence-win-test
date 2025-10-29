import os
import smtplib
from email.message import EmailMessage

SMTP_HOST = os.getenv('SMTP_HOST')
SMTP_PORT = int(os.getenv('SMTP_PORT'))
SMTP_USER = os.getenv('SMTP_USER')
SMTP_PASS = os.getenv('SMTP_PASS')
TO_EMAIL = os.getenv('REPORT_TO')
FROM_EMAIL = os.getenv('REPORT_FROM')
REPORT_DIR = 'report'
VERSION_FILE = os.path.join(REPORT_DIR, 'version.txt')
BASE_NAME = 'test_result_report'

def read_version():
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE) as f:
            return int(f.read().strip())
    return 1

def send_email():
    version = read_version()
    report_path = os.path.join(REPORT_DIR, f"{BASE_NAME}_v{version}.html")

    if not os.path.exists(report_path):
        raise SystemExit(f"❌ Report not found: {report_path}")

    with open(report_path, 'rb') as f:
        report_bytes = f.read()

    msg = EmailMessage()
    msg['Subject'] = f"Test Result Report (v{version})"
    msg['From'] = FROM_EMAIL
    msg['To'] = TO_EMAIL

    msg.set_content(f"Please find attached Test Result Report (v{version}).")
    msg.add_alternative(f"""
        <html><body>
        <h2>✅ Test Result Report (v{version})</h2>
        <p>See the attached enhanced HTML report.</p>
        <hr>
        {report_bytes.decode('utf-8')}
        </body></html>
    """, subtype='html')

    msg.add_attachment(report_bytes, maintype='text', subtype='html', filename=f"{BASE_NAME}_v{version}.html")

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.ehlo()
        if SMTP_PORT == 587:
            s.starttls()
        if SMTP_USER and SMTP_PASS:
            s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)

    print(f"✅ Email sent successfully with version v{version}")

if __name__ == '__main__':
    send_email()
