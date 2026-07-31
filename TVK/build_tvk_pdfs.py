import json
import os
import re
import fitz
from reportlab.lib.pagesizes import A4
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

font_path = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"

configs = {
    "leaders": {
        "json_path": "/Users/sathishkumar/Pictures/Ai-Demos/Q-Gemini/TVK/cache_leaders.json",
        "pdf_output": "/Users/sathishkumar/Pictures/Ai-Demos/Q-Gemini/Data/TVK-Government-Data/TVK_Govt_LEADERS_Policy_Notes_1_usable.pdf",
        "temp_pdf": "/Users/sathishkumar/Pictures/Ai-Demos/Q-Gemini/TVK/temp_page_leaders.pdf"
    },
    "schemes2": {
        "json_path": "/Users/sathishkumar/Pictures/Ai-Demos/Q-Gemini/TVK/cache_schemes2.json",
        "pdf_output": "/Users/sathishkumar/Pictures/Ai-Demos/Q-Gemini/Data/TVK-Government-Data/TVK_govt_Policy_Scheme_part_2_usable.pdf",
        "temp_pdf": "/Users/sathishkumar/Pictures/Ai-Demos/Q-Gemini/TVK/temp_page_schemes2.pdf"
    },
    "schemes3": {
        "json_path": "/Users/sathishkumar/Pictures/Ai-Demos/Q-Gemini/TVK/cache_schemes3.json",
        "pdf_output": "/Users/sathishkumar/Pictures/Ai-Demos/Q-Gemini/Data/TVK-Government-Data/Tvk_govt_policy_Scheme_part_3_usable.pdf",
        "temp_pdf": "/Users/sathishkumar/Pictures/Ai-Demos/Q-Gemini/TVK/temp_page_schemes3.pdf"
    }
}

def sanitize_text(text):
    if not text:
        return ""
    text = re.sub(r'<br\s*/?>', '<br/>', text, flags=re.IGNORECASE)
    text = re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;|nbsp;|bull;)', '&amp;', text)
    
    placeholders = {
        "__B_OPEN__": re.compile(r'<b>', re.IGNORECASE),
        "__B_CLOSE__": re.compile(r'</b>', re.IGNORECASE),
        "__I_OPEN__": re.compile(r'<i>', re.IGNORECASE),
        "__I_CLOSE__": re.compile(r'</i>', re.IGNORECASE),
        "__U_OPEN__": re.compile(r'<u>', re.IGNORECASE),
        "__U_CLOSE__": re.compile(r'</u>', re.IGNORECASE),
        "__BR__": re.compile(r'<br/>', re.IGNORECASE),
    }
    
    for key, pattern in placeholders.items():
        text = pattern.sub(key, text)
        
    text = text.replace("<", "&lt;").replace(">", "&gt;")
    
    restores = {
        "__B_OPEN__": "<b>",
        "__B_CLOSE__": "</b>",
        "__I_OPEN__": "<i>",
        "__I_CLOSE__": "</i>",
        "__U_OPEN__": "<u>",
        "__U_CLOSE__": "</u>",
        "__BR__": "<br/>",
    }
    for key, val in restores.items():
        text = text.replace(key, val)
        
    return text

def parse_markdown_table(lines, style, col_width):
    data = []
    for line in lines:
        if re.match(r'^\s*\|\s*[-:]+\s*\|', line) or re.match(r'^\s*\|?\s*[-:\s\|]+\s*$', line):
            continue
        cells = [c.strip() for c in line.split('|')]
        if len(cells) > 1 and cells[0] == '':
            cells = cells[1:]
        if len(cells) > 0 and cells[-1] == '':
            cells = cells[:-1]
        
        para_cells = []
        for cell in cells:
            para_cells.append(Paragraph(sanitize_text(cell or "&nbsp;"), style))
        if para_cells:
            data.append(para_cells)
            
    if not data:
        return None
        
    col_count = max(len(row) for row in data)
    col_w = col_width / col_count
    t = Table(data, colWidths=[col_w] * col_count)
    t.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#d1d5db')),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f3f4f6')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('LEFTPADDING', (0,0), (-1,-1), 3),
        ('RIGHTPADDING', (0,0), (-1,-1), 3),
    ]))
    return t

