"""
PI（Proforma Invoice）PDF 生成服务
使用 reportlab 生成，不依赖系统 GTK 库
"""
import os
from decimal import Decimal, InvalidOperation
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    Image,
    HRFlowable,
)
from reportlab.platypus.flowables import KeepTogether
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# 品牌蓝
BRAND_BLUE = colors.HexColor("#1a5276")
LIGHT_BLUE = colors.HexColor("#d6eaf8")
HEADER_BLUE = colors.HexColor("#2471a3")
WHITE = colors.white
GRAY_BORDER = colors.HexColor("#aaaaaa")


def _d(val, decimals=2) -> str:
    if val is None:
        return ""
    try:
        v = Decimal(str(val))
        fmt = f"{{:,.{decimals}f}}"
        return fmt.format(v)
    except (InvalidOperation, Exception):
        return str(val)


def _fmt_date(raw) -> str:
    if not raw:
        return ""
    s = str(raw)[:10]
    parts = s.split("-")
    if len(parts) == 3:
        return f"{parts[0]}.{parts[1]}.{parts[2]}"
    return s


def generate_pi_pdf(quotation, company, is_internal: bool = False) -> bytes:
    buf = BytesIO()

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    normal = ParagraphStyle("normal", fontName="Helvetica", fontSize=9, leading=13)
    normal_bold = ParagraphStyle("normal_bold", fontName="Helvetica-Bold", fontSize=9, leading=13)
    small = ParagraphStyle("small", fontName="Helvetica", fontSize=8, leading=11)
    center = ParagraphStyle("center", fontName="Helvetica", fontSize=9, leading=13, alignment=TA_CENTER)
    center_bold = ParagraphStyle("center_bold", fontName="Helvetica-Bold", fontSize=9, alignment=TA_CENTER)
    title_style = ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=18, leading=22, alignment=TA_CENTER, textColor=BRAND_BLUE, spaceAfter=4)
    co_name_style = ParagraphStyle("co_name", fontName="Helvetica-Bold", fontSize=14, textColor=BRAND_BLUE)
    co_info_style = ParagraphStyle("co_info", fontName="Helvetica", fontSize=8, textColor=colors.HexColor("#444444"), leading=12)
    bank_title_style = ParagraphStyle("bank_title", fontName="Helvetica-Bold", fontSize=9, textColor=BRAND_BLUE)
    footer_style = ParagraphStyle("footer", fontName="Helvetica-Bold", fontSize=16, alignment=TA_CENTER, textColor=BRAND_BLUE)

    W = A4[0] - 30 * mm  # usable width

    # ---- 公司信息 ----
    co_name = (company.name_en if company and company.name_en else "XIMO CO., LIMITED")
    co_addr = (company.address_en if company and company.address_en else "")
    co_email = (company.email if company and company.email else "")
    co_mobile = ((company.mobile or company.phone or "") if company else "")

    # ---- 客户信息 ----
    customer = quotation.customer
    buyer_name = customer.company_name if customer else ""
    buyer_addr = getattr(customer, "address", "") or ""
    buyer_tel = (customer.phone or customer.email or "") if customer else ""

    contact = quotation.contact_person or (quotation.salesperson.full_name if quotation.salesperson else "")

    # ---- 产品行 ----
    items = sorted(quotation.items, key=lambda x: x.sort_order)
    total_qty = sum(Decimal(str(it.quantity)) for it in items)
    total_amount = sum(
        Decimal(str(it.quantity)) * Decimal(str(
            it.unit_price_internal if (is_internal and it.unit_price_internal) else it.unit_price
        ))
        for it in items
    )

    currency = quotation.currency or "USD"
    trade_terms = quotation.trade_terms or ""
    price_col = f"{trade_terms} ({currency}/TON)" if trade_terms else f"UNIT PRICE ({currency}/TON)"

    # ========================
    # 组装内容
    # ========================
    story = []

    # ---- 页眉 ----
    logo_cell = ""
    if company and company.logo_path and os.path.exists(company.logo_path):
        try:
            logo_cell = Image(company.logo_path, width=40 * mm, height=12 * mm)
        except Exception:
            logo_cell = Paragraph(co_name, co_name_style)
    else:
        logo_cell = Paragraph("<b>XIMO</b>", ParagraphStyle("logo_txt", fontName="Helvetica-Bold", fontSize=20, textColor=BRAND_BLUE))

    co_block = [
        Paragraph(co_name, co_name_style),
        Paragraph(f"ADD: {co_addr}", co_info_style),
        Paragraph(f"EMAIL:{co_email}&nbsp;&nbsp;&nbsp;MOBILE: {co_mobile}", co_info_style),
    ]

    header_table = Table(
        [[logo_cell, co_block]],
        colWidths=[45 * mm, W - 45 * mm],
        hAlign="LEFT",
    )
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=2, color=BRAND_BLUE, spaceAfter=4))
    story.append(Spacer(1, 3 * mm))

    # ---- 标题 ----
    title_text = "PROFORMA INVOICE"
    if is_internal:
        title_text += "  [INTERNAL]"
    story.append(Paragraph(title_text, title_style))
    story.append(Spacer(1, 2 * mm))

    # ---- 单号 / 日期 ----
    meta_table = Table(
        [[
            Paragraph(f"INVOICE NO. :  <b>{quotation.pi_number}</b>", normal),
            Paragraph(f"DATE: {_fmt_date(quotation.created_at)}", ParagraphStyle("right", fontName="Helvetica", fontSize=9, alignment=TA_RIGHT)),
        ]],
        colWidths=[W / 2, W / 2],
    )
    meta_table.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 2 * mm))

    # ---- 买卖双方 ----
    parties_data = [f"BUYER:   {buyer_name}"]
    if buyer_addr:
        parties_data.append(f"ADDRESS: {buyer_addr}")
    if buyer_tel:
        parties_data.append(f"TEL: {buyer_tel}")
    parties_data.append("")
    parties_data.append(f"SELLER:   {co_name}")
    parties_data.append(f"ADDRESS: {co_addr}")
    tel_email = co_mobile
    if co_email:
        tel_email += f" ({co_email})"
    parties_data.append(f"TEL/EMAIL: {tel_email}")
    if contact:
        parties_data.append(f"ATTAN:  {contact}")

    for line in parties_data:
        story.append(Paragraph(line if line else "&nbsp;", normal))
    story.append(Spacer(1, 3 * mm))

    # ---- 产品明细表 ----
    item_header1 = [
        Paragraph("ITEM\nNUMBER", center_bold),
        Paragraph("GRADE", center_bold),
        Paragraph("HSCODE", center_bold),
        Paragraph("SIZE\n(MM)", center_bold),
        Paragraph("QTY\n(TON)", center_bold),
        Paragraph(price_col, center_bold),
        Paragraph("TOTAL", center_bold),
    ]

    item_rows = [item_header1]
    for idx, it in enumerate(items, 1):
        price = it.unit_price_internal if (is_internal and it.unit_price_internal) else it.unit_price
        line_total = Decimal(str(it.quantity)) * Decimal(str(price))
        item_rows.append([
            Paragraph(str(idx), center),
            Paragraph(it.grade_label or "", center),
            Paragraph(it.hscode or "", center),
            Paragraph(it.description, center),
            Paragraph(_d(it.quantity, 3), center),
            Paragraph(_d(price, 2), center),
            Paragraph(_d(line_total, 2), center),
        ])

    # 合计行
    item_rows.append([
        Paragraph("TOTAL", center_bold),
        "", "", "",
        Paragraph(_d(total_qty, 3), center_bold),
        "",
        Paragraph(_d(total_amount, 2), center_bold),
    ])

    col_widths = [
        0.08 * W, 0.09 * W, 0.10 * W, 0.32 * W,
        0.12 * W, 0.15 * W, 0.14 * W,
    ]
    items_table = Table(item_rows, colWidths=col_widths, repeatRows=1)
    n_data = len(item_rows)
    items_table.setStyle(TableStyle([
        # 表头
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        # 数据行
        ("FONTSIZE", (0, 1), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.5, GRAY_BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#f0f8ff")]),
        # 合计行
        ("BACKGROUND", (0, n_data - 1), (-1, n_data - 1), LIGHT_BLUE),
        ("FONTNAME", (0, n_data - 1), (-1, n_data - 1), "Helvetica-Bold"),
        ("SPAN", (0, n_data - 1), (3, n_data - 1)),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 3 * mm))

    # ---- Terms & Conditions ----
    tc_items = [
        ("STANDARD/GRADE：", quotation.commodity),
        ("COMMODITY:", quotation.commodity),
        ("ORIGIN :", "CHINA"),
        ("PAYMENT TERM :", quotation.payment_terms),
        ("PACKNING :", quotation.packing or "EXPORT STANDARD"),
        ("PORT OF LOADING:", quotation.port_of_loading),
        ("FOR TRANSPORTATION TO:", quotation.destination_port),
        ("NOTE:", quotation.note_pi),
    ]
    tc_data = [
        [Paragraph("<b>TERMS AND CONDITIONS</b>", ParagraphStyle("tc_h", fontName="Helvetica-Bold", fontSize=9, textColor=WHITE)), ""]
    ]
    for label, val in tc_items:
        if val:
            tc_data.append([
                Paragraph(f"<b>{label}</b>", normal_bold),
                Paragraph(str(val), normal),
            ])

    if len(tc_data) > 1:
        tc_table = Table(tc_data, colWidths=[0.38 * W, 0.62 * W])
        n_tc = len(tc_data)
        tc_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HEADER_BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("SPAN", (0, 0), (-1, 0)),
            ("BACKGROUND", (0, 1), (0, -1), LIGHT_BLUE),
            ("GRID", (0, 0), (-1, -1), 0.5, GRAY_BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(tc_table)
        story.append(Spacer(1, 3 * mm))

    # ---- 银行信息 ----
    if company:
        bank_lines = []
        if company.name_en:
            bank_lines.append(f"1. BENEFICIARY'S NAME: {company.name_en}")
        if company.bank_name_full or company.bank_name:
            bank_lines.append(f"2. BANK INFORMATION : {company.bank_name_full or company.bank_name}")
        if company.bank_code:
            bank_lines.append(f"3. BANK CODE : {company.bank_code}")
        if company.bank_address:
            bank_lines.append(f"4. BANK ADDRESS : {company.bank_address}")
        if company.swift_code:
            bank_lines.append(f"5. SWIFT CODE : {company.swift_code}")
        if company.bank_account:
            bank_lines.append(f"6. BANK ACCOUNT NO. : {company.bank_account}")
        if bank_lines:
            story.append(Paragraph("<b>Bank info:</b>", bank_title_style))
            for line in bank_lines:
                story.append(Paragraph(f"&nbsp;&nbsp;&nbsp;{line}", normal))
            story.append(Spacer(1, 3 * mm))

    # ---- 页脚标语 ----
    tagline_table = Table(
        [[Paragraph("Your reliable partner for steel", footer_style)]],
        colWidths=[W],
    )
    tagline_table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 2, BRAND_BLUE),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(tagline_table)
    story.append(Spacer(1, 8 * mm))

    # ---- 签字栏 ----
    sig_table = Table(
        [[
            "",
            Paragraph(
                f"For and on behalf of<br/><b>{co_name}</b><br/><br/><br/>"
                "...............................<br/>Authorized Signature(s)",
                ParagraphStyle("sig", fontName="Helvetica", fontSize=9, alignment=TA_RIGHT, leading=14),
            ),
        ]],
        colWidths=[W * 0.6, W * 0.4],
    )
    sig_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(sig_table)

    doc.build(story)
    return buf.getvalue()
