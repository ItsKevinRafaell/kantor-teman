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


# Shared-host WeasyPrint blank-text root cause (audited 2026-07-21):
# inject_pdf_font used `font-family: "Liberation"` which is NOT installed.
# WeasyPrint then fell back to URW Type1 (Nimbus) and emitted a PDF whose
# CMap rendered blank in browsers (Ctrl+A shows "TEMAN TEMAN / No. No.").
# Previous fix only used DejaVuSans normal; bold tags got synthetic-bold
# from the same normal TTF → letter-spacing collapsed (L AYANAN).
# Fix: embed real TTFs via @font-face file:// (normal + bold at minimum).

_DOC_FONT_MAP = {
    "normal": (
        "DejaVuSans.ttf",
        "LiberationSans-Regular.ttf",
    ),
    "bold": (
        "DejaVuSans-Bold.ttf",
        "LiberationSans-Bold.ttf",
        "DejaVuSans-Bold.ttf",  # second chance after liberation probe fails
    ),
    "italic": (
        "DejaVuSans-Oblique.ttf",
        "LiberationSans-Italic.ttf",
    ),
    "bold_italic": (
        "DejaVuSans-BoldOblique.ttf",
        "LiberationSans-BoldItalic.ttf",
    ),
}

_UPLOADS_CANDIDATE_DIRS = (
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads"),
    "/home/qqwtlphb/backend/uploads",
)


def _resolve_uploads_path(uri: str, uploads_dir: str | None = None) -> str | None:
    """Map '/uploads/<rel>' (atau URL eksternal berpath /uploads/) ke file lokal.

    Return path file di disk kalau ketemu, selain itu None. Guard traversal:
    hasil normpath harus tetap di dalam base dir (pola sama dengan
    _rewrite_uploads_to_file_urls).
    """
    if not uri:
        return None
    parsed = urlparse(uri)
    path = parsed.path if parsed.scheme else uri
    marker = "/uploads/"
    if marker not in path:
        return None
    rel = path.split(marker, 1)[1].split("?", 1)[0].split("#", 1)[0]
    bases = ([uploads_dir] if uploads_dir else []) + list(_UPLOADS_CANDIDATE_DIRS)
    for base in bases:
        if not base:
            continue
        local = os.path.normpath(os.path.join(base, rel))
        real_base = os.path.realpath(base)
        real_local = os.path.realpath(local)
        if not real_local.startswith(real_base + os.sep):
            continue
        if os.path.isfile(real_local):
            return real_local
    return None

_SYSTEM_FALLBACK_TTFS = (
    "/usr/share/fonts/google-droid-sans-fonts/DroidSansFallbackFull.ttf",
)


def _find_ttf_in_uploads(names: tuple[str, ...]) -> str | None:
    for directory in _UPLOADS_CANDIDATE_DIRS:
        for name in names:
            path = os.path.join(directory, name)
            if os.path.isfile(path):
                return os.path.realpath(path)
    return None


def _resolve_doc_fonts() -> dict[str, str]:
    found: dict[str, str] = {}
    for variant, names in _DOC_FONT_MAP.items():
        path = _find_ttf_in_uploads(names)
        if path:
            found[variant] = path
    # System fallbacks — at least we have DejaVu/Liberation regular on most images,
    # but we already checked there. Special case: if no bold, reuse normal rather
    # than falling back to fake bold (synthetic) which breaks spacing.
    if "normal" not in found:
        for sys_path in _SYSTEM_FALLBACK_TTFS:
            if os.path.isfile(sys_path):
                found["normal"] = os.path.realpath(sys_path)
                break
    if "bold" not in found and "normal" in found:
        found["bold"] = found["normal"]
    return found


def _pdf_font_css() -> str:
    fonts = _resolve_doc_fonts()
    if not fonts.get("normal"):
        return "* { font-family: Helvetica, Arial, sans-serif; box-sizing: border-box; }"

    def _face(weight: str, style: str, path: str | None) -> str:
        if not path or not os.path.isfile(path):
            return ""
        uri = "file://" + path
        bold_kw = f"font-weight: {weight};" if weight in ("bold", "normal") else ""
        italic_kw = f"font-style: {style};" if style in ("italic", "normal") else ""
        return f'@font-face {{ font-family: "DocFont"; src: url("{uri}") format("truetype"); {bold_kw} {italic_kw} }}'

    # Always emit normal; fallback bold to normal if bold file missing.
    faces: list[str] = []
    n = fonts.get("normal")
    b = fonts.get("bold") or n
    i = fonts.get("italic")
    bi = fonts.get("bold_italic") or b

    faces.append(_face("normal", "normal", n))
    faces.append(_face("bold", "normal", b))
    if i:
        faces.append(_face("normal", "italic", i))
    if bi:
        faces.append(_face("bold", "italic", bi))

    faces_css = "\n".join(f for f in faces if f)
    # Inject once, but with strong override so template font-family:Helvetica etc
    # does NOT win over embedded font (previous attempt had font-family in template
    # CSS at 10.5pt which overrode inject because WeasyPrint's cascade favored later style).
    return (
        faces_css
        + "\n"
        + "html, body, table, td, th, div, span, p, h1, h2, h3, b, strong, i, em { "
        + 'font-family: "DocFont", Helvetica, Arial, sans-serif !important; '
        + "box-sizing: border-box; "
        + "}\n"
    )


# Back-compat — some callers imported _resolve_doc_font_path
def _resolve_doc_font_path() -> str | None:
    return _resolve_doc_fonts().get("normal")


def visible_text_from_html(rendered_html: str) -> str:
    without_assets = re.sub(r"<(style|script)\b[^>]*>.*?</\1>", " ", rendered_html, flags=re.IGNORECASE | re.DOTALL)
    without_tags = re.sub(r"<[^>]+>", " ", without_assets)
    return " ".join(html_mod.unescape(without_tags).split())


def inject_pdf_font(rendered_html: str) -> str:
    font_tag = f"<style>{_pdf_font_css()}</style>"
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
    # Note: Helvetica Type1 is always available as PDF built-in - OK for text fallback
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
        elif tag in {"br", "div", "p"} and self._current_cell is not None:
            self._current_cell.append("\n")

    def handle_data(self, data):
        if self._current_cell is not None:
            self._current_cell.append(data)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in {"td", "th"} and self._current_cell is not None and self._current_row is not None:
            raw_text = "".join(self._current_cell)
            cell_text = "\n".join(" ".join(part.split()) for part in raw_text.splitlines() if " ".join(part.split()))
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
        elif tag in {"div", "p"} and self._current_cell is not None:
            self._current_cell.append("\n")


def _extract_tables(rendered_html: str) -> list[list[list[str]]]:
    parser = _TableParser()
    parser.feed(rendered_html)
    return parser.tables


def _text_lines_from_html(rendered_html: str) -> list[str]:
    text_html = re.sub(r"<(style|script)\b[^>]*>.*?</\1>", " ", rendered_html, flags=re.IGNORECASE | re.DOTALL)
    text_html = re.sub(r"<\s*br\s*/?\s*>", "\n", text_html, flags=re.IGNORECASE)
    text_html = re.sub(
        r"</\s*(p|div|h[1-6]|tr|td|th|section|table|thead|tbody|tfoot|li)\s*>",
        "\n",
        text_html,
        flags=re.IGNORECASE,
    )
    text = html_mod.unescape(re.sub(r"<[^>]+>", " ", text_html))
    return [" ".join(line.split()) for line in text.splitlines() if " ".join(line.split())]


def _section_lines(lines: list[str], start_labels: set[str], end_labels: set[str]) -> list[str]:
    start_idx = None
    normalized_starts = {label.lower() for label in start_labels}
    normalized_ends = {label.lower() for label in end_labels}
    for idx, line in enumerate(lines):
        if line.strip().lower() in normalized_starts:
            start_idx = idx + 1
            break
    if start_idx is None:
        return []
    end_idx = len(lines)
    for idx in range(start_idx, len(lines)):
        lowered = lines[idx].strip().lower()
        if lowered in normalized_ends:
            end_idx = idx
            break
    return [line for line in lines[start_idx:end_idx] if line.strip()]


def _clean_label_value(value: str) -> str:
    value = re.sub(r"^\s*\d+[\.\)]\s*", "", value or "").strip()
    value = re.sub(r"^\s*(?:tanggal|jatuh\s+tempo|due\s+date)\s*:\s*", "", value, flags=re.IGNORECASE).strip()
    return value


def _clean_date_value(value: str) -> str:
    value = _clean_label_value(value)
    return re.sub(r"\s*[·|]\s*$", "", value).strip()


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


