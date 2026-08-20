#!/usr/bin/env python3
"""
gsc_to_erp_report.py — JEMBATAN 1-KLIK: GSC live -> ERP KantorTeman -> laporan.

Alur:
  1. (opsional) jalanin gsc_to_erp.py biar JSON manual_metrics fresh dari GSC live.
  2. Baca JSON hasil gsc_to_erp.py untuk klien target (gsc-erp-<slug>-<tgl>.json).
  3. Login ke ERP (api.kantorteman.my.id) pakai creds /root/.kt_creds.env.
  4. (opsional --gen-charts) regen chart-<slug>-*.png via gsc_chart_gen.py.
  5. Upload tiap chart PNG ke POST /api/reports/attachments -> dapat file_url,
     lalu susun jadi evidence.items = [{label,url,file_name,file_type,source}].
     Bentuk item persis yang dibaca client_report_service._render_evidence
     (render inline <img> saat file_type image/* atau ekstensi .png).
  6. POST /api/reports/generate dengan:
        target_type=project, target_id=<project_id klien>,
        metrics=<manual_metrics dari GSC>,   <-- injeksi angka.
        evidence={items:[...chart...]}       <-- injeksi grafik (FIX A2).
  7. Balikin report_id + public_slug + public_url + verifikasi chart masuk snapshot.

KENAPA field-nya `metrics` (bukan `manual_metrics`)?
  backend/routers/reports.py -> ReportGenerateIn punya field `metrics: dict`.
  generate_report() memanggil create_report_snapshot(..., manual_metrics=body.metrics, ...).
  Jadi payload HTTP harus pakai key "metrics". Isi dict = manual_metrics apa adanya
  dari gsc_to_erp.py (key gsc_clicks/impressions/ctr/average_position + _previous + _baseline),
  yang persis dibaca _manual_service_metrics(service_type="seo_gmaps") di client_report_service.py.

CATATAN: script INI TIDAK meng-hardcode angka apa pun. Semua metrik berasal dari
JSON hasil GSC live. Kalau JSON belum ada / basi, pakai --refresh untuk narik ulang.

Usage:
  # generate laporan bulanan MLS pakai data GSC yang sudah ada di JSON
  python3 gsc_to_erp_report.py --client mls

  # tarik ulang GSC dulu (jalanin gsc_to_erp.py) lalu generate
  python3 gsc_to_erp_report.py --client mls --refresh

  # kontrol periode / bulan-ke / tipe laporan / draft(non-public)
  python3 gsc_to_erp_report.py --client mls --month 7 --report-type monthly
  python3 gsc_to_erp_report.py --client mls --dry-run     # cuma tunjuk payload, ga hit ERP

Exit code 0 = sukses (report_id tercetak). Non-0 = gagal.
"""
import argparse
import datetime
import glob
import json
import mimetypes
import os
import subprocess
import sys
import urllib.error
import urllib.request
import uuid

BASE = os.environ.get("KT_BASE_URL", "https://api.kantorteman.my.id")
OUT_DIR = "/root/.hermes/shared/outputs"
CREDS = "/root/.kt_creds.env"
GSC_SCRIPT = os.path.join(OUT_DIR, "gsc_to_erp.py")
CHART_SCRIPT = os.path.join(OUT_DIR, "gsc_chart_gen.py")

# Label ramah-klien per jenis chart PNG (dipakai di evidence.items -> render_report_html).
# Nama file mengikuti konvensi gsc_chart_gen.py: chart-<slug>-<kind>.png
CHART_LABELS = {
    "clicks": "Grafik Tren Kunjungan dari Google",
    "position": "Grafik Posisi Rata-rata di Google",
}
# Urutan tampil di laporan (clicks dulu, baru position).
CHART_ORDER = ["clicks", "position"]

# KAMUS RESMI project_id AKTIF per klien (harus match client_facts.py CANONICAL_PROJECT).
# target laporan = PROJECT aktif klien di ERP. Update HANYA saat kontrak ganti.
CANONICAL_PROJECT = {
    "mls": "0377c416-8001-4626-a5e9-63234d010404",  # Mitra Lindung Sarana, SEO+Maintenance AKTIF (service_type=seo_gmaps)
    "mhk": "a160ef94-10ba-4edc-908b-749b7496a88b",  # Momenara - SEO + Maintenance AKTIF
}


