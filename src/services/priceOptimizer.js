class PriceOptimizer {
  static calculateDynamicPrice(product, demand, inventory, competitorPrices) {
    let basePrice = product.price;
    let adjustment = 0;

    if (demand > 100) adjustment += basePrice * 0.1;
    else if (demand > 50) adjustment += basePrice * 0.05;

    if (inventory < 10) adjustment += basePrice * 0.15;
    else if (inventory < 50) adjustment += basePrice * 0.05;

    if (competitorPrices && competitorPrices.length > 0) {
      const avgCompetitor = competitorPrices.reduce((a, b) => a + b, 0) / competitorPrices.length;
      if (basePrice > avgCompetitor * 1.2) {
        adjustment -= basePrice * 0.1;
      }
    }

    return Math.max(basePrice * 0.8, basePrice + adjustment);
  }

  static getDiscountStrategy(userActivity, orderHistory) {
    if (orderHistory.length === 0) return { type: 'welcome', discount: 10 };

    const totalSpent = orderHistory.reduce((sum, order) => sum + order.totalAmount, 0);
    const lastOrder = orderHistory[0];

    const daysSinceLastOrder = Math.floor(
      (Date.now() - new Date(lastOrder.createdAt)) / (1000 * 60 * 60 * 24)
    );

    if (daysSinceLastOrder > 90) return { type: 'winback', discount: 20 };
    if (totalSpent > 1000) return { type: 'vip', discount: 15 };
    if (userActivity.productViews > 50 && userActivity.purchases < 5) {
      return { type: 'cart_abandonment', discount: 10 };
    }

    return { type: 'none', discount: 0 };
  }
}

module.exports = PriceOptimizer;
