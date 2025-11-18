import os
import requests
from requests.auth import HTTPBasicAuth

JIRA_URL = os.getenv("JIRA_URL")
JIRA_USER = os.getenv("JIRA_USER")
RTM_TOKEN = os.getenv("RTM_API_KEY")
PROJECT_KEY = os.getenv("JIRA_PROJECT", "QA")
TESTCASE_KEYS = os.getenv("RTM_TESTCASE_KEYS", "").split(",")

JUNIT_FILE = "report/junit_report.xml"
PDF_REPORT = "report/test_result_report.pdf"
HTML_REPORT = "report/test_result_report.html"


def auth():
    return HTTPBasicAuth(JIRA_USER, RTM_TOKEN)


def create_test_execution():
    """Create RTM Test Execution"""
    url = f"{JIRA_URL}/rest/atm/1.0/testexecutions"
    payload = {
        "projectKey": PROJECT_KEY,
        "name": "Automated Jenkins Test Execution",
        "description": "Imported from Jenkins Pipeline",
    }

    res = requests.post(url, json=payload, auth=auth())
    res.raise_for_status()
    key = res.json()["key"]
    print(f"✔ Created Test Execution: {key}")
    return key


def add_testcases_to_execution(exec_key):
    """Link RTM test cases to execution"""
    url = f"{JIRA_URL}/rest/atm/1.0/testexecutions/{exec_key}/testcases"
    payload = {"add": TESTCASE_KEYS}

    res = requests.post(url, json=payload, auth=auth())
    res.raise_for_status()
    print(f"✔ Added test cases to execution: {TESTCASE_KEYS}")


def create_automated_test_run(exec_key, testcase_key, junit_path):
    """Upload JUnit results to RTM Test Run"""
    url = f"{JIRA_URL}/rest/atm/1.0/automatedtestrun"

    with open(junit_path, "rb") as f:
        xml_data = f.read()

    payload = {
        "projectKey": PROJECT_KEY,
        "testExecKey": exec_key,
        "testCaseKey": testcase_key,
    }

    files = {
        "result": ("junit_report.xml", xml_data, "application/xml"),
        "info": (None, str(payload), "application/json")
    }

    res = requests.post(url, files=files, auth=auth())
    res.raise_for_status()
    print(f"✔ Uploaded automated results for {testcase_key}")


def upload_attachment(issue_key, file_path):
    """Attach PDF/HTML report to Test Execution"""
    url = f"{JIRA_URL}/rest/api/3/issue/{issue_key}/attachments"
    headers = {"X-Atlassian-Token": "no-check"}

    files = {"file": open(file_path, "rb")}

    res = requests.post(url, headers=headers, files=files, auth=auth())
    res.raise_for_status()
    print(f"📎 Attached: {file_path}")


def main():
    # 1. Create Test Execution
    exec_key = create_test_execution()

    # 2. Link Test Cases
    add_testcases_to_execution(exec_key)

    # 3. Upload JUnit for each test case
    if os.path.exists(JUNIT_FILE):
        for tc in TESTCASE_KEYS:
            create_automated_test_run(exec_key, tc.strip(), JUNIT_FILE)

    # 4. Attach HTML/PDF
    if os.path.exists(PDF_REPORT):
        upload_attachment(exec_key, PDF_REPORT)

    if os.path.exists(HTML_REPORT):
        upload_attachment(exec_key, HTML_REPORT)

    print("\n🎉 RTM integration completed successfully!")


if __name__ == "__main__":
    main()
