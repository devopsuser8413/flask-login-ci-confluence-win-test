import os
import re
import sys
import requests
from requests.auth import HTTPBasicAuth

# ----------------------------
# Load environment variables
# ----------------------------
CONFLUENCE_BASE = os.getenv('CONFLUENCE_BASE')
CONFLUENCE_USER = os.getenv('CONFLUENCE_USER')
CONFLUENCE_TOKEN = os.getenv('CONFLUENCE_TOKEN')
CONFLUENCE_SPACE = os.getenv('CONFLUENCE_SPACE')
CONFLUENCE_TITLE = os.getenv('CONFLUENCE_TITLE')
REPORT_PATH = os.getenv('REPORT_PATH', 'report/report.html')
CREATE_NEW_PAGE_PER_VERSION = os.getenv('CREATE_NEW_PAGE_PER_VERSION', 'false').lower() == 'true'

auth = HTTPBasicAuth(CONFLUENCE_USER, CONFLUENCE_TOKEN)
headers = {"Content-Type": "application/json"}
VERSION_FILE = os.path.join(os.path.dirname(REPORT_PATH), "version.txt")

# ----------------------------
# Version reader
# ----------------------------
def read_current_version():
    """Read current version number from shared version.txt"""
    if not os.path.exists(VERSION_FILE):
        print("⚠️ version.txt not found — defaulting to v1")
        return 1
    with open(VERSION_FILE, "r") as f:
        content = f.read().strip()
        return int(content) if content.isdigit() else 1

# ----------------------------
# Confluence helper functions
# ----------------------------
def get_page(title, space):
    url = f"{CONFLUENCE_BASE}/rest/api/content"
    params = {"title": title, "spaceKey": space, "expand": "version"}
    r = requests.get(url, headers=headers, params=params, auth=auth)
    r.raise_for_status()
    results = r.json().get('results', [])
    return results[0] if results else None

def create_page(title, space, content):
    url = f"{CONFLUENCE_BASE}/rest/api/content"
    payload = {
        "type": "page",
        "title": title,
        "space": {"key": space},
        "body": {"storage": {"value": content, "representation": "storage"}}
    }
    r = requests.post(url, headers=headers, json=payload, auth=auth)
    r.raise_for_status()
    print(f"✅ Page '{title}' created successfully.")
    return r.json()

def update_page(page_id, title, version, content):
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
    print(f"✅ Page '{title}' updated successfully.")
    return r.json()

def upload_attachment(page_id, file_path):
    url = f"{CONFLUENCE_BASE}/rest/api/content/{page_id}/child/attachment"
    file_name = os.path.basename(file_path)
    with open(file_path, 'rb') as f:
        files = {'file': (file_name, f, 'text/html')}
        headers_no_json = {"X-Atlassian-Token": "no-check"}
        r = requests.post(url, headers=headers_no_json, files=files, auth=auth)
        r.raise_for_status()
    print(f"📎 Uploaded attachment: {file_name}")
    return file_name

# ----------------------------
# Main logic
# ----------------------------
def main():
    version_number = read_current_version()
    report_dir = os.path.dirname(REPORT_PATH)
    report_file = f"test_result_report_v{version_number}.html"
    report_path = os.path.join(report_dir, report_file)

    if not os.path.exists(report_path):
        print(f"❌ Report file not found: {report_path}")
        sys.exit(1)

    with open(report_path, "r", encoding="utf-8") as f:
        report_content = f.read()

    page_title = f"{CONFLUENCE_TITLE} v{version_number}" if CREATE_NEW_PAGE_PER_VERSION else CONFLUENCE_TITLE
    page = get_page(page_title, CONFLUENCE_SPACE)

    if page:
        page_id = page["id"]
        updated_page = update_page(page_id, page_title, page["version"]["number"], report_content)
    else:
        created_page = create_page(page_title, CONFLUENCE_SPACE, report_content)
        page_id = created_page["id"]

    upload_attachment(page_id, report_path)

    download_url = f"{CONFLUENCE_BASE}/download/attachments/{page_id}/{os.path.basename(report_path)}"
    download_html = f"""
    <p><b>Download HTML report (v{version_number}):</b>
    <a href="{download_url}" target="_blank">Click here</a></p><hr>
    """

    combined_html = download_html + report_content
    update_page(page_id, page_title, get_page(page_title, CONFLUENCE_SPACE)["version"]["number"], combined_html)

    print(f"✅ Report v{version_number} published successfully to page '{page_title}'.")
    print(f"🔗 Download URL: {download_url}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
