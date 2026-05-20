"use client";

import { useEffect, useState, useMemo } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface LeadMap {
  id: number;
  business_name: string;
  phone_number: string;
  address: string;
  status: string;
  product_interest: string | null;
  batch_name: string | null;
  website_url: string | null;
  google_rating: number | null;
  review_count: number | null;
  latitude: number;
  longitude: number;
  lead_score: number;
}

const statusColors: Record<string, string> = {
  Scraped: "#ef4444",
  Contacted: "#f59e0b",
  Replied: "#f59e0b",
  Negotiating: "#3b82f6",
  Client: "#22c55e",
  Lost: "#6b7280",
};

function getStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    Scraped: "Belum Dihubungi",
    Contacted: "Sudah Dihubungi",
    Replied: "Dibalas",
    Negotiating: "Negosiasi",
    Client: "Jadi Klien",
    Lost: "Hilang",
  };
  return labels[status] || status;
}

function StarRating({ rating }: { rating: number | null }) {
  if (rating === null) return <span className="text-gray-400">-</span>;
  const stars = "★".repeat(Math.round(rating)) + "☆".repeat(5 - Math.round(rating));
  return <span className="text-yellow-500">{stars}</span>;
}

export default function MapPage() {
  const [leads, setLeads] = useState<LeadMap[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [filterBatch, setFilterBatch] = useState("");
  const [filterProduct, setFilterProduct] = useState("");
  const [selectedLead, setSelectedLead] = useState<LeadMap | null>(null);

  useEffect(() => {
    const token = document.cookie.split("; ").find((c) => c.startsWith("kt_token="))?.split("=")[1];
    if (!token) {
      setError("Token tidak ditemukan");
      setLoading(false);
      return;
    }
    const params = new URLSearchParams();
    if (filterStatus) params.append("status", filterStatus);
    if (filterBatch) params.append("batch_name", filterBatch);
    if (filterProduct) params.append("product_interest", filterProduct);

    fetch(`${API_BASE}/api/leads/map?${params.toString()}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => res.json())
      .then((data) => {
        if (Array.isArray(data)) {
          setLeads(data);
        } else {
          setError(data.detail || "Gagal memuat data");
        }
      })
      .catch(() => setError("Gagal menghubungi server"))
      .finally(() => setLoading(false));
  }, [filterStatus, filterBatch, filterProduct]);

  useEffect(() => {
    if (typeof window === "undefined" || loading || leads.length === 0) return;

    const initMap = async () => {
      const L = await import("leaflet");

      const mapEl = document.getElementById("map");
      if (!mapEl) return;

      if ((mapEl as unknown as { _leaflet_id?: number })._leaflet_id) return;

      const avgLat = leads.reduce((sum, l) => sum + l.latitude, 0) / leads.length;
      const avgLng = leads.reduce((sum, l) => sum + l.longitude, 0) / leads.length;

      const map = L.map("map").setView([avgLat, avgLng], 5);

      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
      }).addTo(map);

      const createMarkerIcon = (color: string) =>
        L.divIcon({
          className: "custom-marker",
          html: `<div style="background-color: ${color}; width: 24px; height: 24px; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>`,
          iconSize: [24, 24],
          iconAnchor: [12, 12],
        });

      leads.forEach((lead) => {
        const marker = L.marker([lead.latitude, lead.longitude], {
          icon: createMarkerIcon(statusColors[lead.status] || "#6b7280")
        }).addTo(map);
        marker.on("click", () => setSelectedLead(lead));
      });
    };

    initMap();
  }, [loading, leads]);

  const batches = useMemo(() => Array.from(new Set(leads.map((l) => l.batch_name).filter(Boolean))) as string[], [leads]);
  const products = useMemo(() => Array.from(new Set(leads.map((l) => l.product_interest).filter(Boolean))) as string[], [leads]);

  const handleWhatsApp = (phone: string, name: string) => {
    const cleanPhone = phone.replace(/\D/g, "");
    const waPhone = cleanPhone.startsWith("0") ? "62" + cleanPhone.slice(1) : cleanPhone;
    const message = encodeURIComponent(`Halo ${name}, saya dari Kantor Teman...`);
    window.open(`https://wa.me/${waPhone}?text=${message}`, "_blank");
  };

  const handleUpdateStatus = async (leadId: number, newStatus: string) => {
    const token = document.cookie.split("; ").find((c) => c.startsWith("kt_token="))?.split("=")[1];
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE}/api/leads/${leadId}/status`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ status: newStatus }),
      });
      if (res.ok) {
        setLeads((prev) => prev.map((l) => (l.id === leadId ? { ...l, status: newStatus } : l)));
        setSelectedLead(null);
      }
    } catch {
      // ignore
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-lg">Memuat peta...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-lg text-red-500">{error}</div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen">
      <div className="bg-white shadow p-4 flex flex-wrap gap-4 items-center">
        <h1 className="text-xl font-bold mr-4">Peta Leads</h1>
        <div className="flex gap-4 items-center flex-wrap">
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="border rounded px-3 py-1.5 text-sm"
          >
            <option value="">Semua Status</option>
            <option value="Scraped">Belum Dihubungi</option>
            <option value="Contacted">Sudah Dihubungi</option>
            <option value="Replied">Dibalas</option>
            <option value="Negotiating">Negosiasi</option>
            <option value="Client">Jadi Klien</option>
            <option value="Lost">Hilang</option>
          </select>
          <select
            value={filterBatch}
            onChange={(e) => setFilterBatch(e.target.value)}
            className="border rounded px-3 py-1.5 text-sm"
          >
            <option value="">Semua Batch</option>
            {batches.map((b) => (
              <option key={b} value={b}>{b}</option>
            ))}
          </select>
          <select
            value={filterProduct}
            onChange={(e) => setFilterProduct(e.target.value)}
            className="border rounded px-3 py-1.5 text-sm"
          >
            <option value="">Semua Produk</option>
            {products.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
          <span className="text-sm text-gray-500">{leads.length} leads dengan koordinat</span>
        </div>
      </div>

      <div className="flex-1 relative">
        <div id="map" style={{ height: "calc(100vh - 140px)", width: "100%" }}></div>

        {selectedLead && (
          <div className="absolute top-4 right-4 bg-white rounded-lg shadow-lg p-4 w-80 z-[1000]">
            <div className="flex justify-between items-start mb-2">
              <h3 className="font-bold text-lg">{selectedLead.business_name}</h3>
              <button
                onClick={() => setSelectedLead(null)}
                className="text-gray-400 hover:text-gray-600"
              >
                ✕
              </button>
            </div>
            <div className="space-y-2 text-sm">
              <p><span className="text-gray-500">Alamat:</span> {selectedLead.address || "-"}</p>
              <p><span className="text-gray-500">Telepon:</span> {selectedLead.phone_number}</p>
              <p>
                <span className="text-gray-500">Rating Google:</span>{" "}
                <StarRating rating={selectedLead.google_rating} />
                {selectedLead.review_count && <span className="text-gray-400 ml-1">({selectedLead.review_count} ulasan)</span>}
              </p>
              {selectedLead.website_url && (
                <p>
                  <span className="text-gray-500">Website:</span>{" "}
                  <a href={selectedLead.website_url} target="_blank" rel="noopener" className="text-blue-600 hover:underline">
                    {selectedLead.website_url}
                  </a>
                </p>
              )}
              <p>
                <span className="text-gray-500">Status:</span>{" "}
                <span className="px-2 py-0.5 rounded text-white text-xs" style={{ backgroundColor: statusColors[selectedLead.status] || "#6b7280" }}>
                  {getStatusLabel(selectedLead.status)}
                </span>
              </p>
              {selectedLead.product_interest && (
                <p><span className="text-gray-500">Produk:</span> {selectedLead.product_interest}</p>
              )}
              {selectedLead.batch_name && (
                <p><span className="text-gray-500">Batch:</span> {selectedLead.batch_name}</p>
              )}
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <button
                onClick={() => handleWhatsApp(selectedLead.phone_number, selectedLead.business_name)}
                className="px-3 py-1.5 bg-green-500 text-white rounded text-sm hover:bg-green-600"
              >
                Blast WA
              </button>
              <a
                href={`/contacts?highlight=${selectedLead.id}`}
                className="px-3 py-1.5 bg-blue-500 text-white rounded text-sm hover:bg-blue-600"
              >
                Detail
              </a>
              <select
                onChange={(e) => {
                  if (e.target.value) handleUpdateStatus(selectedLead.id, e.target.value);
                }}
                className="px-3 py-1.5 border rounded text-sm"
                defaultValue=""
              >
                <option value="" disabled>Ubah Status</option>
                <option value="Contacted">Sudah Dihubungi</option>
                <option value="Replied">Dibalas</option>
                <option value="Negotiating">Negosiasi</option>
                <option value="Client">Jadi Klien</option>
                <option value="Lost">Hilang</option>
              </select>
            </div>
          </div>
        )}

        <div className="absolute bottom-4 left-4 bg-white rounded shadow p-3 z-[1000]">
          <div className="text-sm font-medium mb-2">Legenda Status:</div>
          <div className="flex flex-wrap gap-3 text-xs">
            {Object.entries(statusColors).map(([status, color]) => (
              <div key={status} className="flex items-center gap-1">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color }}></div>
                <span>{getStatusLabel(status)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
