import pytest
from sqlalchemy.pool import StaticPool

from app_smoothies_pos import (
    app,
    check_stock_quantities_vs_demand,
    validate_cart,
    verify_inventory,
)
from extensions import db
from models import (
    Ingredient,
    Smoothie,
    SmoothieAddonItem,
    SmoothieRecipeItem,
    SmoothieSubItem,
    Supplier,
    User,
)


# =========================================================================
# 0. PYTEST FIXTURES (ISOLATED IN-MEMORY DATABASE & SAMPLE POS DATA)
# =========================================================================

# Switch Flask-SQLAlchemy once to an isolated in-memory database BEFORE any test request runs

app.config["TESTING"] = True
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "connect_args": {"check_same_thread": False},
    "poolclass": StaticPool,
}
app.config["WTF_CSRF_ENABLED"] = False

with app.app_context():
    db.session.remove()
    if app in getattr(db, "_app_engines", {}):
        db.engine.dispose()
        del db._app_engines[app]
    app.extensions.pop("sqlalchemy", None)
    db.init_app(app)
    assert str(db.engine.url) == "sqlite:///:memory:"


@pytest.fixture
def client():
    """Creates fresh in-memory tables per test without re-registering Flask extensions."""
    with app.app_context():
        db.create_all()
        with app.test_client() as test_client:
            yield test_client
        db.session.remove()
        db.drop_all()


@pytest.fixture
def sample_smoothie_setup(client):
    """Seeds sample ingredients and a custom smoothie recipe in the in-memory database."""
    with app.app_context():
        # Healthy stock (> reorder_stock)
        mango = Ingredient(
            id="mango_puree",
            name="Mango Puree",
            cost=1.50,
            current_stock=50,
            reorder_stock=20,
            minimum_stock=10,
        )
        # Warning zone (<= reorder_stock, > minimum_stock -> order_soon_list)
        spinach = Ingredient(
            id="baby_spinach",
            name="Baby Spinach",
            cost=0.75,
            current_stock=15,
            reorder_stock=20,
            minimum_stock=10,
        )
        # Insufficient zone (> minimum_stock, but demand drops stock < minimum_stock)
        almond_milk = Ingredient(
            id="almond_milk",
            name="Almond Milk",
            cost=0.50,
            current_stock=12,
            reorder_stock=20,
            minimum_stock=10,
        )
        # Out-of-stock zone (<= minimum_stock -> out_of_stock_list)
        blueberry = Ingredient(
            id="wild_blueberries",
            name="Wild Blueberries",
            cost=1.25,
            current_stock=10,
            reorder_stock=20,
            minimum_stock=10,
        )
        # Tracked exclusion item (ignored by INVENTORY_EXCLUSIONS)
        crushed_ice = Ingredient(
            id="crushed_ice",
            name="Crushed Ice",
            cost=0.00,
            current_stock=0,
            reorder_stock=20,
            minimum_stock=10,
        )

        db.session.add_all([mango, spinach, almond_milk, blueberry, crushed_ice])
        db.session.commit()

        smoothie = Smoothie(name="Tropical Oasis", slogan="Island fresh", profit_margin=3.00)
        db.session.add(smoothie)
        db.session.commit()

        rec_mango = SmoothieRecipeItem(smoothie_id=smoothie.id, ingredient_id="mango_puree", ingredient_quantity=2)
        rec_spinach = SmoothieRecipeItem(smoothie_id=smoothie.id, ingredient_id="baby_spinach", ingredient_quantity=1)
        rec_blueberry = SmoothieRecipeItem(smoothie_id=smoothie.id, ingredient_id="wild_blueberries", ingredient_quantity=1)
        sub_milk = SmoothieSubItem(
            smoothie_id=smoothie.id,
            group_name="starter",
            ingredient_id="almond_milk",
            is_default=True,
        )
        addon_ice = SmoothieAddonItem(
            smoothie_id=smoothie.id,
            ingredient_id="crushed_ice",
            ingredient_quantity=1,
        )

        db.session.add_all([rec_mango, rec_spinach, rec_blueberry, sub_milk, addon_ice])
        db.session.commit()
        smoothie.calculate_and_save_price()

        return {
            "smoothie_id": smoothie.id,
            "rec_mango_id": rec_mango.id,
            "rec_spinach_id": rec_spinach.id,
            "rec_blueberry_id": rec_blueberry.id,
            "sub_milk_id": sub_milk.id,
            "addon_ice_id": addon_ice.id,
        }