def _extract_doc_parts(rendered_html: str, template_type: str | None = None) -> dict:
    text = visible_text_from_html(rendered_html)
    lines = _text_lines_from_html(rendered_html)
    line_text = "\n".join(lines)
    tables = _extract_tables(rendered_html)
    items_table = _normalize_items_table(max(tables, key=lambda table: len(table), default=[]))

    # Extract logo URL from rendered HTML
    logo_url = ""
    logo_match = re.search(r'<img[^>]+src="([^"]+)"', rendered_html)
    if logo_match:
        logo_url = logo_match.group(1)

    title = "DOKUMEN"
    # Use re.search with word boundaries, but scope to a bounded prefix (first 400
    # chars) so template body clauses that happen to contain "INVOICE ATAU..."
    # don't override the real title in the header.
    head = (text or "")[:400]
    for candidate in (
        r"\b(PERJANJIAN KERJA SAMA\s+[—\-]\s*WEB\s*DEV)\b",
        r"\b(PERJANJIAN KERJA SAMA\s+[—\-]\s*SEO)\b",
        r"\b(PERJANJIAN KERJA SAMA\s+[—\-]\s*SOSMED)\b",
        r"\b(PERJANJIAN KERJA SAMA\s+[—\-]\s*MAINTENANCE)\b",
        r"\b(PERJANJIAN KERJA SAMA\s+[—\-]\s*BRANDING)\b",
        r"\b(PERJANJIAN KERJA SAMA\s+[—\-]\s*RETAINER)\b",
        r"\b(PERJANJIAN KERJA SAMA)\b(?!\s+[—\-])",
        r"\b(LAMPIRAN KONTRAK\s+[—\-]\s*WEB\s*DEV)\b",
        r"\b(LAMPIRAN KONTRAK\s+[—\-]\s*SEO)\b",
        r"\b(LAMPIRAN KONTRAK\s+[—\-]\s*SOSMED)\b",
        r"\b(LAMPIRAN KONTRAK\s+[—\-]\s*MAINTENANCE)\b",
        r"\b(LAMPIRAN KONTRAK\s+[—\-]\s*BRANDING)\b",
        r"\b(LAMPIRAN KONTRAK\s+[—\-]\s*RETAINER)\b",
        r"\b(LAMPIRAN KONTRAK)\b(?!\s+[—\-])",
        r"\b(MEMORANDUM OF UNDERSTANDING)\b",
        r"\b(MOU)(?!\w)",
        r"\b(INVOICE\s+[A-Z0-9/\-]+)(?!\w)",
        r"\b(PROPOSAL PENAWARAN)(?!\w)",
        r"\b(SURAT PENAWARAN)(?!\w)",
        r"\b(BUKTI PEMBAYARAN)(?!\w)",
    ):
        match = re.search(candidate, head, flags=re.IGNORECASE)
        if match:
            title = match.group(1).upper().strip()
            break

    # Normalize MOU title variant to canonical "MOU" so _TITLE_TO_DOC_TYPE matches.
    if title.startswith("MEMORANDUM OF UNDERSTANDING"):
        title = "MOU"
    # Normalize LAMPIRAN KONTRAK variants so title maps to PERJANJIAN KERJA SAMA
    # family in _TITLE_TO_DOC_TYPE (this generic fallback then matches the right
    # subtype via the prefix logic below using the template type if available).
    if title == "LAMPIRAN KONTRAK":
        title = "PERJANJIAN KERJA SAMA"

    # Extract document number (supports all document types)
    invoice_num = _first_value([r"INVOICE\s+(INV[/\-][A-Z0-9/\-]+)", r"(INV[/\-]\d+)"], text) or ""
    doc_number = _first_value(
        [r"(?:No\.?\s*)?((?:PROP|SP|RCPT|MOU|KONTRAK|KTR|INV)[/\-][A-Z0-9/\-]+)"],
        text,
    ) or invoice_num

    # Derive document type from title. Use EXACT match first; fall back to prefix
    # match (longest-prefix-first) only if no exact match. Substring matching
    # (`title_key in title`) caused `kontrak` to incorrectly resolve to
    # `kontrak_maintenance` because "PERJANJIAN KERJA SAMA" is a substring of
    # all variants.
    _TITLE_TO_DOC_TYPE = {
        "INVOICE": "invoice",
        "PROPOSAL PENAWARAN": "proposal_pdf",
        "SURAT PENAWARAN": "surat_penawaran",
        "BUKTI PEMBAYARAN": "receipt",
        "PERJANJIAN KERJA SAMA — WEB DEV": "kontrak_web_dev",
        "PERJANJIAN KERJA SAMA — SEO": "kontrak_seo",
        "PERJANJIAN KERJA SAMA — SOSMED": "kontrak_sosmed",
        "PERJANJIAN KERJA SAMA — MAINTENANCE": "kontrak_maintenance",
        "PERJANJIAN KERJA SAMA — BRANDING": "kontrak_branding",
        "PERJANJIAN KERJA SAMA — RETAINER": "kontrak_retainer",
        "PERJANJIAN KERJA SAMA": "kontrak",
        "MOU": "mou",
    }
    doc_type = "invoice"
    # Step 1: exact match wins immediately.
    if title in _TITLE_TO_DOC_TYPE:
        doc_type = _TITLE_TO_DOC_TYPE[title]
    else:
        # Step 2: prefix-match (longest title key whose start matches `title` start).
        # This avoids "PERJANJIAN KERJA SAMA — MAINTENANCE" swallowing a generic
        # `PERJANJIAN KERJA SAMA` because of substring greediness.
        best_key = None
        for title_key in sorted(_TITLE_TO_DOC_TYPE.keys(), key=len, reverse=True):
            if title.startswith(title_key):
                best_key = title_key
                break
        # Step 3: prefix in the other direction (title is prefix of key) for short titles like "MOU" before "MOU / foo".
        if not best_key:
            for title_key in sorted(_TITLE_TO_DOC_TYPE.keys(), key=len, reverse=True):
                if title_key.startswith(title):
                    best_key = title_key
                    break
        if best_key:
            doc_type = _TITLE_TO_DOC_TYPE[best_key]  # type: ignore[index]  # noqa

    # Trust template_type when it's specific and title-derived detection is generic.
    # Templates like "Kontrak — Website Development" render title "LAMPIRAN KONTRAK"
    # which normalizes to generic "PERJANJIAN KERJA SAMA" → lost the subtype. Recover
    # by checking the template_type passed in: if template_type is a kontrak_*
    # subtype, use that instead of the generic "kontrak" detection.
    if template_type and template_type in _TITLE_TO_DOC_TYPE.values():
        type_to_title = {v: k for k, v in _TITLE_TO_DOC_TYPE.items()}
        expected_title_prefix = type_to_title.get(template_type, "")
        # Only override if expected_title_prefix is more specific than the derived
        # title's family. If the template type is the generic "kontrak" and the
        # derived family is also kontrak, no override needed.
        if expected_title_prefix and len(expected_title_prefix) > len(type_to_title.get(doc_type, "")):
            doc_type = template_type

    section_end_labels = {
        "ditagihkan kepada", "kepada", "rincian tagihan", "rincian layanan",
        "rincian investasi", "layanan yang ditawarkan", "pembayaran",
        "metode pembayaran", "syarat & ketentuan", "ketentuan", "catatan",
    }
    # Provider brand may appear under "Penyedia Jasa", "Dari", "Pihak Pertama -
    # Penyedia Jasa" (or the client-equivalent "Pihak Kedua - Klien") depending
    # on the template. Compound labels with surrounding "Pihak Pertama -" text
    # are included so Kontrak/MoU templates that use that wording don't fall back
    # to the signature block at the bottom of the page.
    brand_details = _section_lines(
        lines,
        {
            "Dari", "DARI",
            "Penyedia Jasa", "PENYEDIA JASA",
            "Pihak Pertama - Penyedia Jasa",
            "Pihak Pertama - Penyedia Layanan",
            "Pihak Pertama",
        },
        section_end_labels,
    )
    client_details = _section_lines(
        lines,
        {"Ditagihkan Kepada", "Kepada", "Disiapkan Untuk"},
        section_end_labels - {"ditagihkan kepada", "kepada"},
    )

    brand = _clean_label_value(brand_details[0]) if brand_details else ""
    # Reject role-label values like "Pihak Kedua," that come from later signature
    # blocks when the section parser matched the wrong "Penyedia Jasa" label.
    if brand and re.match(r"^\s*(Pihak Pertama|Pihak Kedua|Pihak Ketiga|Klien|Nama)", brand, flags=re.IGNORECASE):
        brand = ""
    if not brand:
        brand = _first_value(
            [r"(?:Dari|Penyedia Jasa)\s+(.+?)(?:\s+(?:Ditagihkan Kepada|Kepada|Rincian|Layanan|Tanggal|$))"],
            line_text,
        )
    if not brand:
        # Fallback: pick first line after a "Penyedia Jasa" / "Dari" / "Pihak Pertama"
        # label that looks like a brand name (skip role labels, skip lines with
        # commas or placeholders).
        labels = {
            "penyedia jasa", "dari",
            "pihak pertama - penyedia jasa", "pihak pertama – penyedia jasa",
            "pihak pertama", "pihak pertama -",
        }
        role_words = {"pihak pertama", "pihak kedua", "pihak ketiga",
                      "penyedia jasa", "klien", "dari", "kepada"}
        for i, line in enumerate(lines[:60]):
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.lower() in labels:
                for j in range(i + 1, min(i + 5, len(lines))):
                    nxt = lines[j].strip()
                    if not nxt:
                        continue
                    if "{" in nxt:  # unsubstituted placeholder
                        continue
                    low = nxt.lower()
                    if low in role_words:
                        continue
                    if low.endswith(",") or low.endswith(":"):
                        # Part of a "Pihak Pertama," / "Klien:" header — skip past
                        # the trailing role label and grab the next line if it
                        # looks like a name.
                        for k in range(j + 1, min(j + 5, len(lines))):
                            nxt2 = lines[k].strip()
                            if not nxt2 or "{" in nxt2:
                                continue
                            if nxt2.lower() in role_words:
                                continue
                            if 2 <= len(nxt2) <= 80:
                                brand = nxt2
                                break
                        if brand:
                            break
                        continue
                    if 2 <= len(nxt) <= 80:
                        brand = nxt
                        break
                if brand:
                    break
    if not brand:
        brand = "Kantor Teman"
    client = _clean_label_value(client_details[0]) if client_details else ""
    if not client:
        client = _first_value([r"(?:Ditagihkan Kepada|Kepada)\s+(.+?)(?:\s+(?:Rincian|Layanan|Pembayaran|$))"], line_text)

    brand_contact_lines = brand_details[1:] if len(brand_details) > 1 else []
    client_contact_lines = client_details[1:] if len(client_details) > 1 else []

    # Extract client contact info
    client_address = ""
    client_phone = ""
    client_email = ""
    client_web = ""

    for detail in client_contact_lines:
        detail_clean = detail.strip()
        # Phone pattern
        phone_match = re.search(r"(?:08\d{8,12}|\+62\d{9,12})", detail_clean)
        if phone_match and not client_phone:
            client_phone = phone_match.group(0)
        # Email pattern
        email_match = re.search(r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", detail_clean)
        if email_match and not client_email:
            client_email = email_match.group(1)
        # Web pattern
        web_match = re.search(r"(?:www\.[^\s]+|https?://[^\s]+)", detail_clean)
        if web_match and not client_web:
            client_web = web_match.group(0)
        # Address (remaining text that looks like address)
        if not client_address and not phone_match and not email_match and not web_match:
            if any(x in detail_clean for x in ["Jl", "Jalan", "No", "RT", "RW", "Kota", "Kabupaten"]):
                client_address = detail_clean

    # Brand contact info
    brand_address = ""
    brand_phone = ""
    brand_email = ""

    for detail in brand_contact_lines:
        phone_match = re.search(r"(?:08\d{8,12}|\+62\d{9,12})", detail)
        if phone_match and not brand_phone:
            brand_phone = phone_match.group(0)
        email_match = re.search(r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", detail)
        if email_match and not brand_email:
            brand_email = email_match.group(1)
        if not brand_address and not phone_match and not email_match:
            brand_address = detail

    # Dates
    tanggal = _clean_date_value(_first_value([r"Tanggal[:\s]+(.+?)(?:\s+[·|]\s*Jatuh|\s+Jatuh|\s+Dari|\s+Berlaku|$)"], text))
    due_date = _clean_date_value(_first_value([r"Jatuh\s+Tempo[:\s]+(.+?)(?:\s+Dari|\s+Ditagihkan|\s+Kepada|$)"], text))

    # Payment and terms
    payment = _first_value([r"Pembayaran\s+(.+?)(?:\s+Ketentuan|$)"], text)
    terms = _first_value([r"Ketentuan\s+(.+?)(?:\s+Catatan|\s+Demikian|$)"], text)
    note = _first_value([r"Catatan\s+(.+?)(?:\s+(?:Teman|Dokumen)|$)"], text)
    footer = _first_value([r"(Dokumen ini dibuat secara digital\.?)"], text)

    # Extract total amount - look in last row for "Total" keyword
    total_amount = ""
    for row in items_table:
        row_text = " ".join(row).lower()
        if "total" in row_text:
            # Get the last non-empty cell with numbers
            for cell in reversed(row):
                if any(c.isdigit() for c in cell):
                    total_amount = cell.strip()
                    break

    return {
        "text": text,
        "logo_url": logo_url,
        "title": title,
        "doc_type": doc_type,
        "doc_number": doc_number,
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


def render_pdf_with_reportlab(rendered_html: str, template_type: str | None = None, uploads_dir: str | None = None) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader
    from reportlab.platypus import HRFlowable, Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    _DEJAVU_TTF = "/home/qqwtlphb/backend/uploads/DejaVuSans.ttf"
    if os.path.exists(_DEJAVU_TTF):
        pdfmetrics.registerFont(TTFont("DejaVu", _DEJAVU_TTF))
        pdfmetrics.registerFontFamily("DejaVu", normal="DejaVu", bold="DejaVu", italic="DejaVu", boldItalic="DejaVu")
        _BODY_FONT = "DejaVu"
        _BOLD_FONT = "DejaVu"
    else:
        _BODY_FONT = "Helvetica"
        _BOLD_FONT = "Helvetica-Bold"

    def _resolve_asset(uri: str) -> str:
        if os.path.isabs(uri) and os.path.exists(uri):
            return uri
        if uploads_dir:
            parsed = urlparse(uri)
            path = parsed.path if parsed.scheme else uri
            marker = "/uploads/"
            if marker in path:
                local = os.path.normpath(os.path.join(uploads_dir, path.split(marker, 1)[1]))
                real = os.path.realpath(uploads_dir)
                if local.startswith(real + os.sep) and os.path.exists(local):
                    return local
        return uri

    parts = _extract_doc_parts(rendered_html, template_type=template_type)
    # ReportLab is invoice/proposal-shaped. Client reports ("Laporan ...") are
    # rich HTML/CSS with embedded screenshots — let them fall through to WeasyPrint
    # (which supports <img>, tables, flex CSS). Without this, reportlab renders a
    # tiny valid-but-empty PDF and the chain never reaches weasyprint → images blank.
    # NB: parts["title"] is invoice-derived (defaults to "DOKUMEN", only matches
    # INVOICE/PROPOSAL/etc), so it never equals "LAPORAN". Detect reports via the
    # visible text (the report <h1> is "Laporan Klien ...").
    visible = (parts.get("text") or "").upper()
    if "LAPORAN" in visible and "LAPORAN" not in (parts.get("title") or "").upper():
        raise NotImplementedError("Laporan klien ditangani WeasyPrint, bukan ReportLab")

    # Contract/MoU-aware rendering: contracts use Tanggal Mulai/Selesai,
    # invoices use Tanggal Invoice/Jatuh Tempo. Detect once, reuse below.
    _CONTRACT_TYPES = {
        "kontrak", "kontrak_web_dev", "kontrak_seo", "kontrak_sosmed",
        "kontrak_maintenance", "kontrak_branding", "kontrak_retainer", "mou",
    }
    doc_type = parts.get("doc_type", "invoice")
    is_contract = doc_type in _CONTRACT_TYPES

    # Extract contract dates from rendered HTML (case-insensitive search on `visible`).
    # Source label "Tanggal Mulai" / "Tanggal Selesai" appears in templates via
    # `_format_date_id(today)` then `<br/>` joined. We strip the prefix when reading.
    contract_start = ""
    contract_end = ""
    if is_contract:
        contract_start = _first_value(
            [r"Tanggal\s*Mulai[:\s]+(.+?)(?:\s+[·|]\s*Tanggal|\s+Tanggal|$)"],
            parts.get("text") or "",
        ) or _first_value(
            [r"Tanggal\s*Mulai\s+([^·|\n]+)"], parts.get("text") or ""
        )
        contract_end = _first_value(
            [r"Tanggal\s*Selesai[:\s]+(.+?)(?:\s+[·|]\s*|$)"],
            parts.get("text") or "",
        ) or _first_value(
            [r"Tanggal\s*Selesai\s+([^·|\n]+)"], parts.get("text") or ""
        )
        contract_start = _clean_date_value(contract_start)
        contract_end = _clean_date_value(contract_end)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
    )
    doc.title = parts.get("invoice_num") or parts.get("title") or "Kantor Teman Document"
    doc.author = parts.get("brand") or "Kantor Teman"
    doc.creator = "Kantor Teman"
    doc.subject = f"Dokumen untuk {parts.get('client') or 'Klien'}"
    styles = getSampleStyleSheet()
    # Override base Normal style to use our embedded font
    styles["Normal"].fontName = _BODY_FONT

    # Brand colors
    BRAND_PRIMARY = colors.HexColor("#f5a700")
    BRAND_LIGHT = colors.HexColor("#fff7ed")
    DARK_TEXT = colors.HexColor("#1a1a2e")
    BODY_TEXT = colors.HexColor("#374151")
    MUTED_TEXT = colors.HexColor("#6b7280")
    LIGHT_BG = colors.HexColor("#fafafa")

    # Style definitions
    invoice_title = ParagraphStyle("InvoiceTitle", parent=styles["Normal"], fontName=_BOLD_FONT,
                                    fontSize=28, leading=32, textColor=DARK_TEXT, alignment=TA_CENTER)
    invoice_num = ParagraphStyle("InvoiceNum", parent=styles["Normal"], fontName=_BODY_FONT,
                                  fontSize=11, leading=14, textColor=MUTED_TEXT, alignment=TA_CENTER)
    section_label = ParagraphStyle("SectionLabel", parent=styles["Normal"], fontName=_BOLD_FONT,
                                    fontSize=6.5, leading=8, textColor=MUTED_TEXT, textTransform="uppercase")
    contact_name = ParagraphStyle("ContactName", parent=styles["Normal"], fontName=_BOLD_FONT,
                                  fontSize=10, leading=12, textColor=DARK_TEXT)
    contact_detail = ParagraphStyle("ContactDetail", parent=styles["Normal"], fontName=_BODY_FONT,
                                   fontSize=7.5, leading=10, textColor=BODY_TEXT)
    meta_label = ParagraphStyle("MetaLabel", parent=styles["Normal"], fontName=_BODY_FONT,
                                 fontSize=7, leading=9, textColor=MUTED_TEXT, alignment=TA_RIGHT)
    meta_value = ParagraphStyle("MetaValue", parent=styles["Normal"], fontName=_BOLD_FONT,
                                 fontSize=8, leading=10, textColor=DARK_TEXT, alignment=TA_RIGHT)
    total_label = ParagraphStyle("TotalLabel", parent=styles["Normal"], fontName=_BOLD_FONT,
                                  fontSize=9, leading=11, textColor=BRAND_PRIMARY, alignment=TA_RIGHT)
    total_amount_style = ParagraphStyle("TotalAmount", parent=styles["Normal"], fontName=_BOLD_FONT,
                                        fontSize=16, leading=20, textColor=DARK_TEXT, alignment=TA_RIGHT)
    table_header = ParagraphStyle("TableHeader", parent=styles["Normal"], fontName=_BOLD_FONT,
                                   fontSize=7, leading=8.5, textColor=colors.white, alignment=TA_CENTER)
    item_name = ParagraphStyle("ItemName", parent=styles["Normal"], fontName=_BOLD_FONT,
                               fontSize=7.5, leading=9.5, textColor=DARK_TEXT)
    item_desc = ParagraphStyle("ItemDesc", parent=styles["Normal"], fontName=_BODY_FONT,
                               fontSize=6.5, leading=8, textColor=MUTED_TEXT)
    table_right = ParagraphStyle("TableRight", parent=styles["Normal"], fontName=_BODY_FONT,
                                 fontSize=7.5, leading=9, textColor=BODY_TEXT, alignment=TA_RIGHT)
    footer_brand = ParagraphStyle("FooterBrand", parent=styles["Normal"], fontName=_BOLD_FONT,
                                   fontSize=9, leading=11, textColor=DARK_TEXT)
    footer_detail = ParagraphStyle("FooterDetail", parent=styles["Normal"], fontName=_BODY_FONT,
                                    fontSize=7, leading=9, textColor=MUTED_TEXT)

    story = []

    # === 1. TYPE-AWARE HEADER ===
    # doc_type and is_contract already declared above (just after visible-text branch).
    doc_number = parts.get("doc_number") or parts.get("invoice_num") or ""

    # Map doc_type to display title and number prefix
    _DOC_TYPE_DISPLAY = {
        "invoice": ("INVOICE", "#"),
        "proposal_pdf": ("PROPOSAL PENAWARAN", "No."),
        "surat_penawaran": ("SURAT PENAWARAN", "No."),
        "receipt": ("BUKTI PEMBAYARAN", "No."),
        "kontrak": ("PERJANJIAN KERJA SAMA", ""),
        "kontrak_web_dev": ("PERJANJIAN KERJA SAMA — WEB DEV", ""),
        "kontrak_seo": ("PERJANJIAN KERJA SAMA — SEO", ""),
        "kontrak_sosmed": ("PERJANJIAN KERJA SAMA — SOSMED", ""),
        "kontrak_maintenance": ("PERJANJIAN KERJA SAMA — MAINTENANCE", ""),
        "kontrak_branding": ("PERJANJIAN KERJA SAMA — BRANDING", ""),
        "kontrak_retainer": ("PERJANJIAN KERJA SAMA — RETAINER", ""),
        "mou": ("MOU", "No."),
    }
    display_title, number_prefix = _DOC_TYPE_DISPLAY.get(doc_type, ("INVOICE", "#"))

    story.append(Paragraph(display_title, invoice_title))
    if doc_number:
        story.append(Paragraph(f"{number_prefix} {doc_number}", invoice_num))
    story.append(Spacer(1, 3 * mm))

    # Brand accent line
    story.append(HRFlowable(width="100%", thickness=3, color=BRAND_PRIMARY))
    story.append(Spacer(1, 4 * mm))

    # === 2. LOGO + DATES row ===
    logo_img = None
    if parts.get("logo_url"):
        try:
            # Preserve the source aspect ratio. Horizontal logos fit best at
            # about 36 x 14 mm; square brandmarks fit within 22 x 22 mm.
            logo_path = _resolve_asset(parts["logo_url"])
            reader = ImageReader(logo_path)
            src_w, src_h = reader.getSize()
            max_w, max_h = 36 * mm, 14 * mm
            if src_h and src_w / src_h < 1.6:
                max_w, max_h = 22 * mm, 22 * mm
            scale = min(max_w / src_w, max_h / src_h) if src_w and src_h else 1
            logo_img = Image(logo_path, width=src_w * scale, height=src_h * scale)
        except Exception:
            logo_img = None

    # Logo placeholder if no logo (orange square with brand initial)
    if not logo_img:
        logo_placeholder = Table([[
            Paragraph("T", ParagraphStyle("LogoText", fontName=_BOLD_FONT, fontSize=16,
                                           textColor=colors.white, alignment=TA_CENTER))
        ]], colWidths=[35 * mm], rowHeights=[25 * mm])
        logo_placeholder.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), BRAND_PRIMARY),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))
        logo_img = logo_placeholder

    # Dates section - right aligned, label and value close together.
    # Branch: contracts/MoU use Tanggal Mulai / Tanggal Selesai; invoices use
    # Tanggal Invoice / Jatuh Tempo.
    if is_contract:
        dates_content = [
            [Paragraph("Tanggal Mulai", meta_label), Paragraph(contract_start or "-", meta_value)],
            [Paragraph("Tanggal Selesai", meta_label), Paragraph(contract_end or "-", meta_value)],
        ]
    else:
        tanggal_val = parts.get("tanggal") or "-"
        due_date_val = parts.get("due_date") or "-"
        dates_content = [
            [Paragraph("Tanggal Invoice", meta_label), Paragraph(tanggal_val, meta_value)],
            [Paragraph("Jatuh Tempo", meta_label), Paragraph(due_date_val, meta_value)],
        ]
    dates_table = Table(dates_content, colWidths=[27 * mm, 43 * mm], hAlign="RIGHT")
    dates_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    # Header row: logo left, dates right
    header_row = Table([[logo_img, dates_table]], colWidths=[45 * mm, 125 * mm])
    header_row.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(header_row)
    story.append(Spacer(1, 6 * mm))

    # === 3. FROM/TO SECTION (Dari left, Ditagihkan Kepada right) ===
    # Left: Dari (brand info)
    dari_content = [Paragraph("Dari", section_label), Spacer(1, 2 * mm),
                    Paragraph(html_mod.escape(parts["brand"]) or "Teman UMKM Kita", contact_name)]
    if parts.get("brand_address"):
        dari_content.append(Paragraph(html_mod.escape(parts["brand_address"]), contact_detail))
    if parts.get("brand_phone"):
        dari_content.append(Paragraph(html_mod.escape(parts["brand_phone"]), contact_detail))
    if parts.get("brand_email"):
        dari_content.append(Paragraph(html_mod.escape(parts["brand_email"]), contact_detail))

    # Right: Ditagihkan Kepada (client info)
    kepada_content = [Paragraph("Ditagihkan Kepada", section_label), Spacer(1, 2 * mm),
                      Paragraph(html_mod.escape(parts["client"]) or "Klien", contact_name)]
    if parts.get("client_address"):
        kepada_content.append(Paragraph(html_mod.escape(parts["client_address"]), contact_detail))
    if parts.get("client_phone"):
        kepada_content.append(Paragraph(html_mod.escape(parts["client_phone"]), contact_detail))
    if parts.get("client_email"):
        kepada_content.append(Paragraph(html_mod.escape(parts["client_email"]), contact_detail))
    if parts.get("client_web"):
        kepada_content.append(Paragraph(html_mod.escape(parts["client_web"]), contact_detail))

    from_to = Table([[dari_content, kepada_content]], colWidths=[85 * mm, 85 * mm])
    from_to.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#e5e7eb")),
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
        ("LINEAFTER", (0, 0), (0, -1), 0.5, colors.HexColor("#e5e7eb")),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(from_to)
    story.append(Spacer(1, 8 * mm))

    # === 3b. PASAL KONTRAK / BODY PARAGRAPHS (contracts & MoU) ===
    # Contracts/MoU have long body text (scope, terms, deliverables, pasal-pasal)
    # which ReportLab would otherwise skip because the invoice-shaped story only
    # consumes items_table. Render remaining text lines as wrapped paragraphs.
    if is_contract:
        all_lines = _text_lines_from_html(rendered_html)
        skip_labels = {
            "dari", "ditagihkan kepada", "kepada", "disiapkan untuk",
            "rincian layanan", "rincian tagihan", "rincian investasi",
            "metode pembayaran", "pembayaran", "syarat & ketentuan",
            "ketentuan", "catatan",
        }
        body_lines: list[str] = []
        for line in all_lines:
            stripped = line.strip()
            if not stripped:
                body_lines.append("")
                continue
            if stripped.lower() in skip_labels:
                continue
            # Skip lines that are already shown elsewhere
            low = stripped.lower()
            if any(low.startswith(prefix) for prefix in (
                "tanggal invoice", "jatuh tempo", "tanggal mulai",
                "tanggal selesai", "invoice ", "no.", "no ",
                "dokumen ini dibuat",
            )):
                continue
            # Drop document number line if present
            if re.match(r"^(KONTRAK|INV|RCPT|PROP|SP|MOU)[/\\-]", stripped, flags=re.IGNORECASE):
                continue
            body_lines.append(stripped)
        # Collapse 3+ blank lines into a single break (visual separation only)
        cleaned: list[str] = []
        blank_run = 0
        for ln in body_lines:
            if not ln:
                blank_run += 1
                if blank_run <= 1:
                    cleaned.append(ln)
            else:
                blank_run = 0
                cleaned.append(ln)
        if cleaned:
            story.append(Paragraph(display_title if display_title.upper() != "INVOICE" else "Rincian Kontrak",
                                   section_label))
            story.append(Spacer(1, 3 * mm))
            for ln in cleaned:
                if not ln:
                    story.append(Spacer(1, 2 * mm))
                    continue
                # Truncate very long lines so they wrap (HTML renderer caps at ~96 chars)
                story.append(Paragraph(html_mod.escape(ln[:1200]), contact_detail))
            story.append(Spacer(1, 6 * mm))

    # === 4. ITEMS TABLE ===
    if parts["items_table"]:
        story.append(Paragraph("Rincian Layanan", section_label))
        story.append(Spacer(1, 3 * mm))

        def is_header_row(row: list[str]) -> bool:
            lowered = {cell.strip().lower() for cell in row if cell.strip()}
            return bool(lowered & {"no", "#", "item", "layanan", "deskripsi", "qty", "jumlah", "harga", "subtotal"})

        def map_item_row(row: list[str], header: list[str] | None) -> tuple[str, str, str, str, str]:
            lowered_header = [cell.strip().lower() for cell in (header or [])]
            if lowered_header and len(row) >= len(lowered_header):
                def idx(*names: str) -> int | None:
                    for name in names:
                        if name in lowered_header:
                            return lowered_header.index(name)
                    return None

                service_idx = idx("layanan", "item", "service", "produk") or 0
                desc_idx = idx("deskripsi", "description", "keterangan")
                qty_idx = idx("jumlah", "qty", "kuantitas") or 1
                rate_idx = idx("harga", "rate", "harga satuan") or 2
                amount_idx = idx("subtotal", "total", "amount") or (len(row) - 1)
                return (
                    row[service_idx] if service_idx < len(row) else "",
                    row[desc_idx] if desc_idx is not None and desc_idx < len(row) else "",
                    row[qty_idx] if qty_idx < len(row) else "",
                    row[rate_idx] if rate_idx < len(row) else "",
                    row[amount_idx] if amount_idx < len(row) else "",
                )

            if len(row) >= 6 and re.fullmatch(r"\d+|#|no\.?", row[0].strip(), flags=re.IGNORECASE):
                return row[1], row[2], row[3], row[4], row[5]
            if len(row) >= 5:
                return row[0], row[1], row[2], row[3], row[4]
            if len(row) >= 4:
                return row[0], "", row[1], row[2], row[3]
            return (row[0] if row else "", "", "", "", "")

        source_rows = parts["items_table"]
        header_row = source_rows[0] if source_rows and is_header_row(source_rows[0]) else None
        item_rows = source_rows[1:] if header_row else source_rows
        table_data = [[Paragraph(h, table_header) for h in ["Layanan", "Jumlah", "Harga", "Total"]]]

        for row in item_rows:
            row_text = " ".join(row).lower()
            if "total" in row_text and any(any(ch.isdigit() for ch in cell) for cell in row):
                continue

            service_name, description, qty, rate, amount = map_item_row(row, header_row)
            # If description is empty but service_name has newlines, split it
            if not description and "\n" in service_name:
                service_lines = [line.strip() for line in service_name.splitlines() if line.strip()]
                service_name = service_lines[0] if service_lines else service_name
                description = "\n".join(service_lines[1:])
            # Also check if service_name itself contains feature-like content (bullet points, numbered lists)
            elif description and "\n" not in description and len(service_name.splitlines()) > 1:
                # service_name has multiple lines, keep them
                service_lines = [line.strip() for line in service_name.splitlines() if line.strip()]
                if len(service_lines) > 1:
                    service_name = service_lines[0]
                    # Prepend existing service lines to description
                    extra_desc = "\n".join(service_lines[1:])
                    description = extra_desc + ("\n" + description if description else "")

            service_name = _clean_label_value(service_name)
            description = description.strip()
            service_cell = [Paragraph(html_mod.escape(service_name or "-"), item_name)]
            if description:
                # Convert <br/> and <br> tags to newlines
                desc_clean = description.replace("<br/>", "\n").replace("<br>", "\n")
                # Escape HTML entities
                desc_escaped = html_mod.escape(desc_clean[:500])
                # Convert newlines to <br/> for Paragraph rendering
                desc_final = desc_escaped.replace("\n", "<br/>")
                service_cell.append(Paragraph(desc_final, item_desc))

            table_data.append([
                service_cell,
                Paragraph(html_mod.escape(qty), table_right),
                Paragraph(html_mod.escape(rate), table_right),
                Paragraph(html_mod.escape(amount), table_right),
            ])

        col_widths = [92 * mm, 20 * mm, 34 * mm, 34 * mm]
        items = Table(table_data, colWidths=col_widths, repeatRows=1)
        items.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BRAND_PRIMARY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e5e7eb")),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ]))
        story.append(items)
        story.append(Spacer(1, 6 * mm))

        # === 5. TOTAL TAGIHAN (below items, right aligned) ===
        total_box = Table([[
            [Paragraph("Total Tagihan", total_label), Spacer(1, 2 * mm),
             Paragraph(html_mod.escape(parts.get("total_amount") or "IDR 0"), total_amount_style)]
        ]], colWidths=[80 * mm])
        total_box.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 2, BRAND_PRIMARY),
            ("BACKGROUND", (0, 0), (-1, -1), BRAND_LIGHT),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ]))

        # Wrap in full width table with empty left space
        total_row = Table([["", total_box]], colWidths=[90 * mm, 80 * mm])
        total_row.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(total_row)
        story.append(Spacer(1, 8 * mm))

    # === 6. PAYMENT + TERMS ===
    if parts.get("payment") or parts.get("terms"):
        payment_box = Table([[
            [Paragraph("Metode Pembayaran", section_label), Spacer(1, 2 * mm),
             Paragraph(html_mod.escape(parts.get("payment") or "-"), contact_detail)],
            [Paragraph("Syarat & Ketentuan", section_label), Spacer(1, 2 * mm),
             Paragraph(html_mod.escape(parts.get("terms") or "-"), contact_detail)]
        ]], colWidths=[85 * mm, 85 * mm])
        payment_box.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 1, BRAND_PRIMARY),
            ("BACKGROUND", (0, 0), (-1, -1), BRAND_LIGHT),
            ("LINEAFTER", (0, 0), (0, -1), 0.5, colors.HexColor("#fde68a")),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(payment_box)
        story.append(Spacer(1, 8 * mm))

    # === 7. CATATAN ===
    if parts.get("note"):
        story.append(Paragraph("Catatan", section_label))
        story.append(Paragraph(html_mod.escape(parts["note"]), contact_detail))
        story.append(Spacer(1, 8 * mm))

    # === 8. FOOTER ===
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e5e7eb")))
    story.append(Spacer(1, 4 * mm))

    footer = Table([[
        [Paragraph(html_mod.escape(parts["brand"]) or "Teman UMKM Kita", footer_brand),
         Paragraph(html_mod.escape(parts.get("brand_address") or "Indonesia"), footer_detail),
         Paragraph(html_mod.escape(parts.get("brand_email") or ""), footer_detail)],
        [Paragraph(html_mod.escape(parts.get("footer") or "Dokumen ini dibuat secara digital."), footer_detail)]
    ]], colWidths=[120 * mm, 50 * mm])
    footer.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(footer)

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


