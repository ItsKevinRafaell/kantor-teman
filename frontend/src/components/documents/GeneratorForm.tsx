"use client";
import { ChevronLeft, ChevronRight } from "lucide-react";
import VariableInputForm from "./VariableInputForm";

interface GeneratorFormProps {
  step: number;
  setStep: (s: number) => void;
  selectedTemplate: any;
  variables: Record<string, string>;
  setVariables: (v: Record<string, string> | ((prev: Record<string, string>) => Record<string, string>)) => void;
  lineItems: any;
  setLineItems: (v: any) => void;
  paymentMethods: any[];
  products: any[];
  setProductPickerForKey: (k: string | null) => void;
  setProductPickerMode: (m: "line_item" | "single") => void;
  klienCandidates: any[];
  klienSearch: string;
  setKlienSearch: (s: string) => void;
  klienDropdownOpen: boolean;
  setKlienDropdownOpen: (b: boolean) => void;
  klienRef: React.RefObject<HTMLDivElement | null>;
  setShowSeqEditor: (b: boolean) => void;
  loadCurrentSequence: () => void;
  setToast: (t: { message: string; type: "success" | "error" } | null) => void;
  previewing: boolean;
  handlePreview: () => Promise<void>;
}

export default function GeneratorForm({
  step, setStep, selectedTemplate, variables, setVariables, lineItems, setLineItems,
  paymentMethods, products, setProductPickerForKey, setProductPickerMode,
  klienCandidates, klienSearch, setKlienSearch, klienDropdownOpen, setKlienDropdownOpen,
  klienRef, setShowSeqEditor, loadCurrentSequence, setToast, previewing, handlePreview,
}: GeneratorFormProps) {
  return (
    <div className="space-y-4">
      <VariableInputForm
        variables={variables}
        setVariables={setVariables}
        lineItems={lineItems}
        setLineItems={setLineItems}
        selectedTemplate={selectedTemplate}
        paymentMethods={paymentMethods}
        products={products}
        setProductPickerForKey={setProductPickerForKey}
        setProductPickerMode={setProductPickerMode}
        klienCandidates={klienCandidates}
        klienSearch={klienSearch}
        setKlienSearch={setKlienSearch}
        klienDropdownOpen={klienDropdownOpen}
        setKlienDropdownOpen={setKlienDropdownOpen}
        klienRef={klienRef}
        setShowSeqEditor={setShowSeqEditor}
        loadCurrentSequence={loadCurrentSequence}
        setToast={setToast}
      />
      <div className="flex justify-between pt-2">
        <button onClick={() => setStep(1)} className="flex items-center gap-1.5 px-4 py-2 text-sm font-semibold text-gray-600 border border-gray-200 rounded-xl">
          <ChevronLeft size={16} /> Kembali
        </button>
        <button onClick={handlePreview} disabled={previewing}
          className="flex items-center gap-1.5 px-5 py-2.5 bg-amber-500 hover:bg-amber-600 text-white text-sm font-bold rounded-xl disabled:opacity-50">
          {previewing ? "Menyiapkan Preview..." : "Preview PDF"} <ChevronRight size={16} />
        </button>
      </div>
    </div>
  );
}