"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { useDebounce } from "@/hooks/useDebounce";
import { useAutocomplete } from "@/hooks/useProductSearch";

/** Sections 3 & 5: search input with debounced autocomplete suggestions. */
export function SearchBar({ initialQuery = "" }: { initialQuery?: string }) {
  const router = useRouter();
  const [query, setQuery] = useState(initialQuery);
  const [open, setOpen] = useState(false);
  const debouncedQuery = useDebounce(query, 300);
  const { data } = useAutocomplete(debouncedQuery);

  function submitSearch(term: string) {
    setOpen(false);
    router.push(`/search?q=${encodeURIComponent(term)}`);
  }

  return (
    <div className="relative w-full max-w-xl">
      <label htmlFor="discovery-search" className="sr-only">
        Search products
      </label>
      <input
        id="discovery-search"
        role="combobox"
        aria-expanded={open}
        aria-controls="discovery-search-suggestions"
        autoComplete="off"
        className="w-full rounded-md border border-input bg-background px-4 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        placeholder="Search laptops, phones, monitors..."
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
        }}
        onKeyDown={(e) => {
          if (e.key === "Enter") submitSearch(query);
          if (e.key === "Escape") setOpen(false);
        }}
      />
      {open && data?.suggestions?.length ? (
        <ul
          id="discovery-search-suggestions"
          role="listbox"
          className="absolute z-10 mt-1 w-full rounded-md border border-input bg-popover shadow-md"
        >
          {data.suggestions.map((s, i) => (
            <li key={`${s.type}-${s.label}-${i}`} role="option" aria-selected={false}>
              <button
                type="button"
                className="flex w-full items-center justify-between px-4 py-2 text-left text-sm hover:bg-accent"
                onClick={() => submitSearch(s.label)}
              >
                <span>{s.label}</span>
                <span className="text-xs text-muted-foreground">{s.type}</span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
