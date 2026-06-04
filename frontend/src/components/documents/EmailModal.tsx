"use client";

interface EmailModalProps {
  emailModal: boolean;
  setEmailModal: (b: boolean) => void;
  emailTo: string;
  setEmailTo: (s: string) => void;
  emailSubject: string;
  setEmailSubject: (s: string) => void;
  sendingEmail: boolean;
  handleSendEmail: () => Promise<void>;
  generatedDoc: any;
}

export default function EmailModal({
  emailModal, setEmailModal, emailTo, setEmailTo, emailSubject, setEmailSubject,
  sendingEmail, handleSendEmail, generatedDoc,
}: EmailModalProps) {
  if (!emailModal) return null;

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-neutral-900 rounded-2xl p-6 w-full max-w-md shadow-xl">
        <h3 className="text-lg font-bold text-neutral-800 dark:text-neutral-100 mb-4">Kirim via Email</h3>
        <div className="space-y-3">
          <div>
            <label className="text-xs font-bold text-gray-600 uppercase tracking-wide">Alamat Email</label>
            <input
              type="email"
              value={emailTo}
              onChange={e => setEmailTo(e.target.value)}
              placeholder="klien@email.com"
              className="mt-1 w-full px-3 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800"
            />
          </div>
          <div>
            <label className="text-xs font-bold text-gray-600 uppercase tracking-wide">Subject (opsional)</label>
            <input
              type="text"
              value={emailSubject}
              onChange={e => setEmailSubject(e.target.value)}
              placeholder={`${generatedDoc?.template_name} dari Teman UMKM Kita`}
              className="mt-1 w-full px-3 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800"
            />
          </div>
        </div>
        <div className="flex gap-3 mt-5">
          <button onClick={() => setEmailModal(false)}
            className="flex-1 py-2.5 rounded-xl border border-gray-200 text-sm font-semibold text-gray-600">
            Batal
          </button>
          <button onClick={handleSendEmail} disabled={sendingEmail || !emailTo}
            className="flex-1 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-600 text-white text-sm font-bold disabled:opacity-50">
            {sendingEmail ? "Mengirim..." : "Kirim"}
          </button>
        </div>
      </div>
    </div>
  );
}