def _rewrite_uploads_to_file_urls(html: str, uploads_dir: str | None) -> str:
    """Rewrite /uploads/... (and file:///uploads/...) to absolute file:// URLs.

    WeasyPrint resolves root-relative `/uploads/x` to `file:///uploads/x`
    (filesystem root, not the app uploads dir). Point them at the real disk
    path so logos/images embed without depending on the custom fetcher alone.
    """
    if not uploads_dir or not html:
        return html
    uploads_real = os.path.realpath(uploads_dir)

    def _abs_file_url(match: re.Match) -> str:
        rel = match.group(1)
        # strip query/hash if any slipped in
        rel = rel.split("?", 1)[0].split("#", 1)[0]
        local = os.path.normpath(os.path.join(uploads_real, rel))
        if not (local.startswith(uploads_real + os.sep) or local == uploads_real):
            return match.group(0)
        if not os.path.isfile(local):
            return match.group(0)
        return f'file://{local}'

    # src="/uploads/..." or src='/uploads/...'
    html = re.sub(
        r"""(?i)(?<=src=["'])/uploads/([^"']+)""",
        _abs_file_url,
        html,
    )
    # WeasyPrint-normalized form: file:///uploads/...
    html = re.sub(
        r"""(?i)(?<=src=["'])file:///uploads/([^"']+)""",
        _abs_file_url,
        html,
    )
    return html


