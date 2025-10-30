import os
import re
import base64
from io import BytesIO
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet

INPUT_REPORT = 'report/report.html'
OUTPUT_DIR = 'report'
BASE_NAME = 'test_result_report'
VERSION_FILE = os.path.join(OUTPUT_DIR, 'version.txt')


# ----------------------------
# Extract Summary Counts
# ----------------------------
def extract_summary_counts(html_text):
    matches = {
        'passed': re.search(r'(\d+)\s+Passed', html_text),
        'failed': re.search(r'(\d+)\s+Failed', html_text),
        'skipped': re.search(r'(\d+)\s+Skipped', html_text),
        'error': re.search(r'(\d+)\s+Errors?', html_text),
    }
    return {k: int(v.group(1)) if v else 0 for k, v in matches.items()}


# ----------------------------
# Version Helper
# ----------------------------
def get_next_report_filename():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    pattern = re.compile(rf"{re.escape(BASE_NAME)}_v(\d+)\.html$")
    existing = [f for f in os.listdir(OUTPUT_DIR) if pattern.match(f)]
    next_version = max([int(pattern.match(f).group(1)) for f in existing], default=0) + 1
    return os.path.join(OUTPUT_DIR, f"{BASE_NAME}_v{next_version}.html"), next_version


# ----------------------------
# Chart Creator
# ----------------------------
def create_summary_chart(counts):
    labels = ['Passed', 'Failed', 'Skipped', 'Error']
    values = [counts['passed'], counts['failed'], counts['skipped'], counts['error']]
    colors_ = ['#4CAF50', '#F44336', '#FF9800', '#9E9E9E']

    fig, ax = plt.subplots(figsize=(6, 2))
    bars = ax.barh(labels, values, color=colors_)
    ax.set_xlabel('Number of Tests')
    ax.set_title('Test Summary Overview')
    ax.bar_label(bars, labels=[str(v) for v in values], label_type='edge')
    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close(fig)
    return buf


# ----------------------------
# PDF Report Generator
# ----------------------------
def generate_pdf_report(version, counts, pass_rate, chart_buf):
    pdf_filename = os.path.join(OUTPUT_DIR, f"{BASE_NAME}_v{version}.pdf")
    doc = SimpleDocTemplate(pdf_filename, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    title = Paragraph(f"<b>Test Result Report - v{version}</b>", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 12))

    summary = f"""
    <b>Passed:</b> <font color='green'>{counts['passed']}</font> |
    <b>Failed:</b> <font color='red'>{counts['failed']}</font> |
    <b>Skipped:</b> <font color='orange'>{counts['skipped']}</font> |
    <b>Errors:</b> <font color='gray'>{counts['error']}</font><br/>
    <b>Pass Rate:</b> {pass_rate:.1f}%
    """
    elements.append(Paragraph(summary, styles['Normal']))
    elements.append(Spacer(1, 20))

    # Insert chart image
    img = Image(chart_buf)
    img._restrictSize(400, 150)
    elements.append(img)
    elements.append(Spacer(1, 20))

    # Add details table
    data = [
        ["Metric", "Count"],
        ["Passed", counts["passed"]],
        ["Failed", counts["failed"]],
        ["Skipped", counts["skipped"]],
        ["Error", counts["error"]],
        ["Pass Rate", f"{pass_rate:.1f}%"]
    ]

    table = Table(data, colWidths=[150, 150])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
    ]))
    elements.append(table)

    doc.build(elements)
    print(f"📄 PDF report generated: {pdf_filename}")


# ----------------------------
# Main HTML Enhancer
# ----------------------------
def enhance_html_report():
    if not os.path.exists(INPUT_REPORT):
        raise SystemExit(f"❌ Base report not found: {INPUT_REPORT}")

    with open(INPUT_REPORT, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    html_text = str(soup)
    counts = extract_summary_counts(html_text)
    total = sum(counts.values()) or 1
    pass_rate = (counts['passed'] / total) * 100

    chart_buf = create_summary_chart(counts)

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

    # Generate PDF version
    generate_pdf_report(version, counts, pass_rate, chart_buf)


# ----------------------------
# Run Script
# ----------------------------
if __name__ == "__main__":
    enhance_html_report()
