#!/usr/bin/env python3
"""
gsc_chart_gen.py

Generate PNG trend charts (Clicks + Average Position) from GSC->ERP JSON
produced by gsc_to_erp.py, for injection into client-facing monthly reports.

Data source: /root/.hermes/shared/outputs/gsc-erp-mls-*.json
  manual_metrics:
    gsc_clicks / gsc_clicks_previous / gsc_clicks_baseline
    gsc_average_position / gsc_average_position_previous / gsc_average_position_baseline

Outputs:
    chart-<slug>-clicks.png    -> tren Kunjungan (baseline -> bulan lalu -> bulan ini)
    chart-<slug>-position.png  -> tren Posisi rata-rata (Y axis inverted: naik = membaik)

Notes:
    - Angka HANYA dari JSON asli (anti-halu). Tidak ada dummy.
    - Warna brand: kuning #f5a700 + charcoal.
    - Bahasa Indonesia awam.
"""

import argparse
import glob
import json
import os
import sys

OUT_DIR = "/root/.hermes/shared/outputs"

# Brand colors
BRAND_YELLOW = "#f5a700"
CHARCOAL = "#33373d"
GRID_GRAY = "#d9dbde"
BG = "#ffffff"


def find_latest_json(slug):
    pattern = os.path.join(OUT_DIR, f"gsc-erp-{slug}-*.json")
    files = sorted(glob.glob(pattern))
    if not files:
        raise FileNotFoundError(f"Tidak ada file JSON cocok pola: {pattern}")
    # sorted() on ISO-date filenames -> last is newest
    return files[-1]


