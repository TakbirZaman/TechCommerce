from app.services.filter_engine import build_common_filters, build_spec_filters


def test_common_filters_include_price_brand_status(sample_data, db_session):
    from app.models.stubs import Product
    base_query = db_session.query(Product).filter(Product.category_id == sample_data["laptops"].id)
    filters = build_common_filters(db_session, base_query)
    keys = {f.key for f in filters}
    assert {"price", "brand_id", "status"}.issubset(keys)


def test_spec_filters_derived_from_category_schema(sample_data, db_session):
    from app.models.stubs import Product
    base_query = db_session.query(Product).filter(Product.category_id == sample_data["laptops"].id)
    filters = build_spec_filters(db_session, sample_data["laptops"], base_query)
    keys = {f.key for f in filters}
    assert "cpu" in keys
    assert "ram_gb" in keys

    ram_filter = next(f for f in filters if f.key == "ram_gb")
    assert ram_filter.type == "enum"
    assert any(o.value == 16 for o in ram_filter.options)


def test_no_filters_for_category_without_schema(sample_data, db_session):
    from app.models.stubs import Product
    base_query = db_session.query(Product).filter(Product.category_id == sample_data["phones"].id)
    filters = build_spec_filters(db_session, sample_data["phones"], base_query)
    assert filters == []
