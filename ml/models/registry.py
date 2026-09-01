"""
Model metadata & versioning (spec section 25).

A minimal in-process registry over a JSON metadata file per trained model
artifact. This is intentionally simple — swap `_load_all`/`_save` for a
real DB table without changing the public functions once the platform's
Postgres schema is extended for this. No trained artifact ships with this
codebase (see ml/training/train_ranker.py) — this registry has real
behavior (round-trips metadata, is queried by inference/hybrid.py to decide
whether a model is usable) but starts empty until a real model is trained
on real data.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

_DEFAULT_REGISTRY_PATH = Path(__file__).parent / "model_registry.json"


@dataclass
class ModelMetadata:
    model_name: str
    version: str
    training_date: str  # ISO 8601
    features: list[str]
    metrics: dict[str, float]
    dataset_version: str
    artifact_path: str
    active: bool = field(default=True)


def _load_all(registry_path: Path = _DEFAULT_REGISTRY_PATH) -> list[dict]:
    if not registry_path.exists():
        return []
    return json.loads(registry_path.read_text())


def _save(entries: list[dict], registry_path: Path = _DEFAULT_REGISTRY_PATH) -> None:
    registry_path.write_text(json.dumps(entries, indent=2))


def register_model(metadata: ModelMetadata, registry_path: Path = _DEFAULT_REGISTRY_PATH) -> None:
    entries = _load_all(registry_path)
    entries.append(asdict(metadata))
    _save(entries, registry_path)


def get_active_model(model_name: str, registry_path: Path = _DEFAULT_REGISTRY_PATH) -> ModelMetadata | None:
    """Return the most recently registered active model with this name, or None."""
    entries = [
        e for e in _load_all(registry_path) if e["model_name"] == model_name and e.get("active", True)
    ]
    if not entries:
        return None
    latest = max(entries, key=lambda e: e["training_date"])
    return ModelMetadata(**latest)
