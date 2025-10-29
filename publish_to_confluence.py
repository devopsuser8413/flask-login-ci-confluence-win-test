import os
import requests
from requests.auth import HTTPBasicAuth
import sys

# ----------------------------
# Load environment variables
# ----------------------------
CONFLUENCE_BASE = os.getenv('CONFLUENCE_BASE')
CONFLUENCE_USER = os.getenv('CONFLUENCE_USER')
CONFLUENCE_TOKEN = os.getenv('CONFLUENCE_TOKEN')

CONFLUENCE_SPACE = os.getenv('CONFLUENCE_SPACE', 'DEMO')  # default space
CONFLUENCE_TITLE = os.getenv('CONFLUENCE_TITLE', 'CI Test Report')
REPORT_PATH = os.getenv('REPORT_PATH', 'report/report.html')

auth = HTTPBasicAuth(CONFLUENCE_USER, CONFLUENCE_TOKEN)
headers = {
    "Content-Type": "application/json"
}

# ----------------------------
# Helper functions
# ----------------------------
def get_page(title, space):
    """Get Confluence page info if exists"""
    url = f"{CONFLUENCE_BASE}/rest/api/content"
    params = {
        "title": title,
        "spaceKey": space,
        "expand": "version"
    }
    r = requests.get(url, headers=headers, params=params, auth=auth)
    if r.status_code == 403:
        print(f"❌ Forbidden: User does not have permission to access space '{space}'.")
        sys.exit(1)
    r.raise_for_status()
    results = r.json().get('results')
    if results:
        return results[0]  # return first match
    return None

def create_page(title, space, content):
    """Create a new Confluence page"""
    url = f"{CONFLUENCE_BASE}/rest/api/content"
    payload = {
        "type": "page",
        "title": title,
        "space": {"key": space},
        "body": {
            "storage": {
                "value": content,
                "representation": "storage"
            }
        }
    }
    r = requests.post(url, headers=headers, json=payload, auth=auth)
    if r.status_code == 403:
        print(f"❌ Forbidden: Cannot create page in space '{space}'. Check permissions.")
        sys.exit(1)
    r.raise_for_status()
    print(f"✅ Page '{title}' created successfully in space '{space}'.")
    return r.json()

def update_page(page_id, title, version, content):
    """Update existing Confluence page"""
    url = f"{CONFLUENCE_BASE}/rest/api/content/{page_id}"
    payload = {
        "id": page_id,
        "type": "page",
        "title": title,
        "version": {"number": version + 1},
        "body": {
            "storage": {
                "value": content,
                "representation": "storage"
            }
        }
    }
    r = requests.put(url, headers=headers, json=payload, auth=auth)
    if r.status_code == 403:
        print(f"❌ Forbidden: Cannot update page in space '{CONFLUENCE_SPACE}'. Check permissions.")
        sys.exit(1)
    r.raise_for_status()
    print(f"✅ Page '{title}' updated successfully.")
    return r.json()

def read_report(file_path):
    """Read HTML report content"""
    if not os.path.exists(file_path):
        print(f"❌ Report file '{file_path}' not found.")
        sys.exit(1)
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

# ----------------------------
# Main logic
# ----------------------------
def main():
    report_content = read_report(REPORT_PATH)
    page = get_page(CONFLUENCE_TITLE, CONFLUENCE_SPACE)

    if page:
        print(f"📄 Page '{CONFLUENCE_TITLE}' exists. Updating...")
        update_page(page['id'], CONFLUENCE_TITLE, page['version']['number'], report_content)
    else:
        print(f"📄 Page '{CONFLUENCE_TITLE}' does not exist. Creating...")
        create_page(CONFLUENCE_TITLE, CONFLUENCE_SPACE, report_content)

if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP error occurred: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)
