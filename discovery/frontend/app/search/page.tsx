import type { Metadata } from "next";
import { SearchResultsClient } from "./SearchResultsClient";

export async function generateMetadata({
  searchParams,
}: {
  searchParams: Promise<{ q?: string }>;
}): Promise<Metadata> {
  const { q } = await searchParams;
  const title = q ? `Search results for "${q}"` : "Search";
  return { title, description: `Browse products matching "${q ?? ""}".` };
}

/**
 * Server component shell (Section 30: server components where appropriate);
 * the interactive results/filter list is a client component since it reads
 * live URL state and TanStack Query cache.
 */
export default async function SearchPage({
  searchParams,
}: {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
  const params = await searchParams;
  const q = typeof params.q === "string" ? params.q : "";

  return (
    <main className="mx-auto max-w-6xl px-4 py-8">
      <h1 className="mb-6 text-2xl font-semibold">
        {q ? `Search results for "${q}"` : "Search products"}
      </h1>
      <SearchResultsClient initialQuery={q} />
    </main>
  );
}