# =========================================================================
# 1. INVENTORY DEFICIENCY LOGIC TESTS
# =========================================================================

def test_out_of_stock_list(sample_smoothie_setup):
    """Ingredients at or below minimum_stock must populate out_of_stock_list and trigger has_hard_stop."""
    with app.app_context():
        report = check_stock_quantities_vs_demand({"wild_blueberries": 1})

        assert "wild_blueberries" in report["out_of_stock_list"]
        assert report["has_hard_stop"] is True


def test_insufficient_stock_list(sample_smoothie_setup):
    """Ingredients above minimum_stock whose order demand drops stock below minimum_stock trigger insufficient_stock_list."""
    with app.app_context():
        # almond_milk has current_stock=12, minimum_stock=10; demanding 3 leaves 9 (< 10)
        report = check_stock_quantities_vs_demand({"almond_milk": 3})

        assert "almond_milk" in report["insufficient_stock_list"]
        assert "almond_milk" not in report["out_of_stock_list"]
        assert report["has_hard_stop"] is True


def test_order_soon_list(sample_smoothie_setup):
    """Ingredients safely above minimum_stock after demand but <= reorder_stock populate order_soon_list without hard stop."""
    with app.app_context():
        # baby_spinach has current_stock=15, reorder_stock=20, minimum_stock=10; demanding 1 leaves 14 (>= 10)
        report = check_stock_quantities_vs_demand({"baby_spinach": 1})

        assert "baby_spinach" in report["order_soon_list"]
        assert report["out_of_stock_list"] == []
        assert report["insufficient_stock_list"] == []
        assert report["has_hard_stop"] is False


def test_disabled_ingredients_and_exclusions(sample_smoothie_setup):
    """Excluded recipe items (0 needed) go into disabled_ings_list, and INVENTORY_EXCLUSIONS are ignored."""
    with app.app_context():
        report = check_stock_quantities_vs_demand({"mango_puree": 0, "crushed_ice": 1})

        assert "mango_puree" in report["disabled_ings_list"]
        assert "crushed_ice" not in report["out_of_stock_list"]
        assert "crushed_ice" not in report["disabled_ings_list"]
        assert report["has_hard_stop"] is False


def test_verify_inventory_end_to_end_cart(sample_smoothie_setup):
    """verify_inventory aggregates cart items and flags out-of-stock/order-soon ingredients accurately."""
    data = sample_smoothie_setup
    with app.app_context():
        cart = [
            {
                "smoothie_id": data["smoothie_id"],
                "recipe_inclusions": [data["rec_mango_id"], data["rec_spinach_id"], data["rec_blueberry_id"]],
                "recipe_exclusions": [],
                "sub_inclusions": [data["sub_milk_id"]],
                "sub_exclusions": [],
                "addon_inclusions": [data["addon_ice_id"]],
                "error_flag": False,
            }
        ]
        report = verify_inventory(cart)

        assert "wild_blueberries" in report["out_of_stock_list"]
        assert "baby_spinach" in report["order_soon_list"]
        assert "mango_puree" not in report["out_of_stock_list"]
        assert "crushed_ice" not in report["out_of_stock_list"]
        assert report["has_hard_stop"] is True


# =========================================================================
# 2. MODEL & SECURITY UNIT TESTS
# =========================================================================

def test_ingredient_reduce_stock_guard(sample_smoothie_setup):
    """Ingredient.reduce_stock deducts valid portions and raises ValueError if stock is insufficient."""
    with app.app_context():
        mango = db.session.get(Ingredient, "mango_puree")
        assert mango.reduce_stock(5) is True
        assert mango.current_stock == 45

        with pytest.raises(ValueError):
            mango.reduce_stock(45)


def test_smoothie_dynamic_pricing(sample_smoothie_setup):
    """Smoothie.calculate_and_save_price computes base_price from recipe items, default sub, and profit margin."""
    data = sample_smoothie_setup
    with app.app_context():
        smoothie = db.session.get(Smoothie, data["smoothie_id"])
        # (2 * $1.50 mango) + (1 * $0.75 spinach) + (1 * $1.25 blueberry) + (1 * $0.50 almond_milk) + $3.00 margin = $8.50
        assert smoothie.base_price == 8.50


