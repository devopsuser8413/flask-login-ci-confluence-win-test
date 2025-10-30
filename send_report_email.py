import os, smtplib
from email.message import EmailMessage

SMTP_HOST = os.getenv('SMTP_HOST')
SMTP_PORT = int(os.getenv('SMTP_PORT'))
SMTP_USER = os.getenv('SMTP_USER')
SMTP_PASS = os.getenv('SMTP_PASS')
TO_EMAIL  = os.getenv('REPORT_TO')
FROM_EMAIL= os.getenv('REPORT_FROM')

REPORT_DIR = 'report'
BASE_NAME = 'test_result_report'
VERSION_FILE = os.path.join(REPORT_DIR, 'version.txt')

def read_version():
    with open(VERSION_FILE) as f:
        return int(f.read().strip())

def send_email():
    v = read_version()
    pdf_path = os.path.join(REPORT_DIR, f"{BASE_NAME}_v{v}.pdf")
    with open(pdf_path,'rb') as f: data = f.read()

    msg = EmailMessage()
    msg['Subject'] = f"📊 Test Result Report (v{v})"
    msg['From'] = FROM_EMAIL
    msg['To'] = TO_EMAIL
    msg.set_content(f"Attached is the Test Result Report (v{v}) in PDF format.")
    msg.add_attachment(data, maintype='application', subtype='pdf', filename=os.path.basename(pdf_path))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        if SMTP_PORT == 587: s.starttls()
        s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)
    print(f"✅ Email sent successfully with {pdf_path}")

if __name__ == "__main__":
    send_email()
