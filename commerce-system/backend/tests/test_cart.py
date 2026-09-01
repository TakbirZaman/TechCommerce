def test_get_empty_cart(client):
    resp = client.get("/api/v1/cart")
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["subtotal"] == "0"
    assert body["total_items"] == 0


def test_add_item_to_cart(client, seed_product):
    resp = client.post("/api/v1/cart/items", json={"product_id": seed_product.id, "quantity": 3})
    assert resp.status_code == 201
    body = resp.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["quantity"] == 3
    assert body["items"][0]["unit_price"] == "100.00"
    assert body["items"][0]["subtotal"] == "300.00"


def test_add_item_ignores_client_supplied_price(client, seed_product):
    """Client cannot pass a price at all — schema has no price field — server always uses DB price."""
    resp = client.post(
        "/api/v1/cart/items",
        json={"product_id": seed_product.id, "quantity": 1, "unit_price": "1.00"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["items"][0]["unit_price"] == "100.00"  # server price, not the injected 1.00


def test_increase_then_decrease_quantity(client, seed_product):
    client.post("/api/v1/cart/items", json={"product_id": seed_product.id, "quantity": 3})
    resp = client.get("/api/v1/cart")
    item_id = resp.json()["items"][0]["id"]

    resp = client.patch(f"/api/v1/cart/items/{item_id}", json={"quantity": 5})
    assert resp.status_code == 200
    assert resp.json()["items"][0]["quantity"] == 5

    resp = client.patch(f"/api/v1/cart/items/{item_id}", json={"quantity": 4})
    assert resp.status_code == 200
    assert resp.json()["items"][0]["quantity"] == 4


def test_cannot_exceed_available_stock(client, seed_product):
    # seed_product has total_stock=10
    resp = client.post("/api/v1/cart/items", json={"product_id": seed_product.id, "quantity": 11})
    assert resp.status_code == 409


def test_adding_same_product_twice_accumulates_quantity(client, seed_product):
    client.post("/api/v1/cart/items", json={"product_id": seed_product.id, "quantity": 3})
    resp = client.post("/api/v1/cart/items", json={"product_id": seed_product.id, "quantity": 4})
    assert resp.status_code == 201
    body = resp.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["quantity"] == 7


def test_remove_item(client, seed_product):
    client.post("/api/v1/cart/items", json={"product_id": seed_product.id, "quantity": 2})
    resp = client.get("/api/v1/cart")
    item_id = resp.json()["items"][0]["id"]

    resp = client.delete(f"/api/v1/cart/items/{item_id}")
    assert resp.status_code == 200
    assert resp.json()["items"] == []


def test_clear_cart(client, seed_product):
    client.post("/api/v1/cart/items", json={"product_id": seed_product.id, "quantity": 2})
    resp = client.delete("/api/v1/cart")
    assert resp.status_code == 200
    assert resp.json()["items"] == []


def test_add_nonexistent_product_404(client):
    resp = client.post("/api/v1/cart/items", json={"product_id": 999, "quantity": 1})
    assert resp.status_code == 404


def test_add_inactive_product_rejected(client, db_session, seed_product):
    seed_product.is_active = False
    db_session.commit()

    resp = client.post("/api/v1/cart/items", json={"product_id": seed_product.id, "quantity": 1})
    assert resp.status_code == 422


def test_invalid_quantity_rejected(client, seed_product):
    resp = client.post("/api/v1/cart/items", json={"product_id": seed_product.id, "quantity": 0})
    assert resp.status_code == 422