def render_pdf_with_weasyprint(rendered_html: str, uploads_dir: str | None = None) -> bytes:
    from weasyprint import HTML

    # Allowlisted absolute TTF paths for @font-face (file://). Without this the
    # url_fetcher returns empty bytes for non-/uploads/ URLs and WeasyPrint
    # silently falls back to URW Type1 → blank text in browser PDF viewers.
    _font_allow = set()
    for font_path in _resolve_doc_fonts().values():
        if font_path and os.path.isfile(font_path):
            _font_allow.add(os.path.realpath(font_path))
    uploads_real = os.path.realpath(uploads_dir) if uploads_dir else ""

    def _pdf_url_fetcher(url: str, **_kw):
        parsed = urlparse(url)
        path = parsed.path if parsed.scheme else url

        # 1) /uploads/ assets — handle both /uploads/x and file:///uploads/x
        #    and already-rewritten file:///abs/path/to/uploads/x
        if uploads_real:
            rel = None
            if "/uploads/" in path:
                rel = path.split("/uploads/", 1)[1]
            elif path.startswith(uploads_real + os.sep):
                rel = path[len(uploads_real) + 1:]
            if rel is not None:
                local_path = os.path.normpath(os.path.join(uploads_real, rel))
                if (
                    (local_path.startswith(uploads_real + os.sep) or local_path == uploads_real)
                    and os.path.isfile(local_path)
                ):
                    ext = os.path.splitext(local_path)[1].lower().lstrip(".")
                    mime = {
                        "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                        "webp": "image/webp", "gif": "image/gif", "svg": "image/svg+xml",
                        "pdf": "application/pdf",
                        "ttf": "font/ttf", "otf": "font/otf", "woff": "font/woff", "woff2": "font/woff2",
                    }.get(ext, "application/octet-stream")
                    with open(local_path, "rb") as f:
                        data = f.read()
                    return {"string": data, "mime_type": mime}

        # 2) Explicit font files via file:// or absolute path
        if parsed.scheme in ("file", "") and path.startswith("/"):
            real = os.path.realpath(path)
            if real in _font_allow:
                with open(real, "rb") as f:
                    data = f.read()
                return {"string": data, "mime_type": "font/ttf"}

        return {"string": b"", "mime_type": "text/plain"}

    # Rewrite logo/image paths before render so WeasyPrint never asks for
    # the broken file:///uploads/... root path.
    rendered_html = _rewrite_uploads_to_file_urls(rendered_html, uploads_dir)
    pdf = HTML(string=rendered_html, url_fetcher=_pdf_url_fetcher, base_url=f"file://{uploads_real}/" if uploads_real else None).write_pdf()
    if not _is_valid_pdf(pdf):
        raise RuntimeError("WeasyPrint menghasilkan PDF invalid")
    # NB: do NOT reject small PDFs by byte count. A valid report with one
    # screenshot + little text can be ~4KB yet legitimately embed an image
    # (verified). The byte threshold (PDF_BLANK_FALLBACK_MAX_BYTES, default
    # 8192) was a false-positive trap that dropped valid PDFs → chain fell
    # to text fallback → images lost. Empty HTML is already rejected by
    # visible_text_from_html at the chain entry; structural validity is
    # covered by _is_valid_pdf above.
    return pdf


