"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { buildFilterUrl } from "@/lib/searchParams";

export interface FilterOption {
  value: string | number | boolean;
  label: string;
  count: number;
}

export interface FilterDefinition {
  key: string;
  label: string;
  type: "enum" | "range" | "boolean";
  unit?: string;
  options: FilterOption[];
  min?: number;
  max?: number;
}

/**
 * Section 6-8: renders dynamically-derived filters and writes selections
 * straight into the URL, so results stay shareable/bookmarkable.
 */
export function FilterPanel({ filters }: { filters: FilterDefinition[] }) {
  const router = useRouter();
  const searchParams = useSearchParams();

  function toggleEnumValue(key: string, value: string | number | boolean) {
    const current = searchParams.getAll(key);
    const stringValue = String(value);
    const next = current.includes(stringValue)
      ? current.filter((v) => v !== stringValue)
      : [...current, stringValue];
    router.push(buildFilterUrl(searchParams, { [key]: next.length ? next : null }));
  }

  function setRange(key: string, min?: number, max?: number) {
    router.push(
      buildFilterUrl(searchParams, {
        [`min_${key}`]: min?.toString() ?? null,
        [`max_${key}`]: max?.toString() ?? null,
      })
    );
  }

  return (
    <nav aria-label="Product filters" className="space-y-6">
      {filters.map((filter) => (
        <fieldset key={filter.key} className="space-y-2">
          <legend className="text-sm font-medium">
            {filter.label}
            {filter.unit ? ` (${filter.unit})` : ""}
          </legend>

          {filter.type === "enum" &&
            filter.options.map((opt) => {
              const checked = searchParams.getAll(filter.key).includes(String(opt.value));
              return (
                <label key={String(opt.value)} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => toggleEnumValue(filter.key, opt.value)}
                    className="h-4 w-4 rounded border-input"
                  />
                  <span>{opt.label}</span>
                  <span className="text-xs text-muted-foreground">({opt.count})</span>
                </label>
              );
            })}

          {filter.type === "range" && (
            <div className="flex items-center gap-2">
              <label className="sr-only" htmlFor={`${filter.key}-min`}>
                Minimum {filter.label}
              </label>
              <input
                id={`${filter.key}-min`}
                type="number"
                placeholder={filter.min?.toString()}
                className="w-24 rounded-md border border-input px-2 py-1 text-sm"
                onBlur={(e) => setRange(filter.key, e.target.valueAsNumber || undefined, undefined)}
              />
              <span aria-hidden="true">–</span>
              <label className="sr-only" htmlFor={`${filter.key}-max`}>
                Maximum {filter.label}
              </label>
              <input
                id={`${filter.key}-max`}
                type="number"
                placeholder={filter.max?.toString()}
                className="w-24 rounded-md border border-input px-2 py-1 text-sm"
                onBlur={(e) => setRange(filter.key, undefined, e.target.valueAsNumber || undefined)}
              />
            </div>
          )}

          {filter.type === "boolean" &&
            filter.options.map((opt) => {
              const checked = searchParams.get(filter.key) === String(opt.value);
              return (
                <label key={String(opt.value)} className="flex items-center gap-2 text-sm">
                  <input
                    type="radio"
                    name={filter.key}
                    checked={checked}
                    onChange={() =>
                      router.push(buildFilterUrl(searchParams, { [filter.key]: String(opt.value) }))
                    }
                    className="h-4 w-4"
                  />
                  <span>{opt.label}</span>
                  <span className="text-xs text-muted-foreground">({opt.count})</span>
                </label>
              );
            })}
        </fieldset>
      ))}
    </nav>
  );
}
