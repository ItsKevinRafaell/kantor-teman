"""
Test kecil untuk BLOCKER #1: normalisasi service_type.

Buktikan bahwa service_type gabungan / kosong / free text tetap resolve ke
template seo_gmaps (9 sheet) dan BUKAN fallback general (3 sheet).

Jalankan: python test_service_type_normalize.py
Standalone — cuma butuh workspace_templates.py, tanpa DB / venv.
"""
from workspace_templates import (
    normalize_service_type,
    build_sheets_for_service,
    WORKSPACE_TEMPLATES,
)

CONTRACT_MONTHS = 6

# (input service_type mentah, expected canonical key)
NORMALIZE_CASES = [
    ("seo_gmaps", "seo_gmaps"),
    ("seo_gmaps,maintenance", "seo_gmaps"),   # gabungan CSV -> primary seo
    ("maintenance,seo_gmaps", "seo_gmaps"),   # urutan kebalik, tetap seo
    ("SEO + Maintenance", "seo_gmaps"),        # free text + plus
    ("SEO & Google Maps", "seo_gmaps"),
    ("", "general"),                            # kosong -> general
    (None, "general"),                          # None -> general
    ("   ", "general"),                         # whitespace -> general
    ("maintenance", "maintenance"),             # single valid tetap
    ("maintenance,web_dev", "web_dev"),         # tanpa seo -> web_dev (prioritas)
    ("Kelola Sosmed", "sosmed"),
    ("layanan random ga jelas", "general"),     # unknown -> general
]


def count_sheets(service_type):
    return len(build_sheets_for_service(service_type, CONTRACT_MONTHS))


def main():
    print("=" * 68)
    print("TEST normalize_service_type()")
    print("=" * 68)
    seo_sheet_count = count_sheets("seo_gmaps")
    general_sheet_count = count_sheets("general")
    print(f"[baseline] seo_gmaps -> {seo_sheet_count} sheet | general -> {general_sheet_count} sheet\n")

    passed = 0
    failed = 0
    for raw, expected in NORMALIZE_CASES:
        got = normalize_service_type(raw)
        n_sheets = count_sheets(got)
        ok = got == expected
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        else:
            failed += 1
        print(f"[{status}] {raw!r:38} -> {got!r:16} ({n_sheets} sheet)  expected={expected!r}")

    print()
    print("-" * 68)
    print("VERIFIKASI BLOCKER #1: klien SEO tidak boleh fallback ke general")
    print("-" * 68)
    seo_inputs = ["seo_gmaps,maintenance", "", "SEO + Maintenance"]
    blocker_ok = True
    for raw in seo_inputs:
        # NB: "" sengaja dites — sesuai task. Kosong -> general itu BENAR
        #     (gak ada sinyal SEO), jadi kita tandai khusus.
        resolved = normalize_service_type(raw)
        n = count_sheets(resolved)
        if raw == "":
            note = "(kosong: tidak ada sinyal SEO -> general adalah benar)"
            print(f"  {raw!r:24} -> {resolved!r:12} {n} sheet  {note}")
        else:
            expect_seo = resolved == "seo_gmaps" and n == seo_sheet_count
            blocker_ok = blocker_ok and expect_seo
            mark = "OK" if expect_seo else "BUG"
            print(f"  [{mark}] {raw!r:24} -> {resolved!r:12} {n} sheet (harus seo_gmaps={seo_sheet_count})")

    print()
    print("=" * 68)
    print(f"HASIL: {passed} pass, {failed} fail | seo_gmaps={seo_sheet_count} sheet, general={general_sheet_count} sheet")
    print(f"BLOCKER #1 SEO routing: {'FIXED ✓' if blocker_ok and failed == 0 else 'MASIH BUG ✗'}")
    print("=" * 68)

    assert failed == 0, "Ada case normalize yang gagal!"
    assert blocker_ok, "Klien SEO masih fallback salah!"
    assert seo_sheet_count == 9, f"seo_gmaps harus 9 sheet, dapat {seo_sheet_count}"


if __name__ == "__main__":
    main()
