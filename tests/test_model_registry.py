from ml.models.registry import ModelMetadata, get_active_model, register_model


def test_register_and_get_active_model(tmp_path):
    registry_path = tmp_path / "registry.json"
    metadata = ModelMetadata(
        model_name="laptop_ranker",
        version="v1",
        training_date="2026-06-01T00:00:00",
        features=["price_match", "content_similarity"],
        metrics={"ndcg_at_10": 0.71},
        dataset_version="2026-06-01",
        artifact_path="ml/models/artifacts/laptop_ranker_v1.json",
    )
    register_model(metadata, registry_path=registry_path)

    active = get_active_model("laptop_ranker", registry_path=registry_path)
    assert active is not None
    assert active.version == "v1"
    assert active.metrics["ndcg_at_10"] == 0.71


def test_get_active_model_returns_none_when_absent(tmp_path):
    registry_path = tmp_path / "empty_registry.json"
    assert get_active_model("nonexistent_model", registry_path=registry_path) is None


def test_get_active_model_ignores_inactive_entries(tmp_path):
    registry_path = tmp_path / "registry.json"
    old = ModelMetadata(
        model_name="m", version="v1", training_date="2026-01-01T00:00:00",
        features=[], metrics={}, dataset_version="d1",
        artifact_path="a1", active=False,
    )
    register_model(old, registry_path=registry_path)
    assert get_active_model("m", registry_path=registry_path) is None
