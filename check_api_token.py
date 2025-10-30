import sys, io, os, requests
from requests.auth import HTTPBasicAuth

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = os.getenv('CONFLUENCE_BASE')
USER = os.getenv('CONFLUENCE_USER')
TOKEN = os.getenv('CONFLUENCE_TOKEN')
SPACE = os.getenv('CONFLUENCE_SPACE')

try:
    r = requests.get(f"{BASE}/rest/api/space/{SPACE}", auth=HTTPBasicAuth(USER, TOKEN))
    print(f"Status Code: {r.status_code}")
    r.raise_for_status()
    print("✅ API token is valid and user has access to the space.")
except Exception as e:
    print(f"❌ Error connecting to Confluence: {e}")
    sys.exit(1)
