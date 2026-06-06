"""PDF rendering helpers for document templates.

The production shared host cannot reliably render text through WeasyPrint's
native stack, so xhtml2pdf is the preferred renderer because it is pip-only.
"""
import html as html_mod
import io
import os
import re
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
    renderer = os.getenv("PDF_RENDERER", "xhtml2pdf").lower()
    renderers = (
        ("weasyprint", "xhtml2pdf")
        if renderer == "weasyprint"
        else ("xhtml2pdf", "weasyprint")
    )
    for name in renderers:
        try:
            if name == "xhtml2pdf":
                return render_pdf_with_xhtml2pdf(rendered_html, uploads_dir)
            return render_pdf_with_weasyprint(rendered_html)
        except ImportError:
            continue
        except Exception:
            continue
    return render_text_fallback_pdf(rendered_html)