def load_metrics(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    slug = data.get("slug", "client")
    client = data.get("client", slug)
    m = data.get("manual_metrics", {})

    def req(key):
        if key not in m or m[key] is None:
            raise KeyError(f"manual_metrics.{key} tidak ada di {path}")
        return m[key]

    metrics = {
        "clicks_baseline": req("gsc_clicks_baseline"),
        "clicks_previous": req("gsc_clicks_previous"),
        "clicks_current": req("gsc_clicks"),
        "pos_baseline": req("gsc_average_position_baseline"),
        "pos_previous": req("gsc_average_position_previous"),
        "pos_current": req("gsc_average_position"),
    }
    return slug, client, metrics


def _apply_axes_style(ax):
    ax.set_facecolor(BG)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color(CHARCOAL)
    ax.tick_params(colors=CHARCOAL, labelsize=11)
    ax.grid(True, axis="y", color=GRID_GRAY, linewidth=0.8, alpha=0.9)
    ax.set_axisbelow(True)


def make_clicks_chart(client, metrics, out_path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = ["Periode Awal", "Bulan Lalu", "Bulan Ini"]
    values = [
        metrics["clicks_baseline"],
        metrics["clicks_previous"],
        metrics["clicks_current"],
    ]

    fig, ax = plt.subplots(figsize=(8, 4.6), dpi=110)
    fig.patch.set_facecolor(BG)

    x = list(range(len(values)))
    ax.plot(x, values, color=BRAND_YELLOW, linewidth=3.5, zorder=3,
            marker="o", markersize=11, markerfacecolor=BRAND_YELLOW,
            markeredgecolor=CHARCOAL, markeredgewidth=1.5)

    # Value labels above each point
    ymax = max(values)
    for xi, yi in zip(x, values):
        ax.annotate(f"{yi:,}".replace(",", "."),
                    (xi, yi), textcoords="offset points", xytext=(0, 12),
                    ha="center", fontsize=12, fontweight="bold", color=CHARCOAL)

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylim(0, ymax * 1.25)
    ax.set_ylabel("Jumlah Kunjungan (klik)", color=CHARCOAL, fontsize=12)
    ax.set_title("Perkembangan Kunjungan dari Google",
                 color=CHARCOAL, fontsize=16, fontweight="bold", pad=16)
    _apply_axes_style(ax)

    fig.text(0.5, 0.01, client, ha="center", fontsize=9, color="#8a8d92")
    fig.tight_layout(rect=[0, 0.03, 1, 1])
    fig.savefig(out_path, facecolor=BG)
    plt.close(fig)
    return out_path


def make_position_chart(client, metrics, out_path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = ["Periode Awal", "Bulan Lalu", "Bulan Ini"]
    values = [
        metrics["pos_baseline"],
        metrics["pos_previous"],
        metrics["pos_current"],
    ]

    fig, ax = plt.subplots(figsize=(8, 4.6), dpi=110)
    fig.patch.set_facecolor(BG)

    x = list(range(len(values)))
    ax.plot(x, values, color=BRAND_YELLOW, linewidth=3.5, zorder=3,
            marker="o", markersize=11, markerfacecolor=BRAND_YELLOW,
            markeredgecolor=CHARCOAL, markeredgewidth=1.5)

    for xi, yi in zip(x, values):
        ax.annotate(f"{yi:g}",
                    (xi, yi), textcoords="offset points", xytext=(0, 12),
                    ha="center", fontsize=12, fontweight="bold", color=CHARCOAL)

    ax.set_xticks(x)
    ax.set_xticklabels(labels)

    # INVERT Y: posisi makin kecil = makin bagus, sehingga garis "naik" = membaik
    lo = min(values)
    hi = max(values)
    pad = max(0.5, (hi - lo) * 0.35)
    ax.set_ylim(hi + pad, max(0, lo - pad))  # inverted: bigger (worse) at bottom

    ax.set_ylabel("Posisi di Google (makin atas makin bagus)",
                  color=CHARCOAL, fontsize=11)
    ax.set_title("Posisi Rata-rata di Google",
                 color=CHARCOAL, fontsize=16, fontweight="bold", pad=16)
    _apply_axes_style(ax)

    fig.text(0.5, 0.01, client, ha="center", fontsize=9, color="#8a8d92")
    fig.tight_layout(rect=[0, 0.03, 1, 1])
    fig.savefig(out_path, facecolor=BG)
    plt.close(fig)
    return out_path


def main():
    parser = argparse.ArgumentParser(
        description="Generate GSC trend charts (PNG) for ERP monthly report.")
    parser.add_argument("--slug", default="mls",
                        help="Client slug (default: mls)")
    parser.add_argument("--json", default=None,
                        help="Path ke file JSON spesifik (opsional). "
                             "Kalau kosong, ambil terbaru sesuai slug.")
    args = parser.parse_args()

    # matplotlib preflight (task requirement)
    try:
        import matplotlib  # noqa: F401
    except ImportError:
        print("ERROR: matplotlib tidak terinstall. "
              "Jalankan: pip install matplotlib", file=sys.stderr)
        sys.exit(2)

    json_path = args.json or find_latest_json(args.slug)
    slug, client, metrics = load_metrics(json_path)

    print(f"[gsc_chart_gen] Source JSON : {json_path}")
    print(f"[gsc_chart_gen] Client      : {client}  (slug={slug})")
    print(f"[gsc_chart_gen] Clicks      : baseline={metrics['clicks_baseline']} "
          f"prev={metrics['clicks_previous']} current={metrics['clicks_current']}")
    print(f"[gsc_chart_gen] AvgPosition : baseline={metrics['pos_baseline']} "
          f"prev={metrics['pos_previous']} current={metrics['pos_current']}")

    clicks_png = os.path.join(OUT_DIR, f"chart-{slug}-clicks.png")
    position_png = os.path.join(OUT_DIR, f"chart-{slug}-position.png")

    make_clicks_chart(client, metrics, clicks_png)
    make_position_chart(client, metrics, position_png)

    print(f"[gsc_chart_gen] Wrote: {clicks_png}")
    print(f"[gsc_chart_gen] Wrote: {position_png}")


if __name__ == "__main__":
    main()
