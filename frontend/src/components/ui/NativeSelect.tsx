"use client";

/**
 * Drop-in searchable select for simple option lists.
 * Prefer this over raw <select> everywhere in the app.
 */
import { SearchableSelect, type SearchableOption } from "./SearchableSelect";

export type { SearchableOption };

type Opt = string | SearchableOption;

function normalize(options: Opt[]): SearchableOption[] {
  return options.map((o) =>
    typeof o === "string" ? { value: o, label: o } : o,
  );
}

interface NativeSelectProps {
  value: string | number;
  onChange: (value: string) => void;
  options: Opt[];
  placeholder?: string;
  searchPlaceholder?: string;
  disabled?: boolean;
  className?: string;
  size?: "sm" | "md";
  clearable?: boolean;
  maxDisplay?: number;
}

export default function NativeSelect({
  value,
  onChange,
  options,
  placeholder = "Pilih…",
  searchPlaceholder = "Cari…",
  disabled = false,
  className = "",
  size = "md",
  clearable = true,
  maxDisplay = 80,
}: NativeSelectProps) {
  return (
    <SearchableSelect
      value={value === undefined || value === null ? "" : String(value)}
      onChange={onChange}
      options={normalize(options)}
      placeholder={placeholder}
      searchPlaceholder={searchPlaceholder}
      disabled={disabled}
      className={className}
      size={size}
      clearable={clearable}
      maxDisplay={maxDisplay}
    />
  );
}
