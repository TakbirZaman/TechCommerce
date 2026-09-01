"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { ReviewForm } from "@/components/discovery/ReviewForm";
import { PriceHistoryChart } from "@/components/discovery/PriceHistoryChart";

interface Product {
  id: number;
  name: string;
  slug: string;
  sku: string;
  description: string;
  price: number;
  status: string;
  stock_quantity: number;
  is_featured: boolean;
  specifications: Record<string, any>;
  brand: { id: number; name: string; slug: string };
  category: { id: number; name: string; slug: string };
  image_url: string | null;
  created_at: string;
}

interface Review {
  id: number;
  rating: number;
  title: string;
  body: string;
  pros: string | null;
  cons: string | null;
  is_verified_purchase: boolean;
  created_at: string;
}

interface RatingAggregate {
  average_rating: number;
  total_reviews: number;
  rating_distribution: Record<number, number>;
}

export default function ProductDetailPage() {
  const params = useParams();
  const slug = params.slug as string;

  const [product, setProduct] = useState<Product | null>(null);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [rating, setRating] = useState<RatingAggregate | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"details" | "specs" | "reviews">("details");

  useEffect(() => {
    loadProduct();
  }, [slug]);

  const loadProduct = async () => {
    try {
      setLoading(true);
      // Assuming there's a product detail endpoint
      const response = await fetch(`/api/v1/products/${slug}`);
      if (!response.ok) throw new Error("Product not found");
      const data = await response.json();
      setProduct(data);

      // Load reviews and rating
      const [reviewsRes, ratingRes] = await Promise.all([
        fetch(`/api/v1/products/${data.id}/reviews`),
        fetch(`/api/v1/products/${data.id}/rating`),
      ]);

      if (reviewsRes.ok) setReviews(await reviewsRes.json());
      if (ratingRes.ok) setRating(await ratingRes.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load product");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/3 mb-4"></div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="h-96 bg-gray-200 rounded"></div>
            <div className="space-y-4">
              <div className="h-4 bg-gray-200 rounded w-1/4"></div>
              <div className="h-6 bg-gray-200 rounded w-1/2"></div>
              <div className="h-4 bg-gray-200 rounded w-full"></div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error || !product) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="text-center py-12">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Product Not Found</h1>
          <p className="text-gray-600 mb-4">{error || "The product you're looking for doesn't exist."}</p>
          <Link href="/search" className="text-blue-600 hover:underline">
            Browse all products
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Breadcrumb */}
      <nav className="text-sm text-gray-600 mb-6">
        <Link href="/" className="hover:text-blue-600">Home</Link>
        <span className="mx-2">/</span>
        <Link href={`/categories/${product.category.slug}`} className="hover:text-blue-600">
          {product.category.name}
        </Link>
        <span className="mx-2">/</span>
        <span className="text-gray-900">{product.name}</span>
      </nav>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-12">
        {/* Product Image */}
        <div className="aspect-square bg-gray-100 rounded-lg overflow-hidden">
          {product.image_url ? (
            <img
              src={product.image_url}
              alt={product.name}
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-gray-400">
              No image available
            </div>
          )}
        </div>

        {/* Product Info */}
        <div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">{product.name}</h1>
          <p className="text-lg text-gray-600 mb-4">
            by <span className="font-medium">{product.brand.name}</span>
          </p>

          {/* Rating */}
          {rating && (
            <div className="flex items-center gap-2 mb-4">
              <div className="flex text-yellow-400">
                {[1, 2, 3, 4, 5].map((star) => (
                  <svg
                    key={star}
                    className={`w-5 h-5 ${
                      star <= Math.round(rating.average_rating) ? "fill-current" : "fill-gray-300"
                    }`}
                    viewBox="0 0 20 20"
                  >
                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                  </svg>
                ))}
              </div>
              <span className="text-gray-600">
                {rating.average_rating.toFixed(1)} ({rating.total_reviews} reviews)
              </span>
            </div>
          )}

          {/* Price */}
          <div className="text-3xl font-bold text-blue-600 mb-4">
            ৳{product.price.toLocaleString()}
          </div>

          {/* Stock Status */}
          <div className="mb-4">
            {product.stock_quantity > 0 ? (
              <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
                In Stock ({product.stock_quantity} available)
              </span>
            ) : (
              <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-red-100 text-red-800">
                Out of Stock
              </span>
            )}
          </div>

          {/* Description */}
          <p className="text-gray-700 mb-6">{product.description}</p>

          {/* Add to Cart Button */}
          <button
            className="w-full bg-blue-600 text-white py-3 px-6 rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
            disabled={product.stock_quantity === 0}
          >
            {product.stock_quantity > 0 ? "Add to Cart" : "Out of Stock"}
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="flex gap-8">
          {(["details", "specs", "reviews"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === tab
                  ? "border-blue-600 text-blue-600"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              {tab === "details" ? "Details" : tab === "specs" ? "Specifications" : `Reviews (${reviews.length})`}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="mb-12">
        {activeTab === "details" && (
          <div className="prose max-w-none">
            <p>{product.description}</p>
          </div>
        )}

        {activeTab === "specs" && (
          <div className="grid grid-cols-2 gap-4">
            {Object.entries(product.specifications).map(([key, value]) => (
              <div key={key} className="flex justify-between py-2 border-b">
                <span className="text-gray-600">{key.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase())}</span>
                <span className="font-medium">{String(value)}</span>
              </div>
            ))}
          </div>
        )}

        {activeTab === "reviews" && (
          <div>
            <ReviewForm productId={product.id} onReviewSubmitted={loadProduct} />
            <div className="mt-8 space-y-6">
              {reviews.map((review) => (
                <div key={review.id} className="border rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="flex text-yellow-400">
                      {[1, 2, 3, 4, 5].map((star) => (
                        <svg
                          key={star}
                          className={`w-4 h-4 ${
                            star <= review.rating ? "fill-current" : "fill-gray-300"
                          }`}
                          viewBox="0 0 20 20"
                        >
                          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                        </svg>
                      ))}
                    </div>
                    {review.is_verified_purchase && (
                      <span className="text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded">
                        Verified Purchase
                      </span>
                    )}
                  </div>
                  <h3 className="font-medium mb-1">{review.title}</h3>
                  <p className="text-gray-700 mb-2">{review.body}</p>
                  {review.pros && (
                    <p className="text-sm text-green-700"><strong>Pros:</strong> {review.pros}</p>
                  )}
                  {review.cons && (
                    <p className="text-sm text-red-700"><strong>Cons:</strong> {review.cons}</p>
                  )}
                  <p className="text-xs text-gray-500 mt-2">
                    {new Date(review.created_at).toLocaleDateString()}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Price History */}
      <div className="mb-12">
        <h2 className="text-xl font-bold mb-4">Price History</h2>
        <PriceHistoryChart productId={product.id} />
      </div>
    </div>
  );
}
