import os
import sys
import requests
from requests.auth import HTTPBasicAuth

# ----------------------------
# Environment Variables
# ----------------------------
CONFLUENCE_BASE = os.getenv('CONFLUENCE_BASE')
CONFLUENCE_USER = os.getenv('CONFLUENCE_USER')
CONFLUENCE_TOKEN = os.getenv('CONFLUENCE_TOKEN')
CONFLUENCE_SPACE = os.getenv('CONFLUENCE_SPACE')
CONFLUENCE_TITLE = os.getenv('CONFLUENCE_TITLE')

REPORT_DIR = 'report'
VERSION_FILE = os.path.join(REPORT_DIR, 'version.txt')
BASE_NAME = 'test_result_report'

auth = HTTPBasicAuth(CONFLUENCE_USER, CONFLUENCE_TOKEN)
headers = {"Content-Type": "application/json"}

# ----------------------------
# Helpers
# ----------------------------
def read_version():
    """Read current version number."""
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE) as f:
            return int(f.read().strip())
    return 1


def get_page(title, space):
    """Get Confluence page details if it exists."""
    url = f"{CONFLUENCE_BASE}/rest/api/content"
    params = {"title": title, "spaceKey": space, "expand": "version"}
    r = requests.get(url, headers=headers, params=params, auth=auth)
    r.raise_for_status()
    results = r.json().get('results', [])
    return results[0] if results else None


def update_page(page_id, title, version, content):
    """Update Confluence page content."""
    url = f"{CONFLUENCE_BASE}/rest/api/content/{page_id}"
    payload = {
        "id": page_id,
        "type": "page",
        "title": title,
        "version": {"number": version + 1},
        "body": {"storage": {"value": content, "representation": "storage"}}
    }
    r = requests.put(url, headers=headers, json=payload, auth=auth)
    r.raise_for_status()
    print(f"✅ Page '{title}' updated successfully (version {version + 1}).")


def upload_attachment(page_id, file_path):
    """Upload a report (HTML or PDF) as a unique attachment."""
    file_name = os.path.basename(file_path)
    upload_url = f"{CONFLUENCE_BASE}/rest/api/content/{page_id}/child/attachment"

    with open(file_path, 'rb') as f:
        mime_type = 'application/pdf' if file_name.endswith('.pdf') else 'text/html'
        files = {'file': (file_name, f, mime_type)}
        headers_no_json = {"X-Atlassian-Token": "no-check"}
        res = requests.post(upload_url, headers=headers_no_json, files=files, auth=auth)

    if res.status_code not in (200, 201):
        print(f"❌ Attachment upload failed: {res.status_code} - {res.text}")
        sys.exit(1)

    data = res.json()
    attachment_id = data['results'][0]['id']
    print(f"📎 Uploaded '{file_name}' (attachment id: {attachment_id})")
    return file_name


def construct_download_link(page_id, file_name):
    """Generate Confluence download link for the attachment."""
    return f"{CONFLUENCE_BASE}/download/attachments/{page_id}/{file_name}?api=v2"


# ----------------------------
# Main Logic
# ----------------------------
def main():
    version = read_version()

    html_path = os.path.join(REPORT_DIR, f"{BASE_NAME}_v{version}.html")
    pdf_path = os.path.join(REPORT_DIR, f"{BASE_NAME}_v{version}.pdf")

    if not os.path.exists(html_path):
        print(f"❌ Report HTML file not found: {html_path}")
        sys.exit(1)
    if not os.path.exists(pdf_path):
        print(f"❌ Report PDF file not found: {pdf_path}")
        sys.exit(1)

    # Read HTML for embedding
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # Check Confluence page
    page = get_page(CONFLUENCE_TITLE, CONFLUENCE_SPACE)
    if not page:
        print(f"❌ Page '{CONFLUENCE_TITLE}' not found in space '{CONFLUENCE_SPACE}'. Please create it first.")
        sys.exit(1)

    page_id = page['id']
    page_version = page['version']['number']

    # Upload attachments
    html_file_name = upload_attachment(page_id, html_path)
    pdf_file_name = upload_attachment(page_id, pdf_path)

    # Generate download links
    html_link = construct_download_link(page_id, html_file_name)
    pdf_link = construct_download_link(page_id, pdf_file_name)

    # Create a summary block with links
    summary_block = f"""
    <h2>🚀 Test Result Report (v{version})</h2>
    <p>
      📄 <b>Download Reports:</b><br>
      • <a href="{html_link}" target="_blank">HTML Report v{version}</a><br>
      • <a href="{pdf_link}" target="_blank">PDF Report v{version}</a>
    </p>
    <hr>
    """

    # Preserve old content and append new summary at the top
    old_content_url = f"{CONFLUENCE_BASE}/rest/api/content/{page_id}?expand=body.storage"
    old_page = requests.get(old_content_url, headers=headers, auth=auth).json()
    old_body = old_page.get("body", {}).get("storage", {}).get("value", "")

    new_body = summary_block + old_body

    # Update page with new content
    update_page(page_id, CONFLUENCE_TITLE, page_version, new_body)

    print(f"✅ Report v{version} published successfully with attachments:")
    print(f"   → HTML: {html_link}")
    print(f"   → PDF : {pdf_link}")


# ----------------------------
# Entry Point
# ----------------------------
if __name__ == '__main__':
    try:
        main()
    except requests.exceptions.RequestException as e:
        print(f"❌ HTTP error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)
