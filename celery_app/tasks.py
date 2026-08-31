"""
Celery tasks (spec section 24).

Each task wraps a real function from ml/ — none of these run automatically
against fabricated data. They expect a `data_access` layer (not implemented
here — see api/dependencies.py) that queries the platform's real Postgres
tables for products/events/requirements. Until that layer is wired to a
live database, these tasks are runnable-but-inert: calling them with real
repositories makes them do real work; there is no synthetic data path.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from celery_app.celery_app import celery_app
from ml.models.registry import ModelMetadata, register_model
from ml.training.train_ranker import InsufficientDataError, build_training_dataframe, train_ranker

logger = logging.getLogger(__name__)


@celery_app.task(name="celery_app.tasks.train_ranking_model")
def train_ranking_model(model_name: str, examples: list[dict], products_by_id: dict) -> dict:
    """
    Train the Stage 4 ranking model from real (pre-fetched) examples.
    Returns a status dict rather than raising into Celery's retry logic for
    the expected "not enough data yet" case — that's a normal, common
    outcome (spec section 29), not a failure worth retrying.
    """
    from ml.data.schemas import Product
    from ml.training.train_ranker import TrainingExample

    parsed_examples = [TrainingExample(**e) for e in examples]
    parsed_products = {pid: Product(**p) for pid, p in products_by_id.items()}
    df = build_training_dataframe(parsed_examples, parsed_products)

    try:
        model = train_ranker(df)
    except InsufficientDataError as exc:
        logger.info("Skipping training for %s: %s", model_name, exc)
        return {"status": "skipped", "reason": str(exc)}

    version = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    artifact_path = f"ml/models/artifacts/{model_name}_{version}.json"
    model.save_model(artifact_path)

    register_model(
        ModelMetadata(
            model_name=model_name,
            version=version,
            training_date=datetime.now(timezone.utc).isoformat(),
            features=list(df.columns.drop(["label", "timestamp"])),
            metrics={},  # populated by evaluate_active_models against held-out data
            dataset_version=version,
            artifact_path=artifact_path,
        )
    )
    return {"status": "trained", "version": version, "artifact_path": artifact_path}


@celery_app.task(name="celery_app.tasks.generate_features")
def generate_features(category: str) -> dict:
    """
    Batch-recompute normalized feature vectors for a category's catalog and
    cache them (e.g. in Redis) so the API doesn't recompute per request.
    Requires wiring to the real product repository — see api/dependencies.py.
    """
    logger.info("generate_features called for category=%s (requires product repository wiring)", category)
    return {"status": "not_wired", "category": category}


@celery_app.task(name="celery_app.tasks.refresh_user_profile")
def refresh_user_profile(user_id: str) -> dict:
    """Recompute and cache one user's derived profile (ml/features/user_profile.py)."""
    logger.info("refresh_user_profile called for user_id=%s (requires event/product repository wiring)", user_id)
    return {"status": "not_wired", "user_id": user_id}


@celery_app.task(name="celery_app.tasks.refresh_all_user_profiles")
def refresh_all_user_profiles() -> dict:
    """Periodic (nightly) fan-out that enqueues refresh_user_profile per active user."""
    logger.info("refresh_all_user_profiles: requires user repository wiring to enumerate active users")
    return {"status": "not_wired"}


@celery_app.task(name="celery_app.tasks.aggregate_analytics")
def aggregate_analytics() -> dict:
    """Periodic (hourly) rollup of click-through / add-to-cart / conversion metrics (spec section 26)."""
    logger.info("aggregate_analytics: requires analytics repository wiring")
    return {"status": "not_wired"}


@celery_app.task(name="celery_app.tasks.evaluate_active_models")
def evaluate_active_models() -> dict:
    """Periodic (daily) re-evaluation of each active model against fresh held-out interaction data."""
    logger.info("evaluate_active_models: requires event repository wiring to build held-out evaluation set")
    return {"status": "not_wired"}
