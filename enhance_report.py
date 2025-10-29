import os
import re
import base64
from io import BytesIO
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt

INPUT_REPORT = 'report/report.html'
OUTPUT_DIR = 'report'
BASE_NAME = 'test_result_report'
VERSION_FILE = os.path.join(OUTPUT_DIR, 'version.txt')

def extract_summary_counts(html_text):
    matches = {
        'passed': re.search(r'(\d+)\s+Passed', html_text),
        'failed': re.search(r'(\d+)\s+Failed', html_text),
        'skipped': re.search(r'(\d+)\s+Skipped', html_text),
        'error': re.search(r'(\d+)\s+Errors?', html_text),
    }
    return {k: int(v.group(1)) if v else 0 for k, v in matches.items()}

def get_next_report_filename():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    pattern = re.compile(rf"{re.escape(BASE_NAME)}_v(\d+)\.html$")
    existing = [f for f in os.listdir(OUTPUT_DIR) if pattern.match(f)]
    next_version = max([int(pattern.match(f).group(1)) for f in existing], default=0) + 1
    return os.path.join(OUTPUT_DIR, f"{BASE_NAME}_v{next_version}.html"), next_version

def create_summary_chart(counts):
    labels = ['Passed', 'Failed', 'Skipped', 'Error']
    values = [counts['passed'], counts['failed'], counts['skipped'], counts['error']]
    colors = ['#4CAF50', '#F44336', '#FF9800', '#9E9E9E']

    fig, ax = plt.subplots(figsize=(6, 2))
    bars = ax.barh(labels, values, color=colors)
    ax.set_xlabel('Number of Tests')
    ax.set_title('Test Summary Overview')
    ax.bar_label(bars, labels=[str(v) for v in values], label_type='edge')
    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return f'<img src="data:image/png;base64,{img_base64}" style="width:70%;">'

def enhance_html_report():
    if not os.path.exists(INPUT_REPORT):
        raise SystemExit(f"❌ Base report not found: {INPUT_REPORT}")

    with open(INPUT_REPORT, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    html_text = str(soup)
    counts = extract_summary_counts(html_text)
    total = sum(counts.values()) or 1
    pass_rate = (counts['passed'] / total) * 100

    summary_block = f"""
    <div style="background-color:#f9f9f9; border:1px solid #ddd; padding:15px; margin-bottom:20px;">
      <h2>🔍 Test Execution Summary</h2>
      <p>
        <span style="color:#4CAF50;">🟢 Passed: {counts['passed']}</span> |
        <span style="color:#F44336;">🔴 Failed: {counts['failed']}</span> |
        <span style="color:#FF9800;">🟠 Skipped: {counts['skipped']}</span> |
        <span style="color:#9E9E9E;">⚫ Errors: {counts['error']}</span>
      </p>
      <p><b>✅ Pass Rate:</b> {pass_rate:.1f}%</p>
      {create_summary_chart(counts)}
    </div>
    """

    body = soup.find('body')
    body.insert(0, BeautifulSoup(summary_block, 'html.parser'))

    output_file, version = get_next_report_filename()
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(str(soup))

    with open(VERSION_FILE, 'w') as vf:
        vf.write(str(version))

    print(f"✅ Enhanced report created: {output_file}")
    print(f"📄 Version: v{version}")

if __name__ == "__main__":
    enhance_html_report()
