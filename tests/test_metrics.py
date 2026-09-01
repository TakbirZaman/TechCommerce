import math

from ml.evaluation.metrics import (
    hit_rate_at_k,
    mean_reciprocal_rank,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)


def test_precision_at_k_basic():
    ranked = ["a", "b", "c", "d"]
    relevant = {"b", "d"}
    assert precision_at_k(ranked, relevant, k=2) == 0.5  # b in top 2
    assert precision_at_k(ranked, relevant, k=4) == 0.5  # b,d in top 4 of 4


def test_recall_at_k_basic():
    ranked = ["a", "b", "c", "d"]
    relevant = {"b", "d", "z"}  # z never appears
    assert recall_at_k(ranked, relevant, k=4) == 2 / 3


def test_mrr_first_hit_position():
    assert mean_reciprocal_rank(["a", "b", "c"], {"b"}) == 0.5
    assert mean_reciprocal_rank(["a", "b", "c"], {"a"}) == 1.0
    assert mean_reciprocal_rank(["a", "b", "c"], {"z"}) == 0.0


def test_ndcg_perfect_ranking_is_one():
    ranked = ["a", "b", "c"]
    relevant = {"a", "b"}
    assert ndcg_at_k(ranked, relevant, k=3) == 1.0


def test_ndcg_worse_ranking_scores_lower_than_perfect():
    perfect = ndcg_at_k(["a", "b", "c"], {"a", "b"}, k=3)
    worse = ndcg_at_k(["c", "a", "b"], {"a", "b"}, k=3)
    assert worse < perfect


def test_hit_rate_at_k():
    assert hit_rate_at_k(["a", "b", "c"], {"c"}, k=3) == 1.0
    assert hit_rate_at_k(["a", "b", "c"], {"z"}, k=3) == 0.0


def test_metrics_handle_empty_relevant_set_without_crashing():
    assert precision_at_k(["a", "b"], set(), k=2) == 0.0
    assert recall_at_k(["a", "b"], set(), k=2) == 0.0
    assert ndcg_at_k(["a", "b"], set(), k=2) == 0.0
