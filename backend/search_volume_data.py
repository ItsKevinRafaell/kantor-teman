"""
Localized Search Volume Heuristic Engine
Estimasi volume pencarian bulanan Google berdasarkan kategori bisnis dan kota.
"""
import random

SEARCH_VOLUME_DATA = {
    "KONTRAKTOR": {
        "jakarta": 4800, "bandung": 2200, "surabaya": 3100, "medan": 1800,
        "semarang": 1400, "makassar": 1100, "bali": 900, "balikpapan": 750,
        "samarinda": 620, "malang": 980, "jogja": 1300, "bekasi": 2600,
        "tangerang": 2400, "depok": 1900, "bogor": 1500,
    },
    "EPOXY": {
        "jakarta": 3200, "bandung": 1500, "surabaya": 2100, "medan": 1200,
        "semarang": 900, "makassar": 700, "bali": 650, "balikpapan": 580,
        "samarinda": 450, "malang": 620, "jogja": 850, "bekasi": 1800,
        "tangerang": 1600, "depok": 1100, "bogor": 900,
    },
    "WATERPROOFING": {
        "jakarta": 3800, "bandung": 1800, "surabaya": 2500, "medan": 1400,
        "semarang": 1100, "makassar": 850, "bali": 720, "balikpapan": 600,
        "samarinda": 480, "malang": 750, "jogja": 1000, "bekasi": 2100,
        "tangerang": 1900, "depok": 1300, "bogor": 1100,
    },
    "CAFE": {
        "jakarta": 8500, "bandung": 6200, "surabaya": 5400, "medan": 3800,
        "semarang": 2900, "makassar": 2200, "bali": 4800, "balikpapan": 1200,
        "samarinda": 950, "malang": 3100, "jogja": 4500, "bekasi": 3600,
        "tangerang": 3200, "depok": 2800, "bogor": 2500,
    },
    "RESTO": {
        "jakarta": 9200, "bandung": 5800, "surabaya": 5100, "medan": 3500,
        "semarang": 2700, "makassar": 2100, "bali": 4200, "balikpapan": 1100,
        "samarinda": 880, "malang": 2800, "jogja": 4100, "bekasi": 3400,
        "tangerang": 3000, "depok": 2600, "bogor": 2300,
    },
    "SALON": {
        "jakarta": 7200, "bandung": 4500, "surabaya": 4100, "medan": 2900,
        "semarang": 2200, "makassar": 1700, "bali": 2800, "balikpapan": 950,
        "samarinda": 780, "malang": 2100, "jogja": 3200, "bekasi": 3100,
        "tangerang": 2800, "depok": 2400, "bogor": 2000,
    },
    "CATERING": {
        "jakarta": 6800, "bandung": 3900, "surabaya": 3600, "medan": 2600,
        "semarang": 2000, "makassar": 1500, "bali": 1800, "balikpapan": 850,
        "samarinda": 700, "malang": 1800, "jogja": 2800, "bekasi": 3200,
        "tangerang": 2900, "depok": 2200, "bogor": 1900,
    },
    "AQIQAH": {
        "jakarta": 5400, "bandung": 3200, "surabaya": 2900, "medan": 2100,
        "semarang": 1700, "makassar": 1300, "bali": 400, "balikpapan": 750,
        "samarinda": 620, "malang": 1500, "jogja": 2300, "bekasi": 2800,
        "tangerang": 2500, "depok": 2000, "bogor": 1700,
    },
    "KLINIK_KECANTIKAN": {
        "jakarta": 8100, "bandung": 5100, "surabaya": 4600, "medan": 3200,
        "semarang": 2400, "makassar": 1800, "bali": 3500, "balikpapan": 1000,
        "samarinda": 820, "malang": 2300, "jogja": 3600, "bekasi": 3500,
        "tangerang": 3100, "depok": 2700, "bogor": 2200,
    },
    "LAUNDRY": {
        "jakarta": 6200, "bandung": 3800, "surabaya": 3400, "medan": 2400,
        "semarang": 1900, "makassar": 1400, "bali": 2100, "balikpapan": 900,
        "samarinda": 720, "malang": 1900, "jogja": 2700, "bekasi": 3000,
        "tangerang": 2700, "depok": 2300, "bogor": 1800,
    },
    "WEDDING_ORGANIZER": {
        "jakarta": 5800, "bandung": 4200, "surabaya": 3500, "medan": 2300,
        "semarang": 1800, "makassar": 1300, "bali": 4500, "balikpapan": 800,
        "samarinda": 650, "malang": 1700, "jogja": 3200, "bekasi": 2600,
        "tangerang": 2300, "depok": 1900, "bogor": 1600,
    },
    "TOKO_BANGUNAN": {
        "jakarta": 4200, "bandung": 2400, "surabaya": 2800, "medan": 1700,
        "semarang": 1300, "makassar": 1000, "bali": 800, "balikpapan": 680,
        "samarinda": 550, "malang": 1100, "jogja": 1500, "bekasi": 2300,
        "tangerang": 2100, "depok": 1600, "bogor": 1300,
    },
    "INTERIOR": {
        "jakarta": 5200, "bandung": 2800, "surabaya": 2600, "medan": 1600,
        "semarang": 1200, "makassar": 900, "bali": 1800, "balikpapan": 650,
        "samarinda": 500, "malang": 1000, "jogja": 1700, "bekasi": 2400,
        "tangerang": 2200, "depok": 1700, "bogor": 1300,
    },
    "PERCETAKAN": {
        "jakarta": 4500, "bandung": 2600, "surabaya": 2400, "medan": 1500,
        "semarang": 1200, "makassar": 900, "bali": 700, "balikpapan": 580,
        "samarinda": 450, "malang": 1000, "jogja": 1600, "bekasi": 2200,
        "tangerang": 2000, "depok": 1500, "bogor": 1200,
    },
    "BENGKEL": {
        "jakarta": 7500, "bandung": 4200, "surabaya": 3900, "medan": 2800,
        "semarang": 2100, "makassar": 1600, "bali": 1900, "balikpapan": 1000,
        "samarinda": 850, "malang": 2000, "jogja": 2900, "bekasi": 3400,
        "tangerang": 3100, "depok": 2500, "bogor": 2100,
    },
    "FOTOGRAFI": {
        "jakarta": 4800, "bandung": 3500, "surabaya": 2800, "medan": 1800,
        "semarang": 1400, "makassar": 1100, "bali": 3200, "balikpapan": 700,
        "samarinda": 550, "malang": 1500, "jogja": 2800, "bekasi": 2200,
        "tangerang": 2000, "depok": 1600, "bogor": 1300,
    },
    "FABRIKASI": {
        "jakarta": 2800, "bandung": 1400, "surabaya": 1900, "medan": 1000,
        "semarang": 800, "makassar": 600, "bali": 350, "balikpapan": 520,
        "samarinda": 420, "malang": 650, "jogja": 750, "bekasi": 1600,
        "tangerang": 1400, "depok": 900, "bogor": 700,
    },
    "KONSTRUKSI": {
        "jakarta": 4500, "bandung": 2100, "surabaya": 2900, "medan": 1700,
        "semarang": 1300, "makassar": 1000, "bali": 850, "balikpapan": 720,
        "samarinda": 600, "malang": 950, "jogja": 1200, "bekasi": 2500,
        "tangerang": 2200, "depok": 1800, "bogor": 1400,
    },
}

# Skala kota untuk fallback
CITY_SCALE = {
    "jakarta": 1.0, "bandung": 0.65, "surabaya": 0.7, "medan": 0.5,
    "semarang": 0.4, "makassar": 0.35, "bali": 0.55, "balikpapan": 0.25,
    "samarinda": 0.2, "malang": 0.35, "jogja": 0.5, "bekasi": 0.6,
    "tangerang": 0.55, "depok": 0.45, "bogor": 0.4,
}


def get_monthly_search_volume(category: str, city: str) -> int:
    cat_upper = category.upper().strip().replace(" ", "_")
    city_lower = city.lower().strip()

    if cat_upper in SEARCH_VOLUME_DATA:
        city_data = SEARCH_VOLUME_DATA[cat_upper]
        for key in city_data:
            if key in city_lower or city_lower in key:
                return city_data[key]

    # Fallback: angka acak berdasarkan skala kota
    scale = 0.3
    for key, val in CITY_SCALE.items():
        if key in city_lower or city_lower in key:
            scale = val
            break

    base = random.randint(300, 800)
    return int(base * (scale / 0.3))
