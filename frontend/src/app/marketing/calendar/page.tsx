"use client";
import NativeSelect from "../../../components/ui/NativeSelect";

import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "../../../lib/api";
import Modal from "../../../components/Modal";
import Toast from "../../../components/Toast";
import { Plus, ChevronLeft, ChevronRight, Trash2, Settings } from "lucide-react";

interface ContentItem {
  id: string;
  title: string;
  type: string;
  schedule_date: string;
  google_event_id: string | null;
  status: string;
  created_at: string;
}

interface ContentType {
  value: string;
  label: string;
  color: string;
}

function getDaysInMonth(year: number, month: number): number {
  return new Date(year, month + 1, 0).getDate();
}

function getFirstDayOfMonth(year: number, month: number): number {
  return new Date(year, month, 1).getDay();
}

const MONTH_NAMES = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"];
const DAY_NAMES = ["Min", "Sen", "Sel", "Rab", "Kam", "Jum", "Sab"];

export default function ContentCalendarPage() {
  const [items, setItems] = useState<ContentItem[]>([]);
  const [contentTypes, setContentTypes] = useState<ContentType[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentDate, setCurrentDate] = useState(new Date());
  const [showModal, setShowModal] = useState(false);
  const [showTypesModal, setShowTypesModal] = useState(false);
  const [selectedDate, setSelectedDate] = useState("");
  const [form, setForm] = useState({ title: "", type: "", schedule_date: "", status: "DRAFT" });
  const [saving, setSaving] = useState(false);
  const [newType, setNewType] = useState({ value: "", label: "", color: "#f97316" });
  const [editingType, setEditingType] = useState<string | null>(null);
  const [editTypeForm, setEditTypeForm] = useState({ label: "", color: "" });
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" | "info" } | null>(null);

  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();

  const fetchItems = useCallback(async () => {
    try {
      const res = await apiFetch("/api/content-schedule");
      if (res.ok) setItems(await res.json());
    } finally { setLoading(false); }
  }, []);

  const fetchTypes = useCallback(async () => {
    try {
      const res = await apiFetch("/api/content-types");
      if (res.ok) setContentTypes(await res.json());
    } catch { /* non-critical */ }
  }, []);

  useEffect(() => { fetchItems(); fetchTypes(); }, [fetchItems, fetchTypes]);

  function getTypeColor(type: string): string {
    const found = contentTypes.find(t => t.value === type);
    return found ? found.color : "#6b7280";
  }

  function getTypeLabel(type: string): string {
    return contentTypes.find(t => t.value === type)?.label || type;
  }

  function prevMonth() {
    setCurrentDate(new Date(year, month - 1, 1));
  }

  function nextMonth() {
    setCurrentDate(new Date(year, month + 1, 1));
  }

  function openNewOnDate(dateStr: string) {
    setSelectedDate(dateStr);
    setForm({ title: "", type: contentTypes[0]?.value || "", schedule_date: dateStr, status: "DRAFT" });
    setShowModal(true);
  }

  async function addContentType() {
    if (!newType.value.trim() || !newType.label.trim()) return;
    const updated = [...contentTypes, { value: newType.value.trim().toUpperCase().replace(/\s+/g, "_"), label: newType.label.trim(), color: newType.color }];
    setContentTypes(updated);
    setNewType({ value: "", label: "", color: "#f97316" });
    await apiFetch("/api/content-types", { method: "PUT", body: JSON.stringify(updated) });
  }

  async function removeContentType(value: string) {
    const updated = contentTypes.filter(t => t.value !== value);
    setContentTypes(updated);
    await apiFetch("/api/content-types", { method: "PUT", body: JSON.stringify(updated) });
  }

  function startEditType(t: ContentType) {
    setEditingType(t.value);
    setEditTypeForm({ label: t.label, color: t.color });
  }

  async function saveEditType(value: string) {
    if (!editTypeForm.label.trim()) { setEditingType(null); return; }
    const updated = contentTypes.map(t => t.value === value ? { ...t, label: editTypeForm.label.trim(), color: editTypeForm.color } : t);
    setContentTypes(updated);
    setEditingType(null);
    await apiFetch("/api/content-types", { method: "PUT", body: JSON.stringify(updated) });
  }

  async function createSchedule() {
    if (!form.title || !form.schedule_date) return;
    setSaving(true);
    try {
      const res = await apiFetch("/api/content-schedule", {
        method: "POST",
        body: JSON.stringify(form),
      });
      if (res.ok) {
        const created = await res.json().catch(() => null);
        setShowModal(false);
        fetchItems();
        if (created && !created.google_event_id) {
          setToast({
            message: "Jadwal disimpan di web, tapi belum ter-sync ke Google Calendar. Cek Settings → test-calendar.",
            type: "info",
          });
        } else {
          setToast({ message: "Jadwal dibuat & disync ke Google Calendar.", type: "success" });
        }
      } else {
        setToast({ message: "Gagal membuat jadwal.", type: "error" });
      }
    } finally { setSaving(false); }
  }

  async function deleteSchedule(id: string) {
    const res = await apiFetch(`/api/content-schedule/${id}`, { method: "DELETE" });
    if (res.ok) { setToast({ message: "Berhasil dihapus.", type: "success" }); setItems(prev => prev.filter(i => i.id !== id)); }
    else { setToast({ message: "Gagal hapus.", type: "error" }); }
    setDeleteId(null);
  }

  async function updateStatus(id: string, status: string) {
    await apiFetch(`/api/content-schedule/${id}`, {
      method: "PUT",
      body: JSON.stringify({ status }),
    });
    fetchItems();
  }

  const daysInMonth = getDaysInMonth(year, month);
  const firstDay = getFirstDayOfMonth(year, month);

  const calendarDays: (number | null)[] = [];
  for (let i = 0; i < firstDay; i++) calendarDays.push(null);
  for (let d = 1; d <= daysInMonth; d++) calendarDays.push(d);

  function getItemsForDay(day: number): ContentItem[] {
    const dateStr = `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
    return items.filter(i => i.schedule_date === dateStr);
  }

  const today = new Date();
  const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;

  if (loading) {
    return (
      <div className="max-w-6xl space-y-6">
      <Toast message={toast?.message ?? null} type={toast?.type} onClose={() => setToast(null)} />
      <Modal
        open={!!deleteId}
        title="Hapus Jadwal?"
        message="Event dihapus dari kalender app + Google Calendar (jika ter-sync)."
        confirmLabel="Hapus"
        confirmClass="bg-red-600 hover:bg-red-700"
        onConfirm={() => deleteId !== null && deleteSchedule(deleteId!)}
        onCancel={() => setDeleteId(null)}
      />
        <div className="h-8 bg-neutral-100 dark:bg-neutral-800 rounded w-48 animate-pulse" />
        <div className="h-96 bg-neutral-100 dark:bg-neutral-800 rounded-2xl animate-pulse" />
      </div>
    );
  }

  return (
    <div className="max-w-6xl space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">Kalender</h1>
          <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-0.5">Kalender umum — meeting, deadline, konten, reminder.</p>
          <p className="mt-1 inline-flex items-center rounded-full border border-amber-200 bg-amber-50 px-2.5 py-0.5 text-[11px] font-semibold text-amber-800 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-200">
            Google Calendar: one-way (web → Google). Event di Google tidak ditarik ke sini.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setShowTypesModal(true)} className="btn-ghost flex items-center gap-1.5 text-xs">
            <Settings size={14} /> Kelola Tipe
          </button>
          <button onClick={() => openNewOnDate(todayStr)} className="btn-primary flex items-center gap-1.5 text-sm text-white">
            <Plus size={16} /> Jadwalkan
          </button>
        </div>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap items-center gap-3">
        {contentTypes.map(t => (
          <div key={t.value} className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: t.color }} />
            <span className="text-xs text-neutral-600 dark:text-neutral-400">{t.label}</span>
          </div>
        ))}
      </div>

      {/* Calendar */}
      <div className="card overflow-hidden">
        {/* Month Navigation */}
        <div className="px-5 py-4 border-b border-[var(--border-default)] flex items-center justify-between">
          <button onClick={prevMonth} className="p-2 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded-xl transition-colors">
            <ChevronLeft size={18} className="text-neutral-600 dark:text-neutral-400" />
          </button>
          <h2 className="text-base font-bold text-neutral-900 dark:text-neutral-50">
            {MONTH_NAMES[month]} {year}
          </h2>
          <button onClick={nextMonth} className="p-2 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded-xl transition-colors">
            <ChevronRight size={18} className="text-neutral-600 dark:text-neutral-400" />
          </button>
        </div>

        {/* Day Headers */}
        <div className="grid grid-cols-7 border-b border-[var(--border-default)]">
          {DAY_NAMES.map(d => (
            <div key={d} className="px-2 py-2 text-center text-[11px] font-semibold text-neutral-500 dark:text-neutral-400 uppercase">
              {d}
            </div>
          ))}
        </div>

        {/* Calendar Grid */}
        <div className="grid grid-cols-7">
          {calendarDays.map((day, idx) => {
            if (day === null) {
              return <div key={`empty-${idx}`} className="min-h-[100px] border-b border-r border-[var(--border-subtle)] bg-neutral-50/50 dark:bg-neutral-900/30" />;
            }
            const dateStr = `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
            const dayItems = getItemsForDay(day);
            const isToday = dateStr === todayStr;

            return (
              <div
                key={day}
                onClick={() => openNewOnDate(dateStr)}
                className={`min-h-[100px] border-b border-r border-[var(--border-subtle)] p-1.5 cursor-pointer hover:bg-neutral-50 dark:hover:bg-neutral-800/50 transition-colors ${isToday ? "bg-amber-50/50 dark:bg-amber-900/10" : ""}`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className={`text-xs font-semibold w-6 h-6 flex items-center justify-center rounded-full ${isToday ? "bg-brand-yellow text-white" : "text-neutral-600 dark:text-neutral-400"}`}>
                    {day}
                  </span>
                </div>
                <div className="space-y-0.5">
                  {dayItems.map(item => (
                    <div
                      key={item.id}
                      onClick={e => e.stopPropagation()}
                      style={{ backgroundColor: getTypeColor(item.type) }}
                      className={`group relative px-1.5 py-0.5 rounded text-[10px] font-medium text-white truncate ${item.status === "PUBLISHED" ? "opacity-60" : ""}`}
                    >
                      {item.title}
                      <div className="absolute right-0 top-0 hidden group-hover:flex items-center gap-0.5 bg-black/70 rounded px-1 py-0.5">
                        <select
                          value={item.status}
                          onChange={e => updateStatus(item.id, e.target.value)}
                          onClick={e => e.stopPropagation()}
                          className="text-[9px] bg-transparent text-white border-0 outline-none cursor-pointer"
                        >
                          <option value="DRAFT">Draft</option>
                          <option value="SCHEDULED">Scheduled</option>
                          <option value="PUBLISHED">Published</option>
                        </select>
                        <button onClick={() => setDeleteId(item.id)} className="text-red-300 hover:text-red-100">
                          <Trash2 size={10} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Create Schedule Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-fade-in">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setShowModal(false)} />
          <div className="relative bg-[var(--bg-surface)] rounded-2xl shadow-modal border border-[var(--border-default)] w-full max-w-md p-6 space-y-4 animate-slide-up">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-neutral-900 dark:text-neutral-50">Jadwalkan Konten</h3>
              <button onClick={() => setShowModal(false)} className="p-1 text-neutral-400 hover:text-neutral-600">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
              </button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-neutral-500 uppercase mb-1">Judul Konten</label>
                <input value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} className="input-field" placeholder="Tips SEO untuk UMKM" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-neutral-500 uppercase mb-1">Tipe Konten</label>
                <NativeSelect value={form.type} onChange={v => setForm(f => ({ ...f, type: v }))} clearable={false} options={contentTypes.map((t: any) => ({ value: t.value, label: t.label }))} />
              </div>
              <div>
                <label className="block text-xs font-semibold text-neutral-500 uppercase mb-1">Tanggal Tayang</label>
                <input type="date" value={form.schedule_date} onChange={e => setForm(f => ({ ...f, schedule_date: e.target.value }))} className="input-field" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-neutral-500 uppercase mb-1">Status</label>
                <NativeSelect value={form.status} onChange={v => setForm(f => ({ ...f, status: v }))} clearable={false} options={[{value:"DRAFT",label:"Draft"},{value:"SCHEDULED",label:"Scheduled"},{value:"PUBLISHED",label:"Published"},{value:"CANCELLED",label:"Cancelled"}]} />
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button onClick={() => setShowModal(false)} className="btn-ghost">Batal</button>
              <button onClick={createSchedule} disabled={saving} className="btn-primary text-white">
                {saving ? "Menyimpan..." : "Simpan"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Manage Content Types Modal */}
      {showTypesModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-fade-in">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setShowTypesModal(false)} />
          <div className="relative bg-[var(--bg-surface)] rounded-2xl shadow-modal border border-[var(--border-default)] w-full max-w-md p-6 space-y-4 animate-slide-up">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-neutral-900 dark:text-neutral-50">Kelola Tipe Konten</h3>
              <button onClick={() => setShowTypesModal(false)} className="p-1 text-neutral-400 hover:text-neutral-600">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
              </button>
            </div>

            {/* Existing types */}
            <div className="space-y-2 max-h-60 overflow-y-auto">
              {contentTypes.map(t => (
                <div key={t.value} className="flex items-center justify-between px-3 py-2 rounded-xl bg-neutral-50 dark:bg-neutral-800/50">
                  {editingType === t.value ? (
                    <div className="flex items-center gap-2 flex-1">
                      <input
                        type="color"
                        value={editTypeForm.color}
                        onChange={e => setEditTypeForm(f => ({ ...f, color: e.target.value }))}
                        className="w-7 h-7 rounded border border-neutral-200 dark:border-neutral-700 cursor-pointer shrink-0"
                      />
                      <input
                        autoFocus
                        value={editTypeForm.label}
                        onChange={e => setEditTypeForm(f => ({ ...f, label: e.target.value }))}
                        onBlur={() => saveEditType(t.value)}
                        onKeyDown={e => { if (e.key === "Enter") saveEditType(t.value); if (e.key === "Escape") setEditingType(null); }}
                        className="flex-1 text-sm px-2 py-1 border border-brand-yellow rounded bg-transparent text-neutral-800 dark:text-neutral-200 outline-none"
                      />
                    </div>
                  ) : (
                    <div className="flex items-center gap-2 flex-1 cursor-pointer" onClick={() => startEditType(t)}>
                      <div className="w-4 h-4 rounded-full shrink-0" style={{ backgroundColor: t.color }} />
                      <span className="text-sm text-neutral-800 dark:text-neutral-200 font-medium">{t.label}</span>
                      <span className="text-[10px] text-neutral-400 font-mono">{t.value}</span>
                    </div>
                  )}
                  <button onClick={() => removeContentType(t.value)} className="p-1 text-neutral-400 hover:text-red-500 transition-colors ml-2 shrink-0">
                    <Trash2 size={13} />
                  </button>
                </div>
              ))}
            </div>

            {/* Add new type */}
            <div className="border-t border-[var(--border-default)] pt-4">
              <p className="text-xs font-semibold text-neutral-500 uppercase mb-2">Tambah Tipe Baru</p>
              <div className="flex items-center gap-2">
                <input
                  value={newType.label}
                  onChange={e => setNewType(n => ({ ...n, label: e.target.value, value: e.target.value.toUpperCase().replace(/\s+/g, "_") }))}
                  className="input-field flex-1"
                  placeholder="Nama tipe (misal: IG Story)"
                />
                <input
                  type="color"
                  value={newType.color}
                  onChange={e => setNewType(n => ({ ...n, color: e.target.value }))}
                  className="w-10 h-10 rounded-lg border border-neutral-200 dark:border-neutral-700 cursor-pointer shrink-0"
                />
                <button onClick={addContentType} className="btn-primary text-xs px-3 py-2 shrink-0 text-white">
                  <Plus size={14} />
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