def load_creds():
    email = os.environ.get("KT_EMAIL")
    pw = os.environ.get("KT_PW")
    if email and pw:
        return email, pw
    if os.path.exists(CREDS):
        for line in open(CREDS):
            line = line.strip()
            if line.startswith("export "):
                line = line[7:]
            if "=" in line:
                k, v = line.split("=", 1)
                v = v.strip().strip('"').strip("'")
                if k.strip() == "KT_EMAIL":
                    email = v
                elif k.strip() == "KT_PW":
                    pw = v
    return email, pw


def _post(url, payload, tok=None):
    headers = {"Content-Type": "application/json"}
    if tok:
        headers["Authorization"] = "Bearer " + tok
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode())


def _post_multipart(url, field_name, filepath, tok=None):
    """POST satu file via multipart/form-data (tanpa dependency requests).

    Dipakai untuk /api/reports/attachments yang menerima UploadFile `file`.
    Balikin dict JSON: {id, file_url, file_name, file_type}.
    """
    fname = os.path.basename(filepath)
    ctype = mimetypes.guess_type(fname)[0] or "application/octet-stream"
    with open(filepath, "rb") as f:
        file_bytes = f.read()

    boundary = "----ktboundary" + uuid.uuid4().hex
    crlf = b"\r\n"
    body = b"".join([
        b"--" + boundary.encode() + crlf,
        (f'Content-Disposition: form-data; name="{field_name}"; filename="{fname}"').encode() + crlf,
        (f"Content-Type: {ctype}").encode() + crlf + crlf,
        file_bytes, crlf,
        b"--" + boundary.encode() + b"--" + crlf,
    ])
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    if tok:
        headers["Authorization"] = "Bearer " + tok
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode())


def run_chart_gen(slug, json_path=None):
    """Jalanin gsc_chart_gen.py biar chart-<slug>-*.png fresh dari JSON GSC."""
    if not os.path.exists(CHART_SCRIPT):
        print(f"[chart] WARNING: {CHART_SCRIPT} tidak ada, skip regen chart", flush=True)
        return
    cmd = [sys.executable, CHART_SCRIPT, "--slug", slug]
    if json_path:
        cmd += ["--json", json_path]
    print(f"[chart] regen chart PNG: {' '.join(cmd)}", flush=True)
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    sys.stdout.write(res.stdout)
    if res.returncode != 0:
        sys.stderr.write(res.stderr)
        print(f"[chart] WARNING: gsc_chart_gen.py exit {res.returncode}, lanjut pakai PNG yang ada", flush=True)


def find_chart_pngs(slug):
    """Return list (kind, path) chart PNG yang ada untuk slug, sesuai CHART_ORDER."""
    found = []
    for kind in CHART_ORDER:
        p = os.path.join(OUT_DIR, f"chart-{slug}-{kind}.png")
        if os.path.exists(p) and os.path.getsize(p) > 0:
            found.append((kind, p))
    # chart lain di luar CHART_ORDER (mis. impressions) — ikutkan biar future-proof.
    for p in sorted(glob.glob(os.path.join(OUT_DIR, f"chart-{slug}-*.png"))):
        kind = os.path.splitext(os.path.basename(p))[0].replace(f"chart-{slug}-", "")
        if kind not in CHART_ORDER and os.path.getsize(p) > 0:
            found.append((kind, p))
    return found


def build_chart_evidence_items(slug, tok, base):
    """Upload tiap chart PNG ke /api/reports/attachments, balikin list evidence.items.

    Bentuk item MATCH yang dibaca render_report_html._render_evidence:
      {label, url, file_name, file_type, source}
    render_report_html memilih img inline saat file_type image/* atau ekstensi .png.
    """
    charts = find_chart_pngs(slug)
    if not charts:
        print(f"[chart] WARNING: tidak ada chart-{slug}-*.png di {OUT_DIR}. "
              f"Jalanin dengan --gen-charts atau gsc_chart_gen.py dulu.", flush=True)
        return []
    items = []
    for kind, path in charts:
        try:
            up = _post_multipart(base + "/api/reports/attachments", "file", path, tok)
        except urllib.error.HTTPError as e:
            detail = e.read().decode()[:300]
            print(f"[chart] ERROR upload {os.path.basename(path)}: HTTP {e.code} — {detail}", flush=True)
            continue
        file_url = up.get("file_url")
        if not file_url:
            print(f"[chart] ERROR: upload {os.path.basename(path)} tidak balikin file_url ({up})", flush=True)
            continue
        items.append({
            "label": CHART_LABELS.get(kind, f"Grafik {kind}"),
            "url": file_url,
            "file_name": up.get("file_name") or os.path.basename(path),
            "file_type": up.get("file_type") or "image/png",
            "source": "gsc_chart",
        })
        print(f"[chart] uploaded {os.path.basename(path)} -> {file_url}", flush=True)
    return items


