import type { Metadata } from "next";
import { apiGet } from "@/lib/api";
import { CategoryBrowseClient } from "../../products/[category]/CategoryBrowseClient";

/**
 * Section 22 uses /categories/laptops as the canonical category landing
 * page URL; /products/[category] (Section 8's example URL) renders the
 * same underlying view. Both resolve through the same category API and
 * client component to avoid duplicating the browse logic.
 */
interface CategoryPageData {
  category: { id: number; name: string; slug: string };
  description?: string;
  subcategories: { name: string; slug: string }[];
  popular_brands: { name: string; slug: string; product_count: number }[];
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  try {
    const data = await apiGet<CategoryPageData>(`/categories/${slug}`);
    const canonical = `/categories/${slug}`;
    return {
      title: `${data.category.name} — Shop & Compare`,
      description: data.description ?? `Browse ${data.category.name} with filters, comparisons, and reviews.`,
      alternates: { canonical },
      openGraph: { title: data.category.name, description: data.description, url: canonical, type: "website" },
    };
  } catch {
    return { title: "Category not found" };
  }
}

export default async function CategoryLandingPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const [pageData, filtersData] = await Promise.all([
    apiGet<CategoryPageData>(`/categories/${slug}`),
    apiGet<{ filters: unknown[] }>(`/categories/${slug}/filters`),
  ]);

  return (
    <main className="mx-auto max-w-6xl px-4 py-8">
      <h1 className="text-2xl font-semibold">{pageData.category.name}</h1>
      {pageData.description && <p className="mt-2 text-muted-foreground">{pageData.description}</p>}

      {pageData.subcategories.length > 0 && (
        <nav aria-label="Subcategories" className="mt-4 flex flex-wrap gap-2">
          {pageData.subcategories.map((sc) => (
            <a key={sc.slug} href={`/categories/${sc.slug}`} className="rounded-full border border-border px-3 py-1 text-sm">
              {sc.name}
            </a>
          ))}
        </nav>
      )}

      <CategoryBrowseClient
        categorySlug={slug}
        initialFilters={filtersData.filters as never}
        popularBrands={pageData.popular_brands}
      />
    </main>
  );
}
