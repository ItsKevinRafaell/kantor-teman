"use client";
import { inputCls, inputClsLarge } from "../../../lib/inputCls";

import { useState, useEffect, useCallback, useRef } from "react";
import { apiFetch } from "../../../lib/api";
import { Plus, Edit2, Trash2, X, Grid3X3, Search } from "lucide-react";
import Modal from "../../../components/Modal";
import Toast from "../../../components/Toast";
import Pagination from "../../../components/Pagination";

interface Category {
  id: string;
  name: string;
  description: string | null;
  is_active: boolean;
}

export default function CategoriesPage() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(false);
  const [editing, setEditing] = useState<Category | null>(null);
  const [form, setForm] = useState({ name: "", description: "", is_active: true });
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" | "info" } | null>(null);
  const [statusFilter, setStatusFilter] = useState<"all" | "active" | "inactive">("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 15;
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const fetchCategories = useCallback(async () => {
    try {
      const res = await apiFetch("/api/categories");
      if (res.ok) setCategories(await res.json());
    } finally { setLoading(false); }
  }, []);

  useEffect(() => {
    fetchCategories();
    intervalRef.current = setInterval(fetchCategories, 30000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [fetchCategories]);

  const normalizedSearch = searchQuery.trim().toLowerCase();
  const filteredCategories = categories.filter(c => {
    if (statusFilter === "active" && !c.is_active) return false;
    if (statusFilter === "inactive" && c.is_active) return false;
    if (!normalizedSearch) return true;
    return [c.name, c.description || ""].some(v => v.toLowerCase().includes(normalizedSearch));
  });

  useEffect(() => {
    const totalPages = Math.max(1, Math.ceil(filteredCategories.length / PAGE_SIZE));
    if (page > totalPages) setPage(totalPages);
  }, [filteredCategories.length, page]);

  useEffect(() => {
    setPage(1);
  }, [statusFilter, searchQuery]);

  function openNew() {
    setEditing(null);
    setForm({ name: "", description: "", is_active: true });
    setModal(true);
  }

  function openEdit(c: Category) {
    setEditing(c);
    setForm({ name: c.name, description: c.description || "", is_active: c.is_active });
    setModal(true);
  }

  async function save() {
    if (!form.name.trim()) return;
    const payload = { name: form.name, description: form.description || null, is_active: form.is_active };
    const method = editing ? "PUT" : "POST";
    const url = editing ? `/api/categories/${editing.id}` : "/api/categories";
    const res = await apiFetch(url, { method, body: JSON.stringify(payload) });
    if (res.ok) { setToast({ message: "Kategori berhasil disimpan.", type: "success" }); setModal(false); fetchCategories(); }
  }

  async function deleteCategory(id: string) {
    const res = await apiFetch(`/api/categories/${id}`, { method: "DELETE" });
    if (res.ok) { setToast({ message: "Berhasil dihapus.", type: "success" }); fetchCategories(); }
    else { setToast({ message: "Gagal hapus.", type: "error" }); }
    setDeleteId(null);
  }


  if (loading) {
    return (
      <div className="max-w-6xl space-y-6">
      <Toast message={toast?.message ?? null} type={toast?.type} onClose={() => setToast(null)} />
      <Modal
        open={!!deleteId}
        title="Hapus Kategori?"
        message="Item yang dihapus tidak bisa dikembalikan."
        confirmLabel="Hapus"
        confirmClass="bg-red-600 hover:bg-red-700"
        onConfirm={() => deleteId !== null && deleteCategory(deleteId!)}
        onCancel={() => setDeleteId(null)}
      />
        <div className="h-8 bg-gray-100 dark:bg-gray-800 rounded w-48 animate-pulse" />
        <div className="space-y-3">{[1, 2, 3].map(i => <div key={i} className="h-16 bg-gray-100 dark:bg-gray-800 rounded-2xl animate-pulse" />)}</div>
      </div>
    );
  }

  const pagedCategories = filteredCategories.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  return (
    <div className="max-w-6xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">Kategori Produk</h1>
          <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">Kelola kategori untuk mengelompokkan produk/layanan.</p>
        </div>
        <button onClick={openNew} className="flex items-center gap-1.5 px-2.5 py-1.5 sm:px-4 sm:py-2.5 bg-brand-yellow hover:bg-amber-600 text-white text-xs sm:text-sm font-semibold rounded-xl transition-colors">
          <Plus size={16} /> Tambah Kategori
        </button>
      </div>

      <div className="grid grid-cols-1 gap-3 rounded-2xl border border-amber-100 bg-white p-3 shadow-sm sm:grid-cols-3 dark:border-amber-900/40 dark:bg-[var(--bg-surface)]">
        <label className="relative sm:col-span-2">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
          <input value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
            placeholder="Cari kategori atau deskripsi..."
            className="w-full rounded-xl border border-gray-200 bg-white py-2 pl-9 pr-3 text-sm outline-none focus:ring-2 focus:ring-amber-300 dark:border-gray-700 dark:bg-neutral-800/70 dark:text-neutral-100" />
        </label>
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value as "all" | "active" | "inactive")}
          className="rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-amber-300 dark:border-gray-700 dark:bg-neutral-800/70 dark:text-neutral-100">
          <option value="all">Semua status</option>
          <option value="active">Aktif</option>
          <option value="inactive">Nonaktif</option>
        </select>
      </div>

      {categories.length === 0 ? (
        <div className="text-center py-12 bg-[var(--bg-surface)] rounded-2xl border border-[var(--border-default)] text-gray-400 text-sm">
          Belum ada kategori. Tambahkan kategori pertamamu.
        </div>
      ) : filteredCategories.length === 0 ? (
        <div className="rounded-2xl border border-[var(--border-default)] bg-[var(--bg-surface)] py-12 text-center text-sm text-gray-400">
          Tidak ada kategori yang cocok dengan filter.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-2xl shadow-sm border border-[var(--border-default)]">
          <table className="w-full bg-[var(--bg-surface)] text-sm">
            <thead className="bg-neutral-50 dark:bg-neutral-800 border-b border-[var(--border-default)]">
              <tr>
                {["Kategori", "Deskripsi", "Status", "Aksi"].map(h => (
                  <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border-subtle)]">
              {pagedCategories.map(c => (
                <tr key={c.id} className="hover:bg-[var(--bg-surface-hover)] transition-colors">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-lg bg-brand-yellow/10 flex items-center justify-center"><Grid3X3 size={14} className="text-brand-yellow" /></div>
                      <span className="font-semibold text-neutral-800 dark:text-neutral-200">{c.name}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-neutral-500 dark:text-neutral-400 text-xs max-w-[300px]">{c.description || "—"}</td>
                  <td className="px-4 py-3"><span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${c.is_active ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400" : "bg-gray-200 text-gray-500 dark:bg-gray-700 dark:text-gray-400"}`}>{c.is_active ? "Aktif" : "Nonaktif"}</span></td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1">
                      <button onClick={() => openEdit(c)} className="p-1.5 text-gray-400 hover:text-brand-yellow rounded-lg transition-colors"><Edit2 size={14} /></button>
                      <button onClick={() => setDeleteId(c.id)} className="p-1.5 text-gray-400 hover:text-red-500 rounded-lg transition-colors"><Trash2 size={14} /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <Pagination page={page} pageSize={PAGE_SIZE} total={filteredCategories.length} onPageChange={setPage} itemLabel="kategori" />
        </div>
      )}

      {/* Modal */}
      {modal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setModal(false)} />
          <div className="relative bg-[var(--bg-surface)] rounded-2xl shadow-2xl border border-[var(--border-default)] w-full max-w-md p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-neutral-900 dark:text-neutral-50">{editing ? "Edit Kategori" : "Tambah Kategori"}</h3>
              <button onClick={() => setModal(false)} className="p-1 text-gray-400 hover:text-gray-600"><X size={18} /></button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Nama Kategori</label>
                <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} className={inputCls} placeholder="Contoh: SEO, Web Development, Sosial Media" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Deskripsi Singkat</label>
                <textarea value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} rows={3} className={inputClsLarge} placeholder="Deskripsi opsional tentang kategori ini..." />
              </div>
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={form.is_active} onChange={e => setForm(f => ({ ...f, is_active: e.target.checked }))} className="w-4 h-4 rounded border-gray-300 text-brand-yellow focus:ring-brand-yellow/50" />
                <span className="text-sm text-gray-700 dark:text-gray-300 font-medium">Aktif</span>
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
