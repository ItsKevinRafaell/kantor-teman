"""PDF rendering helpers for document templates.

The production shared host cannot reliably render text through WeasyPrint's
native stack, so xhtml2pdf is the preferred renderer because it is pip-only.
"""
import html as html_mod
import io
import os
import re
from html.parser import HTMLParser
from urllib.parse import urlparse


PDF_FONT_CSS = """
* { font-family: Helvetica, Arial, sans-serif; box-sizing: border-box; }
"""


def visible_text_from_html(rendered_html: str) -> str:
    without_assets = re.sub(r"<(style|script)\b[^>]*>.*?</\1>", " ", rendered_html, flags=re.IGNORECASE | re.DOTALL)
    without_tags = re.sub(r"<[^>]+>", " ", without_assets)
    return " ".join(html_mod.unescape(without_tags).split())


def inject_pdf_font(rendered_html: str) -> str:
    font_tag = f"<style>{PDF_FONT_CSS}</style>"
    if "<head>" in rendered_html:
        return rendered_html.replace("<head>", f"<head>{font_tag}", 1)
    if "<html>" in rendered_html:
        return rendered_html.replace("<html>", f"<html><head>{font_tag}</head>", 1)
    return f"<html><head>{font_tag}</head><body>{rendered_html}</body></html>"


def _pdf_escape_text(text: str) -> str:
    text = (
        text.replace("\u00a0", " ")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
    )
    text = text.encode("latin-1", "replace").decode("latin-1")
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def html_to_pdf_lines(rendered_html: str) -> list[str]:
    text_html = re.sub(r"<(style|script)\b[^>]*>.*?</\1>", " ", rendered_html, flags=re.IGNORECASE | re.DOTALL)
    text_html = re.sub(r"<\s*br\s*/?\s*>", "\n", text_html, flags=re.IGNORECASE)
    text_html = re.sub(r"</\s*(p|div|h[1-6]|tr|section|table|thead|tbody|tfoot)\s*>", "\n", text_html, flags=re.IGNORECASE)
    text_html = re.sub(r"</\s*(td|th)\s*>", " | ", text_html, flags=re.IGNORECASE)
    text = html_mod.unescape(re.sub(r"<[^>]+>", " ", text_html))
    raw_lines = [" ".join(line.split()) for line in text.splitlines()]
    lines: list[str] = []
    for line in raw_lines:
        if not line:
            if lines and lines[-1]:
                lines.append("")
            continue
        while len(line) > 96:
            split_at = line.rfind(" ", 0, 96)
            if split_at < 40:
                split_at = 96
            lines.append(line[:split_at].strip())
            line = line[split_at:].strip()
        lines.append(line)
    return lines or ["Dokumen tidak memiliki teks yang dapat ditampilkan."]


