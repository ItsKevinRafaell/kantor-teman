import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "Laporan Audit Digital";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default async function OGImage({ params }: { params: { slug: string } }) {
  let businessName = "Bisnis Anda";
  let category = "";
  let city = "";

  try {
    const res = await fetch(`${API_BASE}/api/proposals/public/report/${params.slug}`, {
      next: { revalidate: 3600 },
    });
    if (res.ok) {
      const data = await res.json();
      businessName = data.nama_usaha || businessName;
      category = data.category || "";
      city = data.address
        ? data.address.split(",").pop()?.trim() || ""
        : "";
    }
  } catch {
    // Fallback to default values
  }

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: "#09090b",
          position: "relative",
          overflow: "hidden",
        }}
      >
        {/* Border gradient accent */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            height: "4px",
            background: "linear-gradient(90deg, #f59e0b, #10b981, #3b82f6)",
            display: "flex",
          }}
        />

        {/* Content */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            padding: "60px",
            gap: "32px",
          }}
        >
          {/* Header */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "12px",
            }}
          >
            <div
              style={{
                width: "40px",
                height: "40px",
                borderRadius: "8px",
                backgroundColor: "#f59e0b",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "20px",
                fontWeight: 700,
                color: "#09090b",
              }}
            >
              KT
            </div>
            <span
              style={{
                fontSize: "20px",
                color: "#a1a1aa",
                letterSpacing: "0.05em",
              }}
            >
              LAPORAN HASIL AUDIT DIGITAL RESMI
            </span>
          </div>

          {/* Business Name */}
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: "12px",
            }}
          >
            <h1
              style={{
                fontSize: "64px",
                fontWeight: 800,
                color: "#fafafa",
                textAlign: "center",
                lineHeight: 1.1,
                maxWidth: "900px",
              }}
            >
              {businessName}
            </h1>
            {(category || city) && (
              <p
                style={{
                  fontSize: "24px",
                  color: "#71717a",
                  display: "flex",
                }}
              >
                {[category, city].filter(Boolean).join(" — ")}
              </p>
            )}
          </div>

          {/* Branding footer */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              marginTop: "16px",
            }}
          >
            <div
              style={{
                width: "8px",
                height: "8px",
                borderRadius: "50%",
                backgroundColor: "#10b981",
                display: "flex",
              }}
            />
            <span
              style={{
                fontSize: "18px",
                color: "#52525b",
              }}
            >
              Diterbitkan secara eksklusif oleh Teman UMKM Kita Agensi
            </span>
          </div>
        </div>

        {/* Bottom border accent */}
        <div
          style={{
            position: "absolute",
            bottom: 0,
            left: 0,
            right: 0,
            height: "4px",
            background: "linear-gradient(90deg, #3b82f6, #10b981, #f59e0b)",
            display: "flex",
          }}
        />
      </div>
    ),
    {
      ...size,
    }
  );
}
