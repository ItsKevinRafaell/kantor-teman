"use client";
import { Check, ChevronRight } from "lucide-react";

const STEPS = ["Pilih Template", "Pilih Target", "Isi Variabel", "Preview", "Selesai"];

interface GeneratorStepsProps {
  currentStep: number;
  onStepChange?: (step: number) => void;
}

export default function GeneratorSteps({ currentStep: step }: GeneratorStepsProps) {
  return (
    <div className="flex items-center gap-1">
      {STEPS.map((s, i) => (
        <div key={i} className="flex items-center gap-1">
          <div className={`flex items-center justify-center w-7 h-7 rounded-full text-xs font-bold transition-colors ${
            i < step ? "bg-green-500 text-white" : i === step ? "bg-amber-500 text-white" : "bg-gray-200 dark:bg-neutral-700 text-gray-500"
          }`}>
            {i < step ? <Check size={12} /> : i + 1}
          </div>
          <span className={`text-xs font-medium hidden sm:block ${i === step ? "text-amber-600" : "text-gray-400"}`}>{s}</span>
          {i < STEPS.length - 1 && <div className="w-4 h-px bg-gray-200 dark:bg-neutral-700 mx-1" />}
        </div>
      ))}
    </div>
  );
}