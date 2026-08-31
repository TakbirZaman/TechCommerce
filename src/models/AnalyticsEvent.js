const mongoose = require('mongoose');

const analyticsEventSchema = new mongoose.Schema({
  user: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'User'
  },
  eventType: {
    type: String,
    required: true,
    enum: ['page_view', 'product_view', 'add_to_cart', 'purchase', 'search']
  },
  data: {
    type: mongoose.Schema.Types.Mixed
  },
  timestamp: {
    type: Date,
    default: Date.now
  }
});

analyticsEventSchema.index({ eventType: 1, timestamp: -1 });
analyticsEventSchema.index({ user: 1, timestamp: -1 });

module.exports = mongoose.model('AnalyticsEvent', analyticsEventSchema);