def test_user_password_hashing(client):
    """User password hashing stores scrambled hash rather than plaintext and verifies properly."""
    with app.app_context():
        user = User(username="barista_test", role="employee")
        user.set_password("StrongPass123!")
        db.session.add(user)
        db.session.commit()

        assert user.password_hash != "StrongPass123!"
        assert user.check_password("StrongPass123!") is True
        assert user.check_password("WrongPass") is False


def test_smoothie_component_inheritance_and_polymorphism(sample_smoothie_setup):
    """Verifies Inheritance (SmoothieComponent) and Polymorphism (get_customer_charge / format_ticket_label)."""
    from models import SmoothieComponent

    data = sample_smoothie_setup
    with app.app_context():
        rec = db.session.get(SmoothieRecipeItem, data["rec_mango_id"])
        sub = db.session.get(SmoothieSubItem, data["sub_milk_id"])
        addon = db.session.get(SmoothieAddonItem, data["addon_ice_id"])

        components = [rec, sub, addon]
        # Inheritance check
        assert all(isinstance(comp, SmoothieComponent) for comp in components)

        # Polymorphic behavior check across shared interface
        charges = [comp.get_customer_charge() for comp in components]
        labels = [comp.format_ticket_label() for comp in components]

        assert charges == [0.0, 0.0, 0.0]
        assert labels[0].startswith("Recipe:")
        assert labels[1].startswith("Sub (starter):")
        assert labels[2].startswith("Add-on:")


# =========================================================================
# 3. CART VALIDATION & POS ROUTE TESTS
# =========================================================================


def test_validate_cart_rejects_invalid_recipe_id(sample_smoothie_setup):
    """validate_cart catches tampered or nonexistent recipe IDs."""
    data = sample_smoothie_setup
    with app.app_context():
        bad_cart = [
            {
                "smoothie_id": data["smoothie_id"],
                "recipe_inclusions":[99999],
                "recipe_exclusions": [],
                "sub_inclusions": [],
                "sub_exclusions": [],
                "addon_inclusions": [],
            }
        ]
        result = validate_cart(bad_cart)
        assert result["error_flag"] is True
        assert "Invalid recipe item ID" in result["error_message"]


def test_view_menu_route_loads(client, sample_smoothie_setup):
    """GET /checkout/menu returns HTTP 200 and renders seeded smoothies."""
    response = client.get("/checkout/menu")
    assert response.status_code == 200
    assert b"Tropical Oasis" in response.data


