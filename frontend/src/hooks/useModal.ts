import { useState, useCallback } from "react";

interface ModalState<T = unknown> {
  open: boolean;
  data: T | null;
}

interface UseModalReturn<T = unknown> {
  isOpen: boolean;
  data: T | null;
  openModal: (data?: T) => void;
  closeModal: () => void;
}

/**
 * Generic modal state management hook
 */
export function useModal<T = unknown>(initialData: T | null = null): UseModalReturn<T> {
  const [state, setState] = useState<ModalState<T>>({
    open: false,
    data: initialData,
  });

  const openModal = useCallback((data?: T) => {
    setState({
      open: true,
      data: data !== undefined ? data : null,
    });
  }, []);

  const closeModal = useCallback(() => {
    setState((prev) => ({
      ...prev,
      open: false,
    }));
  }, []);

  return {
    isOpen: state.open,
    data: state.data,
    openModal,
    closeModal,
  };
}

// Convenience overload for simpler modal (just open/close)
interface SimpleModalReturn {
  isOpen: boolean;
  openModal: () => void;
  closeModal: () => void;
  toggleModal: () => void;
}

export function useSimpleModal(initialState: boolean = false): SimpleModalReturn {
  const [isOpen, setIsOpen] = useState(initialState);

  const openModal = useCallback(() => setIsOpen(true), []);
  const closeModal = useCallback(() => setIsOpen(false), []);
  const toggleModal = useCallback(() => setIsOpen((prev) => !prev), []);

  return { isOpen, openModal, closeModal, toggleModal };
}