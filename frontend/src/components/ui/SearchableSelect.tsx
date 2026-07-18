"use client";

import { useState, useRef, useEffect } from "react";
import { Search, ChevronDown, X } from "lucide-react";

interface Option {
  value: string;
  label: string;
  sub?: string;
}

interface SearchableSelectProps {
  options: Option[];
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  searchPlaceholder?: string;
  maxDisplay?: number;
  disabled?: boolean;
}

export function SearchableSelect({
  options,
  value,
  onChange,
  placeholder = "Pilih...",
  searchPlaceholder = "Ketik untuk cari...",
  maxDisplay = 10,
  disabled = false,
}: SearchableSelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const selectedOption = options.find((o) => o.value === value);

  const filteredOptions = options
    .filter(
      (o) =>
        o.label.toLowerCase().includes(search.toLowerCase()) ||
        o.sub?.toLowerCase().includes(search.toLowerCase())
    )
    .slice(0, maxDisplay);

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
        setSearch("");
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSelect = (option: Option) => {
    onChange(option.value);
    setIsOpen(false);
    setSearch("");
  };

  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation();
    onChange("");
  };

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={() => !disabled && setIsOpen(!isOpen)}
        disabled={disabled}
        className={`
          w-full flex items-center justify-between gap-2 px-3 py-2
          text-sm text-left bg-white dark:bg-neutral-900
          border border-neutral-300 dark:border-neutral-700
          rounded-lg shadow-sm
          ${disabled ? "opacity-50 cursor-not-allowed" : "hover:border-neutral-400 dark:hover:border-neutral-600 cursor-pointer"}
          ${isOpen ? "ring-2 ring-amber-500 border-amber-500" : ""}
        `}
      >
        <span className={selectedOption ? "text-neutral-900 dark:text-neutral-100" : "text-neutral-400"}>
          {selectedOption ? (
            <span>
              {selectedOption.label}
              {selectedOption.sub && (
                <span className="text-neutral-400 ml-1">— {selectedOption.sub}</span>
              )}
            </span>
          ) : (
            placeholder
          )}
        </span>
        <div className="flex items-center gap-1">
          {value && !disabled && (
            <X
              size={14}
              className="text-neutral-400 hover:text-neutral-600"
              onClick={handleClear}
            />
          )}
          <ChevronDown
            size={14}
            className={`text-neutral-400 transition-transform ${isOpen ? "rotate-180" : ""}`}
          />
        </div>
      </button>

      {isOpen && (
        <div className="absolute z-50 w-full mt-1 bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-700 rounded-lg shadow-lg overflow-hidden">
          {/* Search input */}
          <div className="p-2 border-b border-neutral-100 dark:border-neutral-800">
            <div className="relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400" />
              <input
                ref={inputRef}
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder={searchPlaceholder}
                className="w-full pl-9 pr-3 py-2 text-sm bg-neutral-50 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-md focus:outline-none focus:ring-1 focus:ring-amber-500"
              />
            </div>
          </div>

          {/* Options list */}
          <div className="max-h-64 overflow-y-auto">
            {filteredOptions.length === 0 ? (
              <div className="px-4 py-8 text-center text-neutral-400 text-sm">
                Tidak ditemukan
              </div>
            ) : (
              filteredOptions.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => handleSelect(option)}
                  className={`
                    w-full px-4 py-2.5 text-left hover:bg-amber-50 dark:hover:bg-amber-900/20
                    ${option.value === value ? "bg-amber-50 dark:bg-amber-900/30" : ""}
                  `}
                >
                  <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                    {option.label}
                  </p>
                  {option.sub && (
                    <p className="text-xs text-neutral-400 mt-0.5">{option.sub}</p>
                  )}
                </button>
              ))
            )}
          </div>

          {/* Footer */}
          {filteredOptions.length > 0 && filteredOptions.length < options.length && (
            <div className="px-4 py-2 border-t border-neutral-100 dark:border-neutral-800 text-xs text-neutral-400">
              Menampilkan {filteredOptions.length} dari {options.length} opsi
            </div>
          )}
        </div>
      )}
    </div>
  );
}
