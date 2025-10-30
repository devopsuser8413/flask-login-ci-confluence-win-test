import os
import smtplib
from email.message import EmailMessage

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


# ----------------------------
# Helpers
# ----------------------------
def read_version():
    """Read the latest report version number."""
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE) as f:
            return int(f.read().strip())
    return 1


# ----------------------------
# Main Logic
# ----------------------------
def send_email():
    version = read_version()
    pdf_report_path = os.path.join(REPORT_DIR, f"{BASE_NAME}_v{version}.pdf")

    if not os.path.exists(pdf_report_path):
        raise SystemExit(f"❌ PDF report not found: {pdf_report_path}")

    # Read the PDF file as bytes
    with open(pdf_report_path, 'rb') as f:
        pdf_bytes = f.read()

    # Create email message
    msg = EmailMessage()
    msg['Subject'] = f"📊 Test Result Report (v{version})"
    msg['From'] = FROM_EMAIL
    msg['To'] = TO_EMAIL

    msg.set_content(
        f"""Hi,

Please find attached the latest Test Result Report (v{version}) in PDF format.

Regards,
Automated QA System
"""
    )

    msg.add_alternative(f"""
        <html>
            <body>
                <h2>✅ Test Result Report (v{version})</h2>
                <p>The latest test result report is attached below in PDF format.</p>
                <p>Regards,<br><b>Automated QA System</b></p>
            </body>
        </html>
    """, subtype='html')

    # Attach PDF file
    msg.add_attachment(
        pdf_bytes,
        maintype='application',
        subtype='pdf',
        filename=f"{BASE_NAME}_v{version}.pdf"
    )

    # Send the email
    print(f"📤 Sending email to {TO_EMAIL} via {SMTP_HOST}:{SMTP_PORT} ...")

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.ehlo()
        if SMTP_PORT == 587:
            s.starttls()
        if SMTP_USER and SMTP_PASS:
            s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)

    print(f"✅ Email sent successfully with PDF report v{version} attached.")


# ----------------------------
# Entry Point
# ----------------------------
if __name__ == '__main__':
    try:
        send_email()
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        raise
