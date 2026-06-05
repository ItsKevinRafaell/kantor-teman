"use client";
import { formatRupiah } from "../../utils/formatter";

interface ProposalROIProps {
  proposal: {
    base_price: number | null;
    discount_price: number | null;
    roi_data?: {
      enabled?: boolean;
      roi_months?: number;
      roi_multiplier?: number;
      monthly_ads_cost?: number;
      has_retainer?: boolean;
      retainer_period?: number;
      retainer_monthly?: number;
      onetime_total?: number;
      our_total_cost?: number;
      ads_total_cost?: number;
      comparison_period?: number;
      comparison_points?: { aspect: string; ads: string; ours: string }[];
    } | null;
  };
}

export default function ProposalROI({ proposal }: ProposalROIProps) {
  const roiData = proposal.roi_data;
  if (roiData?.enabled === false) return null;

  const finalTotal = proposal.discount_price || proposal.base_price || 0;
  const roiMonths = roiData?.roi_months || 3;
  const roiMultiplier = roiData?.roi_multiplier || 3.5;
  const ourTotalCost = roiData?.our_total_cost || finalTotal;
  const comparisonPeriod = roiData?.comparison_period || 12;
  const hasRetainer = roiData?.has_retainer || false;
  const retainerPeriod = roiData?.retainer_period || 0;
  const retainerMonthly = roiData?.retainer_monthly || 0;
  const onetimeTotal = roiData?.onetime_total || finalTotal;

  return (
    <>
      {/* ROI Calculator */}
      <section className="bg-white border-2 border-zinc-200 rounded-2xl p-6 mb-12 shadow-sm break-inside-avoid print:border-zinc-300 print:shadow-none">
        <h2 className="text-xs font-bold uppercase tracking-widest text-zinc-600 mb-5">Kalkulasi Return on Investment</h2>
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-zinc-50 rounded-xl p-3 text-center border border-zinc-200">
              <p className="text-[10px] text-zinc-500 uppercase tracking-wide font-bold mb-1">Investasi</p>
              <p className="text-sm md:text-base font-black text-zinc-900">{formatRupiah(ourTotalCost)}</p>
              <p className="text-[10px] text-zinc-400 mt-0.5">{hasRetainer ? `${retainerPeriod} bulan` : "sekali bayar"}</p>
            </div>
            <div className="bg-amber-50 rounded-xl p-3 text-center border border-amber-200">
              <p className="text-[10px] text-amber-700 uppercase tracking-wide font-bold mb-1">Estimasi Balik Modal</p>
              <p className="text-sm md:text-base font-black text-amber-600">{roiMonths} Bulan</p>
              <p className="text-[10px] text-amber-500 mt-0.5">berdasarkan proyeksi</p>
            </div>
            <div className="bg-green-50 rounded-xl p-3 text-center border border-green-200">
              <p className="text-[10px] text-green-700 uppercase tracking-wide font-bold mb-1">Profit {comparisonPeriod} Bulan</p>
              <p className="text-sm md:text-base font-black text-green-600">{formatRupiah(ourTotalCost * roiMultiplier)}</p>
              <p className="text-[10px] text-green-500 mt-0.5">estimasi konservatif</p>
            </div>
          </div>
          {hasRetainer && (
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-3">
              <p className="text-[10px] text-amber-700 font-semibold">Rincian: {onetimeTotal > 0 ? `${formatRupiah(onetimeTotal)} (sekali bayar) + ` : ""}{formatRupiah(retainerMonthly)}/bulan × {retainerPeriod} bulan</p>
            </div>
          )}
          <div className="bg-zinc-50 border border-zinc-200 rounded-xl p-4">
            <div className="flex items-center gap-3">
              <div className="flex-1">
                <div className="flex justify-between text-[10px] text-zinc-500 font-bold mb-1">
                  <span>Bulan 1</span>
                  <span>Bulan {roiMonths} (BEP)</span>
                  <span>Bulan {comparisonPeriod}</span>
                </div>
                <div className="h-3 bg-zinc-200 rounded-full overflow-hidden">
                  <div className="h-full rounded-full bg-gradient-to-r from-red-400 via-amber-400 to-green-500" style={{ width: "100%" }}></div>
                </div>
                <div className="flex justify-between text-[9px] text-zinc-400 mt-1">
                  <span>Investasi</span>
                  <span className="text-amber-600 font-bold">Balik Modal</span>
                  <span className="text-green-600 font-bold">Profit</span>
                </div>
              </div>
            </div>
          </div>
          <p className="text-[11px] text-zinc-500 text-center italic">Estimasi berdasarkan rata-rata performa klien kami di industri serupa. Hasil aktual dapat bervariasi.</p>
        </div>
      </section>

      {/* Comparison Table */}
      <section className="bg-white border-2 border-zinc-200 rounded-2xl p-6 mb-12 shadow-sm break-inside-avoid print:border-zinc-300 print:shadow-none">
        <h2 className="text-xs font-bold uppercase tracking-widest text-zinc-600 mb-5">Perbandingan: Iklan Berbayar vs Optimasi Digital</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b-2 border-zinc-200">
                <th className="text-left py-3 text-xs text-zinc-500 font-bold uppercase tracking-wide">Aspek</th>
                <th className="text-center py-3 text-xs text-zinc-400 font-bold uppercase tracking-wide">Google Ads</th>
                <th className="text-center py-3 text-xs text-amber-600 font-bold uppercase tracking-wide">Optimasi Kami</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100">
              {(roiData?.comparison_points && roiData.comparison_points.length > 0) ? (
                roiData.comparison_points.map((point, i) => (
                  <tr key={i}>
                    <td className="py-3 text-zinc-700 font-medium">{point.aspect}</td>
                    <td className="py-3 text-center text-zinc-500">{point.ads}</td>
                    <td className="py-3 text-center text-amber-700 font-bold">{point.ours}</td>
                  </tr>
                ))
              ) : (
                <>
                  <tr>
                    <td className="py-3 text-zinc-700 font-medium">Durasi Efek</td>
                    <td className="py-3 text-center text-zinc-500">Berhenti bayar = hilang</td>
                    <td className="py-3 text-center text-amber-700 font-bold">{hasRetainer ? "Akumulatif selama kontrak" : "Permanen & akumulatif"}</td>
                  </tr>
                  <tr>
                    <td className="py-3 text-zinc-700 font-medium">Kepercayaan User</td>
                    <td className="py-3 text-center text-zinc-500">Rendah (label "Iklan")</td>
                    <td className="py-3 text-center text-amber-700 font-bold">Tinggi (organik)</td>
                  </tr>
                  <tr>
                    <td className="py-3 text-zinc-700 font-medium">Kompetisi Harga</td>
                    <td className="py-3 text-center text-zinc-500">Makin mahal tiap tahun</td>
                    <td className="py-3 text-center text-amber-700 font-bold">Investasi tetap</td>
                  </tr>
                </>
              )}
            </tbody>
          </table>
        </div>
        <div className="mt-4 bg-amber-50 border border-amber-200 rounded-xl p-3 text-center">
          <p className="text-xs text-amber-800 font-semibold">
            Dengan optimasi digital, Anda menghemat biaya iklan dalam {comparisonPeriod} bulan dibanding iklan berbayar.
          </p>
        </div>
      </section>
    </>
  );
}