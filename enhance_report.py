import os
import re
from io import BytesIO
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image

REPORT_DIR = 'report'
BASE_NAME = 'test_result_report'
VERSION_FILE = os.path.join(REPORT_DIR, 'version.txt')
PYTEST_OUTPUT = os.path.join(REPORT_DIR, 'pytest_output.txt')

def read_version():
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE) as f:
            return int(f.read().strip())
    return 1

def write_version(v):
    with open(VERSION_FILE, 'w') as f:
        f.write(str(v))

def get_next_version():
    pattern = re.compile(rf"{BASE_NAME}_v(\d+)\.pdf$")
    existing = [f for f in os.listdir(REPORT_DIR) if pattern.match(f)]
    return max([int(pattern.match(f).group(1)) for f in existing], default=0) + 1

def extract_counts():
    """Parse pytest output to get summary counts"""
    passed = failed = errors = skipped = 0
    if not os.path.exists(PYTEST_OUTPUT):
        return {"passed":0,"failed":0,"error":0,"skipped":0}
    with open(PYTEST_OUTPUT, 'r', encoding='utf-8', errors='ignore') as f:
        text = f.read()
    m = re.search(r"(\d+)\s+passed", text);   passed = int(m.group(1)) if m else 0
    m = re.search(r"(\d+)\s+failed", text);   failed = int(m.group(1)) if m else 0
    m = re.search(r"(\d+)\s+error", text);    errors = int(m.group(1)) if m else 0
    m = re.search(r"(\d+)\s+skipped", text);  skipped = int(m.group(1)) if m else 0
    return {"passed":passed,"failed":failed,"error":errors,"skipped":skipped}

def create_chart(counts):
    labels = list(counts.keys())
    values = list(counts.values())
    colors_ = ['#4CAF50','#F44336','#9E9E9E','#FF9800']
    fig, ax = plt.subplots(figsize=(4,2))
    bars = ax.barh(labels, values, color=colors_)
    ax.bar_label(bars)
    ax.set_title('Test Summary')
    buf = BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    return buf

def generate_pdf(version, counts, pass_rate, chart_buf):
    pdf_path = os.path.join(REPORT_DIR, f"{BASE_NAME}_v{version}.pdf")
    doc = SimpleDocTemplate(pdf_path, pagesize=A4)
    styles = getSampleStyleSheet()
    content = []

    content.append(Paragraph(f"<b>Test Result Report v{version}</b>", styles['Title']))
    content.append(Spacer(1, 12))
    summary = [
        ['Status', 'Count'],
        ['✅ Passed', counts['passed']],
        ['❌ Failed', counts['failed']],
        ['⚠️ Skipped', counts['skipped']],
        ['⚫ Errors', counts['error']],
        ['Pass Rate', f"{pass_rate:.1f}%"]
    ]
    table = Table(summary)
    table.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.lightgrey),
        ('GRID',(0,0),(-1,-1),1,colors.grey),
        ('ALIGN',(1,1),(-1,-1),'CENTER')
    ]))
    content.append(table)
    content.append(Spacer(1, 20))
    content.append(Image(chart_buf, width=300, height=100))
    doc.build(content)
    print(f"📄 PDF report generated: {pdf_path}")

def enhance_pdf():
    counts = extract_counts()
    total = sum(counts.values()) or 1
    pass_rate = (counts['passed']/total)*100

    current_version = read_version()
    next_version = get_next_version()
    version = max(current_version, next_version - 1)

    chart_buf = create_chart(counts)
    generate_pdf(version, counts, pass_rate, chart_buf)
    write_version(version)
    print(f"✅ PDF-only report generated successfully (v{version}).")

if __name__ == "__main__":
    enhance_pdf()
