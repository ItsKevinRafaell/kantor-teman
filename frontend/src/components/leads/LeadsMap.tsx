"use client";

import { useEffect, useState, useMemo, useRef } from "react";
import { apiFetch } from "../../lib/api";
import { Star, X } from "lucide-react";
import { getLeadStatusLabel } from "../../types/lead";

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
  Closed: "#22c55e",
  "Closed/Client": "#22c55e",
  Lost: "#6b7280",
};

const INDONESIA_CENTER: [number, number] = [-2.5, 118];
const INDONESIA_BOUNDS: [[number, number], [number, number]] = [[-11.2, 94.5], [6.3, 141.1]];

function hasValidIndonesiaCoordinate(lead: LeadMap) {
  const lat = Number(lead.latitude);
  const lng = Number(lead.longitude);
  return Number.isFinite(lat) && Number.isFinite(lng) && lat >= -11.5 && lat <= 6.5 && lng >= 94 && lng <= 142;
}

function StarRating({ rating }: { rating: number | null }) {
  if (rating === null) return <span className="text-gray-400">-</span>;
  const filled = Math.round(rating);
  return (
    <span className="inline-flex items-center gap-0.5 text-yellow-500">
      {[1,2,3,4,5].map(i => (
        <Star key={i} size={11} fill={i <= filled ? "currentColor" : "none"} className={i <= filled ? "" : "text-gray-300"} />
      ))}
    </span>
  );
}

interface Props {
  height?: string;
  onShowDetail?: (leadId: number) => void;
}

