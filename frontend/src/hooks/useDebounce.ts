import { useState, useEffect } from "react";

/**
 * Debounce hook for search inputs
 * Delays updating the value until after a specified delay
 */
export function useDebounce<T>(value: T, delay: number = 300): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(timer);
    };
  }, [value, delay]);

  return debouncedValue;
}

// Specialized version for search inputs
export function useSearchDebounce(initialValue: string = ""): {
  value: string;
  debouncedValue: string;
  setValue: (value: string) => void;
} {
  const [value, setValue] = useState(initialValue);
  const debouncedValue = useDebounce(value, 300);

  return { value, debouncedValue, setValue };
}