def render_text_fallback_pdf(rendered_html: str) -> bytes:
    lines = html_to_pdf_lines(rendered_html)
    page_width = 595
    page_height = 842
    margin_x = 46
    start_y = 792
    lines_per_page = 55
    pages = [lines[i:i + lines_per_page] for i in range(0, len(lines), lines_per_page)] or [[]]

    objects: list[bytes] = []

    def add_object(data: bytes) -> int:
        objects.append(data)
        return len(objects)

    catalog_id = add_object(b"<< /Type /Catalog /Pages 2 0 R >>")
    pages_id = add_object(b"")
    font_id = add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    page_ids: list[int] = []

    for page_lines in pages:
        content_parts = ["BT", "/F1 10 Tf", f"{margin_x} {start_y} Td", "14 TL"]
        first = True
        for line in page_lines:
            if not first:
                content_parts.append("T*")
            first = False
            if line:
                content_parts.append(f"({_pdf_escape_text(line)}) Tj")
        content_parts.append("ET")
        stream = "\n".join(content_parts).encode("latin-1", "replace")
        content_id = add_object(
            b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream"
        )
        page_id = add_object(
            (
                f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 {page_width} {page_height}] "
                f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>"
            ).encode("ascii")
        )
        page_ids.append(page_id)

    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects[pages_id - 1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode("ascii")

    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")
    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(pdf)


def _is_valid_pdf(pdf: bytes) -> bool:
    return bool(pdf and pdf.startswith(b"%PDF") and len(pdf) >= 1024)


class _TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self._current_table: list[list[str]] | None = None
        self._current_row: list[str] | None = None
        self._current_cell: list[str] | None = None
        self._current_colspan = 1

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == "table":
            self._current_table = []
        elif tag == "tr" and self._current_table is not None:
            self._current_row = []
        elif tag in {"td", "th"} and self._current_row is not None:
            self._current_cell = []
            attrs_dict = dict(attrs)
            try:
                self._current_colspan = max(1, int(attrs_dict.get("colspan", "1")))
            except ValueError:
                self._current_colspan = 1

    def handle_data(self, data):
        if self._current_cell is not None:
            self._current_cell.append(data)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in {"td", "th"} and self._current_cell is not None and self._current_row is not None:
            cell_text = " ".join("".join(self._current_cell).split())
            if self._current_colspan > 1 and cell_text.lower() in {"total", "subtotal", "grand total"}:
                self._current_row.extend([""] * (self._current_colspan - 1))
                self._current_row.append(cell_text)
            else:
                self._current_row.append(cell_text)
                self._current_row.extend([""] * (self._current_colspan - 1))
            self._current_cell = None
            self._current_colspan = 1
        elif tag == "tr" and self._current_row is not None and self._current_table is not None:
            if any(cell for cell in self._current_row):
                self._current_table.append(self._current_row)
            self._current_row = None
        elif tag == "table" and self._current_table is not None:
            if self._current_table:
                self.tables.append(self._current_table)
            self._current_table = None


def _extract_tables(rendered_html: str) -> list[list[list[str]]]:
    parser = _TableParser()
    parser.feed(rendered_html)
    return parser.tables


def _normalize_items_table(table: list[list[str]]) -> list[list[str]]:
    if not table:
        return []
    normalized: list[list[str]] = []
    for row in table:
        cells = [cell.strip() for cell in row]
        if not any(cells):
            continue
        lowered = [cell.lower() for cell in cells]
        if len(cells) == 1 and "tidak ada item" in lowered[0]:
            return [["Keterangan"], [cells[0]]]
        if len(cells) == 2 and lowered[0] in {"total", "subtotal", "grand total"}:
            cells = ["", "", "", "", cells[0], cells[1]]
        elif len(cells) == 6 and lowered[0] in {"total", "subtotal", "grand total"}:
            cells = ["", "", "", "", cells[0], cells[-1]]
        elif len(cells) > 6:
            cells = cells[:5] + [" ".join(cells[5:])]
        normalized.append(cells)

    max_cols = max((len(row) for row in normalized), default=0)
    if max_cols <= 0:
        return []
    if max_cols < 6 and any("subtotal" in cell.lower() or "harga" in cell.lower() for row in normalized for cell in row):
        max_cols = 6
    for row in normalized:
        row.extend([""] * (max_cols - len(row)))
    return normalized


def _first_value(patterns: list[str], text: str) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return " ".join(match.group(1).split())
    return ""


def _extract_doc_parts(rendered_html: str) -> dict:
    text = visible_text_from_html(rendered_html)
    tables = _extract_tables(rendered_html)
    items_table = _normalize_items_table(max(tables, key=lambda table: len(table), default=[]))

    title = "DOKUMEN"
    for candidate in (
        r"\b(INVOICE\s+[A-Z0-9/\-]+)",
        r"\b(PROPOSAL PENAWARAN)",
        r"\b(SURAT PENAWARAN)",
        r"\b(BUKTI PEMBAYARAN)",
        r"\b(PERJANJIAN KERJA SAMA)",
    ):
        match = re.search(candidate, text, flags=re.IGNORECASE)
        if match:
            title = match.group(1).upper()
            break

    # Extract invoice number
    invoice_num = _first_value([r"INVOICE\s+(INV[/\-][A-Z0-9/\-]+)", r"(INV[/\-]\d+)"], text) or ""

    brand = _first_value([r"^(.+?)\s+INVOICE", r"^(.+?)\s+PROPOSAL", r"^(.+?)\s+SURAT"], text) or "Teman UMKM Kita"
    client = _first_value([
        r"Ditagihkan Kepada\s+(.+?)\s+Rincian",
        r"Kepada\s+(.+?)\s+Rincian",
        r"Disiapkan Untuk\s+(.+?)\s+Layanan",
    ], text)

    # Extract client contact info (address, phone, email, web)
    client_address = _first_value([r"Alamat:\s*(.+?)(?:\s+Telepon|\s+Email|\s+Website|\s+Rincian|$)"], text)
    client_phone = _first_value([r"(?:Telepon|Phone|Telp)[:\s]+(.+?)(?:\s+Email|\s+Website|\s+Rincian|$)"], text)
    client_email = _first_value([r"(?:Email|E-mail)[:\s]+([^\s]+@[^\s]+)"], text)
    client_web = _first_value([r"(?:Website|Web|URL)[:\s]+(.+?)(?:\s+Rincian|\s+Catatan|$)"], text)

    # Brand contact info (extract from template text)
    brand_address = _first_value([r"(?:Alamat|Company).*?(Indonesia|Malaysia|Singapore|\w+\s+\d{5})"], text)
    brand_phone = _first_value([r"(?:Telepon|Phone|HP).*?(08\d{8,11})"], text)
    brand_email = _first_value([r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"], text)

    tanggal = _first_value([r"Tanggal:\s+(.+?)(?:\s+Jatuh|\s+Dari|\s+Berlaku|$)"], text)
    due_date = _first_value([r"Jatuh tempo:\s+(.+?)(?:\s+Dari|\s+Ditagihkan|$)", r"Jatuh Tempo:\s+(.+?)(?:\s+Dari|\s+Ditagihkan|$)"], text)
    payment = _first_value([r"Pembayaran\s+(.+?)(?:\s+Ketentuan|$)"], text)
    terms = _first_value([r"Ketentuan\s+(.+?)(?:\s+Catatan|\s+Demikian|$)"], text)
    note = _first_value([r"Catatan\s+(.+?)(?:\s+(?:Teman|Dokumen)|$)"], text)
    footer = _first_value([r"(Dokumen ini dibuat secara digital\.?)"], text)

    # Extract total amount from items table
    total_amount = ""
    for row in items_table:
        for cell in row:
            if "total" in cell.lower() and any(c.isdigit() for c in cell):
                total_amount = cell
                break

    return {
        "text": text,
        "title": title,
        "invoice_num": invoice_num,
        "brand": brand or "Teman UMKM Kita",
        "client": client,
        "client_address": client_address,
        "client_phone": client_phone,
        "client_email": client_email,
        "client_web": client_web,
        "brand_address": brand_address or "Indonesia",
        "brand_phone": brand_phone,
        "brand_email": brand_email,
        "tanggal": tanggal,
        "due_date": due_date,
        "payment": payment,
        "terms": terms,
        "note": note,
        "footer": footer,
        "total_amount": total_amount,
        "items_table": items_table,
    }


def render_pdf_with_reportlab(rendered_html: str) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    parts = _extract_doc_parts(rendered_html)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
    )
    styles = getSampleStyleSheet()

    # Style definitions - Indonesian labels
    invoice_title = ParagraphStyle("InvoiceTitle", parent=styles["Normal"], fontName="Helvetica-Bold",
                                    fontSize=28, leading=32, textColor=colors.HexColor("#111827"), alignment=TA_CENTER)
    invoice_num = ParagraphStyle("InvoiceNum", parent=styles["Normal"], fontName="Helvetica",
                                  fontSize=12, leading=16, textColor=colors.HexColor("#374151"), alignment=TA_CENTER)
    section_label = ParagraphStyle("SectionLabel", parent=styles["Normal"], fontName="Helvetica-Bold",
                                    fontSize=7, leading=9, textColor=colors.HexColor("#6b7280"), textTransform="uppercase")
    client_name = ParagraphStyle("ClientName", parent=styles["Normal"], fontName="Helvetica-Bold",
                                  fontSize=11, leading=13, textColor=colors.HexColor("#111827"))
    client_detail = ParagraphStyle("ClientDetail", parent=styles["Normal"], fontName="Helvetica",
                                   fontSize=7.5, leading=9.5, textColor=colors.HexColor("#4b5563"))
    meta_label = ParagraphStyle("MetaLabel", parent=styles["Normal"], fontName="Helvetica",
                                 fontSize=7.5, leading=10, textColor=colors.HexColor("#6b7280"))
    balance_label = ParagraphStyle("BalanceLabel", parent=styles["Normal"], fontName="Helvetica-Bold",
                                    fontSize=8, leading=10, textColor=colors.HexColor("#92400e"))
    balance_amount = ParagraphStyle("BalanceAmount", parent=styles["Normal"], fontName="Helvetica-Bold",
                                    fontSize=13, leading=16, textColor=colors.HexColor("#111827"))
    table_header = ParagraphStyle("TableHeader", parent=styles["Normal"], fontName="Helvetica-Bold",
                                   fontSize=7, leading=8.5, textColor=colors.HexColor("#374151"))
    item_name = ParagraphStyle("ItemName", parent=styles["Normal"], fontName="Helvetica-Bold",
                               fontSize=7.5, leading=9.5, textColor=colors.HexColor("#111827"))
    item_desc = ParagraphStyle("ItemDesc", parent=styles["Normal"], fontName="Helvetica",
                               fontSize=6.5, leading=8, textColor=colors.HexColor("#6b7280"))
    table_right = ParagraphStyle("TableRight", parent=styles["Normal"], fontName="Helvetica",
                                 fontSize=7.5, leading=9, textColor=colors.HexColor("#1f2937"), alignment=TA_RIGHT)
    section_title = ParagraphStyle("SectionTitle", parent=styles["Normal"], fontName="Helvetica-Bold",
                                   fontSize=7.5, leading=9.5, textColor=colors.HexColor("#4b5563"))
    footer_brand = ParagraphStyle("FooterBrand", parent=styles["Normal"], fontName="Helvetica-Bold",
                                   fontSize=9, leading=11, textColor=colors.HexColor("#111827"))
    footer_detail = ParagraphStyle("FooterDetail", parent=styles["Normal"], fontName="Helvetica",
                                    fontSize=7, leading=9, textColor=colors.HexColor("#6b7280"))

    story = []

    # === 1. HEADER: INVOICE + Number (centered) ===
    story.append(Paragraph("INVOICE", invoice_title))
    story.append(Paragraph(f"#{parts.get('invoice_num') or parts.get('title', 'DOKUMEN')}", invoice_num))
    story.append(Spacer(1, 6 * mm))

    # === 2. FROM/TO SECTION (2 columns) ===
    # Left: Ditagihkan Kepada (Bill To)
    bill_to_content = [Paragraph("Ditagihkan Kepada", section_label), Spacer(1, 1 * mm),
                       Paragraph(html_mod.escape(parts["client"]) or "Klien", client_name)]
    if parts.get("client_address"):
        bill_to_content.append(Paragraph(html_mod.escape(parts["client_address"]), client_detail))
    if parts.get("client_phone"):
        bill_to_content.append(Paragraph(html_mod.escape(parts["client_phone"]), client_detail))
    if parts.get("client_email"):
        bill_to_content.append(Paragraph(html_mod.escape(parts["client_email"]), client_detail))
    if parts.get("client_web"):
        bill_to_content.append(Paragraph(html_mod.escape(parts["client_web"]), client_detail))

    # Right: Dari (From)
    from_content = [Paragraph("Dari", section_label), Spacer(1, 1 * mm),
                    Paragraph(html_mod.escape(parts["brand"]) or "Teman UMKM Kita", client_name)]
    if parts.get("brand_address"):
        from_content.append(Paragraph(html_mod.escape(parts["brand_address"]), client_detail))
    if parts.get("brand_phone"):
        from_content.append(Paragraph(html_mod.escape(parts["brand_phone"]), client_detail))
    if parts.get("brand_email"):
        from_content.append(Paragraph(html_mod.escape(parts["brand_email"]), client_detail))

    from_to_table = Table([[bill_to_content, from_content]], colWidths=[85 * mm, 85 * mm])
    from_to_table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#d1d5db")),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("LINEAFTER", (0, 0), (0, -1), 0.5, colors.HexColor("#d1d5db")),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(from_to_table)
    story.append(Spacer(1, 5 * mm))

    # === 3. TANGGAL + SISA TAGIHAN (Date + Balance) ===
    tanggal_row = Table([[
        [Paragraph("Tanggal Invoice:", meta_label),
         Paragraph(html_mod.escape(parts.get("tanggal") or "-"), client_detail),
         Spacer(1, 2 * mm),
         Paragraph("Jatuh Tempo:", meta_label),
         Paragraph(html_mod.escape(parts.get("due_date") or "-"), client_detail)],
        [Paragraph("Sisa Tagihan", balance_label),
         Paragraph(html_mod.escape(parts.get("total_amount") or "IDR 0"), balance_amount)]
    ]], colWidths=[85 * mm, 85 * mm])
    tanggal_row.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    balance_box = Table([[tanggal_row]], colWidths=[170 * mm])
    balance_box.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#f59e0b")),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fffbeb")),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
    ]))
    story.append(balance_box)
    story.append(Spacer(1, 8 * mm))

    # === 4. ITEMS TABLE with description below ===
    if parts["items_table"]:
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#d1d5db")))
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph("Rincian Layanan", section_label))
        story.append(Spacer(1, 2 * mm))

        table_data = []
        for row_idx, row in enumerate(parts["items_table"]):
            if row_idx == 0:  # Header row
                rendered_row = []
                headers = ["#", "Layanan", "Jumlah", "Harga", "Total"]
                for i, h in enumerate(headers[:len(row)]):
                    rendered_row.append(Paragraph(h, table_header))
                while len(rendered_row) < 5:
                    rendered_row.append(Paragraph("", table_header))
                table_data.append(rendered_row)
            else:
                # Item row: name + description stacked, qty, rate, amount
                service_name = row[0] if len(row) > 0 else ""
                description = row[1] if len(row) > 1 else ""
                qty = row[2] if len(row) > 2 else ""
                rate = row[3] if len(row) > 3 else ""
                amount = row[4] if len(row) > 4 else row[-1] if row else ""

                # Build service cell with name + description
                service_cell = [Paragraph(html_mod.escape(service_name), item_name)]
                if description:
                    service_cell.append(Paragraph(html_mod.escape(description[:200]), item_desc))

                row_data = [
                    service_cell,
                    Paragraph(html_mod.escape(qty), table_right),
                    Paragraph(html_mod.escape(rate), table_right),
                    Paragraph(html_mod.escape(amount), table_right),
                ]
                table_data.append(row_data)

        # Column widths: #, Layanan(desc), Jumlah, Harga, Total
        col_widths = [8 * mm, 75 * mm, 18 * mm, 28 * mm, 28 * mm]

        items = Table(table_data, colWidths=col_widths, repeatRows=1)
        items.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5e7eb")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#374151")),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d1d5db")),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#fffbeb")),
            ("LINEABOVE", (0, -1), (-1, -1), 1, colors.HexColor("#f59e0b")),
        ]))
        story.append(items)
        story.append(Spacer(1, 8 * mm))

    # === 5. METODE PEMBAYARAN + SYARAT ===
    if parts.get("payment") or parts.get("terms"):
        payment_table = Table([[
            [Paragraph("Metode Pembayaran", section_title), Spacer(1, 2 * mm),
             Paragraph(html_mod.escape(parts.get("payment") or "-"), client_detail)],
            [Paragraph("Syarat & Ketentuan", section_title), Spacer(1, 2 * mm),
             Paragraph(html_mod.escape(parts.get("terms") or "-"), client_detail)]
        ]], colWidths=[85 * mm, 85 * mm])
        payment_table.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#f59e0b")),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fffbeb")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#fde68a")),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(payment_table)
        story.append(Spacer(1, 8 * mm))

    # === 6. CATATAN ===
    if parts.get("note"):
        story.append(Paragraph("Catatan", section_title))
        story.append(Paragraph(html_mod.escape(parts["note"]), client_detail))
        story.append(Spacer(1, 8 * mm))

    # === 7. FOOTER ===
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#d1d5db")))
    story.append(Spacer(1, 3 * mm))

    footer_table = Table([[
        [Paragraph(html_mod.escape(parts["brand"]) or "Teman UMKM Kita", footer_brand),
         Paragraph(html_mod.escape(parts.get("brand_address") or "Indonesia"), footer_detail),
         Paragraph(html_mod.escape(parts.get("brand_email") or ""), footer_detail)],
        [Paragraph(html_mod.escape(parts.get("footer") or "Dokumen ini dibuat secara digital."), footer_detail)]
    ]], colWidths=[120 * mm, 50 * mm])
    footer_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(footer_table)

    doc.build(story)
    pdf = buffer.getvalue()
    if not _is_valid_pdf(pdf):
        raise RuntimeError("ReportLab menghasilkan PDF invalid")
    return pdf


