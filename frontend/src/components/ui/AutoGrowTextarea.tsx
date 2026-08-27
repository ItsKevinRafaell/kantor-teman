"use client";

import React, { useCallback, useEffect, useRef } from "react";

type AutoGrowTextareaProps = React.TextareaHTMLAttributes<HTMLTextAreaElement> & {
  /** Minimum number of visible text rows before growing. */
  minRows?: number;
};

/**
 * A textarea that automatically grows its height to fit its content, so long
 * report notes don't get stuck inside a tiny scroll box.
 *
 * It behaves like a normal controlled/uncontrolled <textarea>: pass `value` +
 * `onChange` (or `defaultValue`) and any standard textarea props. Height is
 * recomputed on every value change and on mount.
 */
const AutoGrowTextarea = React.forwardRef<HTMLTextAreaElement, AutoGrowTextareaProps>(
  function AutoGrowTextarea({ value, minRows = 2, onChange, style, ...rest }, forwardedRef) {
    const innerRef = useRef<HTMLTextAreaElement | null>(null);

    const setRefs = useCallback(
      (node: HTMLTextAreaElement | null) => {
        innerRef.current = node;
        if (typeof forwardedRef === "function") {
          forwardedRef(node);
        } else if (forwardedRef) {
          (forwardedRef as React.MutableRefObject<HTMLTextAreaElement | null>).current = node;
        }
      },
      [forwardedRef],
    );

    const resize = useCallback(() => {
      const el = innerRef.current;
      if (!el) return;
      el.style.height = "auto";
      el.style.height = `${el.scrollHeight}px`;
    }, []);

    // Re-fit whenever the controlled value changes (and on mount).
    useEffect(() => {
      resize();
    }, [value, resize]);

    const handleChange = useCallback(
      (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        resize();
        onChange?.(e);
      },
      [onChange, resize],
    );

    return (
      <textarea
        ref={setRefs}
        rows={minRows}
        value={value}
        onChange={handleChange}
        style={{ resize: "none", overflow: "hidden", ...style }}
        {...rest}
      />
    );
  },
);

export default AutoGrowTextarea;
