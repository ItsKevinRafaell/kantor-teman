"use client";
import { useState } from "react";

interface FAQ {
  question: string;
  answer: string;
}

interface ReportFAQProps {
  faqs: FAQ[];
}

function AccordionItem({ question, answer }: { question: string; answer: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="py-3">
      <button onClick={() => setOpen(!open)} className="w-full flex items-center justify-between text-left gap-3">
        <span className="text-sm font-medium text-zinc-900 dark:text-zinc-100">{question}</span>
        <svg className={`w-4 h-4 shrink-0 text-amber-500 transition-transform duration-200 ${open ? "rotate-180" : ""}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      <div className={`overflow-hidden transition-all duration-300 ease-in-out ${open ? "max-h-40 opacity-100 mt-2" : "max-h-0 opacity-0"}`}>
        <p className="text-sm text-zinc-700 dark:text-zinc-300 leading-relaxed">{answer}</p>
      </div>
    </div>
  );
}

export default function ReportFAQ({ faqs }: ReportFAQProps) {
  if (!faqs || faqs.length === 0) return null;

  return (
    <section className="bg-white dark:bg-zinc-900 border-2 border-zinc-200 dark:border-zinc-700 rounded-2xl p-6 shadow-sm transition-all duration-300 ease-in-out hover:border-amber-500">
      <h3 className="text-sm font-bold uppercase tracking-widest text-zinc-700 dark:text-zinc-300 mb-4">Pertanyaan yang Sering Ditanyakan</h3>
      <div className="divide-y divide-zinc-200 dark:divide-zinc-700">
        {faqs.map((faq, i) => (
          <AccordionItem key={i} question={faq.question} answer={faq.answer} />
        ))}
      </div>
    </section>
  );
}