const Product = require('../models/Product');
const AnalyticsEvent = require('../models/AnalyticsEvent');

class RecommendationEngine {
  static async getPersonalizedRecommendations(userId, limit = 5) {
    const recentEvents = await AnalyticsEvent.find({
      user: userId,
      eventType: { $in: ['product_view', 'add_to_cart', 'purchase'] }
    }).sort({ timestamp: -1 }).limit(50);

    const productIds = recentEvents
      .filter(e => e.data?.productId)
      .map(e => e.data.productId);

    const viewedProducts = await Product.find({ _id: { $in: productIds } });
    const categories = [...new Set(viewedProducts.map(p => p.category))];

    if (categories.length === 0) {
      return Product.find({ isActive: true }).sort({ createdAt: -1 }).limit(limit);
    }

    const recommended = await Product.find({
      category: { $in: categories },
      _id: { $nin: productIds },
      isActive: true
    }).limit(limit);

    if (recommended.length < limit) {
      const additional = await Product.find({
        _id: { $nin: [...productIds, ...recommended.map(r => r._id)] },
        isActive: true
      }).limit(limit - recommended.length);
      return [...recommended, ...additional];
    }

    return recommended;
  }

  static async getFrequentlyBoughtTogether(productId, limit = 4) {
    const orders = await Order.find({
      'items.product': productId
    });

    const coOccurring = {};
    orders.forEach(order => {
      order.items.forEach(item => {
        if (item.product.toString() !== productId) {
          coOccurring[item.product] = (coOccurring[item.product] || 0) + 1;
        }
      });
    });

    const sorted = Object.entries(coOccurring)
      .sort(([, a], [, b]) => b - a)
      .slice(0, limit)
      .map(([id]) => id);

    return Product.find({ _id: { $in: sorted }, isActive: true });
  }
}

module.exports = RecommendationEngine;