def build_single_page_story(lines, font_size, leading, col_width):
    story = []
    
    body_style = ParagraphStyle(
        'TempBody',
        fontName='ArialUnicode',
        fontSize=font_size,
        leading=leading,
        spaceBefore=1,
        spaceAfter=2,
        textColor=colors.HexColor('#1f2937')
    )
    
    bullet_style = ParagraphStyle(
        'TempBullet',
        parent=body_style,
        leftIndent=10,
        firstLineIndent=-6
    )
    
    h1_style = ParagraphStyle(
        'TempH1',
        fontName='ArialUnicode',
        fontSize=font_size * 1.3,
        leading=leading * 1.3,
        spaceBefore=5,
        spaceAfter=3,
        textColor=colors.HexColor('#1e3a8a'),
        keepWithNext=True
    )
    
    h2_style = ParagraphStyle(
        'TempH2',
        fontName='ArialUnicode',
        fontSize=font_size * 1.15,
        leading=leading * 1.15,
        spaceBefore=4,
        spaceAfter=2,
        textColor=colors.HexColor('#0369a1'),
        keepWithNext=True
    )
    
    table_cell_style = ParagraphStyle(
        'TempTableCell',
        parent=body_style,
        fontSize=font_size * 0.85,
        leading=leading * 0.85,
        spaceBefore=0,
        spaceAfter=0
    )
    
    table_lines = []
    in_table = False
    
    for line in lines:
        stripped = line.strip()
        
        if stripped.startswith('|'):
            in_table = True
            table_lines.append(line)
            continue
        elif in_table:
            if table_lines:
                t = parse_markdown_table(table_lines, table_cell_style, col_width)
                if t:
                    story.append(t)
                    story.append(Spacer(1, 3))
                table_lines = []
                in_table = False
        
        if not stripped:
            continue
            
        if stripped.startswith('###'):
            story.append(Paragraph(sanitize_text(stripped.lstrip('#').strip()), h2_style))
        elif stripped.startswith('##') or stripped.startswith('#'):
            story.append(Paragraph(sanitize_text(stripped.lstrip('#').strip()), h1_style))
        elif stripped.startswith('*') or stripped.startswith('-') or stripped.startswith('•'):
            clean_text = stripped.lstrip('*-•').strip()
            story.append(Paragraph(f"&bull; {sanitize_text(clean_text)}", bullet_style))
        else:
            story.append(Paragraph(sanitize_text(stripped), body_style))
            
    if in_table and table_lines:
        t = parse_markdown_table(table_lines, table_cell_style, col_width)
        if t:
            story.append(t)
            story.append(Spacer(1, 3))
            
    return story

def check_fits(lines, font_size, col_width, temp_pdf_path):
    doc = BaseDocTemplate(temp_pdf_path, pagesize=A4)
    frame_left = Frame(36, 36, 252, 770, id='col1', topPadding=0, bottomPadding=0, leftPadding=0, rightPadding=0)
    frame_right = Frame(306, 36, 252, 770, id='col2', topPadding=0, bottomPadding=0, leftPadding=0, rightPadding=0)
    template = PageTemplate(id='two_col', frames=[frame_left, frame_right])
    doc.addPageTemplates([template])
    
    leading = font_size * 1.35
    story = build_single_page_story(lines, font_size, leading, col_width)
    
    try:
        doc.build(story)
        pdf = fitz.open(temp_pdf_path)
        pages_count = len(pdf)
        pdf.close()
        return pages_count == 1
    except Exception as e:
        print(f"Error checking fit: {e}")
        return False

def build_pdf(name, cfg):
    json_path = cfg["json_path"]
    pdf_output = cfg["pdf_output"]
    temp_pdf_path = cfg["temp_pdf"]
    
    print(f"\n==========================================")
    print(f"BUILDING PDF: {name}")
    print(f"==========================================")
    
    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found.")
        return
        
    with open(json_path, "r", encoding="utf-8") as f:
        pages_dict = json.load(f)
        
    num_pages = len(pages_dict)
    col_width = 252.0
    
    # 1. Optimize page font sizes
    optimized_sizes = {}
    print("Optimizing page font sizes...")
    for i in range(1, num_pages + 1):
        page_key = f"page_{i}"
        if page_key not in pages_dict:
            continue
        page_text = pages_dict[page_key]
        lines = page_text.split('\n')
        
        font_size = 9.5
        fits = False
        while font_size >= 3.5:
            if check_fits(lines, font_size, col_width, temp_pdf_path):
                fits = True
                break
            font_size -= 0.3
            
        if not fits:
            font_size = 3.5
            
        optimized_sizes[i] = font_size
        print(f"  Page {i}/{num_pages}: Optimal font size: {font_size:.1f} pt")
        
    if os.path.exists(temp_pdf_path):
        os.remove(temp_pdf_path)
        
    # 2. Build final PDF
    print("Building final two-column PDF...")
    doc = BaseDocTemplate(pdf_output, pagesize=A4)
    frame_left = Frame(36, 36, 252, 770, id='col1', topPadding=0, bottomPadding=0, leftPadding=0, rightPadding=0)
    frame_right = Frame(306, 36, 252, 770, id='col2', topPadding=0, bottomPadding=0, leftPadding=0, rightPadding=0)
    template = PageTemplate(id='two_col', frames=[frame_left, frame_right])
    doc.addPageTemplates([template])
    
    final_story = []
    for i in range(1, num_pages + 1):
        page_key = f"page_{i}"
        if page_key not in pages_dict:
            continue
        page_text = pages_dict[page_key]
        lines = page_text.split('\n')
        
        fs = optimized_sizes[i]
        leading = fs * 1.35
        
        page_story = build_single_page_story(lines, fs, leading, col_width)
        final_story.extend(page_story)
        
        if i < num_pages:
            final_story.append(PageBreak())
            
    print(f"Saving final PDF to {pdf_output}...")
    doc.build(final_story)
    print(f"SUCCESS: Created {pdf_output} ({num_pages} pages)")

def main():
    print("Registering Arial Unicode font...")
    pdfmetrics.registerFont(TTFont('ArialUnicode', font_path))
    
    for name, cfg in configs.items():
        build_pdf(name, cfg)
        
    print("\nAll usable TVK PDFs built successfully!")

if __name__ == "__main__":
    main()
