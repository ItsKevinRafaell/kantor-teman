"use client";
import { formatRupiah } from "../../utils/formatter";

interface ProposalPricingProps {
  proposal: {
    services_detail: { name: string; price: number }[];
    total_price: number;
    base_price: number | null;
    discount_price: number | null;
  };
}

export default function ProposalPricing({ proposal }: ProposalPricingProps) {
  const serviceTotal = proposal.services_detail.reduce((total, service) => total + (service.price || 0), 0);
  const subtotal = proposal.base_price || proposal.total_price || serviceTotal;
  const discount = subtotal - (proposal.discount_price || subtotal);
  const finalTotal = proposal.discount_price || subtotal;

  return (
    <section className="bg-white border-2 border-zinc-200 rounded-2xl p-6 mb-12 shadow-sm break-inside-avoid print:border-zinc-300 print:shadow-none">
      <h2 className="text-xs font-bold uppercase tracking-widest text-zinc-600 mb-5">Rincian Nilai Investasi</h2>
      <div className="space-y-3">
        {proposal.services_detail.map((service, i) => (
          <div key={i} className="flex justify-between items-center py-2 border-b-2 border-zinc-100 last:border-0 print:border-zinc-200">
            <span className="text-sm text-zinc-700 print:text-zinc-800">{service.name}</span>
            <span className="text-sm font-bold text-zinc-900 whitespace-nowrap print:text-black">{formatRupiah(service.price)}</span>
          </div>
        ))}
      </div>
      <div className="border-t-2 border-zinc-200 mt-4 pt-4 space-y-2 print:border-zinc-300">
        <div className="flex justify-between text-sm">
          <span className="text-zinc-600">Subtotal Nilai Jasa</span>
          <span className="text-zinc-800 font-medium print:text-zinc-900">{formatRupiah(subtotal)}</span>
        </div>
        {discount > 0 && (
          <div className="flex justify-between text-sm">
            <span className="text-amber-600 font-medium">Potongan Harga Promo 15%</span>
            <span className="text-amber-600 font-medium line-through">-{formatRupiah(discount)}</span>
          </div>
        )}
        <div className="flex justify-between items-center pt-3 border-t-2 border-zinc-200 print:border-zinc-300">
          <span className="text-sm font-bold text-zinc-600 print:text-zinc-700">Total Investasi Final</span>
          <span className="text-2xl md:text-3xl font-black text-amber-600 print:text-amber-700">{formatRupiah(finalTotal)}</span>
        </div>
      </div>
    </section>
  );
}
