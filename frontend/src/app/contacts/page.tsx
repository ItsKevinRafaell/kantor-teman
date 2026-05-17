import dynamic from "next/dynamic";

const LeadsTable = dynamic(() => import("../../components/LeadsTable"), { ssr: false });

export default function ContactsPage() {
  return (
    <div className="max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-[#fcfaf7]">Semua Kontak</h1>
        <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">Kelola semua leads dan update status follow-up.</p>
      </div>
      <LeadsTable />
    </div>
  );
}