def render_report_pdf_reportlab(payload: dict, brand: dict | None = None, uploads_dir: str | None = None) -> bytes:
    """Render a client report PDF from the structured payload via ReportLab.

    This is a REPORT-SPECIFIC renderer (separate from render_pdf_with_reportlab,
    which is invoice/contract-shaped). It consumes the dict produced by
    build_report_payload — NOT HTML — so the text is always correct (no garbled
    CMap like WeasyPrint on this shared host) AND we get colored KPI cards +
    bordered tables (unlike render_text_fallback_pdf which is plain text).

    Empty sections are skipped. Raises on failure so the caller can fall back to
    the plain-text renderer as a safety net.
    """
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        HRFlowable,
        Image,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    brand = brand or {}

    # --- fonts (prefer embedded DejaVu, else built-in Helvetica) --------------
    _BODY_FONT = "Helvetica"
    _BOLD_FONT = "Helvetica-Bold"
    for _ttf in (
        "/home/qqwtlphb/backend/uploads/DejaVuSans.ttf",
        _find_ttf_in_uploads(("DejaVuSans.ttf",)),
    ):
        if _ttf and os.path.exists(_ttf):
            try:
                if "DejaVu" not in pdfmetrics.getRegisteredFontNames():
                    pdfmetrics.registerFont(TTFont("DejaVu", _ttf))
                    bold = _find_ttf_in_uploads(("DejaVuSans-Bold.ttf",)) or _ttf
                    pdfmetrics.registerFont(TTFont("DejaVu-Bold", bold))
                    pdfmetrics.registerFontFamily(
                        "DejaVu", normal="DejaVu", bold="DejaVu-Bold",
                        italic="DejaVu", boldItalic="DejaVu-Bold",
                    )
                _BODY_FONT = "DejaVu"
                _BOLD_FONT = "DejaVu-Bold"
            except Exception:
                pass
            break

    # --- brand colors ---------------------------------------------------------
    ACCENT = colors.HexColor("#f5a700")       # brand yellow
    ACCENT_SOFT = colors.HexColor("#fff7e0")  # light card fill
    DARK = colors.HexColor("#242423")         # brand dark
    BODY = colors.HexColor("#374151")
    MUTED = colors.HexColor("#6b7280")
    BORDER = colors.HexColor("#e5e7eb")
    GOOD = colors.HexColor("#15803d")         # green (improving)
    BAD = colors.HexColor("#b91c1c")          # red (declining)
    HEADER_BG = DARK

    styles = getSampleStyleSheet()
    styles["Normal"].fontName = _BODY_FONT

    def _pstyle(name, **kw):
        kw.setdefault("parent", styles["Normal"])
        kw.setdefault("fontName", _BODY_FONT)
        return ParagraphStyle(name, **kw)

    st_brand = _pstyle("RptBrand", fontName=_BOLD_FONT, fontSize=10, leading=13,
                       textColor=ACCENT, alignment=TA_LEFT)
    st_title = _pstyle("RptTitle", fontName=_BOLD_FONT, fontSize=19, leading=23,
                       textColor=DARK)
    st_meta = _pstyle("RptMeta", fontSize=9, leading=14, textColor=MUTED)
    st_h2 = _pstyle("RptH2", fontName=_BOLD_FONT, fontSize=12.5, leading=16,
                    textColor=DARK, spaceBefore=4, spaceAfter=6)
    st_body = _pstyle("RptBody", fontSize=10, leading=15, textColor=BODY)
    st_muted = _pstyle("RptMutedBody", fontSize=9.5, leading=14, textColor=MUTED)
    st_kpi_label = _pstyle("RptKpiLabel", fontName=_BOLD_FONT, fontSize=7.5,
                           leading=10, textColor=colors.HexColor("#92400e"))
    st_kpi_value = _pstyle("RptKpiValue", fontName=_BOLD_FONT, fontSize=17,
                           leading=20, textColor=DARK)
    st_th = _pstyle("RptTh", fontName=_BOLD_FONT, fontSize=8.5, leading=11,
                    textColor=colors.white)
    st_th_r = _pstyle("RptThR", parent=st_th, alignment=TA_RIGHT)
    st_td = _pstyle("RptTd", fontSize=9, leading=12, textColor=BODY)
    st_td_r = _pstyle("RptTdR", parent=st_td, alignment=TA_RIGHT)
    st_td_b = _pstyle("RptTdB", parent=st_td, fontName=_BOLD_FONT, textColor=DARK)

    def _txt(value, default="-"):
        if value in (None, ""):
            return default
        return html_mod.escape(str(value))

    def _num(value):
        """Indonesian thousands formatting (mirror client_report_service)."""
        if value in (None, ""):
            return "-"
        try:
            n = float(value)
            if n.is_integer():
                return f"{int(n):,}".replace(",", ".")
            return f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except Exception:
            return html_mod.escape(str(value))

    narrative = payload.get("narrative", {}) or {}
    client = payload.get("client", {}) or {}
    project = payload.get("project", {}) or {}
    period = payload.get("period", {}) or {}
    metrics = payload.get("metrics", {}) or {}
    service_type = payload.get("service_type") or "general"
    _report_has_maps = payload.get("has_maps")
    brand_name = brand.get("brand_name") or "Kantor Teman"
    title = payload.get("title") or "Laporan Klien"

    story: list = []
    avail_w = A4[0] - 36 * mm  # matches 18mm side margins

    # --- header ---------------------------------------------------------------
    story.append(Paragraph(_txt(brand_name).upper(), st_brand))
    story.append(Paragraph(_txt(title), st_title))
    story.append(Spacer(1, 3))
    meta_bits = []
    if client.get("name"):
        meta_bits.append(f"Klien: <b>{_txt(client.get('name'))}</b>")
    if project.get("name"):
        meta_bits.append(f"Proyek: {_txt(project.get('name'))}")
    if period.get("label"):
        meta_bits.append(f"Periode: {_txt(period.get('label'))}")
    from datetime import datetime as _dt, timezone as _tz
    meta_bits.append(f"Dibuat: {_dt.now(_tz.utc).strftime('%d/%m/%Y')}")
    story.append(Paragraph("&nbsp;&nbsp;•&nbsp;&nbsp;".join(meta_bits), st_meta))
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=2, color=ACCENT,
                            spaceBefore=2, spaceAfter=12))

    def _section_heading(text):
        story.append(Paragraph(_txt(text), st_h2))

    # --- executive summary ----------------------------------------------------
    exec_sum = narrative.get("executive_summary")
    if exec_sum:
        _section_heading("Ringkasan Eksekutif")
        story.append(Paragraph(_txt(exec_sum, ""), st_body))
        story.append(Spacer(1, 10))

    # --- KPI cards ------------------------------------------------------------
    # Keputusan FINAL Kevin (1 Sep 2026, review draft MLS M08): KPI task
    # internal (Progress tugas / Tugas selesai / Card aktif) DILARANG muncul
    # di PDF klien-facing — bagian pekerjaan di laporan = output nyata doang
    # (metrik GSC/GBP, chart, narrative output-based). Yang tampil: KPI
    # eksternal saja (PageSpeed).
    pagespeed = metrics.get("pagespeed", {}) or {}
    kpi_cards: list[tuple[str, str]] = []
    ps_score = pagespeed.get("performance_score")
    if pagespeed.get("status") == "ok" and ps_score not in (None, "", 0):
        kpi_cards.append(("PAGESPEED MOBILE", _num(ps_score)))

    if kpi_cards:
        card_cells = []
        for label, value in kpi_cards:
            inner = Table(
                [[Paragraph(_txt(label), st_kpi_label)],
                 [Paragraph(_txt(value), st_kpi_value)]],
                colWidths=[None],
            )
            inner.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), ACCENT_SOFT),
                ("BOX", (0, 0), (-1, -1), 1, ACCENT),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (0, 0), 9),
                ("BOTTOMPADDING", (-1, -1), (-1, -1), 9),
                ("TOPPADDING", (-1, -1), (-1, -1), 2),
            ]))
            card_cells.append(inner)
        n = len(card_cells)
        gap = 4 * mm
        col_w = (avail_w - gap * (n - 1)) / n
        # interleave spacer columns for the gap
        row = []
        widths = []
        for i, c in enumerate(card_cells):
            row.append(c)
            widths.append(col_w)
            if i < n - 1:
                row.append("")
                widths.append(gap)
        grid = Table([row], colWidths=widths)
        grid.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(grid)
        story.append(Spacer(1, 14))

    def _bordered_table(header_cells, body_rows, col_widths, right_cols=()):
        """Build a bordered table with dark header + zebra body."""
        header = [
            Paragraph(_txt(h), st_th_r if i in right_cols else st_th)
            for i, h in enumerate(header_cells)
        ]
        data = [header] + body_rows
        tbl = Table(data, colWidths=col_widths, repeatRows=1)
        style = [
            ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
            ("GRID", (0, 0), (-1, -1), 0.6, BORDER),
            ("BOX", (0, 0), (-1, -1), 1, DARK),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]
        for r in range(1, len(data)):
            if r % 2 == 0:
                style.append(("BACKGROUND", (0, r), (-1, r), colors.HexColor("#fafafa")))
        tbl.setStyle(TableStyle(style))
        return tbl

    # --- service performance section (SEO/Gmaps + others) ---------------------
    service = metrics.get("service", {}) or {}
    _st = (service_type or "").lower()
    _is_seo = _st in ("seo", "seo_gmaps", "seo_pro", "seo_only") or ("seo" in _st and "web" not in _st)
    if _is_seo:
        gsc = service.get("gsc", {}) or {}
        gbp = service.get("google_business", {}) or {}
        rows = []
        seo_pairs = [
            ("GSC Clicks", _num(gsc.get("clicks"))),
            ("GSC Impressions", _num(gsc.get("impressions"))),
            ("CTR", _txt(gsc.get("ctr"))),
            ("Average Position", _txt(gsc.get("average_position"))),
        ]
        if any(v not in ("-", None, "") for _, v in seo_pairs):
            for label, val in seo_pairs:
                rows.append([Paragraph(_txt(label), st_td_b),
                             Paragraph(_txt(val), st_td_r)])
        # Opsi B (product-driven): baris GBP HANYA kalau Maps in-scope
        # (product/addons). Kalau paket SEO-only (mis. SEO Pro), skip total.
        gbp_pairs = [
            ("Google Business Views", _num(gbp.get("views"))),
            ("Calls", _num(gbp.get("calls"))),
            ("Directions", _num(gbp.get("directions"))),
            ("Website Clicks", _num(gbp.get("website_clicks"))),
        ]
        has_gbp_data = any(v not in ("-", None, "") for _, v in gbp_pairs)
        # Kalau payload eksplisit bilang has_maps, itu yang menang. Fallback
        # (payload lama tanpa flag) = ikut ada/tidaknya data GBP.
        show_gbp = _report_has_maps if _report_has_maps is not None else has_gbp_data
        if show_gbp:
            for label, val in gbp_pairs:
                if val not in ("-", None, ""):
                    rows.append([Paragraph(_txt(label), st_td_b),
                                 Paragraph(_txt(val), st_td_r)])
        if rows:
            _section_heading(
                "Performa SEO & Google Maps" if show_gbp else "Performa SEO")
            story.append(_bordered_table(
                ["Metrik", "Nilai"], rows,
                [avail_w * 0.6, avail_w * 0.4], right_cols=(1,)))
            story.append(Spacer(1, 14))

    # --- comparison groups (bulan lalu vs sekarang + %) -----------------------
    comparison_groups = metrics.get("comparison_groups") or []
    for group in comparison_groups:
        grows = []
        for item in group.get("rows", []):
            delta = item.get("delta") or {}
            raw = delta.get("delta")
            pct = delta.get("delta_pct")
            lower_better = bool(item.get("lower_is_better"))
            try:
                good = float(raw or 0) < 0 if lower_better else float(raw or 0) > 0
            except Exception:
                good = None
            pct_text = f"{pct:+.1f}%" if isinstance(pct, (int, float)) else "-"
            color = GOOD if good else (BAD if good is False else MUTED)
            change_style = _pstyle(f"chg{len(grows)}", parent=st_td_r,
                                   fontName=_BOLD_FONT, textColor=color)
            grows.append([
                Paragraph(_txt(item.get("label")), st_td_b),
                Paragraph(_num(delta.get("previous")), st_td_r),
                Paragraph(_num(delta.get("current")), st_td_r),
                Paragraph(_txt(pct_text), change_style),
            ])
        if not grows:
            continue
        _section_heading(group.get("title") or "Komparasi Performa")
        ref = group.get("reference_label") or "Bulan Lalu"
        cur = group.get("current_label") or "Sekarang"
        story.append(_bordered_table(
            ["Metrik", _txt(ref), _txt(cur), "Perubahan"], grows,
            [avail_w * 0.34, avail_w * 0.22, avail_w * 0.22, avail_w * 0.22],
            right_cols=(1, 2, 3)))
        if group.get("notes"):
            story.append(Spacer(1, 3))
            story.append(Paragraph(f"Catatan: {_txt(group.get('notes'))}", st_muted))
        story.append(Spacer(1, 14))

    # --- fallback comparison section (metrics.comparisons) --------------------
    comparisons = metrics.get("comparisons", {}) or {}
    comp_metrics = comparisons.get("metrics", []) or []
    if comp_metrics and not comparison_groups:
        crows = []
        for item in comp_metrics:
            delta = item.get("delta") or {}
            raw = delta.get("delta")
            pct = delta.get("delta_pct")
            lower_better = bool(item.get("lower_is_better"))
            try:
                good = float(raw or 0) < 0 if lower_better else float(raw or 0) > 0
            except Exception:
                good = None
            pct_text = f"{pct:+.1f}%" if isinstance(pct, (int, float)) else "-"
            color = GOOD if good else (BAD if good is False else MUTED)
            change_style = _pstyle(f"cchg{len(crows)}", parent=st_td_r,
                                   fontName=_BOLD_FONT, textColor=color)
            crows.append([
                Paragraph(_txt(item.get("label")), st_td_b),
                Paragraph(_num(delta.get("previous")), st_td_r),
                Paragraph(_num(delta.get("current")), st_td_r),
                Paragraph(_txt(pct_text), change_style),
            ])
        if crows:
            _section_heading("Komparasi Performa")
            ref = comparisons.get("reference_label") or "Pembanding"
            story.append(_bordered_table(
                ["Metrik", _txt(ref), "Sekarang", "Perubahan"], crows,
                [avail_w * 0.34, avail_w * 0.22, avail_w * 0.22, avail_w * 0.22],
                right_cols=(1, 2, 3)))
            story.append(Spacer(1, 14))

    # --- narrative lists (highlights / issues / next steps) -------------------
    def _list_block(heading, items):
        if not items:
            return
        if isinstance(items, str):
            items = [ln.strip() for ln in items.splitlines() if ln.strip()]
        if not isinstance(items, list):
            items = [str(items)]
        items = [i for i in items if i][:12]
        if not items:
            return
        _section_heading(heading)
        for it in items:
            story.append(Paragraph(f"•&nbsp;&nbsp;{_txt(it)}", st_body))
        story.append(Spacer(1, 10))

    _list_block("Highlight", narrative.get("highlights"))
    _list_block("Issue dan Catatan", narrative.get("issues"))
    _list_block("Rencana Berikutnya", narrative.get("next_steps"))

    # --- evidence images (chart GSC, screenshot bukti output) -----------------
    # Keputusan FINAL Kevin (1 Sep 2026): evidence bergambar (mis. chart GSC,
    # source=gsc_chart) WAJIB ke-embed di PDF sebagai image — bukan cuma link.
    # Sumber: payload.evidence.items (fallback workspace_evidence, sama dengan
    # _render_evidence di HTML). File yang ga ada di disk di-skip, bukan bikin
    # seluruh render gagal (fallback textfb = kehilangan styling juga).
    evidence = payload.get("evidence", {}) or {}
    ev_items = evidence.get("items") or evidence.get("workspace_evidence") or []
    _img_count = 0
    for item in ev_items:
        if not isinstance(item, dict):
            continue
        url = item.get("url") or ""
        ftype = (item.get("file_type") or "").lower()
        ext = os.path.splitext(url)[1].lower()
        if not (ftype.startswith("image/") or ext in (".png", ".jpg", ".jpeg", ".webp", ".gif")):
            continue
        local = _resolve_uploads_path(url, uploads_dir)
        if not local:
            continue
        try:
            from reportlab.lib.utils import ImageReader

            ir = ImageReader(local)
            iw, ih = ir.getSize()
            if not iw or not ih:
                continue
            w = avail_w * 0.75
            img = Image(local, width=w, height=ih * (w / iw), mask="auto")
            img.hAlign = "CENTER"
            if _img_count == 0:
                _section_heading("Lampiran Grafik")
            story.append(img)
            label = item.get("label") or item.get("file_name")
            if label:
                story.append(Spacer(1, 2))
                story.append(Paragraph(
                    _txt(label),
                    _pstyle(f"RptImgCap{_img_count}", fontSize=8.5, leading=11,
                            textColor=MUTED, alignment=TA_CENTER)))
            story.append(Spacer(1, 8))
            _img_count += 1
        except Exception:
            continue

    # --- footer ---------------------------------------------------------------
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=0.6, color=BORDER,
                            spaceBefore=2, spaceAfter=6))
    story.append(Paragraph(
        f"Laporan dibuat oleh {_txt(brand_name)}. Data eksternal manual/API "
        f"ditampilkan sesuai input yang tersedia saat laporan dibuat.",
        _pstyle("RptFooter", fontSize=7.5, leading=10, textColor=MUTED,
                alignment=TA_CENTER)))

    if not story:
        raise RuntimeError("Report payload kosong, tidak ada yang bisa dirender")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=18 * mm, leftMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=14 * mm,
    )
    doc.title = title
    doc.author = brand_name
    doc.creator = "Kantor Teman"
    doc.subject = f"Laporan untuk {client.get('name') or 'Klien'}"
    doc.build(story)
    pdf = buffer.getvalue()
    if not _is_valid_pdf(pdf):
        raise RuntimeError("ReportLab menghasilkan PDF report invalid")
    return pdf


