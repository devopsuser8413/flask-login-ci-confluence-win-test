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
    """Upload HTML report as attachment under unique name."""
    file_name = os.path.basename(file_path)
    upload_url = f"{CONFLUENCE_BASE}/rest/api/content/{page_id}/child/attachment"

    with open(file_path, 'rb') as f:
        files = {'file': (file_name, f, 'text/html')}
        headers_no_json = {"X-Atlassian-Token": "no-check"}
        res = requests.post(upload_url, headers=headers_no_json, files=files, auth=auth)

    if res.status_code not in (200, 201):
        print(f"❌ Attachment upload failed: {res.status_code} - {res.text}")
        sys.exit(1)

    data = res.json()
    attachment_id = data['results'][0]['id']
    print(f"📎 Uploaded attachment '{file_name}' (id: {attachment_id})")
    return file_name

# ----------------------------
# Main Logic
# ----------------------------
def main():
    version = read_version()
    report_path = os.path.join(REPORT_DIR, f"{BASE_NAME}_v{version}.html")

    if not os.path.exists(report_path):
        print(f"❌ Report file not found: {report_path}")
        sys.exit(1)

    with open(report_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # Check or create page
    page = get_page(CONFLUENCE_TITLE, CONFLUENCE_SPACE)
    if not page:
        print(f"❌ Page '{CONFLUENCE_TITLE}' not found in space '{CONFLUENCE_SPACE}'. Please create it first.")
        sys.exit(1)

    page_id = page['id']
    page_version = page['version']['number']

    # Upload attachment first
    file_name = upload_attachment(page_id, report_path)

    # Construct valid Confluence download URL
    download_link = (
        f"{CONFLUENCE_BASE}/download/attachments/{page_id}/{file_name}?api=v2"
    )

    # Create new HTML body
    content = f"""
    <h2>🚀 Test Result Report (v{version})</h2>
    <p><b>Download Full Report:</b> 
        <a href="{download_link}" target="_blank">Click here to download (v{version})</a>
    </p>
    <hr>
    {html_content}
    """

    # Update page
    update_page(page_id, CONFLUENCE_TITLE, page_version, content)
    print(f"✅ Report v{version} published successfully with attachment link: {download_link}")

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
