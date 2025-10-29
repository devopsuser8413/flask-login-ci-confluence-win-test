import os
import sys
import requests
from requests.auth import HTTPBasicAuth

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

def read_version():
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE) as f:
            return int(f.read().strip())
    return 1

def upload_attachment(page_id, file_path):
    url = f"{CONFLUENCE_BASE}/rest/api/content/{page_id}/child/attachment"
    file_name = os.path.basename(file_path)
    with open(file_path, 'rb') as f:
        files = {'file': (file_name, f, 'text/html')}
        headers_no_json = {"X-Atlassian-Token": "no-check"}
        res = requests.post(url, headers=headers_no_json, files=files, auth=auth)
        res.raise_for_status()
    print(f"📎 Uploaded attachment: {file_name}")
    return file_name

def get_page(title, space):
    url = f"{CONFLUENCE_BASE}/rest/api/content"
    params = {"title": title, "spaceKey": space, "expand": "version"}
    r = requests.get(url, headers=headers, params=params, auth=auth)
    r.raise_for_status()
    results = r.json().get('results', [])
    return results[0] if results else None

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

def main():
    version = read_version()
    report_path = os.path.join(REPORT_DIR, f"{BASE_NAME}_v{version}.html")
    if not os.path.exists(report_path):
        print(f"❌ Report file not found: {report_path}")
        sys.exit(1)

    with open(report_path, 'r', encoding='utf-8') as f:
        html = f.read()

    download_html = f"<p><b>Download Report v{version}:</b> Attached below.</p><hr>"
    content = download_html + html

    page = get_page(CONFLUENCE_TITLE, CONFLUENCE_SPACE)
    if page:
        update_page(page['id'], CONFLUENCE_TITLE, page['version']['number'], content)
        upload_attachment(page['id'], report_path)
    else:
        print("❌ Page not found. Please create it manually once.")

    print(f"✅ Report v{version} published to Confluence")

if __name__ == '__main__':
    main()
