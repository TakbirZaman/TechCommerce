"use client";

import { useEffect, useState } from "react";

/**
 * Section 5: avoid firing an autocomplete request on every keystroke.
 * Usage: const debouncedQuery = useDebounce(query, 300);
 */
export function useDebounce<T>(value: T, delayMs: number = 300): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);

  return debounced;
}
