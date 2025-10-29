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
REPORT_PATH = os.getenv('REPORT_PATH')

auth = HTTPBasicAuth(CONFLUENCE_USER, CONFLUENCE_TOKEN)
headers = {"Content-Type": "application/json"}

# ----------------------------
# Incremental report generator
# ----------------------------
def get_next_report_filename(report_dir, base_name):
    """Generate next incremental filename like test_result_report_v3.html"""
    os.makedirs(report_dir, exist_ok=True)
    pattern = re.compile(rf"{re.escape(base_name)}_v(\d+)\.html$")
    existing_files = [f for f in os.listdir(report_dir) if pattern.match(f)]

    next_version = max([int(pattern.match(f).group(1)) for f in existing_files], default=0) + 1
    return os.path.join(report_dir, f"{base_name}_v{next_version}.html"), next_version


def create_incremental_report(base_report_path):
    """Copy the report.html file to an incremental versioned file"""
    if not os.path.exists(base_report_path):
        print(f"❌ Base report file not found: {base_report_path}")
        sys.exit(1)

    report_dir = os.path.dirname(base_report_path)
    base_name = 'test_result_report'
    new_report_path, version = get_next_report_filename(report_dir, base_name)

    with open(base_report_path, 'rb') as src, open(new_report_path, 'wb') as dest:
        data = src.read()
        dest.write(data)

    print(f"📄 New incremental report created: {new_report_path}")
    return new_report_path, version

# ----------------------------
# Confluence helper functions
# ----------------------------
def get_page(title, space):
    """Get Confluence page info if it exists"""
    url = f"{CONFLUENCE_BASE}/rest/api/content"
    params = {"title": title, "spaceKey": space, "expand": "version"}
    r = requests.get(url, headers=headers, params=params, auth=auth)

    if r.status_code == 403:
        print(f"❌ Forbidden: No permission to access space '{space}'.")
        sys.exit(1)

    r.raise_for_status()
    results = r.json().get('results', [])
    return results[0] if results else None


def create_page(title, space, content):
    """Create a new Confluence page"""
    url = f"{CONFLUENCE_BASE}/rest/api/content"
    payload = {
        "type": "page",
        "title": title,
        "space": {"key": space},
        "body": {"storage": {"value": content, "representation": "storage"}}
    }

    r = requests.post(url, headers=headers, json=payload, auth=auth)
    if r.status_code == 403:
        print(f"❌ Forbidden: Cannot create page in '{space}'. Check permissions.")
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
        "body": {"storage": {"value": content, "representation": "storage"}}
    }

    r = requests.put(url, headers=headers, json=payload, auth=auth)
    if r.status_code == 403:
        print(f"❌ Forbidden: Cannot update page '{title}'. Check permissions.")
        sys.exit(1)

    r.raise_for_status()
    print(f"✅ Page '{title}' updated successfully.")
    return r.json()


def upload_attachment(page_id, file_path):
    """Upload or replace the HTML report as a Confluence attachment"""
    url = f"{CONFLUENCE_BASE}/rest/api/content/{page_id}/child/attachment"
    file_name = os.path.basename(file_path)

    # Check if attachment already exists
    existing_url = f"{url}?filename={file_name}"
    r = requests.get(existing_url, auth=auth)
    replace = False
    if r.status_code == 200 and r.json().get('results'):
        # Replace existing attachment
        att_id = r.json()['results'][0]['id']
        upload_url = f"{CONFLUENCE_BASE}/rest/api/content/{page_id}/child/attachment/{att_id}/data"
        replace = True
    else:
        upload_url = url

    with open(file_path, 'rb') as f:
        files = {'file': (file_name, f, 'text/html')}
        headers_no_json = {"X-Atlassian-Token": "no-check"}
        method = requests.put if replace else requests.post
        res = method(upload_url, headers=headers_no_json, files=files, auth=auth)
        res.raise_for_status()

    print(f"📎 Uploaded report as attachment: {file_name}")
    return file_name


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
    # Step 1: Create incremental report
    new_report_path, version_number = create_incremental_report(REPORT_PATH)

    # Step 2: Read HTML content
    report_content = read_report(new_report_path)

    # Step 3: Add download link HTML
    download_html = f"""
    <p><b>Download full HTML report:</b> 
    <a href='/download/attachments/{{page.id}}/{os.path.basename(new_report_path)}' 
    data-linked-resource-type='attachment'>Click here to download (v{version_number})</a></p>
    <hr>
    """

    combined_html = download_html + report_content

    # Step 4: Check page existence
    page = get_page(CONFLUENCE_TITLE, CONFLUENCE_SPACE)

    if page:
        print(f"📄 Page '{CONFLUENCE_TITLE}' exists. Updating...")
        updated_page = update_page(page['id'], CONFLUENCE_TITLE, page['version']['number'], combined_html)
        upload_attachment(page['id'], new_report_path)
    else:
        print(f"📄 Page '{CONFLUENCE_TITLE}' does not exist. Creating...")
        new_page = create_page(CONFLUENCE_TITLE, CONFLUENCE_SPACE, combined_html)
        upload_attachment(new_page['id'], new_report_path)

    print(f"✅ Report v{version_number} published to Confluence successfully.")

# ----------------------------
# Entry point
# ----------------------------
if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP error occurred: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)
