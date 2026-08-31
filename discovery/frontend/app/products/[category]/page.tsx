import type { Metadata } from "next";
import { apiGet } from "@/lib/api";
import { CategoryBrowseClient } from "./CategoryBrowseClient";

interface CategoryPageData {
  category: { id: number; name: string; slug: string };
  description?: string;
  subcategories: { name: string; slug: string }[];
  popular_brands: { name: string; slug: string; product_count: number }[];
  products: unknown[];
}

/**
 * URL shape (Section 8): /products/laptops?brand=asus&ram_gb=16&max_price=100000
 * Category comes from the path (SEO-friendly, Section 28); everything else
 * from query params so it's shareable/bookmarkable.
 */
export async function generateMetadata({
  params,
}: {
  params: Promise<{ category: string }>;
}): Promise<Metadata> {
  const { category } = await params;
  let data: CategoryPageData | null = null;
  try {
    data = await apiGet<CategoryPageData>(`/categories/${category}`);
  } catch {
    return { title: "Category not found" };
  }
  const canonical = `/products/${category}`;
  return {
    title: `${data.category.name} — Shop & Compare`,
    description: data.description ?? `Browse ${data.category.name} with filters, comparisons, and reviews.`,
    alternates: { canonical },
    openGraph: {
      title: data.category.name,
      description: data.description,
      url: canonical,
      type: "website",
    },
  };
}

export default async function CategoryPage({ params }: { params: Promise<{ category: string }> }) {
  const { category } = await params;
  const [pageData, filtersData] = await Promise.all([
    apiGet<CategoryPageData>(`/categories/${category}`),
    apiGet<{ filters: unknown[] }>(`/categories/${category}/filters`),
  ]);

  return (
    <main className="mx-auto max-w-6xl px-4 py-8">
      <h1 className="text-2xl font-semibold">{pageData.category.name}</h1>
      {pageData.description && <p className="mt-2 text-muted-foreground">{pageData.description}</p>}
      <CategoryBrowseClient categorySlug={category} initialFilters={filtersData.filters} popularBrands={pageData.popular_brands} />
    </main>
  );
}
