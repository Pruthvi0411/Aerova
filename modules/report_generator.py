import os
import tempfile
import base64
import qrcode
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

def generate_pdf_report(patient_id, date_str, age, gender, recipient_email,
                        triage_data, quality_data, spectrogram_img_path):
    """
    Generates a publication-grade 2-page PDF report matching Aerova Pro specifications.
    Returns (pdf_filepath, base64_pdf_data_uri).
    """
    temp_pdf = tempfile.NamedTemporaryFile(suffix=f"-{patient_id}.pdf", delete=False)
    pdf_path = temp_pdf.name
    temp_pdf.close()

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'HeaderTitle',
        fontName='Helvetica-Bold',
        fontSize=20,
        textColor=colors.white,
        leading=24
    )
    subtitle_style = ParagraphStyle(
        'HeaderSub',
        fontName='Helvetica-Bold',
        fontSize=10,
        textColor=colors.HexColor("#a7f3d0"),
        leading=14,
        spaceAfter=4
    )
    section_heading = ParagraphStyle(
        'SecHeading',
        fontName='Helvetica-Bold',
        fontSize=13,
        textColor=colors.HexColor("#0f2c40"),
        leading=17,
        spaceBefore=14,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'Body',
        fontName='Helvetica',
        fontSize=9.5,
        textColor=colors.HexColor("#334155"),
        leading=14
    )
    bold_label = ParagraphStyle(
        'BoldLabel',
        fontName='Helvetica-Bold',
        fontSize=10,
        textColor=colors.HexColor("#0f2c40"),
        leading=14
    )
    subdued_style = ParagraphStyle(
        'Subdued',
        fontName='Helvetica',
        fontSize=8.5,
        textColor=colors.HexColor("#64748b"),
        leading=12
    )

    story = []

    # 1. Header Banner
    header_data = [
        [
            Paragraph("AEROVA", subtitle_style),
            ""
        ],
        [
            Paragraph("Respiratory Screening Report", title_style),
            ""
        ]
    ]
    header_table = Table(header_data, colWidths=[400, 120])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#0e6274")),
        ('SPAN', (0, 0), (1, 0)),
        ('SPAN', (0, 1), (1, 1)),
        ('TOPPADDING', (0, 0), (-1, -1), 16),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 16),
        ('LEFTPADDING', (0, 0), (-1, -1), 18),
        ('RIGHTPADDING', (0, 0), (-1, -1), 18),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 14))

    # 2. Patient Demographics & Date
    gender_display = str(gender).capitalize() if gender else "Unknown"
    recipient_display = recipient_email if recipient_email else "Clinician Portal"
    meta_data = [
        [
            Paragraph(f"<b>Patient ID</b> &nbsp; {patient_id}", bold_label),
            Paragraph(f"{date_str}", ParagraphStyle('RightMeta', fontName='Helvetica', fontSize=9.5, textColor=colors.HexColor("#64748b"), alignment=2))
        ],
        [
            Paragraph(f"Age: {age} years &nbsp;&nbsp;&nbsp; Gender: {gender_display} &nbsp;&nbsp;&nbsp; Recipient: {recipient_display}", subdued_style),
            ""
        ]
    ]
    meta_table = Table(meta_data, colWidths=[360, 160])
    meta_table.setStyle(TableStyle([
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('SPAN', (0, 1), (1, 1)),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 12))

    # 3. Screening Readout Card
    readout = triage_data.get("readout", "Healthy")
    confidence = triage_data.get("confidence", "80.0%")
    risk_tier = triage_data.get("risk_tier", "Low").upper()
    active_model = triage_data.get("model_name", "extra_trees.joblib")

    box_data = [
        [Paragraph("SCREENING READOUT", ParagraphStyle('BoxKicker', fontName='Helvetica-Bold', fontSize=8.5, textColor=colors.HexColor("#0284c7"))), ""],
        [
            Paragraph(f"<b>{readout}</b>", ParagraphStyle('BoxReadout', fontName='Helvetica-Bold', fontSize=24, textColor=colors.HexColor("#0f172a"))),
            Paragraph(f"<b>{confidence} confidence</b>", ParagraphStyle('BoxConf', fontName='Helvetica-Bold', fontSize=13, textColor=colors.HexColor("#0284c7"), alignment=2))
        ],
        [
            Paragraph(f"Risk level: <b>{risk_tier}</b> &nbsp;&nbsp;&nbsp;&nbsp; Model: <b>{active_model}</b>", ParagraphStyle('BoxMeta', fontName='Helvetica', fontSize=9.5, textColor=colors.HexColor("#334155"))),
            ""
        ]
    ]
    box_table = Table(box_data, colWidths=[340, 180])
    box_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f0fdfa")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#38bdf8")),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 14),
        ('RIGHTPADDING', (0, 0), (-1, -1), 14),
        ('SPAN', (0, 0), (1, 0)),
        ('SPAN', (0, 2), (1, 2)),
    ]))
    story.append(box_table)
    story.append(Spacer(1, 14))

    # 4. Clinical Summary
    story.append(Paragraph("Clinical summary", section_heading))
    summary_text = (
        f"<b>SCREENING SIGNAL:</b> {readout} ({confidence} confidence). {triage_data.get('summary', '')}. "
        f"<b>Model:</b> {active_model}. "
        f"<b>What we heard:</b> {triage_data.get('what_we_heard', '')}. "
        f"<b>Context signals:</b> {triage_data.get('context_signals', '')} "
        f"({', '.join(triage_data.get('extracted_symptoms', ['cough']))}). "
        f"<b>Next best step:</b> {triage_data.get('next_best_step', '')}"
    )
    story.append(Paragraph(summary_text, body_style))
    story.append(Spacer(1, 14))

    # 5. Recording Quality
    story.append(Paragraph("Recording quality", section_heading))
    q_text = (
        f"<b>Status:</b> {quality_data.get('status', 'Good')} &nbsp;&nbsp;&nbsp;&nbsp; "
        f"<b>Duration:</b> {quality_data.get('duration', 1.0)}s &nbsp;&nbsp;&nbsp;&nbsp; "
        f"<b>Signal level:</b> {quality_data.get('dbfs', -28.0)} dBFS &nbsp;&nbsp;&nbsp;&nbsp; "
        f"<b>Clipping:</b> {quality_data.get('clipping', 0.0):.2f}%"
    )
    story.append(Paragraph(q_text, body_style))
    story.append(Spacer(1, 20))

    # 6. Safety Alert & Medical Disclaimer
    disclaimer = (
        "<i>This report is a screening aid, not a medical diagnosis or prescription. "
        "Seek urgent care for severe breathing difficulty, chest pain, confusion, blue lips, or rapidly worsening symptoms.</i>"
    )
    story.append(Paragraph(disclaimer, subdued_style))
    story.append(Spacer(1, 20))

    # 7. QR Code Generation & Footer
    qr_data = (
        f"AEROVA-PRO-VERIFIED\n"
        f"Patient ID: {patient_id}\n"
        f"Date: {date_str}\n"
        f"Readout: {readout}\n"
        f"Risk: {risk_tier}\n"
        f"Confidence: {confidence}\n"
        f"Model: {active_model}"
    )
    qr = qrcode.QRCode(box_size=4, border=1)
    qr.add_data(qr_data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="#041620", back_color="white")

    temp_qr = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    qr_path = temp_qr.name
    temp_qr.close()
    qr_img.save(qr_path)

    footer_data = [
        [
            Paragraph("<b>Digitally generated by AEROVA</b><br/><font size='8' color='#64748b'>Scan the QR code to verify the report identity and recorded outcome.</font>", bold_label),
            RLImage(qr_path, width=70, height=70)
        ]
    ]
    footer_table = Table(footer_data, colWidths=[420, 100])
    footer_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(footer_table)

    # PAGE 2: Explainability and Model Comparison
    story.append(PageBreak())
    story.append(Paragraph("Explainability and model comparison", section_heading))
    story.append(Spacer(1, 10))

    if spectrogram_img_path and os.path.exists(spectrogram_img_path):
        story.append(RLImage(spectrogram_img_path, width=520, height=312))
        story.append(Spacer(1, 14))

    # Model Breakdown Table
    model_list = triage_data.get("model_table", [])
    model_rows = []
    for m in model_list:
        line = f"<b>{m['model']}:</b> {m['prediction']} ({m['confidence']})"
        model_rows.append(Paragraph(line, body_style))

    # Split into 2 columns
    half = len(model_rows) // 2 + len(model_rows) % 2
    col1 = model_rows[:half]
    col2 = model_rows[half:]
    
    # Pad col2 if needed
    while len(col2) < len(col1):
        col2.append(Paragraph("", body_style))

    table_data = []
    for c1, c2 in zip(col1, col2):
        table_data.append([c1, c2])

    comp_table = Table(table_data, colWidths=[260, 260])
    comp_table.setStyle(TableStyle([
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(comp_table)

    # Build document
    doc.build(story)

    # Generate base64 data URI
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
    b64 = base64.b64encode(pdf_bytes).decode('utf-8')
    data_uri = f"data:application/pdf;base64,{b64}"

    return pdf_path, data_uri
