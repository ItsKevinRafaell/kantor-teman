"use client";

import { useEffect, useRef } from "react";

interface ModalProps {
  open: boolean;
  title: string;
  message?: string;
  confirmLabel?: string;
  confirmClass?: string;
  cancelLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
  children?: React.ReactNode;
}

export default function Modal({
  open, title, message, confirmLabel = "Ya", confirmClass, cancelLabel = "Batal",
  onConfirm, onCancel, children,
}: ModalProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open) ref.current?.focus();
  }, [open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-fade-in" role="dialog" aria-modal="true" aria-labelledby="modal-title">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onCancel} />
      <div ref={ref} tabIndex={-1} className="relative bg-[var(--bg-surface)] rounded-2xl shadow-modal border border-[var(--border-default)] w-full max-w-md p-6 outline-none animate-slide-up">
        <h3 id="modal-title" className="text-base font-bold text-neutral-900 dark:text-neutral-50 mb-2">{title}</h3>
        {message && <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-5 leading-relaxed">{message}</p>}
        {children && <div className="mb-5">{children}</div>}
        <div className="flex justify-end gap-3">
          <button onClick={onCancel} className="btn-ghost">
            {cancelLabel}
          </button>
          <button onClick={onConfirm}
            className={confirmClass ? `px-4 py-2.5 text-sm font-semibold text-white rounded-xl transition-all duration-200 hover:scale-[1.02] active:scale-[0.98] ${confirmClass}` : "btn-primary"}>
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