export default function LeadsMap({ height = "calc(100vh - 220px)", onShowDetail }: Props) {
  const [leads, setLeads] = useState<LeadMap[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [filterBatch, setFilterBatch] = useState("");
  const [filterProduct, setFilterProduct] = useState("");
  const [selectedLead, setSelectedLead] = useState<LeadMap | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const mapRef = useRef<any>(null);
  const mapContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setLoading(true);
    setError("");
    const params = new URLSearchParams();
    if (filterStatus) params.append("status", filterStatus);
    if (filterBatch) params.append("batch_name", filterBatch);
    if (filterProduct) params.append("product_interest", filterProduct);

    apiFetch(`/api/leads/map?${params.toString()}`)
      .then((res) => res.json())
      .then((data) => {
        if (Array.isArray(data)) {
          const validLeads = data.filter(hasValidIndonesiaCoordinate);
          setLeads(validLeads);
          if (validLeads.length === 0) {
            setError("Tidak ada leads dengan koordinat. Jalankan scraper untuk mendapatkan leads dengan latitude & longitude.");
          }
        } else {
          setError(data.detail || "Gagal memuat data");
        }
      })
      .catch(() => setError("Gagal menghubungi server"))
      .finally(() => setLoading(false));
  }, [filterStatus, filterBatch, filterProduct]);

  useEffect(() => {
    if (typeof window === "undefined" || loading || leads.length === 0 || !mapContainerRef.current) return;
    const container = mapContainerRef.current;
    let resizeObserver: ResizeObserver | null = null;
    let visibilityHandler: (() => void) | null = null;

    const initMap = async () => {
      const L = await import("leaflet");

      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }

      const map = L.map(container, {
        maxBounds: INDONESIA_BOUNDS,
        maxBoundsViscosity: 0.2,
      }).setView(INDONESIA_CENTER, 5);

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

      const markerBounds: Array<[number, number]> = [];
      leads.forEach((lead) => {
        const latLng: [number, number] = [Number(lead.latitude), Number(lead.longitude)];
        markerBounds.push(latLng);
        const marker = L.marker(latLng, {
          icon: createMarkerIcon(statusColors[lead.status] || "#6b7280")
        }).addTo(map);
        marker.on("click", () => setSelectedLead(lead));
      });

      if (markerBounds.length > 1) {
        map.fitBounds(markerBounds, { padding: [28, 28], maxZoom: 13 });
      } else if (markerBounds.length === 1) {
        map.setView(markerBounds[0], 13);
      } else {
        map.fitBounds(INDONESIA_BOUNDS, { padding: [20, 20] });
      }

      mapRef.current = map;
      resizeObserver = new ResizeObserver(() => map.invalidateSize());
      resizeObserver.observe(container);
      visibilityHandler = () => {
        if (document.visibilityState === "visible") setTimeout(() => map.invalidateSize(), 80);
      };
      document.addEventListener("visibilitychange", visibilityHandler);
      setTimeout(() => map.invalidateSize(), 150);
      setTimeout(() => map.invalidateSize(), 600);
    };

    initMap();

    return () => {
      if (resizeObserver) resizeObserver.disconnect();
      if (visibilityHandler) document.removeEventListener("visibilitychange", visibilityHandler);
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
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
    try {
      const res = await apiFetch(`/api/leads/${leadId}/status`, {
        method: "PATCH",
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

  return (
    <div className="flex flex-col" style={{ height }}>
      <div className="bg-white dark:bg-neutral-900 shadow p-3 flex flex-wrap gap-3 items-center border-b border-neutral-200 dark:border-neutral-700">
        <div className="flex gap-3 items-center flex-wrap">
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="border rounded px-2 py-1 text-sm bg-white dark:bg-neutral-800"
          >
            <option value="">Semua Status</option>
            <option value="Scraped">Belum Dihubungi</option>
            <option value="Contacted">Sudah Dihubungi</option>
            <option value="Replied">Dibalas</option>
            <option value="Negotiating">Negosiasi</option>
            <option value="Closed">Jadi Klien</option>
            <option value="Lost">Hilang</option>
          </select>
          <select
            value={filterBatch}
            onChange={(e) => setFilterBatch(e.target.value)}
            className="border rounded px-2 py-1 text-sm bg-white dark:bg-neutral-800"
          >
            <option value="">Semua Batch</option>
            {batches.map((b) => (
              <option key={b} value={b}>{b}</option>
            ))}
          </select>
          <select
            value={filterProduct}
            onChange={(e) => setFilterProduct(e.target.value)}
            className="border rounded px-2 py-1 text-sm bg-white dark:bg-neutral-800"
          >
            <option value="">Semua Produk</option>
            {products.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
          <span className="text-sm text-gray-500">{leads.length} prospek berkoordinat</span>
        </div>
      </div>

      {loading ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-sm text-neutral-500">Memuat peta...</div>
        </div>
      ) : error ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-sm text-neutral-500 text-center max-w-md p-6">{error}</div>
        </div>
      ) : (
        <div className="flex-1 relative">
          <div ref={mapContainerRef} className="w-full h-full" style={{ minHeight: "400px" }} />

          {selectedLead && (
            <div className="absolute top-4 right-4 bg-white dark:bg-neutral-800 rounded-lg shadow-lg p-4 w-72 z-[1000]">
              <div className="flex justify-between items-start mb-2">
                <h3 className="font-bold">{selectedLead.business_name}</h3>
                <button
                  onClick={() => setSelectedLead(null)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <X size={14} />
                </button>
              </div>
              <div className="space-y-1 text-sm">
                <p><span className="text-gray-500">Alamat:</span> {selectedLead.address || "-"}</p>
                <p><span className="text-gray-500">Telepon:</span> {selectedLead.phone_number}</p>
                <p>
                  <span className="text-gray-500">Rating:</span>{" "}
                  <StarRating rating={selectedLead.google_rating} />
                  {selectedLead.review_count && <span className="text-gray-400 ml-1">({selectedLead.review_count})</span>}
                </p>
                {selectedLead.website_url && (
                  <p>
                    <span className="text-gray-500">Website:</span>{" "}
                    <a href={selectedLead.website_url} target="_blank" rel="noopener" className="text-blue-600 hover:underline text-xs">
                      {selectedLead.website_url.substring(0, 30)}...
                    </a>
                  </p>
                )}
                <p>
                  <span className="text-gray-500">Status:</span>{" "}
                  <span className="px-2 py-0.5 rounded text-white text-xs" style={{ backgroundColor: statusColors[selectedLead.status] || "#6b7280" }}>
                    {getLeadStatusLabel(selectedLead.status)}
                  </span>
                </p>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  onClick={() => handleWhatsApp(selectedLead.phone_number, selectedLead.business_name)}
                  className="px-2 py-1 bg-green-500 text-white rounded text-xs hover:bg-green-600"
                >
                  WhatsApp
                </button>
                {onShowDetail && (
                  <button
                    onClick={() => onShowDetail(selectedLead.id)}
                    className="px-2 py-1 bg-blue-500 text-white rounded text-xs hover:bg-blue-600"
                  >
                    Detail
                  </button>
                )}
                <select
                  onChange={(e) => {
                    if (e.target.value) handleUpdateStatus(selectedLead.id, e.target.value);
                  }}
                  className="px-2 py-1 border rounded text-xs bg-white dark:bg-neutral-800"
                  defaultValue=""
                >
                  <option value="" disabled>Ubah Status</option>
                  <option value="Contacted">Dihubungi</option>
                  <option value="Replied">Dibalas</option>
                  <option value="Negotiating">Negosiasi</option>
                  <option value="Closed">Jadi Klien</option>
                  <option value="Lost">Hilang</option>
                </select>
              </div>
            </div>
          )}

          <div className="absolute bottom-4 left-4 bg-white dark:bg-neutral-800 rounded shadow p-2 z-[1000]">
            <div className="text-xs font-medium mb-1">Legenda:</div>
            <div className="flex flex-wrap gap-2 text-[10px]">
              {Object.entries(statusColors).map(([status, color]) => (
                <div key={status} className="flex items-center gap-1">
                  <div className="w-2 h-2 rounded-full" style={{ backgroundColor: color }}></div>
                  <span>{getLeadStatusLabel(status)}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
