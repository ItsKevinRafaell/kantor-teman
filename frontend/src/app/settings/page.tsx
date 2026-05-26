"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { getUserInfo, clearToken, apiFetch } from "../../lib/api";
import Toast from "../../components/Toast";

type Tab = "profile" | "api";

interface AIProxy {
  id: string;
  name: string;
  base_url: string;
  api_key: string;
  model: string;
  is_active: boolean;
  created_at: string;
}

const EMPTY_PROXY_FORM = { name: "", base_url: "", api_key: "", model: "" };

export default function SettingsPage() {
  const router = useRouter();
  const [tab, setTab] = useState<Tab>("profile");
  const [userInfo, setUserInfo] = useState({ name: "", email: "" });
  const [name, setName] = useState("");
  const [currentPw, setCurrentPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [fonnteToken, setFonnteToken] = useState("");
  const [followupEnabled, setFollowupEnabled] = useState(false);
  const [followupHour, setFollowupHour] = useState("9");
  const [googleApiKey, setGoogleApiKey] = useState("");
  const [googleCalendarId, setGoogleCalendarId] = useState("");
  const [googleServiceAccountJson, setGoogleServiceAccountJson] = useState("");
  const [adminWa, setAdminWa] = useState("");
  const [adminName, setAdminName] = useState("");
  const [testingCalendar, setTestingCalendar] = useState(false);
  const [cmsUrl, setCmsUrl] = useState("");
  const [cmsApiToken, setCmsApiToken] = useState("");
  const [externalLeadApiKey, setExternalLeadApiKey] = useState("");
  const [regeneratingKey, setRegeneratingKey] = useState(false);
  const [smtpHost, setSmtpHost] = useState("");
  const [smtpPort, setSmtpPort] = useState("587");
  const [smtpUser, setSmtpUser] = useState("");
  const [smtpPassword, setSmtpPassword] = useState("");
  const [smtpFrom, setSmtpFrom] = useState("");
  // Content Generator AI (separate from chat proxy)
  const [contentAiBaseUrl, setContentAiBaseUrl] = useState("");
  const [contentAiApiKey, setContentAiApiKey] = useState("");
  const [contentAiModel, setContentAiModel] = useState("");
  // AI Proxies (for chat)
  const [proxies, setProxies] = useState<AIProxy[]>([]);
  const [showProxyForm, setShowProxyForm] = useState(false);
  const [editingProxy, setEditingProxy] = useState<AIProxy | null>(null);
  const [proxyForm, setProxyForm] = useState(EMPTY_PROXY_FORM);
  const [savingProxy, setSavingProxy] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  const loadProxies = useCallback(async () => {
    try {
      const res = await apiFetch("/api/ai-proxies");
      if (res.ok) setProxies(await res.json());
    } catch {}
  }, []);

  useEffect(() => {
    const info = getUserInfo();
    setUserInfo(info);
    setName(info.name);
    apiFetch("/api/settings").then((r) => r.json()).then((d) => {
      setFonnteToken(d.fonnte_token ?? "");
      setContentAiApiKey(d.openai_api_key ?? "");
      setContentAiBaseUrl(d.ai_base_url ?? "");
      setContentAiModel(d.ai_model ?? "");
      setFollowupEnabled(d.followup_enabled === "true");
      setFollowupHour(d.followup_hour ?? "9");
      setGoogleApiKey(d.google_api_key ?? "");
      setGoogleCalendarId(d.google_calendar_id ?? "");
      setGoogleServiceAccountJson(d.google_service_account_json ?? "");
      setAdminWa(d.admin_wa ?? "");
      setAdminName(d.admin_name ?? "");
      setCmsUrl(d.cms_url ?? "");
      setCmsApiToken(d.cms_api_token ?? "");
      setExternalLeadApiKey(d.external_lead_api_key ?? "");
      setSmtpHost(d.smtp_host ?? "");
      setSmtpPort(d.smtp_port ?? "587");
      setSmtpUser(d.smtp_user ?? "");
      setSmtpPassword(d.smtp_password ?? "");
      setSmtpFrom(d.smtp_from ?? "");
    });
    loadProxies();
  }, [loadProxies]);

  function showToast(message: string, type: "success" | "error" = "success") {
    setToast({ message, type });
  }

  async function testApi(provider: string) {
    setTesting(provider);
    try {
      const res = await apiFetch(`/api/settings/test-api?provider=${provider}`, { method: "POST" });
      const data = await res.json();
      showToast(data.message, data.success ? "success" : "error");
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : "Gagal test koneksi.", "error");
    } finally {
      setTesting(null);
    }
  }

  async function saveProfile() {
    setSaving(true);
    try {
      const body: Record<string, string> = { name };
      if (newPw) { body.current_password = currentPw; body.new_password = newPw; }
      const res = await apiFetch("/api/user/me", { method: "PUT", body: JSON.stringify(body) });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail ?? "Gagal menyimpan");
      }
      const d = await res.json();
      localStorage.setItem("kt_name", d.name);
      setUserInfo((u) => ({ ...u, name: d.name }));
      setCurrentPw(""); setNewPw("");
      showToast("Profil berhasil diperbarui");
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : "Gagal", "error");
    } finally {
      setSaving(false);
    }
  }

  async function saveApiConfig() {
    setSaving(true);
    try {
      const res = await apiFetch("/api/settings", { method: "PUT", body: JSON.stringify({
        fonnte_token: fonnteToken,
        openai_api_key: contentAiApiKey,
        ai_base_url: contentAiBaseUrl,
        ai_model: contentAiModel,
        followup_enabled: followupEnabled ? "true" : "false",
        followup_hour: followupHour,
        google_api_key: googleApiKey,
        google_calendar_id: googleCalendarId,
        google_service_account_json: googleServiceAccountJson,
        admin_wa: adminWa,
        admin_name: adminName,
        cms_url: cmsUrl,
        cms_api_token: cmsApiToken,
        smtp_host: smtpHost,
        smtp_port: smtpPort,
        smtp_user: smtpUser,
        smtp_password: smtpPassword,
        smtp_from: smtpFrom,
      }) });
      if (!res.ok) throw new Error("Gagal menyimpan");
      showToast("Konfigurasi disimpan");
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : "Gagal", "error");
    } finally {
      setSaving(false);
    }
  }

  async function saveProxy() {
    if (!proxyForm.name.trim() || !proxyForm.base_url.trim()) return;
    setSavingProxy(true);
    try {
      const method = editingProxy ? "PUT" : "POST";
      const url = editingProxy ? `/api/ai-proxies/${editingProxy.id}` : "/api/ai-proxies";
      const res = await apiFetch(url, { method, body: JSON.stringify(proxyForm) });
      if (!res.ok) throw new Error("Gagal simpan proxy");
      await loadProxies();
      setShowProxyForm(false);
      setEditingProxy(null);
      setProxyForm(EMPTY_PROXY_FORM);
      showToast(editingProxy ? "Proxy diupdate" : "Proxy ditambahkan");
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : "Gagal", "error");
    } finally {
      setSavingProxy(false);
    }
  }

  async function activateProxy(id: string) {
    try {
      const res = await apiFetch(`/api/ai-proxies/${id}/activate`, { method: "POST" });
      if (!res.ok) throw new Error("Gagal aktifkan proxy");
      await loadProxies();
      showToast("Proxy diaktifkan");
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : "Gagal", "error");
    }
  }

  async function deleteProxy(id: string) {
    try {
      const res = await apiFetch(`/api/ai-proxies/${id}`, { method: "DELETE" });
      if (res.ok) {
        await loadProxies();
        showToast("Proxy dihapus");
      }
    } catch { showToast("Gagal hapus proxy", "error"); }
  }

  function handleLogout() {
    clearToken();
    router.push("/login");
  }

  const inputCls = "w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-gray-50 dark:bg-[#2a2a29] dark:text-[#fcfaf7] focus:bg-white dark:focus:bg-[#333] focus:outline-none focus:ring-2 focus:ring-amber-300 font-mono transition";
  const inputClsNoMono = "w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-gray-50 dark:bg-[#2a2a29] dark:text-[#fcfaf7] focus:bg-white dark:focus:bg-[#333] focus:outline-none focus:ring-2 focus:ring-amber-300 transition";
  const labelCls = "block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1.5";

  return (
    <div className="max-w-2xl space-y-6">
      <Toast message={toast?.message ?? null} type={toast?.type} onClose={() => setToast(null)} />

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-[#fcfaf7]">Pengaturan</h1>
          <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">Kelola profil dan konfigurasi API.</p>
        </div>
        <button onClick={handleLogout}
          className="flex items-center gap-2 px-4 py-2 text-sm font-semibold text-red-600 bg-red-50 hover:bg-red-100 rounded-xl transition-colors">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><polyline points="16 17 21 12 16 7" /><line x1="21" y1="12" x2="9" y2="12" />
          </svg>
          Logout
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-white dark:bg-[#242423] border border-gray-200 dark:border-gray-700 rounded-xl p-1 w-fit shadow-sm">
        {(["profile", "api"] as Tab[]).map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-5 py-2 rounded-lg text-sm font-semibold transition-colors ${tab === t ? "bg-amber-600 text-white shadow-sm" : "text-neutral-500 dark:text-neutral-400 hover:text-gray-700 dark:hover:text-gray-200"}`}>
            {t === "profile" ? "Profil" : "API Configuration"}
          </button>
        ))}
      </div>

      {/* Profile tab */}
      {tab === "profile" && (
        <div className="bg-white dark:bg-[#242423] rounded-2xl border border-[var(--border-default)] shadow-sm p-6 space-y-5">
          <div className="flex items-center gap-4 pb-4 border-b border-[var(--border-default)]">
            <div className="w-12 h-12 rounded-full bg-gradient-to-br from-amber-500 to-yellow-600 flex items-center justify-center text-white font-bold text-lg">
              {userInfo.name.charAt(0).toUpperCase()}
            </div>
            <div>
              <p className="font-semibold text-gray-800 dark:text-[#fcfaf7]">{userInfo.name}</p>
              <p className="text-sm text-gray-400">{userInfo.email}</p>
            </div>
          </div>
          <div>
            <label className={labelCls}>Nama</label>
            <input value={name} onChange={(e) => setName(e.target.value)} className={inputClsNoMono} />
          </div>
          <div className="border-t border-[var(--border-default)] pt-4">
            <p className="text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-3">Ganti Password</p>
            <div className="space-y-3">
              <input type="password" placeholder="Password lama" value={currentPw} onChange={(e) => setCurrentPw(e.target.value)} className={inputClsNoMono} />
              <input type="password" placeholder="Password baru" value={newPw} onChange={(e) => setNewPw(e.target.value)} className={inputClsNoMono} />
            </div>
          </div>
          <button onClick={saveProfile} disabled={saving || !name.trim()}
            className="px-6 py-2.5 bg-gradient-to-r from-amber-600 to-yellow-600 hover:from-amber-700 hover:to-yellow-700 text-white text-sm font-semibold rounded-xl disabled:opacity-50 transition-all shadow-sm">
            {saving ? "Menyimpan..." : "Simpan Profil"}
          </button>
        </div>
      )}

      {/* API Config tab */}
      {tab === "api" && (
        <div className="bg-white dark:bg-[#242423] rounded-2xl border border-[var(--border-default)] shadow-sm p-6 space-y-5">

          {/* ── AI Proxy (Chat) ── */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <div>
                <h3 className="text-sm font-bold text-neutral-800 dark:text-neutral-200">AI Proxy (Chat)</h3>
                <p className="text-xs text-gray-400 mt-0.5">Provider untuk fitur Chat & Agent. Pilih satu yang aktif.</p>
              </div>
              <button onClick={() => { setEditingProxy(null); setProxyForm(EMPTY_PROXY_FORM); setShowProxyForm(p => !p); }}
                className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-800 hover:bg-amber-100 transition-colors">
                + Tambah Proxy
              </button>
            </div>

            {proxies.length === 0 ? (
              <p className="text-xs text-neutral-400 py-3 text-center border border-dashed border-gray-200 dark:border-gray-700 rounded-xl">
                Belum ada proxy. Tambahkan proxy untuk mengaktifkan Chat.
              </p>
            ) : (
              <div className="space-y-2">
                {proxies.map(p => (
                  <div key={p.id} className={`flex items-center gap-3 p-3 rounded-xl border transition-colors ${p.is_active ? "bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-700" : "bg-gray-50 dark:bg-gray-800/50 border-gray-200 dark:border-gray-700"}`}>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-semibold text-neutral-800 dark:text-neutral-200 truncate">{p.name}</p>
                        {p.is_active && <span className="text-xs px-1.5 py-0.5 rounded-full bg-amber-500 text-white font-semibold shrink-0">Aktif</span>}
                      </div>
                      <p className="text-xs text-neutral-400 truncate mt-0.5">{p.base_url} {p.model ? `· ${p.model}` : ""}</p>
                    </div>
                    <div className="flex gap-1 shrink-0">
                      {!p.is_active && (
                        <button onClick={() => activateProxy(p.id)}
                          className="text-xs px-2 py-1 rounded-lg bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 hover:bg-amber-200 transition-colors font-medium">
                          Aktifkan
                        </button>
                      )}
                      <button onClick={() => { setEditingProxy(p); setProxyForm({ name: p.name, base_url: p.base_url, api_key: p.api_key, model: p.model }); setShowProxyForm(true); }}
                        className="text-xs px-2 py-1 rounded-lg bg-gray-100 dark:bg-gray-700 text-neutral-500 hover:bg-gray-200 transition-colors">
                        Edit
                      </button>
                      <button onClick={() => deleteProxy(p.id)}
                        className="text-xs px-2 py-1 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-500 hover:bg-red-100 transition-colors">
                        Hapus
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Proxy form */}
            {showProxyForm && (
              <div className="mt-3 p-4 border border-gray-200 dark:border-gray-700 rounded-xl space-y-3 bg-gray-50 dark:bg-gray-800/30">
                <p className="text-xs font-bold text-neutral-600 dark:text-neutral-300 uppercase tracking-wide">
                  {editingProxy ? "Edit Proxy" : "Proxy Baru"}
                </p>
                {([
                  { label: "Nama", key: "name" as const, placeholder: "AIMurah", type: "text" },
                  { label: "Base URL", key: "base_url" as const, placeholder: "https://api.aimurah.com/v1", type: "text" },
                  { label: "API Key", key: "api_key" as const, placeholder: "sk-...", type: "password" },
                  { label: "Model (opsional)", key: "model" as const, placeholder: "glm-5", type: "text" },
                ] as { label: string; key: "name"|"base_url"|"api_key"|"model"; placeholder: string; type: string }[]).map(({ label, key, placeholder, type }) => (
                  <div key={key}>
                    <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">{label}</label>
                    <input type={type} value={proxyForm[key]}
                      onChange={e => setProxyForm(prev => ({ ...prev, [key]: e.target.value }))}
                      placeholder={placeholder}
                      className="w-full px-3 py-2 bg-white dark:bg-[#2a2a29] border border-gray-200 dark:border-gray-700 rounded-lg text-sm font-mono focus:ring-2 focus:ring-amber-300 outline-none transition" />
                  </div>
                ))}
                <div className="flex gap-2">
                  <button onClick={saveProxy} disabled={savingProxy || !proxyForm.name.trim() || !proxyForm.base_url.trim()}
                    className="flex-1 px-4 py-2 text-sm rounded-lg font-medium bg-amber-500 hover:bg-amber-600 text-white disabled:opacity-50 transition-colors">
                    {savingProxy ? "Menyimpan..." : editingProxy ? "Simpan Perubahan" : "Tambah Proxy"}
                  </button>
                  <button onClick={() => { setShowProxyForm(false); setEditingProxy(null); setProxyForm(EMPTY_PROXY_FORM); }}
                    className="px-4 py-2 text-sm rounded-lg bg-gray-100 dark:bg-gray-700 text-neutral-600 hover:bg-gray-200 transition-colors">
                    Batal
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* ── Fonnte ── */}
          <div className="border-t border-[var(--border-default)] pt-5">
            <label className={labelCls}>Fonnte API Token</label>
            <p className="text-xs text-gray-400 mb-3">Token untuk fitur WA Blast. Dapatkan di dashboard Fonnte.</p>
            <input type="password" value={fonnteToken} onChange={(e) => setFonnteToken(e.target.value)}
              placeholder="Masukkan Fonnte token..." className={inputCls} />
            <button onClick={() => testApi("fonnte")} disabled={testing === "fonnte"}
              className="mt-2 px-3 py-1.5 text-xs font-semibold bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800 rounded-lg hover:bg-emerald-100 transition-colors disabled:opacity-50">
              {testing === "fonnte" ? "Testing..." : "Test Koneksi Fonnte"}
            </button>
          </div>

          {/* ── Content Generator AI ── */}
          <div className="border-t border-[var(--border-default)] pt-5">
            <h3 className="text-sm font-bold text-neutral-800 dark:text-neutral-200 mb-1">Content Generator AI</h3>
            <p className="text-xs text-gray-400 mb-4">AI khusus untuk generate artikel SEO & gambar. Terpisah dari Chat proxy.</p>
            <div className="space-y-4">
              <div>
                <label className={labelCls}>Base URL</label>
                <input type="text" value={contentAiBaseUrl} onChange={(e) => setContentAiBaseUrl(e.target.value)}
                  placeholder="https://api.aimurah.com/v1" className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>API Key</label>
                <input type="password" value={contentAiApiKey} onChange={(e) => setContentAiApiKey(e.target.value)}
                  placeholder="sk-..." className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>Model</label>
                <input type="text" value={contentAiModel} onChange={(e) => setContentAiModel(e.target.value)}
                  placeholder="claude-sonnet-4-5" className={inputCls} />
              </div>
            </div>
          </div>

          {/* ── Google Services ── */}
          <div className="border-t border-[var(--border-default)] pt-5">
            <h3 className="text-sm font-bold text-neutral-800 dark:text-neutral-200 mb-3">Google Services</h3>
            <div className="space-y-4">
              <div>
                <label className={labelCls}>Google Maps API Key</label>
                <p className="text-xs text-gray-400 mb-3">Untuk fitur Maps Scraper. Dapatkan di Google Cloud Console.</p>
                <input type="password" value={googleApiKey} onChange={(e) => setGoogleApiKey(e.target.value)}
                  placeholder="Masukkan Google API key..." className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>Google Calendar ID</label>
                <p className="text-xs text-gray-400 mb-3">ID kalender untuk sync Content Calendar. Default: primary.</p>
                <input value={googleCalendarId} onChange={(e) => setGoogleCalendarId(e.target.value)}
                  placeholder="primary" className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>Google Service Account JSON</label>
                <p className="text-xs text-gray-400 mb-3">Paste isi file JSON service account untuk Google Calendar sync.</p>
                <textarea value={googleServiceAccountJson} onChange={(e) => setGoogleServiceAccountJson(e.target.value)}
                  placeholder='{"type": "service_account", "project_id": "...", ...}'
                  rows={4}
                  className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-gray-50 dark:bg-[#2a2a29] dark:text-[#fcfaf7] focus:bg-white dark:focus:bg-[#333] focus:outline-none focus:ring-2 focus:ring-amber-300 font-mono transition resize-none" />
              </div>
              <button type="button" onClick={async () => {
                setTestingCalendar(true);
                try {
                  const res = await apiFetch("/api/settings/test-calendar", { method: "POST" });
                  const data = await res.json();
                  showToast(data.message, data.success ? "success" : "error");
                } catch { showToast("Gagal test calendar", "error"); }
                finally { setTestingCalendar(false); }
              }} disabled={testingCalendar}
                className="px-4 py-2 text-sm font-semibold bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-xl transition-colors disabled:opacity-50">
                {testingCalendar ? "Testing..." : "Test Calendar Connection"}
              </button>
            </div>
          </div>

          {/* ── WhatsApp Notification ── */}
          <div className="border-t border-[var(--border-default)] pt-5">
            <h3 className="text-sm font-bold text-neutral-800 dark:text-neutral-200 mb-3">WhatsApp Notification</h3>
            <div className="space-y-3">
              <div>
                <label className={labelCls}>Nomor Admin WA</label>
                <p className="text-xs text-gray-400 mb-3">Nomor yang menerima notifikasi (format: 6281xxx). Dipakai juga di template proposal/report.</p>
                <input value={adminWa} onChange={(e) => setAdminWa(e.target.value)}
                  placeholder="6281234567890" className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>Nama Admin (untuk template)</label>
                <p className="text-xs text-gray-400 mb-3">Nama yang muncul di template WA &quot;Halo {"{nama}"}&quot;. Contoh: Vin, Kevin, dll.</p>
                <input value={adminName} onChange={(e) => setAdminName(e.target.value)}
                  placeholder="Vin" className={inputCls} />
              </div>
            </div>
          </div>

          {/* ── Auto Follow-up ── */}
          <div className="border-t border-gray-200 dark:border-gray-700 pt-5">
            <h3 className="text-xs font-bold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-4">Auto Follow-up Scheduler</h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Aktifkan Auto Follow-up</p>
                  <p className="text-xs text-gray-400 mt-0.5">Sistem otomatis kirim pesan follow-up ke lead yang belum reply.</p>
                </div>
                <button type="button" onClick={() => setFollowupEnabled(!followupEnabled)}
                  className={`relative w-11 h-6 rounded-full transition-colors ${followupEnabled ? "bg-amber-500" : "bg-gray-300 dark:bg-gray-600"}`}>
                  <div className={`absolute top-1 w-4 h-4 rounded-full bg-white shadow transition-transform ${followupEnabled ? "translate-x-6" : "translate-x-1"}`}></div>
                </button>
              </div>
              {followupEnabled && (
                <div>
                  <label className={labelCls}>Jam Pengiriman (WIB)</label>
                  <select value={followupHour} onChange={(e) => setFollowupHour(e.target.value)}
                    className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-gray-50 dark:bg-[#2a2a29] dark:text-[#fcfaf7] focus:outline-none focus:ring-2 focus:ring-amber-300 transition">
                    {["7","8","9","10","11","13","14","16"].map(h => (
                      <option key={h} value={h}>{h.padStart(2,"0")}:00 WIB{h === "9" ? " (Recommended)" : ""}</option>
                    ))}
                  </select>
                </div>
              )}
            </div>
          </div>

          {/* ── CMS Integration ── */}
          <div className="border-t border-[var(--border-default)] pt-5">
            <h3 className="text-sm font-bold text-neutral-800 dark:text-neutral-200 mb-3">CMS Integration</h3>
            <div className="space-y-4">
              <div>
                <label className={labelCls}>CMS URL</label>
                <p className="text-xs text-gray-400 mb-3">URL base CMS untuk publish artikel (mis. https://temanumkmkita.com).</p>
                <input type="text" value={cmsUrl} onChange={(e) => setCmsUrl(e.target.value)}
                  placeholder="https://temanumkmkita.com" className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>CMS API Token</label>
                <p className="text-xs text-gray-400 mb-3">Bearer token untuk autentikasi ke CMS API.</p>
                <input type="password" value={cmsApiToken} onChange={(e) => setCmsApiToken(e.target.value)}
                  placeholder="Masukkan CMS API token..." className={inputCls} />
              </div>
            </div>
          </div>

          {/* ── External Lead API (Web Form Integration) ── */}
          <div className="border-t border-[var(--border-default)] pt-5">
            <h3 className="text-sm font-bold text-neutral-800 dark:text-neutral-200 mb-3">External Lead API</h3>
            <div className="space-y-4">
              <div>
                <label className={labelCls}>API Key</label>
                <p className="text-xs text-gray-400 mb-3">Key untuk validasi POST /api/leads/external dari website eksternal (form kontak temanumkmkita.com).</p>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={externalLeadApiKey}
                    readOnly
                    placeholder="Belum digenerate. Klik Generate untuk membuat."
                    className={`${inputCls} font-mono text-xs`}
                  />
                  <button
                    onClick={async () => {
                      setRegeneratingKey(true);
                      try {
                        const res = await apiFetch("/api/settings/external-lead-key/regenerate", { method: "POST" });
                        if (!res.ok) throw new Error("Gagal generate");
                        const data = await res.json();
                        setExternalLeadApiKey(data.key);
                        showToast(externalLeadApiKey ? "API key di-regenerate" : "API key digenerate");
                      } catch {
                        showToast("Gagal generate key", "error");
                      } finally {
                        setRegeneratingKey(false);
                      }
                    }}
                    disabled={regeneratingKey}
                    className="px-4 py-2 bg-amber-500 hover:bg-amber-600 text-white text-xs font-bold rounded-lg disabled:opacity-50 whitespace-nowrap"
                  >
                    {regeneratingKey ? "..." : externalLeadApiKey ? "Regenerate" : "Generate"}
                  </button>
                </div>
                {externalLeadApiKey && (
                  <p className="text-[11px] text-amber-600 mt-2">
                    Regenerate akan invalidate key lama — pastikan update di temanumkmkita backend setelah regenerate.
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* ── SMTP / Email ── */}
          <div className="border-t border-[var(--border-default)] pt-5">
            <h3 className="text-sm font-bold text-neutral-800 dark:text-neutral-200 mb-3">SMTP / Email</h3>
            <p className="text-xs text-gray-400 mb-4">Konfigurasi server SMTP untuk kirim dokumen via email (Document Generator).</p>
            <div className="grid sm:grid-cols-2 gap-4">
              <div>
                <label className={labelCls}>SMTP Host</label>
                <input type="text" value={smtpHost} onChange={(e) => setSmtpHost(e.target.value)}
                  placeholder="smtp.gmail.com" className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>SMTP Port</label>
                <input type="text" value={smtpPort} onChange={(e) => setSmtpPort(e.target.value)}
                  placeholder="587" className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>SMTP User</label>
                <input type="text" value={smtpUser} onChange={(e) => setSmtpUser(e.target.value)}
                  placeholder="username@gmail.com" className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>SMTP Password</label>
                <input type="password" value={smtpPassword} onChange={(e) => setSmtpPassword(e.target.value)}
                  placeholder="App password" className={inputCls} />
              </div>
              <div className="sm:col-span-2">
                <label className={labelCls}>From Address</label>
                <input type="text" value={smtpFrom} onChange={(e) => setSmtpFrom(e.target.value)}
                  placeholder="noreply@kantorteman.my.id (kosongkan = pakai SMTP User)" className={inputCls} />
              </div>
            </div>
          </div>

          <button onClick={saveApiConfig} disabled={saving}
            className="px-6 py-2.5 bg-gradient-to-r from-amber-600 to-yellow-600 hover:from-amber-700 hover:to-yellow-700 text-white text-sm font-semibold rounded-xl disabled:opacity-50 transition-all shadow-sm">
            {saving ? "Menyimpan..." : "Simpan Konfigurasi"}
          </button>
        </div>
      )}
    </div>
  );
}
