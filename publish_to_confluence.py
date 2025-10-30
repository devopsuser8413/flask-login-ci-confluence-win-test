import os, sys, requests
from requests.auth import HTTPBasicAuth

BASE = os.getenv('CONFLUENCE_BASE')
USER = os.getenv('CONFLUENCE_USER')
TOKEN = os.getenv('CONFLUENCE_TOKEN')
SPACE = os.getenv('CONFLUENCE_SPACE')
TITLE = os.getenv('CONFLUENCE_TITLE')
REPORT_DIR = 'report'
BASE_NAME = 'test_result_report'
VERSION_FILE = os.path.join(REPORT_DIR, 'version.txt')

auth = HTTPBasicAuth(USER, TOKEN)

def read_version():
    with open(VERSION_FILE) as f:
        return int(f.read().strip())

def get_page():
    url = f"{BASE}/rest/api/content"
    params = {"title": TITLE, "spaceKey": SPACE, "expand": "version"}
    r = requests.get(url, params=params, auth=auth)
    r.raise_for_status()
    res = r.json().get('results', [])
    return res[0] if res else None

def upload(page_id, file_path):
    url = f"{BASE}/rest/api/content/{page_id}/child/attachment"
    with open(file_path,'rb') as f:
        res = requests.post(url, files={'file': (os.path.basename(file_path), f)}, auth=auth)
    res.raise_for_status()
    print(f"📎 Uploaded {os.path.basename(file_path)}")

def main():
    v = read_version()
    pdf = os.path.join(REPORT_DIR, f"{BASE_NAME}_v{v}.pdf")
    page = get_page()
    if not page: sys.exit("❌ Confluence page not found.")
    page_id = page['id']
    upload(page_id, pdf)
    print(f"✅ PDF v{v} published to Confluence page '{TITLE}'")

if __name__ == "__main__":
    main()
