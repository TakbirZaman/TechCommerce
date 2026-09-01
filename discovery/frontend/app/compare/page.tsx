import type { Metadata } from "next";
import { ComparisonTable } from "@/components/discovery/ComparisonTable";

export const metadata: Metadata = {
  title: "Compare Products",
  description: "Compare specifications, pricing, and availability side by side.",
};

export default function ComparePage() {
  return (
    <main className="mx-auto max-w-6xl px-4 py-8">
      <h1 className="mb-6 text-2xl font-semibold">Compare Products</h1>
      <ComparisonTable />
    </main>
  );
}
