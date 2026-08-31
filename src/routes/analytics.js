const express = require('express');
const router = express.Router();
const auth = require('../middleware/auth');
const AnalyticsEvent = require('../models/AnalyticsEvent');
const Order = require('../models/Order');

router.post('/track', auth, async (req, res) => {
  try {
    const event = new AnalyticsEvent({
      user: req.user.userId,
      eventType: req.body.eventType,
      data: req.body.data
    });
    await event.save();
    res.status(201).json({ message: 'Event tracked' });
  } catch (error) {
    res.status(500).json({ message: 'Server error' });
  }
});

router.get('/dashboard', auth, async (req, res) => {
  try {
    const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);

    const salesData = await Order.aggregate([
      { $match: { createdAt: { $gte: thirtyDaysAgo } } },
      { $group: {
        _id: { $dateToString: { format: '%Y-%m-%d', date: '$createdAt' } },
        totalSales: { $sum: '$totalAmount' },
        orderCount: { $sum: 1 }
      }},
      { $sort: { _id: 1 } }
    ]);

    const topProducts = await Order.aggregate([
      { $unwind: '$items' },
      { $group: {
        _id: '$items.product',
        totalSold: { $sum: '$items.quantity' },
        revenue: { $sum: { $multiply: ['$items.price', '$items.quantity'] } }
      }},
      { $sort: { revenue: -1 } },
      { $limit: 5 }
    ]);

    const totalRevenue = salesData.reduce((sum, day) => sum + day.totalSales, 0);
    const totalOrders = salesData.reduce((sum, day) => sum + day.orderCount, 0);

    res.json({
      summary: { totalRevenue, totalOrders, averageOrderValue: totalOrders ? totalRevenue / totalOrders : 0 },
      salesByDay: salesData,
      topProducts
    });
  } catch (error) {
    res.status(500).json({ message: 'Server error' });
  }
});

router.get('/user-insights', auth, async (req, res) => {
  try {
    const events = await AnalyticsEvent.find({ user: req.user.userId })
      .sort({ timestamp: -1 })
      .limit(100);

    const productViews = events.filter(e => e.eventType === 'product_view').length;
    const searches = events.filter(e => e.eventType === 'search').length;
    const addToCarts = events.filter(e => e.eventType === 'add_to_cart').length;
    const purchases = events.filter(e => e.eventType === 'purchase').length;

    const viewedProducts = events
      .filter(e => e.eventType === 'product_view' && e.data?.productId)
      .map(e => e.data.productId);
    const uniqueViewed = [...new Set(viewedProducts)];

    const recentSearches = events
      .filter(e => e.eventType === 'search' && e.data?.query)
      .map(e => e.data.query)
      .filter((v, i, a) => a.indexOf(v) === i)
      .slice(0, 5);

    res.json({
      activity: { productViews, searches, addToCarts, purchases },
      uniqueProductsViewed: uniqueViewed.length,
      recentSearches,
      conversionRate: productViews ? (purchases / productViews * 100).toFixed(2) : 0
    });
  } catch (error) {
    res.status(500).json({ message: 'Server error' });
  }
});

module.exports = router;
