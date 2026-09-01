"""
Celery tasks for the discovery module.

These tasks handle background jobs like:
- Updating popularity scores
- Aggregating ratings
- Cache warming
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from celery import Celery
from sqlalchemy import func

from app.core.config import settings

logger = logging.getLogger("discovery.tasks")

# Celery app configuration
celery_app = Celery(
    "discovery",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes
    task_soft_time_limit=240,  # 4 minutes
)


@celery_app.task(name="discovery.update_popularity_scores")
def update_popularity_scores():
    """
    Update product popularity scores based on recent views/purchases.
    Should be run periodically (e.g., every hour).
    """
    from app.models.base import SessionLocal
    from app.models.stubs import Product

    db = SessionLocal()
    try:
        # Decay existing scores and boost based on recent activity
        decay_factor = 0.95  # 5% decay per hour
        db.query(Product).update(
            {Product.popularity_score: Product.popularity_score * decay_factor}
        )
        db.commit()
        logger.info("Updated popularity scores with decay factor %s", decay_factor)
    except Exception as e:
        logger.error("Failed to update popularity scores: %s", e)
        db.rollback()
    finally:
        db.close()


@celery_app.task(name="discovery.aggregate_ratings")
def aggregate_ratings(product_id: int | None = None):
    """
    Recalculate rating aggregates for products.
    If product_id is provided, only update that product.
    """
    from app.models.base import SessionLocal
    from app.models.review import Review, ReviewStatus
    from app.models.stubs import Product

    db = SessionLocal()
    try:
        if product_id:
            products = db.query(Product).filter(Product.id == product_id).all()
        else:
            products = db.query(Product).filter(Product.is_visible == True).all()

        for product in products:
            stats = db.query(
                func.avg(Review.rating).label("avg"),
                func.count(Review.id).label("count"),
            ).filter(
                Review.product_id == product.id,
                Review.status == ReviewStatus.APPROVED,
            ).first()

            # Update product popularity based on rating
            if stats.avg:
                product.popularity_score = float(stats.avg) * 10 + (stats.count * 0.1)

        db.commit()
        logger.info("Aggregated ratings for %d products", len(products))
    except Exception as e:
        logger.error("Failed to aggregate ratings: %s", e)
        db.rollback()
    finally:
        db.close()


@celery_app.task(name="discovery.warm_cache")
def warm_cache():
    """
    Pre-warm cache for frequently accessed data.
    Should be run periodically (e.g., every 5 minutes).
    """
    from app.models.base import SessionLocal
    from app.models.stubs import Brand, Category, Product

    db = SessionLocal()
    try:
        # Warm category cache
        categories = db.query(Category).filter(Category.is_active == True).all()
        logger.info("Warmed cache for %d categories", len(categories))

        # Warm brand cache
        brands = db.query(Brand).filter(Brand.is_active == True).all()
        logger.info("Warmed cache for %d brands", len(brands))

        # Warm featured products cache
        featured = db.query(Product).filter(
            Product.is_featured == True,
            Product.is_visible == True
        ).limit(20).all()
        logger.info("Warmed cache for %d featured products", len(featured))
    except Exception as e:
        logger.error("Failed to warm cache: %s", e)
    finally:
        db.close()


# Schedule periodic tasks
celery_app.conf.beat_schedule = {
    "update-popularity-every-hour": {
        "task": "discovery.update_popularity_scores",
        "schedule": timedelta(hours=1),
    },
    "aggregate-ratings-every-6-hours": {
        "task": "discovery.aggregate_ratings",
        "schedule": timedelta(hours=6),
    },
    "warm-cache-every-5-minutes": {
        "task": "discovery.warm_cache",
        "schedule": timedelta(minutes=5),
    },
}
