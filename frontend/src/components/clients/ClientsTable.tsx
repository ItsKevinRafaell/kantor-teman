"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { apiFetch } from "../../lib/api";
import { downloadBlob } from "../../utils/download";
import Breadcrumb from "../Breadcrumb";
import Toast from "../Toast";
import Modal from "../Modal";
import { useAuth } from "../../contexts/AuthContext";
import type { Contact, ProjectData } from "../../types";

interface ContactWithLead extends Contact { lead_id?: number; }

// Client components
import AddClientModal from "./AddClientModal";
import EditClientModal from "./EditClientModal";
import ClientDetailModal from "./ClientDetailModal";
import ProjectModal from "./ProjectModal";
import NotesModal from "./NotesModal";
import ProposalModal from "./ProposalModal";
import ClientsTableRow from "./ClientsTableRow";

export default function ClientsTable() {
  const { isAdmin } = useAuth();
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [projects, setProjects] = useState<ProjectData[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [sortField, setSortField] = useState<"business_name" | "id">("id");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" | "info" } | null>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  // Delete modals
  const [deleteModal, setDeleteModal] = useState({ open: false, id: null as number | null, name: "" });
  const [deleteProjectId, setDeleteProjectId] = useState<string | null>(null);

  // Other modals
  const [addClientOpen, setAddClientOpen] = useState(false);
  const [editClientData, setEditClientData] = useState<{ open: boolean; contact: Contact | null }>({ open: false, contact: null });
  const [detailClientData, setDetailClientData] = useState<{ open: boolean; contact: Contact | null }>({ open: false, contact: null });
  const [projectModal, setProjectModal] = useState<{ open: boolean; contactId: number | null }>({ open: false, contactId: null });
  const [editingProject, setEditingProject] = useState<ProjectData | null>(null);
  const [notesModal, setNotesModal] = useState<{ open: boolean; contact: Contact | null }>({ open: false, contact: null });
  const [proposalModal, setProposalModal] = useState<{ open: boolean; contact: Contact | null }>({ open: false, contact: null });
  const [proposalSuccess, setProposalSuccess] = useState<{ open: boolean; url: string }>({ open: false, url: "" });
  const [copied, setCopied] = useState(false);
  const [contactLeadIds, setContactLeadIds] = useState<Record<number, number>>({});

  const fetchContacts = useCallback(async () => {
    try {
      const [cRes, pRes] = await Promise.all([
        apiFetch("/api/contacts"),
        apiFetch("/api/projects"),
      ]);
      if (cRes.ok) {
        const contactsData = await cRes.json();
        setContacts(contactsData);
        // Build contact.id → contact.lead_id map from contacts
        const leadMap: Record<number, number> = {};
        for (const c of contactsData) {
          if (c.lead_id) leadMap[c.id] = c.lead_id;
        }
        setContactLeadIds(leadMap);
      }
      if (pRes.ok) {
        setProjects(await pRes.json());
      }
    } finally { setLoading(false); }
  }, []);

  useEffect(() => {
    fetchContacts();
    intervalRef.current = setInterval(fetchContacts, 30000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [fetchContacts]);

  async function handleDelete() {
    if (!deleteModal.id) return;
    const res = await apiFetch(`/api/contacts/${deleteModal.id}`, { method: "DELETE" });
    if (res.ok) {
      setContacts(prev => prev.filter(c => c.id !== deleteModal.id));
      setToast({ message: "Klien berhasil dihapus.", type: "success" });
    } else {
      setToast({ message: "Gagal menghapus klien.", type: "error" });
    }
    setDeleteModal({ open: false, id: null, name: "" });
  }

  async function handleDeleteProject() {
    if (!deleteProjectId) return;
    const res = await apiFetch(`/api/projects/${deleteProjectId}`, { method: "DELETE" });
    if (res.ok) {
      setProjects(prev => prev.filter(p => p.id !== deleteProjectId));
      setToast({ message: "Project dihapus.", type: "success" });
    }
    setDeleteProjectId(null);
  }

  function handleCopyProposalLink(id: string) {
    const link = `${window.location.origin}/proposal/${id}`;
    navigator.clipboard.writeText(link);
    setToast({ message: "Link proposal tersalin!", type: "info" });
  }

  function copySuccessUrl() {
    navigator.clipboard.writeText(proposalSuccess.url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  const filteredContacts = contacts
    .filter(c => {
      if (!search) return true;
      const q = search.toLowerCase();
      return c.business_name.toLowerCase().includes(q) || (c.owner_name || "").toLowerCase().includes(q);
    })
    .sort((a, b) => {
      const valA = sortField === "business_name" ? a.business_name.toLowerCase() : String(a.id);
      const valB = sortField === "business_name" ? b.business_name.toLowerCase() : String(b.id);
      return sortDir === "asc" ? valA.localeCompare(valB) : valB.localeCompare(valA);
    });

  async function exportCSV() {
    const res = await apiFetch("/api/export/leads");
    if (res.ok) {
      const blob = await res.blob();
      downloadBlob(blob, "leads_export.csv");
    }
  }

  return (
    <div className="max-w-6xl space-y-6">
      <Toast message={toast?.message ?? null} type={toast?.type} onClose={() => setToast(null)} />

      {/* Delete modals */}
      <Modal open={deleteModal.open} title="Hapus Klien"
        message={`Hapus "${deleteModal.name}" dari buku klien?`}
        confirmLabel="Hapus" confirmClass="bg-red-600 hover:bg-red-700"
        onConfirm={handleDelete} onCancel={() => setDeleteModal({ open: false, id: null, name: "" })} />
      <Modal open={!!deleteProjectId} title="Hapus Project?"
        message="Project yang dihapus tidak bisa dikembalikan."
        confirmLabel="Hapus" confirmClass="bg-red-600 hover:bg-red-700"
        onConfirm={handleDeleteProject} onCancel={() => setDeleteProjectId(null)} />

      {/* Proposal success modal */}
      <Modal open={proposalSuccess.open} title="Proposal Berhasil Dibuat!"
        confirmLabel="Tutup" confirmClass="bg-gray-200 hover:bg-gray-300 text-gray-700"
        onConfirm={() => setProposalSuccess({ open: false, url: "" })}
        onCancel={() => setProposalSuccess({ open: false, url: "" })}>
        <div className="space-y-3 text-center">
          <div className="flex justify-center">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-green-500"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" /><polyline points="22 4 12 14.01 9 11.01" /></svg>
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-300">Kirim link ini ke klien:</p>
          <div className="flex items-center gap-2 bg-neutral-50 dark:bg-neutral-800 border border-gray-200 dark:border-gray-700 rounded-xl px-3 py-2.5">
            <input type="text" readOnly value={proposalSuccess.url}
              className="flex-1 text-xs bg-transparent text-gray-700 dark:text-gray-200 outline-none truncate" />
            <button onClick={copySuccessUrl}
              className="flex items-center gap-1 px-3 py-1.5 bg-brand-yellow hover:bg-amber-600 text-white text-xs font-semibold rounded-lg transition-colors">
              {copied ? "Tersalin!" : "Copy"}
            </button>
          </div>
        </div>
      </Modal>

      {/* Extracted modals */}
      <AddClientModal open={addClientOpen} onClose={() => setAddClientOpen(false)} onSuccess={fetchContacts} setToast={setToast} />
      <EditClientModal contact={editClientData.contact} open={editClientData.open} onClose={() => setEditClientData({ open: false, contact: null })} onSuccess={fetchContacts} setToast={setToast} />
      <ClientDetailModal contact={detailClientData.contact} open={detailClientData.open} onClose={() => setDetailClientData({ open: false, contact: null })} onCopyLink={handleCopyProposalLink} />
      <ProjectModal contactId={projectModal.contactId} contactLeadId={projectModal.contactId ? contactLeadIds[projectModal.contactId] : undefined} editingProject={editingProject} open={projectModal.open} onClose={() => { setProjectModal({ open: false, contactId: null }); setEditingProject(null); }} onSuccess={fetchContacts} setToast={setToast} />
      <NotesModal contact={notesModal.contact} open={notesModal.open} onClose={() => setNotesModal({ open: false, contact: null })} />
      <ProposalModal contact={proposalModal.contact} open={proposalModal.open} onClose={() => setProposalModal({ open: false, contact: null })} onSuccess={(url) => setProposalSuccess({ open: true, url })} setToast={setToast} />

      {/* Header */}
      <Breadcrumb items={[{ label: "Buku Klien" }]} showBack backHref="/" />
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">Buku Klien</h1>
          <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">Daftar klien aktif yang sudah dikonversi dari leads.</p>
        </div>
        <div className="flex gap-2">
          <button onClick={exportCSV} className="flex items-center gap-1.5 px-2.5 py-1.5 sm:px-4 sm:py-2.5 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 text-xs sm:text-sm font-semibold rounded-xl transition-colors">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" /></svg>
            Export CSV
          </button>
          {isAdmin && (
            <button onClick={() => setAddClientOpen(true)} className="flex items-center gap-1.5 px-2.5 py-1.5 sm:px-4 sm:py-2.5 bg-brand-yellow hover:bg-amber-600 text-white text-xs sm:text-sm font-semibold rounded-xl transition-colors">
              + Tambah Klien
            </button>
          )}
        </div>
      </div>

      {/* Search & Sort */}
      <div className="flex items-center gap-3 flex-wrap">
        <input type="text" value={search} onChange={e => setSearch(e.target.value)} placeholder="Cari nama bisnis atau owner..."
          className="flex-1 max-w-sm px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-neutral-50 dark:bg-neutral-800 dark:text-gray-200 focus:outline-none focus:ring-2 focus:ring-brand-yellow/50 transition" />
        <select value={sortField} onChange={e => setSortField(e.target.value as "business_name" | "id")}
          className="px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-xl text-xs bg-neutral-50 dark:bg-neutral-800 dark:text-gray-200 focus:outline-none focus:ring-2 focus:ring-brand-yellow/50">
          <option value="id">Urut: Terbaru</option>
          <option value="business_name">Urut: Nama</option>
        </select>
        <button onClick={() => setSortDir(d => d === "asc" ? "desc" : "asc")}
          className="px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-xl text-xs font-semibold bg-neutral-50 dark:bg-neutral-800 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors">
          {sortDir === "asc" ? "A-Z" : "Z-A"}
        </button>
      </div>

      {/* Loading state */}
      {loading && (
        <div className="bg-[var(--bg-surface)] rounded-2xl border border-[var(--border-default)] shadow-card overflow-hidden">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="flex gap-4 px-6 py-4 border-b border-[var(--border-subtle)] last:border-0 animate-pulse">
              <div className="h-4 bg-gray-100 dark:bg-gray-800 rounded w-1/4" />
              <div className="h-4 bg-gray-100 dark:bg-gray-800 rounded w-1/4" />
              <div className="h-4 bg-gray-100 dark:bg-gray-800 rounded w-1/6" />
              <div className="h-4 bg-gray-100 dark:bg-gray-800 rounded w-1/3 ml-auto" />
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && contacts.length === 0 && (
        <div className="text-center py-16 bg-[var(--bg-surface)] rounded-2xl border border-[var(--border-default)] text-gray-400 text-sm">
          Belum ada klien. Konversi lead dari halaman <span className="font-semibold text-gray-600 dark:text-gray-300">Semua Leads</span>.
        </div>
      )}

      {/* Table */}
      {!loading && contacts.length > 0 && (
        <div className="overflow-x-auto rounded-2xl shadow-sm border border-[var(--border-default)]">
          <table className="w-full bg-[var(--bg-surface)] text-sm">
            <thead className="bg-neutral-50 dark:bg-neutral-800 border-b border-[var(--border-default)]">
              <tr>{["#", "Nama Bisnis", "Nama Owner", "Nomor WA", "Proyek Aktif", "Nilai Kontrak", "Timeline", "Aksi"].map((h) => (
                <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide whitespace-nowrap">{h}</th>
              ))}</tr>
            </thead>
            <tbody className="divide-y divide-[var(--border-subtle)]">
              {filteredContacts.map((c, i) => (
                <ClientsTableRow
                  key={c.id}
                  contact={c}
                  projects={projects}
                  contactLeadId={contactLeadIds[c.id]}
                  index={i}
                  isAdmin={isAdmin}
                  onDetail={(contact) => setDetailClientData({ open: true, contact })}
                  onNotes={(contact) => setNotesModal({ open: true, contact })}
                  onProject={(contactId) => setProjectModal({ open: true, contactId })}
                  onProposal={(contact) => setProposalModal({ open: true, contact })}
                  onEdit={(contact) => setEditClientData({ open: true, contact })}
                  onDelete={(contact) => setDeleteModal({ open: true, id: contact.id, name: contact.business_name })}
                />
              ))}
            </tbody>
          </table>
          <div className="px-4 py-2 bg-neutral-50 dark:bg-neutral-800 border-t border-[var(--border-default)] text-xs text-gray-400">{contacts.length} klien aktif</div>
        </div>
      )}
    </div>
  );
}