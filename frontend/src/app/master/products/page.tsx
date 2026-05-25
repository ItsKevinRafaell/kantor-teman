"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { apiFetch } from "../../../lib/api";
import { Plus, Edit2, Trash2, X, Package } from "lucide-react";
import { formatRupiahInput, cleanRupiahInput } from "../../../utils/formatter";
import Pagination from "../../../components/Pagination";

interface Product {
  id: string;
  name: string;
  description: string | null;
  base_price: number;
  features: string[];
  category_id: string | null;
  category_name: string | null;
  is_active: boolean;
  is_retainer: boolean;
}

interface CategoryOption {
  id: string;
  name: string;
}

function formatRupiah(num: number): string {
  return new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", minimumFractionDigits: 0 }).format(num);
}

export default function ProductsPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [categories, setCategories] = useState<CategoryOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 20;
  const [modal, setModal] = useState(false);
  const [editing, setEditing] = useState<Product | null>(null);
  const [form, setForm] = useState({ name: "", description: "", base_price: 0, features: "", category_id: "", is_active: true, is_retainer: false });
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const fetchProducts = useCallback(async () => {
    try {
      const res = await apiFetch("/api/products");
      if (res.ok) setProducts(await res.json());
    } finally { setLoading(false); }
  }, []);

  const fetchCategories = useCallback(async () => {
    try {
      const res = await apiFetch("/api/categories?active_only=true");
      if (res.ok) setCategories(await res.json());
    } catch { /* silent */ }
  }, []);

  useEffect(() => {
    fetchProducts();
    fetchCategories();
    intervalRef.current = setInterval(fetchProducts, 5000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [fetchProducts]);

  function openNew() {
    setEditing(null);
    setForm({ name: "", description: "", base_price: 0, features: "", category_id: "", is_active: true, is_retainer: false });
    setModal(true);
  }

  function openEdit(p: Product) {
    setEditing(p);
    setForm({ name: p.name, description: p.description || "", base_price: p.base_price, features: p.features.join("\n"), category_id: p.category_id || "", is_active: p.is_active, is_retainer: p.is_retainer });
    setModal(true);
  }

  async function save() {
    const payload = {
      name: form.name,
      description: form.description || null,
      base_price: form.base_price,
      features: form.features.split(/[\n,]+/).map(f => f.trim()).filter(Boolean),
      category_id: form.category_id || null,
      is_active: form.is_active,
      is_retainer: form.is_retainer,
    };
    const method = editing ? "PUT" : "POST";
    const url = editing ? `/api/products/${editing.id}` : "/api/products";
    const res = await apiFetch(url, { method, body: JSON.stringify(payload) });
    if (res.ok) { setModal(false); fetchProducts(); }
  }

  async function deleteProduct(id: string) {
    const res = await apiFetch(`/api/products/${id}`, { method: "DELETE" });
    if (res.ok) fetchProducts();
  }

  const inputCls = "w-full px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-neutral-50 dark:bg-neutral-800 dark:text-gray-200 focus:outline-none focus:ring-2 focus:ring-brand-yellow/50 transition";

  if (loading) {
    return (
      <div className="max-w-6xl space-y-6">
        <div className="h-8 bg-gray-100 dark:bg-gray-800 rounded w-48 animate-pulse" />
        <div className="space-y-3">{[1, 2, 3].map(i => <div key={i} className="h-20 bg-gray-100 dark:bg-gray-800 rounded-2xl animate-pulse" />)}</div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">Katalog Produk</h1>
          <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">Master data layanan/produk — Single Source of Truth.</p>
        </div>
        <button onClick={openNew} className="flex items-center gap-1.5 px-2.5 py-1.5 sm:px-4 sm:py-2.5 bg-brand-yellow hover:bg-amber-600 text-white text-xs sm:text-sm font-semibold rounded-xl transition-colors">
          <Plus size={16} /> Tambah Produk
        </button>
      </div>

      {products.length === 0 ? (
        <div className="text-center py-12 bg-[var(--bg-surface)] rounded-2xl border border-[var(--border-default)] text-gray-400 text-sm">
          Belum ada produk. Tambahkan produk pertamamu.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-2xl shadow-sm border border-[var(--border-default)]">
          <table className="w-full bg-[var(--bg-surface)] text-sm">
            <thead className="bg-neutral-50 dark:bg-neutral-800 border-b border-[var(--border-default)]">
              <tr>
                {["Produk", "Kategori", "Harga Dasar", "Fitur", "Status", "Aksi"].map(h => (
                  <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border-subtle)]">
              {products.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE).map(p => (
                <tr key={p.id} className="hover:bg-[var(--bg-surface-hover)] transition-colors">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-lg bg-brand-yellow/10 flex items-center justify-center"><Package size={14} className="text-brand-yellow" /></div>
                      <div>
                        <p className="font-semibold text-neutral-800 dark:text-neutral-200">{p.name}</p>
                        {p.description && <p className="text-xs text-gray-400 truncate max-w-[200px]">{p.description}</p>}
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3"><span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400">{p.category_name || "—"}</span></td>
                  <td className="px-4 py-3 font-semibold text-neutral-800 dark:text-neutral-200">{formatRupiah(p.base_price)}{p.is_retainer && <span className="ml-1 text-[10px] text-amber-600 font-bold">/bln</span>}</td>
                  <td className="px-4 py-3 text-xs text-neutral-500 dark:text-neutral-400 max-w-[200px]">{p.features.length > 0 ? p.features.slice(0, 3).join(", ") + (p.features.length > 3 ? ` +${p.features.length - 3}` : "") : "—"}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1.5">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${p.is_active ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400" : "bg-gray-200 text-gray-500 dark:bg-gray-700 dark:text-gray-400"}`}>{p.is_active ? "Aktif" : "Nonaktif"}</span>
                      {p.is_retainer && <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">Retainer</span>}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1">
                      <button onClick={() => openEdit(p)} className="p-1.5 text-gray-400 hover:text-brand-yellow rounded-lg transition-colors"><Edit2 size={14} /></button>
                      <button onClick={() => deleteProduct(p.id)} className="p-1.5 text-gray-400 hover:text-red-500 rounded-lg transition-colors"><Trash2 size={14} /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <Pagination page={page} pageSize={PAGE_SIZE} total={products.length} onPageChange={setPage} itemLabel="produk" />
          <div className="px-4 py-2 bg-neutral-50 dark:bg-neutral-800 border-t border-[var(--border-default)] text-xs text-gray-400">{products.length} produk</div>
        </div>
      )}

      {/* Modal */}
      {modal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setModal(false)} />
          <div className="relative bg-[var(--bg-surface)] rounded-2xl shadow-2xl border border-[var(--border-default)] w-full max-w-md p-6 space-y-4 max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-neutral-900 dark:text-neutral-50">{editing ? "Edit Produk" : "Tambah Produk"}</h3>
              <button onClick={() => setModal(false)} className="p-1 text-gray-400 hover:text-gray-600"><X size={18} /></button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Nama Produk</label>
                <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} className={inputCls} placeholder="Contoh: Paket SEO Premium" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Deskripsi</label>
                <input value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} className={inputCls} placeholder="Deskripsi singkat (opsional)" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Harga Dasar (Rp)</label>
                  <input type="text" value={formatRupiahInput(form.base_price)} onChange={e => setForm(f => ({ ...f, base_price: cleanRupiahInput(e.target.value) }))} className={inputCls} />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Kategori</label>
                  <select value={form.category_id} onChange={e => setForm(f => ({ ...f, category_id: e.target.value }))} className={inputCls}>
                    <option value="">— Tanpa Kategori —</option>
                    {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Fitur (satu per baris)</label>
                <textarea value={form.features} onChange={e => setForm(f => ({ ...f, features: e.target.value }))} rows={4} className={inputCls + " resize-none"} placeholder="Riset keyword&#10;Optimasi on-page&#10;Backlink building" />
              </div>
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={form.is_active} onChange={e => setForm(f => ({ ...f, is_active: e.target.checked }))} className="w-4 h-4 rounded border-gray-300 text-brand-yellow focus:ring-brand-yellow/50" />
                <span className="text-sm text-gray-700 dark:text-gray-300 font-medium">Aktif</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={form.is_retainer} onChange={e => setForm(f => ({ ...f, is_retainer: e.target.checked }))} className="w-4 h-4 rounded border-gray-300 text-amber-500 focus:ring-amber-500/50" />
                <span className="text-sm text-gray-700 dark:text-gray-300 font-medium">Retainer (bayar bulanan)</span>
              </label>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button onClick={() => setModal(false)} className="px-4 py-2 text-sm font-semibold text-gray-600 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-xl transition-colors">Batal</button>
              <button onClick={save} className="px-4 py-2 text-sm font-semibold bg-brand-yellow hover:bg-amber-600 text-white rounded-xl transition-colors">Simpan</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