def login():
    email, pw = load_creds()
    if not (email and pw):
        raise SystemExit("ERROR: creds ERP tidak ditemukan (KT_EMAIL/KT_PW di /root/.kt_creds.env)")
    body = _post(BASE + "/api/auth/login", {"email": email, "password": pw})
    tok = body.get("access_token") or body.get("token") or body.get("kt_token")
    if not tok:
        raise SystemExit("ERROR: login ERP tidak mengembalikan token")
    return tok


def latest_gsc_json(slug):
    """File gsc-erp-<slug>-<tgl>.json terbaru (by tanggal di nama file)."""
    files = sorted(glob.glob(os.path.join(OUT_DIR, f"gsc-erp-{slug}-*.json")))
    return files[-1] if files else None


def run_gsc_puller():
    print(f"[refresh] jalanin {GSC_SCRIPT} (narik GSC live)...", flush=True)
    res = subprocess.run([sys.executable, GSC_SCRIPT], capture_output=True, text=True, timeout=300)
    sys.stdout.write(res.stdout)
    if res.returncode != 0:
        sys.stderr.write(res.stderr)
        raise SystemExit(f"ERROR: gsc_to_erp.py gagal (exit {res.returncode})")


def build_payload(slug, gsc_json, args):
    manual_metrics = gsc_json.get("manual_metrics") or {}
    if not manual_metrics:
        raise SystemExit(f"ERROR: JSON GSC {slug} tidak punya manual_metrics")
    # service_type dari JSON (seo_gmaps) ikut diselipkan ke metrics — build_report_payload
    # bisa fallback ke metrics.service_type kalau project.service_type kosong (mis. MHK).
    metrics = dict(manual_metrics)
    metrics.setdefault("service_type", gsc_json.get("service_type") or "seo_gmaps")

    payload = {
        "report_type": args.report_type,
        "target_type": "project",
        "target_id": CANONICAL_PROJECT[slug],
        "metrics": metrics,          # <-- injeksi manual_metrics GSC ke report
        "evidence": {},
        "narrative": {},
        "run_pagespeed": args.run_pagespeed,
        "public_enabled": not args.draft,
    }
    if args.month is not None:
        payload["month_number"] = args.month
    if args.period_start:
        payload["period_start"] = args.period_start
    if args.period_end:
        payload["period_end"] = args.period_end
    return payload


