import os
import requests
from requests.auth import HTTPBasicAuth
import sys

# Load environment variables
BASE = os.getenv("CONFLUENCE_BASE")
USER = os.getenv("CONFLUENCE_USER")
TOKEN = os.getenv("CONFLUENCE_TOKEN")
SPACE = os.getenv("CONFLUENCE_SPACE")

auth = HTTPBasicAuth(USER, TOKEN)
url = f"{BASE}/rest/api/space/{SPACE}"

try:
    response = requests.get(url, auth=auth)
    print("Status Code:", response.status_code)
    
    if response.status_code == 200:
        print("✅ API token is valid and user has access to the space.")
        sys.exit(0)
    elif response.status_code == 403:
        print("❌ Forbidden: User does not have permission to access this space.")
        sys.exit(1)
    elif response.status_code == 401:
        print("❌ Unauthorized: Invalid API token or user email.")
        sys.exit(1)
    else:
        print("❌ Unexpected error:", response.text)
        sys.exit(1)
except Exception as e:
    print("❌ Error connecting to Confluence:", str(e))
    sys.exit(1)