def test_customize_menu_blocks_fewer_than_two_ingredients(client, sample_smoothie_setup):
    """POST /checkout/menu/customize rejects a smoothie with fewer than 2 main recipe ingredients."""
    data = sample_smoothie_setup
    response = client.post(
        "/checkout/menu/customize",
        data={
            "action": "add_smoothie",
            "smoothie_id": str(data["smoothie_id"]),
            f"recipe_items-{data['smoothie_id']}": [str(data["rec_mango_id"])],
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"at least two main recipe ingredients" in response.data

def test_customize_menu_two_step_out_of_stock_warning_and_resubmit(client, sample_smoothie_setup):
    """Step 1 warns and disables out-of-stock ingredient without adding to cart; Step 2 succeeds on user resubmit."""
    data = sample_smoothie_setup

    # 1. Attempt with wild_blueberries included (at minimum_stock=10 -> out_of_stock)
    blocked_resp = client.post(
        "/checkout/menu/customize",
        data={
            "action": "add_smoothie",
            "smoothie_id": str(data["smoothie_id"]),
            f"recipe_items-{data['smoothie_id']}": [
                str(data["rec_mango_id"]),
                str(data["rec_spinach_id"]),
                str(data["rec_blueberry_id"]),
            ],
            f"group_starter_{data['smoothie_id']}": str(data["sub_milk_id"]),
        },
        follow_redirects=False,
    )
    assert blocked_resp.status_code == 200

    # 2. Skip wild_blueberries and order with mango + spinach -> succeeds and redirects (302)
    success_resp = client.post(
        "/checkout/menu/customize",
        data={
            "action": "add_smoothie",
            "smoothie_id": str(data["smoothie_id"]),
            f"recipe_items-{data['smoothie_id']}": [
                str(data["rec_mango_id"]),
                str(data["rec_spinach_id"]),
            ],
            f"group_starter_{data['smoothie_id']}": str(data["sub_milk_id"]),
        },
        follow_redirects=False,
    )
    assert success_resp.status_code == 302

# =========================================================================
# 4. FULL CRUD & ROLE-BASED INVENTORY UPDATE TESTS
# =========================================================================

def _login_as(client, username, role):
    """Creates a test user and logs in via /login so Flask-Login's strong session protection validates."""
    with app.app_context():
        user = User(username=username, role=role)
        user.set_password("TestPass123!")
        db.session.add(user)
        db.session.commit()

    client.post(
        "/login",
        data={"username": username, "password": "TestPass123!"},
        follow_redirects=False,
    )


def test_full_crud_lifecycle_on_models(client):
    """Verifies Create, Read, Update, and Delete (CRUD) across Supplier, Ingredient, and Smoothie models."""
    with app.app_context():
        # CREATE
        supplier = Supplier(name="Fresh Farms Co", email="orders@freshfarms.example", phone="555-0100")
        db.session.add(supplier)
        db.session.commit()

        ing = Ingredient(
            id="dragon_fruit",
            name="Dragon Fruit",
            cost=2.00,
            current_stock=40,
            reorder_stock=15,
            minimum_stock=5,
            supplier_id=supplier.id,
        )
        db.session.add(ing)
        db.session.commit()

        # READ
        fetched = db.session.get(Ingredient, "dragon_fruit")
        assert fetched is not None
        assert fetched.name == "Dragon Fruit"
        assert fetched.supplier.name == "Fresh Farms Co"

        # UPDATE
        fetched.current_stock = 35
        db.session.commit()
        assert db.session.get(Ingredient, "dragon_fruit").current_stock == 35

        # DELETE
        db.session.delete(fetched)
        db.session.commit()
        assert db.session.get(Ingredient, "dragon_fruit") is None


def test_inventory_routes_require_login(client):
    """Unauthenticated users are redirected (302) to /login when accessing protected inventory routes."""
    dash_resp = client.get("/inventory-dashboard", follow_redirects=False)
    update_resp = client.get("/admin/inventory/update", follow_redirects=False)

    assert dash_resp.status_code == 302
    assert "/login" in dash_resp.headers["Location"]
    assert update_resp.status_code == 302
    assert "/login" in update_resp.headers["Location"]


def test_update_inventory_blocks_non_manager_employee(client):
    """RBAC Security: Logged-in 'employee' users receive HTTP 403 Access Denied on /admin/inventory/update."""
    _login_as(client, username="staff_employee", role="employee")

    response = client.get("/admin/inventory/update")
    assert response.status_code == 403
    assert b"Access Denied: Managers Only" in response.data


def test_update_inventory_enforces_stock_relationship_rules(client):
    """Rule 1 & Rule 2: Rejects current_stock < minimum_stock or reorder_stock <= minimum_stock without altering DB."""
    _login_as(client, username="store_manager", role="manager")

    with app.app_context():
        ing = Ingredient(
            id="oat_milk",
            name="Oat Milk",
            cost=0.60,
            current_stock=30,
            reorder_stock=15,
            minimum_stock=10,
        )
        db.session.add(ing)
        db.session.commit()

    # Attempt update violating both rules: current_stock (8) < minimum_stock (10) AND reorder_stock (10) <= minimum_stock (10)
    response = client.post(
        "/admin/inventory/update",
        data={
            "current_stock_oat_milk": "8",
            "reorder_stock_oat_milk": "10",
            "minimum_stock_oat_milk": "10",
        },
        follow_redirects=False,
    )
    # Aborts save and re-renders inventory.html (200) instead of redirecting (302)
    assert response.status_code == 200
    assert b"INVENTORY UPDATE HAS ABORTED" in response.data

    # Confirm original DB values were NOT overwritten
    with app.app_context():
        unchanged = db.session.get(Ingredient, "oat_milk")
        assert unchanged.current_stock == 30
        assert unchanged.reorder_stock == 15


def test_update_inventory_blocks_negative_values(client):
    """Defensive Input Validation: Rejects negative stock inputs without crashing or updating DB."""
    _login_as(client, username="store_manager_neg", role="manager")

    with app.app_context():
        ing = Ingredient(
            id="chia_seeds",
            name="Chia Seeds",
            cost=0.40,
            current_stock=25,
            reorder_stock=12,
            minimum_stock=5,
        )
        db.session.add(ing)
        db.session.commit()

    response = client.post(
        "/admin/inventory/update",
        data={
            "current_stock_chia_seeds": "-5",
            "reorder_stock_chia_seeds": "12",
            "minimum_stock_chia_seeds": "5",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert b"INVENTORY UPDATE HAS ABORTED" in response.data

    with app.app_context():
        assert db.session.get(Ingredient, "chia_seeds").current_stock == 25


def test_update_inventory_succeeds_for_manager_with_valid_rules(client):
    """Valid Manager Update: Saves compliant stock numbers to DB and redirects to /inventory-dashboard."""
    _login_as(client, username="store_manager_ok", role="manager")

    with app.app_context():
        ing = Ingredient(
            id="matcha_powder",
            name="Matcha Powder",
            cost=1.10,
            current_stock=20,
            reorder_stock=15,
            minimum_stock=8,
        )
        db.session.add(ing)
        db.session.commit()

    response = client.post(
        "/admin/inventory/update",
        data={
            "current_stock_matcha_powder": "45",
            "reorder_stock_matcha_powder": "20",
            "minimum_stock_matcha_powder": "10",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "/inventory-dashboard" in response.headers["Location"]

    with app.app_context():
        updated = db.session.get(Ingredient, "matcha_powder")
        assert updated.current_stock == 45
        assert updated.reorder_stock == 20
        assert updated.minimum_stock == 10


def test_navbar_hides_update_inventory_for_non_manager(client):
    """UI RBAC: Employees see Inventory Dashboard in top nav, while Update Inventory is hidden."""
    _login_as(client, username="barista_nav_test", role="employee")

    response = client.get("/inventory-dashboard")
    assert response.status_code == 200
    assert b"/admin/inventory/update" not in response.data


def test_navbar_hides_staff_links_for_guests(client):
    """UI RBAC: Unauthenticated guests do not see Pending Orders or Inventory links in the top navbar."""
    response = client.get("/checkout/menu")
    assert response.status_code == 200
    assert b"/inventory-dashboard" not in response.data
    assert b"/admin/inventory/update" not in response.data

# =========================================================================
# 5. ORDER SEARCH & RECEIPT LOOKUP TESTS
# =========================================================================

def test_find_order_search_returns_receipt_and_status(client, sample_smoothie_setup):
    """GET /orders/find-order?order_id=<id> displays itemized receipt and payment/service status."""
    from models import Order, OrderItem, PaymentStatus, ServiceStatus

    _login_as(client, username="cashier_search", role="employee")
    data = sample_smoothie_setup

    with app.app_context():
        order = Order(
            total_price=8.50,
            payment_status=PaymentStatus.PENDING,
            service_status=ServiceStatus.PREPARING,
        )
        db.session.add(order)
        db.session.commit()

        line = OrderItem(
            order_id=order.id,
            smoothie_id=data["smoothie_id"],
            ingredient_id="mango_puree",
            ingredient_quantity=2,
            add_ingredient=True,
            smoothie_number=1,
            smoothie_price=8.50,
        )
        db.session.add(line)
        db.session.commit()
        order_id = order.id

    response = client.get(f"/orders/find-order?order_id={order_id}")
    assert response.status_code == 200
    assert b"Tropical Oasis" in response.data
    assert b"Mango Puree" in response.data
    assert b"PENDING" in response.data
    assert b"PREPARING" in response.data


def test_find_order_handles_nonexistent_id_gracefully(client):
    """GET /orders/find-order?order_id=99999 warns user cleanly without crashing."""
    _login_as(client, username="cashier_notfound", role="employee")

    response = client.get("/orders/find-order?order_id=99999")
    assert response.status_code == 200
    assert b"No order found matching Order #99999" in response.data