def main():
    ap = argparse.ArgumentParser(description="Jembatan 1-klik GSC live -> laporan ERP KantorTeman")
    ap.add_argument("--client", required=True, choices=sorted(CANONICAL_PROJECT.keys()),
                    help="slug klien (mls/mhk)")
    ap.add_argument("--refresh", action="store_true",
                    help="jalanin gsc_to_erp.py dulu (tarik GSC live terbaru) sebelum generate")
    ap.add_argument("--report-type", default="monthly",
                    choices=["monthly", "completion", "internal", "lead_audit"])
    ap.add_argument("--month", type=int, default=None, help="month_number (1-60) untuk periode retainer")
    ap.add_argument("--period-start", default=None, help="YYYY-MM-DD (opsional)")
    ap.add_argument("--period-end", default=None, help="YYYY-MM-DD (opsional)")
    ap.add_argument("--draft", action="store_true", help="public_enabled=False (tanpa public slug)")
    ap.add_argument("--run-pagespeed", action="store_true", default=False,
                    help="jalanin PageSpeed saat generate (default OFF biar cepat)")
    ap.add_argument("--json-file", default=None, help="paksa pakai file JSON GSC tertentu")
    ap.add_argument("--gen-charts", action="store_true",
                    help="regen chart-<slug>-*.png dari JSON GSC (via gsc_chart_gen.py) sebelum upload")
    ap.add_argument("--no-charts", action="store_true",
                    help="jangan inject chart PNG ke evidence (kirim evidence kosong seperti perilaku lama)")
    ap.add_argument("--dry-run", action="store_true", help="cuma cetak payload, tidak hit ERP")
    args = ap.parse_args()

    slug = args.client

    if args.refresh:
        run_gsc_puller()

    path = args.json_file or latest_gsc_json(slug)
    if not path or not os.path.exists(path):
        raise SystemExit(
            f"ERROR: JSON GSC untuk '{slug}' tidak ditemukan. Jalanin dengan --refresh dulu, "
            f"atau pastikan file gsc-erp-{slug}-*.json ada di {OUT_DIR}"
        )
    gsc_json = json.load(open(path, encoding="utf-8"))
    print(f"[data] pakai {path} (generated_at={gsc_json.get('generated_at')})", flush=True)

    payload = build_payload(slug, gsc_json, args)

    mm = payload["metrics"]
    print(f"[map] target project={payload['target_id']} service={mm.get('service_type')}")
    print(f"[map] GSC 90hari: {mm.get('gsc_clicks')} klik / {mm.get('gsc_impressions')} imp / "
          f"CTR {mm.get('gsc_ctr')}% / pos {mm.get('gsc_average_position')}")

    if args.dry_run:
        print("\n[dry-run] payload yang AKAN dikirim ke POST /api/reports/generate:")
        if not args.no_charts:
            if args.gen_charts:
                run_chart_gen(slug, path)
            charts = find_chart_pngs(slug)
            if charts:
                print(f"[dry-run] {len(charts)} chart PNG akan di-upload ke /api/reports/attachments "
                      f"lalu masuk ke evidence.items: {[os.path.basename(p) for _, p in charts]}")
            else:
                print(f"[dry-run] TIDAK ada chart-{slug}-*.png ditemukan (evidence.items akan kosong). "
                      f"Pakai --gen-charts / jalanin gsc_chart_gen.py dulu.")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    tok = login()
    print("[erp] login OK", flush=True)

    # === INJEKSI CHART PNG ke evidence.items ===
    # Upload chart-<slug>-*.png ke /api/reports/attachments -> file_url -> evidence.items.
    # Ini yang bikin chart ke-render inline di laporan publik + PDF (bukan nyangkut lokal).
    if not args.no_charts:
        if args.gen_charts:
            run_chart_gen(slug, path)
        chart_items = build_chart_evidence_items(slug, tok, BASE)
        if chart_items:
            evidence = payload.setdefault("evidence", {})
            existing = evidence.get("items") or []
            evidence["items"] = existing + chart_items
            print(f"[chart] evidence.items terisi {len(evidence['items'])} chart -> di-inject ke report", flush=True)
        else:
            print("[chart] evidence.items kosong (tidak ada chart ter-upload). Laporan tetap dibuat tanpa grafik.", flush=True)

    print("[erp] generate report...", flush=True)
    try:
        snap = _post(BASE + "/api/reports/generate", payload, tok)
    except urllib.error.HTTPError as e:
        detail = e.read().decode()[:500]
        raise SystemExit(f"ERROR: /api/reports/generate HTTP {e.code} — {detail}")

    report_id = snap.get("id")
    slug_out = snap.get("public_slug")
    public_url = snap.get("public_url")
    print("\n=== LAPORAN DIBUAT ===")
    print(f"  report_id  : {report_id}")
    print(f"  title      : {snap.get('title')}")
    print(f"  service    : {snap.get('service_type')}")
    print(f"  status     : {snap.get('status')}")
    print(f"  public_slug: {slug_out}")
    print(f"  public_url : {public_url}")
    print(f"  doc_id     : {snap.get('generated_document_id')}")
    # verifikasi angka GSC beneran masuk ke snapshot
    gsc_in_snap = (((snap.get('metrics') or {}).get('service') or {}).get('gsc') or {})
    if gsc_in_snap:
        print(f"  [verify] snapshot.metrics.service.gsc.clicks = {gsc_in_snap.get('clicks')} "
              f"(harus == {mm.get('gsc_clicks')})")
    # verifikasi chart PNG beneran masuk ke evidence.items snapshot
    ev_items = (((snap.get('evidence') or {}).get('items')) or [])
    chart_items_in_snap = [i for i in ev_items if (i.get('source') == 'gsc_chart' or 'chart-' in (i.get('file_name') or ''))]
    if not args.no_charts:
        print(f"  [verify] evidence.items = {len(ev_items)} total, {len(chart_items_in_snap)} chart "
              f"({[i.get('file_name') for i in chart_items_in_snap]})")
    print("======================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
