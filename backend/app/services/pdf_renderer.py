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

    brand = _first_value([r"^(.+?)\s+INVOICE", r"^(.+?)\s+PROPOSAL", r"^(.+?)\s+SURAT"], text) or "Kantor Teman"
    client = _first_value([
        r"Ditagihkan Kepada\s+(.+?)\s+Rincian",
        r"Kepada\s+(.+?)\s+Rincian",
        r"Disiapkan Untuk\s+(.+?)\s+Layanan",
    ], text)
    tanggal = _first_value([r"Tanggal:\s+(.+?)(?:\s+Jatuh|\s+Dari|\s+Berlaku|$)"], text)
    due_date = _first_value([r"Jatuh tempo:\s+(.+?)(?:\s+Dari|\s+Ditagihkan|$)", r"Jatuh Tempo:\s+(.+?)(?:\s+Dari|\s+Ditagihkan|$)"], text)
    payment = _first_value([r"Pembayaran\s+(.+?)\s+Ketentuan"], text)
    terms = _first_value([r"Ketentuan\s+(.+?)\s+Catatan", r"Syarat dan Ketentuan\s+(.+?)(?:\s+Demikian|$)"], text)
    note = _first_value([r"Catatan\s+(.+?)\s+Kantor Teman"], text)
    footer = _first_value([r"(Dokumen ini dibuat secara digital\.?)"], text)

    return {
        "text": text,
        "title": title,
        "brand": brand,
        "client": client,
        "tanggal": tanggal,
        "due_date": due_date,
        "payment": payment,
        "terms": terms,
        "note": note,
        "footer": footer,
        "items_table": items_table,
    }


def render_pdf_with_reportlab(rendered_html: str) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

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
    normal = ParagraphStyle("KTNormal", parent=styles["Normal"], fontName="Helvetica", fontSize=9, leading=12, textColor=colors.HexColor("#334155"))
    small = ParagraphStyle("KTSmall", parent=normal, fontSize=8, leading=10, textColor=colors.HexColor("#64748b"))
    table_text = ParagraphStyle("KTTableText", parent=normal, fontSize=7.6, leading=9.2, textColor=colors.HexColor("#334155"))
    table_header = ParagraphStyle("KTTableHeader", parent=table_text, fontName="Helvetica-Bold", fontSize=7.2, leading=8.6, textColor=colors.HexColor("#475569"))
    table_right = ParagraphStyle("KTTableRight", parent=table_text, alignment=TA_RIGHT)
    title = ParagraphStyle("KTTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=22, leading=26, textColor=colors.HexColor("#111827"))
    label = ParagraphStyle("KTLabel", parent=normal, fontName="Helvetica-Bold", fontSize=7, leading=9, textColor=colors.HexColor("#64748b"))
    right_small = ParagraphStyle("KTRightSmall", parent=small, alignment=TA_RIGHT)

    story = []
    header = Table(
        [[
            Paragraph(f"<b>{html_mod.escape(parts['brand'])}</b><br/><font size='18'><b>{html_mod.escape(parts['title'])}</b></font>", title),
            Paragraph(f"Tanggal: <b>{html_mod.escape(parts['tanggal'])}</b><br/>Jatuh tempo: <b>{html_mod.escape(parts['due_date'])}</b>", right_small),
        ]],
        colWidths=[115 * mm, 55 * mm],
    )
    header.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, -1), 1.6, colors.HexColor("#111827")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.extend([header, Spacer(1, 9 * mm)])

    cards = Table(
        [[
            Paragraph(f"<font size='7'><b>DARI</b></font><br/><b>{html_mod.escape(parts['brand'])}</b>", normal),
            Paragraph(f"<font size='7'><b>DITAGIHKAN KEPADA</b></font><br/><b>{html_mod.escape(parts['client'])}</b>", normal),
        ]],
        colWidths=[82 * mm, 82 * mm],
        hAlign="LEFT",
    )
    cards.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#d1d5db")),
        ("INNERGRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#d1d5db")),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("PADDING", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.extend([cards, Spacer(1, 7 * mm)])

    if parts["items_table"]:
        story.append(Paragraph("RINCIAN TAGIHAN", label))
        table_data = []
        for row_idx, row in enumerate(parts["items_table"]):
            rendered_row = []
            for col_idx, cell in enumerate(row):
                style = table_header if row_idx == 0 else table_text
                if row_idx > 0 and col_idx >= 3:
                    style = table_right
                rendered_row.append(Paragraph(html_mod.escape(cell), style))
            table_data.append(rendered_row)
        max_cols = max(len(row) for row in table_data)
        for row in table_data:
            while len(row) < max_cols:
                row.append(Paragraph("", table_text))
        col_widths = [11 * mm, 30 * mm, 61 * mm, 12 * mm, 25 * mm, 29 * mm][:max_cols]
        if len(col_widths) < max_cols:
            col_widths.extend([25 * mm] * (max_cols - len(col_widths)))
        items = Table(table_data, colWidths=col_widths, repeatRows=1)
        items.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#475569")),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#e5e7eb")),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#fffbeb")),
            ("LINEABOVE", (0, -1), (-1, -1), 0.8, colors.HexColor("#f59e0b")),
        ]))
        story.extend([items, Spacer(1, 7 * mm)])

    info = Table(
        [[
            Paragraph(f"<font size='7'><b>PEMBAYARAN</b></font><br/>{html_mod.escape(parts['payment'])}", normal),
            Paragraph(f"<font size='7'><b>KETENTUAN</b></font><br/>{html_mod.escape(parts['terms'])}", normal),
        ]],
        colWidths=[95 * mm, 69 * mm],
        hAlign="LEFT",
    )
    info.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#f59e0b")),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#fde68a")),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fffbeb")),
        ("PADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.extend([info, Spacer(1, 6 * mm)])

    if parts["note"]:
        story.extend([Paragraph("CATATAN", label), Paragraph(html_mod.escape(parts["note"]), small), Spacer(1, 8 * mm)])
    story.append(Paragraph(f"<b>{html_mod.escape(parts['brand'])}</b><br/>{html_mod.escape(parts['footer'] or 'Dokumen ini dibuat secara digital.')}", small))

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
