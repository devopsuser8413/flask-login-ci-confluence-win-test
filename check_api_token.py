import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Existing imports and code
import requests
from requests.auth import HTTPBasicAuth
import os

# --- keep your previous logic ---
CONFLUENCE_BASE = os.getenv('CONFLUENCE_BASE')
CONFLUENCE_USER = os.getenv('CONFLUENCE_USER')
CONFLUENCE_TOKEN = os.getenv('CONFLUENCE_TOKEN')
CONFLUENCE_SPACE = os.getenv('CONFLUENCE_SPACE')

auth = HTTPBasicAuth(CONFLUENCE_USER, CONFLUENCE_TOKEN)

try:
    r = requests.get(f"{CONFLUENCE_BASE}/rest/api/space/{CONFLUENCE_SPACE}", auth=auth)
    print(f"Status Code: {r.status_code}")
    r.raise_for_status()
    print("✅ API token is valid and user has access to the space.")
except Exception as e:
    print(f"❌ Error connecting to Confluence: {e}")
    sys.exit(1)
