"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getUserInfo, clearToken, apiFetch } from "../../lib/api";
import Toast from "../../components/Toast";

type Tab = "profile" | "api";

export default function SettingsPage() {
  const router = useRouter();
  const [tab, setTab] = useState<Tab>("profile");
  const [userInfo, setUserInfo] = useState({ name: "", email: "" });
  const [name, setName] = useState("");
  const [currentPw, setCurrentPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [fonnteToken, setFonnteToken] = useState("");
  const [geminiKey, setGeminiKey] = useState("");
  const [claudeKey, setClaudeKey] = useState("");
  const [openaiKey, setOpenaiKey] = useState("");
  const [aiProvider, setAiProvider] = useState("gemini");
  const [aiBaseUrl, setAiBaseUrl] = useState("");
  const [aiModel, setAiModel] = useState("");
  const [followupEnabled, setFollowupEnabled] = useState(false);
  const [followupHour, setFollowupHour] = useState("9");
  const [googleApiKey, setGoogleApiKey] = useState("");
  const [googleCalendarId, setGoogleCalendarId] = useState("");
  const [googleServiceAccountJson, setGoogleServiceAccountJson] = useState("");
  const [adminWa, setAdminWa] = useState("");
  const [cmsUrl, setCmsUrl] = useState("");
  const [cmsApiToken, setCmsApiToken] = useState("");
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  useEffect(() => {
    const info = getUserInfo();
    setUserInfo(info);
    setName(info.name);
    apiFetch("/api/settings").then((r) => r.json()).then((d) => {
      setFonnteToken(d.fonnte_token ?? "");
      setGeminiKey(d.gemini_api_key ?? "");
      setClaudeKey(d.claude_api_key ?? "");
      setOpenaiKey(d.openai_api_key ?? "");
      setAiProvider(d.ai_provider ?? "gemini");
      setAiBaseUrl(d.ai_base_url ?? "");
      setAiModel(d.ai_model ?? "");
      setFollowupEnabled(d.followup_enabled === "true");
      setFollowupHour(d.followup_hour ?? "9");
      setGoogleApiKey(d.google_api_key ?? "");
      setGoogleCalendarId(d.google_calendar_id ?? "");
      setGoogleServiceAccountJson(d.google_service_account_json ?? "");
      setAdminWa(d.admin_wa ?? "");
      setCmsUrl(d.cms_url ?? "");
      setCmsApiToken(d.cms_api_token ?? "");
    });
  }, []);

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
        gemini_api_key: geminiKey,
        claude_api_key: claudeKey,
        openai_api_key: openaiKey,
        ai_provider: aiProvider,
        ai_base_url: aiBaseUrl,
        ai_model: aiModel,
        followup_enabled: followupEnabled ? "true" : "false",
        followup_hour: followupHour,
        google_api_key: googleApiKey,
        google_calendar_id: googleCalendarId,
        google_service_account_json: googleServiceAccountJson,
        admin_wa: adminWa,
        cms_url: cmsUrl,
        cms_api_token: cmsApiToken,
      }) });
      if (!res.ok) throw new Error("Gagal menyimpan");
      showToast("Konfigurasi disimpan");
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : "Gagal", "error");
    } finally {
      setSaving(false);
    }
  }

  function handleLogout() {
    clearToken();
    router.push("/login");
  }

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
            <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1.5">Nama</label>
            <input value={name} onChange={(e) => setName(e.target.value)}
              className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-gray-50 dark:bg-[#2a2a29] dark:text-[#fcfaf7] focus:bg-white dark:focus:bg-[#333] focus:outline-none focus:ring-2 focus:ring-amber-300 transition" />
          </div>

          <div className="border-t border-[var(--border-default)] pt-4">
            <p className="text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-3">Ganti Password</p>
            <div className="space-y-3">
              <input type="password" placeholder="Password lama" value={currentPw} onChange={(e) => setCurrentPw(e.target.value)}
                className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-gray-50 dark:bg-[#2a2a29] dark:text-[#fcfaf7] focus:bg-white dark:focus:bg-[#333] focus:outline-none focus:ring-2 focus:ring-amber-300 transition" />
              <input type="password" placeholder="Password baru" value={newPw} onChange={(e) => setNewPw(e.target.value)}
                className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-gray-50 dark:bg-[#2a2a29] dark:text-[#fcfaf7] focus:bg-white dark:focus:bg-[#333] focus:outline-none focus:ring-2 focus:ring-amber-300 transition" />
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
          <div>
            <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1.5">
              Fonnte API Token
            </label>
            <p className="text-xs text-gray-400 mb-3">Token digunakan untuk fitur WA Blast. Dapatkan di dashboard Fonnte.</p>
            <input type="password" value={fonnteToken} onChange={(e) => setFonnteToken(e.target.value)}
              placeholder="Masukkan Fonnte token..."
              className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-gray-50 dark:bg-[#2a2a29] dark:text-[#fcfaf7] focus:bg-white dark:focus:bg-[#333] focus:outline-none focus:ring-2 focus:ring-amber-300 font-mono transition" />
            <button onClick={() => testApi("fonnte")} disabled={testing === "fonnte"}
              className="mt-2 px-3 py-1.5 text-xs font-semibold bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800 rounded-lg hover:bg-emerald-100 dark:hover:bg-emerald-900/40 transition-colors disabled:opacity-50">
              {testing === "fonnte" ? "Testing..." : "Test Koneksi Fonnte"}
            </button>
          </div>

          <div className="border-t border-[var(--border-default)] pt-5">
            <h3 className="text-sm font-bold text-neutral-800 dark:text-neutral-200 mb-3">AI Analysis Provider</h3>
            <div>
              <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1.5">Provider Aktif</label>
              <select value={aiProvider} onChange={(e) => setAiProvider(e.target.value)}
                className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-gray-50 dark:bg-[#2a2a29] dark:text-[#fcfaf7] focus:outline-none focus:ring-2 focus:ring-amber-300 transition">
                <option value="gemini">Google Gemini 2.5 Flash</option>
                <option value="claude">Anthropic Claude 4.5 Haiku</option>
                <option value="openai">OpenAI GPT-5</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1.5">
              Gemini API Key
            </label>
            <p className="text-xs text-gray-400 mb-3">Dapatkan di Google AI Studio (aistudio.google.com).</p>
            <input type="password" value={geminiKey} onChange={(e) => setGeminiKey(e.target.value)}
              placeholder="Masukkan Gemini API key..."
              className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-gray-50 dark:bg-[#2a2a29] dark:text-[#fcfaf7] focus:bg-white dark:focus:bg-[#333] focus:outline-none focus:ring-2 focus:ring-amber-300 font-mono transition" />
            <button onClick={() => testApi("gemini")} disabled={testing === "gemini"}
              className="mt-2 px-3 py-1.5 text-xs font-semibold bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800 rounded-lg hover:bg-emerald-100 dark:hover:bg-emerald-900/40 transition-colors disabled:opacity-50">
              {testing === "gemini" ? "Testing..." : "Test Koneksi Gemini"}
            </button>
          </div>

          <div>
            <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1.5">
              Claude API Key
            </label>
            <p className="text-xs text-gray-400 mb-3">Dapatkan di console.anthropic.com.</p>
            <input type="password" value={claudeKey} onChange={(e) => setClaudeKey(e.target.value)}
              placeholder="Masukkan Claude API key..."
              className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-gray-50 dark:bg-[#2a2a29] dark:text-[#fcfaf7] focus:bg-white dark:focus:bg-[#333] focus:outline-none focus:ring-2 focus:ring-amber-300 font-mono transition" />
            <button onClick={() => testApi("claude")} disabled={testing === "claude"}
              className="mt-2 px-3 py-1.5 text-xs font-semibold bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800 rounded-lg hover:bg-emerald-100 dark:hover:bg-emerald-900/40 transition-colors disabled:opacity-50">
              {testing === "claude" ? "Testing..." : "Test Koneksi Claude"}
            </button>
          </div>

          <div>
            <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1.5">
              OpenAI API Key
            </label>
            <p className="text-xs text-gray-400 mb-3">Dapatkan di platform.openai.com.</p>
            <input type="password" value={openaiKey} onChange={(e) => setOpenaiKey(e.target.value)}
              placeholder="Masukkan OpenAI API key..."
              className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-gray-50 dark:bg-[#2a2a29] dark:text-[#fcfaf7] focus:bg-white dark:focus:bg-[#333] focus:outline-none focus:ring-2 focus:ring-amber-300 font-mono transition" />
            <button onClick={() => testApi("openai")} disabled={testing === "openai"}
              className="mt-2 px-3 py-1.5 text-xs font-semibold bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800 rounded-lg hover:bg-emerald-100 dark:hover:bg-emerald-900/40 transition-colors disabled:opacity-50">
              {testing === "openai" ? "Testing..." : "Test Koneksi OpenAI"}
            </button>
          </div>

          <div>
            <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1.5">
              AI Base URL (Opsional)
            </label>
            <p className="text-xs text-gray-400 mb-3">Untuk OpenAI-compatible provider (OpenRouter, LiteLLM, dll). Kosongkan jika pakai default.</p>
            <input type="text" value={aiBaseUrl} onChange={(e) => setAiBaseUrl(e.target.value)}
              placeholder="https://openrouter.ai/api/v1"
              className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-gray-50 dark:bg-[#2a2a29] dark:text-[#fcfaf7] focus:bg-white dark:focus:bg-[#333] focus:outline-none focus:ring-2 focus:ring-amber-300 font-mono transition" />
          </div>

          <div>
            <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1.5">
              AI Model (Opsional)
            </label>
            <p className="text-xs text-gray-400 mb-3">Nama model yang digunakan. Kosongkan untuk default provider.</p>
            <input type="text" value={aiModel} onChange={(e) => setAiModel(e.target.value)}
              placeholder="claude-haiku-4-5-20251001"
              className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-gray-50 dark:bg-[#2a2a29] dark:text-[#fcfaf7] focus:bg-white dark:focus:bg-[#333] focus:outline-none focus:ring-2 focus:ring-amber-300 font-mono transition" />
          </div>

          <div className="border-t border-[var(--border-default)] pt-5">
            <h3 className="text-sm font-bold text-neutral-800 dark:text-neutral-200 mb-3">Google Services</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1.5">
                  Google Maps API Key
                </label>
                <p className="text-xs text-gray-400 mb-3">Untuk fitur Maps Scraper. Dapatkan di Google Cloud Console.</p>
                <input type="password" value={googleApiKey} onChange={(e) => setGoogleApiKey(e.target.value)}
                  placeholder="Masukkan Google API key..."
                  className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-gray-50 dark:bg-[#2a2a29] dark:text-[#fcfaf7] focus:bg-white dark:focus:bg-[#333] focus:outline-none focus:ring-2 focus:ring-amber-300 font-mono transition" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1.5">
                  Google Calendar ID
                </label>
                <p className="text-xs text-gray-400 mb-3">ID kalender untuk sync Content Calendar. Default: primary.</p>
                <input value={googleCalendarId} onChange={(e) => setGoogleCalendarId(e.target.value)}
                  placeholder="primary"
                  className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-gray-50 dark:bg-[#2a2a29] dark:text-[#fcfaf7] focus:bg-white dark:focus:bg-[#333] focus:outline-none focus:ring-2 focus:ring-amber-300 font-mono transition" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1.5">
                  Google Service Account JSON
                </label>
                <p className="text-xs text-gray-400 mb-3">Paste isi file JSON service account untuk Google Calendar sync.</p>
                <textarea value={googleServiceAccountJson} onChange={(e) => setGoogleServiceAccountJson(e.target.value)}
                  placeholder='{"type": "service_account", "project_id": "...", ...}'
                  rows={4}
                  className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-gray-50 dark:bg-[#2a2a29] dark:text-[#fcfaf7] focus:bg-white dark:focus:bg-[#333] focus:outline-none focus:ring-2 focus:ring-amber-300 font-mono transition resize-none" />
              </div>
            </div>
          </div>

          <div className="border-t border-[var(--border-default)] pt-5">
            <h3 className="text-sm font-bold text-neutral-800 dark:text-neutral-200 mb-3">WhatsApp Notification</h3>
            <div>
              <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1.5">
                Nomor Admin WA
              </label>
              <p className="text-xs text-gray-400 mb-3">Nomor yang menerima notifikasi (format: 6281xxx).</p>
              <input value={adminWa} onChange={(e) => setAdminWa(e.target.value)}
                placeholder="6281234567890"
                className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-gray-50 dark:bg-[#2a2a29] dark:text-[#fcfaf7] focus:bg-white dark:focus:bg-[#333] focus:outline-none focus:ring-2 focus:ring-amber-300 font-mono transition" />
            </div>
          </div>

          {/* Auto Follow-up Settings */}
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
                  <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1.5">Jam Pengiriman (WIB)</label>
                  <select value={followupHour} onChange={(e) => setFollowupHour(e.target.value)}
                    className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-gray-50 dark:bg-[#2a2a29] dark:text-[#fcfaf7] focus:outline-none focus:ring-2 focus:ring-amber-300 transition">
                    <option value="7">07:00 WIB</option>
                    <option value="8">08:00 WIB</option>
                    <option value="9">09:00 WIB (Recommended)</option>
                    <option value="10">10:00 WIB</option>
                    <option value="11">11:00 WIB</option>
                    <option value="13">13:00 WIB</option>
                    <option value="14">14:00 WIB</option>
                    <option value="16">16:00 WIB</option>
                  </select>
                  <p className="text-[10px] text-gray-400 mt-1.5 italic">Follow-up akan dikirim otomatis setiap hari pada jam yang dipilih untuk sequence yang aktif.</p>
                </div>
              )}
            </div>
          </div>

          <div className="border-t border-[var(--border-default)] pt-5">
            <h3 className="text-sm font-bold text-neutral-800 dark:text-neutral-200 mb-3">CMS Integration</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1.5">
                  CMS URL
                </label>
                <p className="text-xs text-gray-400 mb-3">URL base CMS yang digunakan untuk publish artikel (mis. https://temanumkmkita.com).</p>
                <input type="text" value={cmsUrl} onChange={(e) => setCmsUrl(e.target.value)}
                  placeholder="https://temanumkmkita.com"
                  className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-gray-50 dark:bg-[#2a2a29] dark:text-[#fcfaf7] focus:bg-white dark:focus:bg-[#333] focus:outline-none focus:ring-2 focus:ring-amber-300 font-mono transition" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1.5">
                  CMS API Token
                </label>
                <p className="text-xs text-gray-400 mb-3">Bearer token untuk autentikasi ke CMS API.</p>
                <input type="password" value={cmsApiToken} onChange={(e) => setCmsApiToken(e.target.value)}
                  placeholder="Masukkan CMS API token..."
                  className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-gray-50 dark:bg-[#2a2a29] dark:text-[#fcfaf7] focus:bg-white dark:focus:bg-[#333] focus:outline-none focus:ring-2 focus:ring-amber-300 font-mono transition" />
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