def _pdf_has_legible_text(pdf: bytes, min_chars: int = 50) -> bool:
    """Best-effort post-render sanity check.

    WeasyPrint on hosts without Helvetica/Arial/Noto Sans TTFs can produce a
    structurally-valid PDF whose glyph CMap is empty for most characters
    (every other glyph slot renders blank in viewers that respect CID
    mappings). Detect that by extracting text with pdfminer.six and
    rejecting PDFs with too few decoded characters.

    Returns True on extraction failure so we don't accidentally fail the
    chain on a transient extractor error — the structural `_is_valid_pdf`
    guard already covers mal-formed files.
    """
    if len(pdf) < 1024:
        return False
    try:
        from pdfminer.high_level import extract_text  # type: ignore
    except Exception:
        return True
    try:
        text = extract_text(io.BytesIO(pdf)) or ""
    except Exception:
        return True
    cleaned = "".join(ch for ch in text if not ch.isspace())
    return len(cleaned) >= min_chars


# Template types whose layout fits inside ReportLab's invoice-shaped pipeline.
# WeasyPrint path is reserved here for client reports (CSS-flex + screenshots)
# but WeasyPrint on this shared host is broken (sparse CMap), so client_report
# is routed to the text-fallback renderer instead — see `_renderer_chain`.
_REPORTLAB_FIRST_TYPES = {
    "invoice", "receipt", "surat_penawaran",
    "kontrak", "kontrak_web_dev", "kontrak_seo", "kontrak_sosmed",
    "kontrak_maintenance", "kontrak_branding", "kontrak_retainer", "mou",
}

