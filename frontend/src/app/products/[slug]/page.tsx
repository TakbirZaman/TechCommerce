'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { catalog, commerce, compare } from '@/lib/api'
import { ShoppingCart, GitCompare, Heart, Share2, Star, Truck, ChevronRight, MessageSquare, CheckCircle2, XCircle } from 'lucide-react'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import { FadeIn, Stagger, StaggerItem } from '@/components/motion'

const EASE: [number, number, number, number] = [0.22, 1, 0.36, 1]

export default function ProductDetailPage() {
  const params = useParams()
  const slug = params.slug as string
  const reduceMotion = useReducedMotion()
  
  const [product, setProduct] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [quantity, setQuantity] = useState(1)
  const [addingToCart, setAddingToCart] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [selectedImage, setSelectedImage] = useState(0)
  const [reviewsData, setReviewsData] = useState<any>({ reviews: [], average_rating: 0, total_reviews: 0 })
  const [showReviewForm, setShowReviewForm] = useState(false)
  const [reviewForm, setReviewForm] = useState({ rating: 5, title: '', comment: '', reviewer_name: '', reviewer_email: '' })

  useEffect(() => {
    loadProduct()
  }, [slug])

  const loadProduct = async () => {
    try {
      const [data, reviews] = await Promise.all([
        catalog.product(slug),
        catalog.productReviews(slug).catch(() => ({ reviews: [], average_rating: 0, total_reviews: 0 })),
      ])
      setProduct(data)
      setReviewsData(reviews)
    } catch (error) {
      console.error('Failed to load product:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleAddToCart = async () => {
    setAddingToCart(true)
    try {
      await commerce.addToCart(product.id, quantity)
      setMessage({ type: 'success', text: 'Added to cart!' })
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to add to cart' })
    } finally {
      setAddingToCart(false)
      setTimeout(() => setMessage(null), 3000)
    }
  }

  const handleAddToCompare = async () => {
    try {
      await compare.add(product.id)
      setMessage({ type: 'success', text: 'Added to comparison!' })
    } catch (error: any) {
      setMessage({ type: 'error', text: error.message || 'Failed to add to comparison' })
    }
    setTimeout(() => setMessage(null), 3000)
  }

  const handleSubmitReview = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await catalog.createReview(slug, reviewForm)
      setMessage({ type: 'success', text: 'Review submitted!' })
      setShowReviewForm(false)
      setReviewForm({ rating: 5, title: '', comment: '', reviewer_name: '', reviewer_email: '' })
      // Reload reviews
      const reviews = await catalog.productReviews(slug)
      setReviewsData(reviews)
    } catch (error: any) {
      setMessage({ type: 'error', text: error.message || 'Failed to submit review' })
    }
    setTimeout(() => setMessage(null), 3000)
  }

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="h-6 shimmer rounded w-1/4 mb-6" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div className="h-96 shimmer rounded-2xl" />
          <div className="space-y-4">
            <div className="h-4 shimmer rounded w-1/4" />
            <div className="h-10 shimmer rounded w-3/4" />
            <div className="h-24 shimmer rounded w-full" />
            <div className="h-12 shimmer rounded w-full" />
          </div>
        </div>
      </div>
    )
  }

  if (!product) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8 text-center">
        <h1 className="text-2xl font-bold mb-4">Product Not Found</h1>
        <Link href="/products" className="text-primary-600 hover:underline underline-offset-4">
          Browse all products
        </Link>
      </div>
    )
  }

  const specs = product.specifications?.reduce((acc: any, spec: any) => {
    acc[spec.spec_key] = spec.value
    return acc
  }, {}) || {}

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Breadcrumb */}
      <FadeIn y={10}>
        <nav className="flex items-center gap-2 text-sm text-gray-600 mb-6">
          <Link href="/" className="hover:text-primary-600 transition-colors">Home</Link>
          <ChevronRight className="w-4 h-4 text-gray-300" />
          <Link href="/products" className="hover:text-primary-600 transition-colors">Products</Link>
          <ChevronRight className="w-4 h-4 text-gray-300" />
          <Link href={`/products?category=${product.category?.slug}`} className="hover:text-primary-600 transition-colors">
            {product.category?.name}
          </Link>
          <ChevronRight className="w-4 h-4 text-gray-300" />
          <span className="text-gray-900 font-medium truncate max-w-[16rem]">{product.name}</span>
        </nav>
      </FadeIn>

      {/* Message Toast */}
      <AnimatePresence>
        {message && (
          <motion.div
            key={`${message.type}-${message.text}`}
            initial={reduceMotion ? { opacity: 0 } : { opacity: 0, y: 24, scale: 0.95 }}
            animate={reduceMotion ? { opacity: 1 } : { opacity: 1, y: 0, scale: 1 }}
            exit={reduceMotion ? { opacity: 0 } : { opacity: 0, y: 12, scale: 0.97 }}
            transition={{ duration: 0.25, ease: EASE }}
            className={`fixed bottom-4 right-4 px-4 py-2.5 rounded-xl shadow-glow-md z-50 flex items-center gap-2 font-medium text-white ${
              message.type === 'success'
                ? 'bg-gradient-to-br from-green-500 to-green-700 shadow-green-600/40'
                : 'bg-gradient-to-br from-red-500 to-red-700 shadow-red-600/40'
            }`}
          >
            {message.type === 'success' ? (
              <CheckCircle2 className="w-5 h-5" />
            ) : (
              <XCircle className="w-5 h-5" />
            )}
            {message.text}
          </motion.div>
        )}
      </AnimatePresence>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-12">
        {/* Product Image Gallery */}
        <FadeIn y={20}>
          <div>
            <div className="group relative bg-gray-100 rounded-2xl overflow-hidden mb-4 ring-1 ring-gray-900/5">
              {product.images?.[selectedImage]?.url ? (
                <img
                  src={product.images[selectedImage].url}
                  alt={product.name}
                  className="w-full h-96 object-contain transition-transform duration-500 ease-out-expo group-hover:scale-110"
                />
              ) : (
                <div className="w-full h-96 flex items-center justify-center text-6xl transition-transform duration-500 group-hover:scale-110">📦</div>
              )}
            </div>
            {product.images && product.images.length > 1 && (
              <div className="flex gap-2 overflow-x-auto pb-1">
                {product.images.map((img: any, idx: number) => (
                  <motion.button
                    key={idx}
                    onClick={() => setSelectedImage(idx)}
                    whileHover={{ scale: 1.06 }}
                    whileTap={{ scale: 0.96 }}
                    transition={{ duration: 0.15 }}
                    className={`flex-shrink-0 w-20 h-20 rounded-lg overflow-hidden border-2 transition-all duration-200 ${
                      selectedImage === idx
                        ? 'border-primary-600 shadow-glow-sm'
                        : 'border-transparent hover:border-primary-300'
                    }`}
                  >
                    <img src={img.url} alt="" className="w-full h-full object-cover" />
                  </motion.button>
                ))}
              </div>
            )}
          </div>
        </FadeIn>

        {/* Product Info */}
        <div>
          <FadeIn y={16} delay={0.05}>
            <div className="text-xs font-medium uppercase tracking-wider text-primary-600 bg-primary-50 inline-block px-2.5 py-1 rounded-md mb-3">{product.brand?.name}</div>
          </FadeIn>
          <FadeIn y={16} delay={0.1}>
            <h1 className="text-3xl font-bold text-gray-900 mb-4">{product.name}</h1>
          </FadeIn>
          
          <FadeIn y={16} delay={0.15}>
            <div className="flex items-center gap-4 mb-4">
              <div className="flex items-center gap-1">
                {[1, 2, 3, 4, 5].map((star) => (
                  <Star key={star} className="w-5 h-5 text-yellow-400 fill-current" />
                ))}
                <span className="text-gray-600 ml-2">(0 reviews)</span>
              </div>
            </div>
          </FadeIn>

          <FadeIn y={16} delay={0.2}>
            <div className="mb-6 flex items-baseline gap-3">
              <span className="text-3xl font-bold gradient-text">
                ৳{product.price.toLocaleString()}
              </span>
              {product.compare_at_price && product.compare_at_price > product.price && (
                <span className="text-lg text-gray-400 line-through">
                  ৳{product.compare_at_price.toLocaleString()}
                </span>
              )}
            </div>
          </FadeIn>

          <FadeIn y={16} delay={0.25}>
            <div className="mb-6">
              {product.stock_quantity > 0 ? (
                <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
                  <Truck className="w-4 h-4 mr-1" />
                  In Stock ({product.stock_quantity} available)
                </span>
              ) : (
                <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-red-100 text-red-800">
                  Out of Stock
                </span>
              )}
            </div>
          </FadeIn>

          <FadeIn y={16} delay={0.3}>
            <p className="text-gray-700 mb-6 leading-relaxed">{product.description}</p>
          </FadeIn>

          {/* Quantity & Add to Cart */}
          <FadeIn y={16} delay={0.35}>
            <div className="flex items-center gap-4 mb-6">
              <div className="flex items-center border border-gray-300 rounded-lg overflow-hidden">
                <motion.button
                  onClick={() => setQuantity(Math.max(1, quantity - 1))}
                  whileTap={reduceMotion ? undefined : { scale: 0.9 }}
                  className="px-4 py-2.5 hover:bg-gray-100 transition-colors text-gray-600 font-medium"
                >
                  −
                </motion.button>
                <span className="px-4 py-2 font-semibold min-w-[3rem] text-center">{quantity}</span>
                <motion.button
                  onClick={() => setQuantity(Math.min(product.stock_quantity, quantity + 1))}
                  whileTap={reduceMotion ? undefined : { scale: 0.9 }}
                  className="px-4 py-2.5 hover:bg-gray-100 transition-colors text-gray-600 font-medium"
                >
                  +
                </motion.button>
              </div>
              
              <motion.button
                onClick={handleAddToCart}
                disabled={addingToCart || product.stock_quantity === 0}
                whileHover={reduceMotion || product.stock_quantity === 0 ? undefined : { scale: 1.02 }}
                whileTap={reduceMotion || addingToCart || product.stock_quantity === 0 ? undefined : { scale: 0.96 }}
                transition={{ duration: 0.15 }}
                className="flex-1 bg-gradient-to-br from-primary-500 to-primary-700 text-white py-3 px-6 rounded-lg font-semibold shadow-lg shadow-primary-600/30 hover:shadow-glow-md disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:shadow-lg flex items-center justify-center gap-2 transition-shadow duration-300"
              >
                <ShoppingCart className={`w-5 h-5 ${addingToCart ? 'animate-bounce' : ''}`} />
                {addingToCart ? 'Adding...' : 'Add to Cart'}
              </motion.button>
            </div>
          </FadeIn>

          {/* Action Buttons */}
          <FadeIn y={16} delay={0.4}>
            <div className="flex gap-3">
              <motion.button
                onClick={handleAddToCompare}
                whileTap={reduceMotion ? undefined : { scale: 0.95 }}
                className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 hover:border-primary-300 hover:text-primary-700 transition-all duration-200"
              >
                <GitCompare className="w-4 h-4" />
                Compare
              </motion.button>
              <motion.button
                whileTap={reduceMotion ? undefined : { scale: 0.95 }}
                className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 hover:border-red-300 hover:text-red-600 transition-all duration-200"
              >
                <Heart className="w-4 h-4" />
                Wishlist
              </motion.button>
              <motion.button
                whileTap={reduceMotion ? undefined : { scale: 0.95 }}
                className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 hover:border-primary-300 hover:text-primary-700 transition-all duration-200"
              >
                <Share2 className="w-4 h-4" />
                Share
              </motion.button>
            </div>
          </FadeIn>
        </div>
      </div>

      {/* Specifications */}
      {Object.keys(specs).length > 0 && (
        <FadeIn className="mb-8">
          <div className="card p-6">
            <h2 className="text-xl font-bold mb-4 flex items-center gap-2 text-gray-900">
              <span className="h-5 w-1 rounded-full bg-gradient-to-b from-primary-400 to-primary-700" />
              Specifications
            </h2>
            <Stagger className="grid grid-cols-1 md:grid-cols-2 gap-x-8" gap={0.05}>
              {Object.entries(specs).map(([key, value]) => (
                <StaggerItem key={key}>
                  <div className="flex justify-between py-2.5 border-b border-gray-100 text-sm">
                    <span className="text-gray-500 capitalize">{key.replace(/_/g, ' ')}</span>
                    <span className="font-medium text-gray-900">{String(value)}</span>
                  </div>
                </StaggerItem>
              ))}
            </Stagger>
          </div>
        </FadeIn>
      )}

      {/* Reviews Section */}
      <FadeIn className="mb-8">
        <div className="card p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-xl font-bold flex items-center gap-2 text-gray-900">
                <MessageSquare className="w-5 h-5 text-primary-600" />
                Reviews
              </h2>
              <div className="flex items-center gap-2 mt-1">
                <div className="flex">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <Star key={star} className={`w-4 h-4 ${star <= reviewsData.average_rating ? 'text-yellow-400 fill-current' : 'text-gray-300'}`} />
                  ))}
                </div>
                <span className="text-sm text-gray-600">
                  {reviewsData.average_rating}/5 ({reviewsData.total_reviews} reviews)
                </span>
              </div>
            </div>
            <button
              onClick={() => setShowReviewForm(!showReviewForm)}
              className="btn-primary text-sm"
            >
              Write Review
            </button>
          </div>

          {/* Review Form */}
          <AnimatePresence initial={false}>
            {showReviewForm && (
              <motion.form
                key="review-form"
                onSubmit={handleSubmitReview}
                initial={reduceMotion ? { opacity: 0 } : { opacity: 0, height: 0 }}
                animate={reduceMotion ? { opacity: 1 } : { opacity: 1, height: 'auto' }}
                exit={reduceMotion ? { opacity: 0 } : { opacity: 0, height: 0 }}
                transition={{ duration: 0.3, ease: EASE }}
                className="border border-gray-200 rounded-xl p-4 mb-6 bg-gray-50 overflow-hidden"
              >
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Your Name *</label>
                    <input
                      type="text"
                      required
                      value={reviewForm.reviewer_name}
                      onChange={(e) => setReviewForm({ ...reviewForm, reviewer_name: e.target.value })}
                      className="input"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Email (optional)</label>
                    <input
                      type="email"
                      value={reviewForm.reviewer_email}
                      onChange={(e) => setReviewForm({ ...reviewForm, reviewer_email: e.target.value })}
                      className="input"
                    />
                  </div>
                </div>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Rating *</label>
                  <div className="flex gap-1">
                    {[1, 2, 3, 4, 5].map((star) => (
                      <motion.button
                        key={star}
                        type="button"
                        onClick={() => setReviewForm({ ...reviewForm, rating: star })}
                        whileTap={reduceMotion ? undefined : { scale: 0.8 }}
                        whileHover={reduceMotion ? undefined : { scale: 1.15 }}
                        className={`w-8 h-8 ${star <= reviewForm.rating ? 'text-yellow-400' : 'text-gray-300'}`}
                      >
                        <Star className="w-full h-full fill-current" />
                      </motion.button>
                    ))}
                  </div>
                </div>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Title</label>
                  <input
                    type="text"
                    value={reviewForm.title}
                    onChange={(e) => setReviewForm({ ...reviewForm, title: e.target.value })}
                    className="input"
                    placeholder="Summary of your review"
                  />
                </div>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Comment *</label>
                  <textarea
                    required
                    rows={3}
                    value={reviewForm.comment}
                    onChange={(e) => setReviewForm({ ...reviewForm, comment: e.target.value })}
                    className="input"
                    placeholder="Share your experience with this product"
                  />
                </div>
                <div className="flex gap-3">
                  <button type="submit" className="btn-primary">
                    Submit Review
                  </button>
                  <button type="button" onClick={() => setShowReviewForm(false)} className="btn-secondary">
                    Cancel
                  </button>
                </div>
              </motion.form>
            )}
          </AnimatePresence>

          {/* Reviews List */}
          {reviewsData.reviews.length === 0 ? (
            <p className="text-gray-500 text-center py-4">No reviews yet. Be the first to review!</p>
          ) : (
            <Stagger className="space-y-4" gap={0.08}>
              {reviewsData.reviews.map((review: any) => (
                <StaggerItem key={review.id}>
                  <div className="border-b border-gray-100 pb-4 last:border-0">
                    <div className="flex items-center gap-2 mb-2">
                      <div className="flex">
                        {[1, 2, 3, 4, 5].map((star) => (
                          <Star key={star} className={`w-4 h-4 ${star <= review.rating ? 'text-yellow-400 fill-current' : 'text-gray-300'}`} />
                        ))}
                      </div>
                      <span className="font-medium text-sm">{review.reviewer_name}</span>
                      {review.is_verified && (
                        <span className="text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded-full">Verified</span>
                      )}
                      <span className="text-xs text-gray-500">{new Date(review.created_at).toLocaleDateString()}</span>
                    </div>
                    {review.title && <h4 className="font-medium mb-1">{review.title}</h4>}
                    <p className="text-gray-700 text-sm">{review.comment}</p>
                  </div>
                </StaggerItem>
              ))}
            </Stagger>
          )}
        </div>
      </FadeIn>

      {/* Similar Products */}
      <FadeIn>
        <div className="mt-12">
          <h2 className="text-xl font-bold mb-4 text-gray-900">Similar Products</h2>
          <p className="text-gray-600">Coming soon...</p>
        </div>
      </FadeIn>
    </div>
  )
}
