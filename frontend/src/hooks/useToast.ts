import { useState, useCallback, useEffect, useRef } from "react";

interface ToastState {
  message: string | null;
  type: "success" | "error" | "info";
}

interface UseToastReturn {
  toast: ToastState | null;
  showToast: (message: string, type?: "success" | "error" | "info") => void;
  hideToast: () => void;
}

/**
 * Toast notification hook with auto-dismiss
 */
export function useToast(duration: number = 4000): UseToastReturn {
  const [toast, setToast] = useState<ToastState | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  const hideToast = useCallback(() => {
    setToast(null);
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const showToast = useCallback(
    (message: string, type: "success" | "error" | "info" = "success") => {
      // Clear existing timer
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }

      setToast({ message, type });

      // Auto-dismiss
      timerRef.current = setTimeout(() => {
        setToast(null);
        timerRef.current = null;
      }, duration);
    },
    [duration]
  );

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
    };
  }, []);

  return { toast, showToast, hideToast };
}