# Rich client reports use CSS-grid + screenshots + KPI cards that ReportLab
# cannot lay out (it would emit "Teman UMKM Kita" placeholders everywhere
# because `_extract_doc_parts` doesn't understand the report's HTML). Route
# them straight to the pure-PDF text-fallback renderer, which always renders
# every line correctly even without system fonts.
_REPORT_TYPES = {"client_report", "laporan"}
# Templates with rich HTML/CSS that ReportLab can't parse — use xhtml2pdf first
_HTML_FIRST_TYPES = {"proposal_pdf"}


def _renderer_chain(env_value: str, template_type: str | None) -> tuple[str, ...]:
    """Return the ordered renderer tuple for the chain.

    On shared-host prod (no Helvetica/Arial/Noto Sans TTF) WeasyPrint emits
    a broken CMap that renders as blank text in most viewers, so prefer
    ReportLab first. ReportLab embeds its built-in Helvetica-Bold and is
    unaffected by system fonts.
    """
    # With @font-face file:// DejaVu inject, WeasyPrint now embeds legible text
    # on this shared host. Prefer it for HTML-shaped templates (proposals).
    if env_value == "weasyprint":
        order = ["weasyprint", "xhtml2pdf", "textfb"]
    elif env_value == "xhtml2pdf":
        order = ["xhtml2pdf", "reportlab", "textfb"]
    elif env_value == "auto":
        if template_type in _REPORT_TYPES:
            order = ["textfb"]
        elif template_type in _REPORTLAB_FIRST_TYPES:
            order = ["reportlab", "xhtml2pdf", "textfb"]
        elif template_type in _HTML_FIRST_TYPES:
            order = ["weasyprint", "xhtml2pdf", "textfb"]
        else:
            order = ["weasyprint", "xhtml2pdf", "textfb"]
    else:
        # PDF_RENDERER=reportlab (prod .env) — still route HTML templates
        # through WeasyPrint so proposal/CSS layouts stay intact.
        if template_type in _REPORT_TYPES:
            order = ["textfb"]
        elif template_type in _REPORTLAB_FIRST_TYPES:
            order = ["reportlab", "xhtml2pdf", "textfb"]
        elif template_type in _HTML_FIRST_TYPES:
            order = ["weasyprint", "xhtml2pdf", "textfb"]
        else:
            order = ["weasyprint", "xhtml2pdf", "textfb"]
    return tuple(order)


