const express = require('express');
const router = express.Router();
const Product = require('../models/Product');
const Order = require('../models/Order');

router.get('/related/:productId', async (req, res) => {
  try {
    const product = await Product.findById(req.params.productId);
    if (!product) {
      return res.status(404).json({ message: 'Product not found' });
    }

    const related = await Product.find({
      category: product.category,
      _id: { $ne: product._id },
      isActive: true
    }).limit(4);

    res.json(related);
  } catch (error) {
    res.status(500).json({ message: 'Server error' });
  }
});

router.get('/trending', async (req, res) => {
  try {
    const trending = await Order.aggregate([
      { $unwind: '$items' },
      { $group: { _id: '$items.product', count: { $sum: '$items.quantity' } } },
      { $sort: { count: -1 } },
      { $limit: 10 }
    ]);

    const productIds = trending.map(t => t._id);
    const products = await Product.find({ _id: { $in: productIds }, isActive: true });

    res.json(products);
  } catch (error) {
    res.status(500).json({ message: 'Server error' });
  }
});

router.get('/recent', async (req, res) => {
  try {
    const recent = await Product.find({ isActive: true })
      .sort({ createdAt: -1 })
      .limit(8);
    res.json(recent);
  } catch (error) {
    res.status(500).json({ message: 'Server error' });
  }
});

module.exports = router;
