import os
import re
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
REPORT_PATH = os.environ.get('REPORT_PATH')
REPORT_DIR = os.path.dirname(REPORT_PATH)
REPORT_BASENAME = 'test_result_report'

# Optional: Jenkins workspace URL (for download link)
WORKSPACE_URL = os.environ.get('WORKSPACE_URL', '')  # e.g. "http://jenkins-server/job/Test-Pipeline/ws/report"

# ----------------------------
# Incremental report naming
# ----------------------------
def get_next_report_filename(report_dir, base_name):
    """Find next incremental filename like test_result_report_v1.html."""
    os.makedirs(report_dir, exist_ok=True)
    pattern = re.compile(rf"{re.escape(base_name)}_v(\d+)\.html$")
    existing_files = [f for f in os.listdir(report_dir) if pattern.match(f)]
    
    next_version = max([int(pattern.match(f).group(1)) for f in existing_files], default=0) + 1
    return os.path.join(report_dir, f"{base_name}_v{next_version}.html"), next_version

# ----------------------------
# Email sender
# ----------------------------
def send_email():
    # Determine next incremental report file name
    new_report_path, version_number = get_next_report_filename(REPORT_DIR, REPORT_BASENAME)

    # Check that the base report exists
    base_report_path = os.environ.get('REPORT_PATH', 'report/report.html')
    if not os.path.exists(base_report_path):
        raise SystemExit(f"❌ Report not found: {base_report_path}")

    # Copy the base report into the new incremental file
    with open(base_report_path, 'rb') as src, open(new_report_path, 'wb') as dest:
        report_bytes = src.read()
        dest.write(report_bytes)

    print(f"📄 New incremental report generated: {new_report_path}")

    # ----------------------------
    # Prepare Email
    # ----------------------------
    msg = EmailMessage()
    msg['Subject'] = f"CI Test Report (v{version_number})"
    msg['From'] = FROM_EMAIL
    msg['To'] = TO_EMAIL

    # Build HTML body
    file_name = os.path.basename(new_report_path)
    download_link = ""

    # Optional link if Jenkins WORKSPACE_URL is provided
    if WORKSPACE_URL:
        encoded_file = quote(file_name)
        download_link = f"<p><b>Download full HTML report:</b> <a href='{WORKSPACE_URL}/{encoded_file}'>Click here (v{version_number})</a></p><hr>"

    html_body = f"""
    <html>
    <body>
        <h2>CI Test Report (v{version_number})</h2>
        {download_link}
        <p>The detailed HTML test report is attached and also viewable inline below.</p>
        <hr>
        {report_bytes.decode('utf-8')}
    </body>
    </html>
    """

    # Add text and HTML alternatives
    msg.set_content(f"Please find attached CI test report (v{version_number}).")
    msg.add_alternative(html_body, subtype='html')

    # Attach report file
    msg.add_attachment(report_bytes, maintype='text', subtype='html', filename=file_name)

    # ----------------------------
    # Send Email
    # ----------------------------
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.ehlo()
        if SMTP_PORT == 587:
            s.starttls()
        if SMTP_USER and SMTP_PASS:
            try:
                s.login(SMTP_USER, SMTP_PASS)
            except smtplib.SMTPNotSupportedError:
                print("⚠️ SMTP AUTH not supported by this server — continuing without login.")
        s.send_message(msg)

    print(f"✅ Email sent successfully with downloadable report: {file_name}")

# ----------------------------
# Entry Point
# ----------------------------
if __name__ == '__main__':
    send_email()
