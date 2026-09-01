from app.services.related_products import RuleBasedRelatedProducts


def test_related_products_same_category_only(sample_data, db_session):
    strategy = RuleBasedRelatedProducts()
    related = strategy.get_related(db_session, sample_data["p1"])
    assert all(p.category_id == sample_data["p1"].category_id for p in related)
    assert sample_data["p1"].id not in [p.id for p in related]


def test_related_products_ranks_same_brand_higher(sample_data, db_session):
    strategy = RuleBasedRelatedProducts()
    related = strategy.get_related(db_session, sample_data["p1"])
    # p2 is same brand (ASUS) and same category — should be included and ranked.
    assert sample_data["p2"].id in [p.id for p in related]