def _try_renderer(name: str, rendered_html: str, uploads_dir: str | None, template_type: str | None) -> bytes | None:
    try:
        if name == "reportlab":
            return render_pdf_with_reportlab(rendered_html, template_type=template_type, uploads_dir=uploads_dir)
        if name == "xhtml2pdf":
            return render_pdf_with_xhtml2pdf(rendered_html, uploads_dir)
        if name == "weasyprint":
            return render_pdf_with_weasyprint(rendered_html, uploads_dir)
        if name == "textfb":
            return render_text_fallback_pdf(rendered_html)
    except ImportError:
        return None
    except Exception:
        return None
    return None


def render_pdf_from_html(rendered_html: str, uploads_dir: str | None = None, template_type: str | None = None) -> bytes:
    pdf, _ = render_pdf_from_html_with_meta(rendered_html, uploads_dir, template_type)
    return pdf


def render_pdf_from_html_with_meta(
    rendered_html: str, uploads_dir: str | None = None, template_type: str | None = None
) -> tuple[bytes, str]:
    """Render PDF and also report which renderer actually produced it.

    Useful for diagnosing the recurring "blank text" prod issue: if the
    response header says `weasyprint` but text is invisible, the host's
    fontconfig override (Helvetica -> Droid Sans Fallback) is not taking
    effect and WeasyPrint is emitting a sparse CMap.
    """
    if not visible_text_from_html(rendered_html):
        raise ValueError("Template PDF kosong. Isi HTML template terlebih dahulu.")
    if os.getenv("PDF_FORCE_TEXT_FALLBACK", "").lower() == "true":
        return render_text_fallback_pdf(rendered_html), "textfb-force"

    rendered_html = inject_pdf_font(rendered_html)
    env_value = os.getenv("PDF_RENDERER", "auto").lower()
    chain = _renderer_chain(env_value, template_type)

    expected_chars = max(50, len(visible_text_from_html(rendered_html)) // 4)

    for name in chain:
        pdf = _try_renderer(name, rendered_html, uploads_dir, template_type)
        if not pdf or not _is_valid_pdf(pdf):
            continue
        if name == "weasyprint":
            if not _pdf_has_legible_text(pdf, min_chars=expected_chars):
                continue
        return pdf, name
    return render_text_fallback_pdf(rendered_html), "textfb-fallback"


def pdf_render_diagnostics() -> dict:
    """Surface the prod PDF render environment for debugging blank-text."""
    import importlib.util

    def _have(mod: str) -> bool:
        return importlib.util.find_spec(mod) is not None

    fontconfig_file = os.environ.get("FONTCONFIG_FILE", "")
    return {
        "pdf_renderer_env": os.getenv("PDF_RENDERER", "auto"),
        "pdf_force_text_fallback": os.getenv("PDF_FORCE_TEXT_FALLBACK", "false"),
        "fontconfig_file": fontconfig_file,
        "fontconfig_file_exists": bool(fontconfig_file) and os.path.exists(fontconfig_file),
        "renderers_available": {
            "reportlab": _have("reportlab"),
            "weasyprint": _have("weasyprint"),
            "xhtml2pdf": _have("xhtml2pdf"),
            "pdfminer": _have("pdfminer"),
        },
    }
