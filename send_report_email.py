import os, smtplib
from email.message import EmailMessage

SMTP_HOST = os.environ.get('SMTP_HOST')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
SMTP_USER = os.environ.get('SMTP_USER')
SMTP_PASS = os.environ.get('SMTP_PASS')
TO_EMAIL = os.environ.get('REPORT_TO', 'recipient@example.com')
FROM_EMAIL = os.environ.get('REPORT_FROM', SMTP_USER or 'ci@example.com')
REPORT_PATH = os.environ.get('REPORT_PATH', 'report/report.html')

def send_email():
    if not os.path.exists(REPORT_PATH):
        raise SystemExit(f'Report not found: {REPORT_PATH}')
    with open(REPORT_PATH, 'rb') as f:
        report_bytes = f.read()
    msg = EmailMessage()
    msg['Subject'] = 'CI Test Report'
    msg['From'] = FROM_EMAIL
    msg['To'] = TO_EMAIL
    msg.set_content('Please find the attached HTML test report.')
    msg.add_alternative(report_bytes.decode('utf-8'), subtype='html')
    msg.add_attachment(report_bytes, maintype='text', subtype='html', filename='report.html')
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.starttls()
        if SMTP_USER and SMTP_PASS:
            s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)
        print('Email sent')

if __name__ == '__main__':
    send_email()
