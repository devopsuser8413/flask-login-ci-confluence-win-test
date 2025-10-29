import os
import re
import base64
from io import BytesIO
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt

# Input and output
SOURCE_REPORT = 'report/test_result_report_v4.html'
OUTPUT_REPORT = 'report/test_result_report_v4_enhanced.html'

def extract_summary_counts(html_text):
    """Extract test result counts from pytest-html summary section."""
    matches = {
        'passed': re.search(r'(\d+)\s+Passed', html_text),
        'failed': re.search(r'(\d+)\s+Failed', html_text),
        'skipped': re.search(r'(\d+)\s+Skipped', html_text),
        'error': re.search(r'(\d+)\s+Errors?', html_text),
    }
    return {k: int(v.group(1)) if v else 0 for k, v in matches.items()}

def create_summary_chart(counts):
    """Generate a horizontal bar chart and return base64-encoded image."""
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
    return f'<img src="data:image/png;base64,{img_base64}" alt="Test Summary Chart" style="width:70%;">'

def enhance_html_report(source_path, output_path):
    """Read pytest HTML, insert summary dashboard, and save new enhanced report."""
    with open(source_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    html_text = str(soup)
    counts = extract_summary_counts(html_text)
    total = sum(counts.values()) or 1
    pass_rate = (counts['passed'] / total) * 100

    summary_block = f"""
    <div style="background-color:#f9f9f9; border:1px solid #ddd; padding:15px; margin-bottom:20px;">
      <h2>🔍 Test Execution Summary</h2>
      <p>
        <span style="color:#4CAF50; font-weight:bold;">🟢 Passed: {counts['passed']}</span> |
        <span style="color:#F44336; font-weight:bold;">🔴 Failed: {counts['failed']}</span> |
        <span style="color:#FF9800; font-weight:bold;">🟠 Skipped: {counts['skipped']}</span> |
        <span style="color:#9E9E9E; font-weight:bold;">⚫ Errors: {counts['error']}</span>
      </p>
      <p style="font-weight:bold;">✅ Pass Rate: {pass_rate:.1f}%</p>
      {create_summary_chart(counts)}
    </div>
    """

    # Insert summary block right after <body>
    body = soup.find('body')
    body.insert(0, BeautifulSoup(summary_block, 'html.parser'))

    # Highlight failure logs in red boxes
    for span in soup.find_all('span', class_='error'):
        span['style'] = 'background-color:#ffe6e6; color:#d32f2f; font-weight:bold;'

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(str(soup))

    print(f"✅ Enhanced report created: {output_path}")

if __name__ == "__main__":
    enhance_html_report(SOURCE_REPORT, OUTPUT_REPORT)