def _uploads_link_callback(uri: str, _rel: str, uploads_dir: str | None = None) -> str:
    if not uploads_dir:
        return uri
    parsed = urlparse(uri)
    path = parsed.path if parsed.scheme else uri
    marker = "/uploads/"
    if marker not in path:
        return uri
    local_path = os.path.join(uploads_dir, path.split(marker, 1)[1])
    return local_path if os.path.exists(local_path) else uri


def render_pdf_with_xhtml2pdf(rendered_html: str, uploads_dir: str | None = None) -> bytes:
    from xhtml2pdf import pisa

    output = io.BytesIO()
    status = pisa.CreatePDF(
        src=rendered_html,
        dest=output,
        encoding="UTF-8",
        link_callback=lambda uri, rel: _uploads_link_callback(uri, rel, uploads_dir),
    )
    pdf = output.getvalue()
    if status.err or not _is_valid_pdf(pdf):
        raise RuntimeError("xhtml2pdf menghasilkan PDF invalid")
    return pdf


def render_pdf_with_weasyprint(rendered_html: str) -> bytes:
    from weasyprint import HTML

    def _pdf_url_fetcher(_url: str, **_kw):
        return {"string": b"", "mime_type": "text/plain"}

    pdf = HTML(string=rendered_html, url_fetcher=_pdf_url_fetcher).write_pdf()
    if not _is_valid_pdf(pdf):
        raise RuntimeError("WeasyPrint menghasilkan PDF invalid")
    if len(pdf) < int(os.getenv("PDF_BLANK_FALLBACK_MAX_BYTES", "8192")):
        raise RuntimeError("WeasyPrint menghasilkan PDF yang kemungkinan blank")
    return pdf


def render_pdf_from_html(rendered_html: str, uploads_dir: str | None = None) -> bytes:
    if not visible_text_from_html(rendered_html):
        raise ValueError("Template PDF kosong. Isi HTML template terlebih dahulu.")
    if os.getenv("PDF_FORCE_TEXT_FALLBACK", "").lower() == "true":
        return render_text_fallback_pdf(rendered_html)

    rendered_html = inject_pdf_font(rendered_html)
    renderer = os.getenv("PDF_RENDERER", "reportlab").lower()
    if renderer == "weasyprint":
        renderers = ("weasyprint", "reportlab", "xhtml2pdf")
    elif renderer == "xhtml2pdf":
        renderers = ("xhtml2pdf", "reportlab", "weasyprint")
    else:
        renderers = ("reportlab", "xhtml2pdf", "weasyprint")
    for name in renderers:
        try:
            if name == "reportlab":
                return render_pdf_with_reportlab(rendered_html)
            if name == "xhtml2pdf":
                return render_pdf_with_xhtml2pdf(rendered_html, uploads_dir)
            return render_pdf_with_weasyprint(rendered_html)
        except ImportError:
            continue
        except Exception:
            continue
    return render_text_fallback_pdf(rendered_html)
