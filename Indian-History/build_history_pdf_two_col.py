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

json_path = "/Users/sathishkumar/.gemini/antigravity/brain/17695494-8089-45b1-a1dc-9ce7f3eac4ce/scratch/history_transcribed_pages.json"
pdf_output = "/Users/sathishkumar/Pictures/Ai-Demos/Q-Gemini/Data/Indian-History-Data/Indian_history_suresh_usable.pdf"
temp_pdf_path = "/Users/sathishkumar/.gemini/antigravity/brain/17695494-8089-45b1-a1dc-9ce7f3eac4ce/scratch/temp_page_history.pdf"
font_path = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"

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
            para_cells.append(Paragraph(cell or "&nbsp;", style))
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
            story.append(Paragraph(stripped.lstrip('#').strip(), h2_style))
        elif stripped.startswith('##') or stripped.startswith('#'):
            story.append(Paragraph(stripped.lstrip('#').strip(), h1_style))
        elif stripped.startswith('*') or stripped.startswith('-') or stripped.startswith('•'):
            clean_text = stripped.lstrip('*-•').strip()
            story.append(Paragraph(f"&bull; {clean_text}", bullet_style))
        else:
            story.append(Paragraph(stripped, body_style))
            
    if in_table and table_lines:
        t = parse_markdown_table(table_lines, table_cell_style, col_width)
        if t:
            story.append(t)
            story.append(Spacer(1, 3))
            
    return story

def check_fits(lines, font_size, col_width):
    # Setup document
    doc = BaseDocTemplate(temp_pdf_path, pagesize=A4)
    
    # Left column: x=36, y=36, width=252, height=770
    # Right column: x=306, y=36, width=252, height=770
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

def build_history_pdf_two_col():
    print(f"Reading transcribed text from {json_path}...")
    with open(json_path, "r", encoding="utf-8") as f:
        pages_dict = json.load(f)
        
    print("Registering Arial Unicode font...")
    pdfmetrics.registerFont(TTFont('ArialUnicode', font_path))
    
    num_pages = len(pages_dict)
    col_width = 252.0 # width of a single column frame
    
    # Find optimal font sizes page-by-page
    optimized_sizes = {}
    print("Optimizing page font sizes...")
    for i in range(1, num_pages + 1):
        page_key = f"page_{i}"
        if page_key not in pages_dict:
            continue
        page_text = pages_dict[page_key]
        lines = page_text.split('\n')
        
        # Binary or linear search from 9.5 down to 3.5 (smaller step for precision)
        font_size = 9.5
        fits = False
        while font_size >= 3.5:
            if check_fits(lines, font_size, col_width):
                fits = True
                break
            font_size -= 0.3
            
        if not fits:
            font_size = 3.5 # Fallback min size
            
        optimized_sizes[i] = font_size
        print(f"  Page {i}/{num_pages}: Optimal font size: {font_size:.1f} pt")
        
    # Clean up temp file
    if os.path.exists(temp_pdf_path):
        os.remove(temp_pdf_path)
        
    # Build final PDF
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
        
        # Get optimized font size for this page
        fs = optimized_sizes[i]
        leading = fs * 1.35
        
        # Build paragraphs and tables
        page_story = build_single_page_story(lines, fs, leading, col_width)
        final_story.extend(page_story)
        
        # Add PageBreak after each page's content except the last
        if i < num_pages:
            final_story.append(PageBreak())
            
    print(f"Saving final two-column PDF to {pdf_output}...")
    doc.build(final_story)
    print("Saved successfully!")

if __name__ == "__main__":
    build_history_pdf_two_col()
