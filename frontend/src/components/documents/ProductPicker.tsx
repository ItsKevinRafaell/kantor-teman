"use client";
import { formatRupiah } from "../../utils/formatter";
import { Search, Plus } from "lucide-react";

export default function ProductPicker({
  productPickerForKey,
  productPickerMode,
  productSearch,
  setProductSearch,
  filteredProducts,
  setProductPickerForKey,
  addLineItemFromProduct,
  pickProductForSingleField,
}: any) {
  if (!productPickerForKey) return null;

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-neutral-900 rounded-2xl p-6 w-full max-w-lg shadow-xl max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-bold text-neutral-800 dark:text-neutral-100">Pilih dari Paket</h3>
            <p className="text-xs text-gray-400 mt-0.5">
              {productPickerMode === "single" ? "Klik paket untuk mengisi field layanan" : "Klik paket untuk menambah ke daftar item"}
            </p>
          </div>
          <button onClick={() => setProductPickerForKey(null)} className="text-gray-400 hover:text-gray-600">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
        <div className="relative mb-3">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            value={productSearch}
            onChange={e => setProductSearch(e.target.value)}
            placeholder="Cari nama paket..."
            autoFocus
            className="w-full pl-10 pr-3 py-2.5 text-sm border border-gray-200 dark:border-neutral-700 rounded-xl bg-white dark:bg-neutral-800"
          />
        </div>
        <div className="flex-1 overflow-y-auto space-y-2">
          {filteredProducts.length === 0 && (
            <p className="text-sm text-gray-400 text-center py-4">Tidak ada paket. Tambahkan di Master Produk dulu.</p>
          )}
          {filteredProducts.map((p: any) => (
            <button
              key={p.id}
              onClick={() => productPickerMode === "single"
                ? pickProductForSingleField(productPickerForKey, p)
                : addLineItemFromProduct(productPickerForKey, p)}
              className="w-full text-left p-3 rounded-xl border border-[var(--border-default)] bg-white dark:bg-neutral-900 hover:border-amber-300 transition-colors">
              <div className="flex items-center justify-between">
                <p className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">{p.name}</p>
                <p className="text-sm font-bold text-amber-600">{formatRupiah(p.base_price)}</p>
              </div>
              {p.description && <p className="text-xs text-gray-500 mt-1 line-clamp-2">{p.description}</p>}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}