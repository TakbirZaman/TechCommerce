import type { Metadata } from "next";
import { apiGet } from "@/lib/api";

interface BrandPageData {
  brand: { id: number; name: string; slug: string; logo_url?: string };
  description?: string;
  categories: { name: string; slug: string }[];
  popular_products: { id: number; name: string; slug: string; price: number }[];
  products: { id: number; name: string; slug: string; price: number }[];
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  try {
    const data = await apiGet<BrandPageData>(`/brands/${slug}`);
    const canonical = `/brands/${slug}`;
    return {
      title: `${data.brand.name} Products`,
      description: data.description ?? `Explore ${data.brand.name}'s products, categories, and best sellers.`,
      alternates: { canonical },
      openGraph: { title: data.brand.name, description: data.description, url: canonical, type: "website" },
    };
  } catch {
    return { title: "Brand not found" };
  }
}

export default async function BrandPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const data = await apiGet<BrandPageData>(`/brands/${slug}`);

  return (
    <main className="mx-auto max-w-6xl px-4 py-8">
      <header className="flex items-center gap-4">
        {data.brand.logo_url && (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={data.brand.logo_url} alt={`${data.brand.name} logo`} className="h-16 w-16 object-contain" />
        )}
        <div>
          <h1 className="text-2xl font-semibold">{data.brand.name}</h1>
          {data.description && <p className="text-muted-foreground">{data.description}</p>}
        </div>
      </header>

      {data.categories.length > 0 && (
        <nav aria-label="Categories" className="mt-6 flex flex-wrap gap-2">
          {data.categories.map((c) => (
            <a key={c.slug} href={`/products/${c.slug}?brand=${data.brand.slug}`} className="rounded-full border border-border px-3 py-1 text-sm">
              {c.name}
            </a>
          ))}
        </nav>
      )}

      <section className="mt-8">
        <h2 className="mb-4 text-lg font-semibold">Popular Products</h2>
        <ul className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {data.popular_products.map((p) => (
            <li key={p.id} className="rounded-lg border border-border p-4">
              <a href={`/products/detail/${p.slug}`}>
                <h3 className="text-sm font-medium">{p.name}</h3>
                <p className="font-semibold">${p.price.toLocaleString()}</p>
              </a>
            </li>
          ))}
        </ul>
      </section>

      <section className="mt-8">
        <h2 className="mb-4 text-lg font-semibold">All Products</h2>
        <ul className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {data.products.map((p) => (
            <li key={p.id} className="rounded-lg border border-border p-4">
              <a href={`/products/detail/${p.slug}`}>
                <h3 className="text-sm font-medium">{p.name}</h3>
                <p className="font-semibold">${p.price.toLocaleString()}</p>
              </a>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
