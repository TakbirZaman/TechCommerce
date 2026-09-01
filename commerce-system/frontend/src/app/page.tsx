import Link from "next/link";

export default function HomePage() {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Store</h1>
      <p className="text-gray-600">
        Product browsing/listing pages belong to the core-platform / catalog branch. This
        placeholder just links to the commerce flows built in this branch.
      </p>
      <div className="flex gap-3">
        <Link href="/cart" className="text-brand-600 hover:underline">
          View Cart
        </Link>
        <Link href="/orders" className="text-brand-600 hover:underline">
          Order History
        </Link>
      </div>
    </div>
  );
}
