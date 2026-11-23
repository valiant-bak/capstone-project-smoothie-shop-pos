import enum
from datetime import datetime
from extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


# DATABASE MODELS (SQLAlchemy Schema)

# =========================================================================
# 1. ENUM CLASSES (Enforced Integrity Shields)
# =========================================================================

# SECURITY: Prevents wrong data injection for the payment_status table
class PaymentStatus(str, enum.Enum):
    PENDING = 'pending'
    PAID = 'paid'
    REFUNDED = 'refunded'
    FAILED = 'failed'
    ON_HOLD = 'on_hold'


# SECURITY: Prevents wrong data injection for the service_status table
class ServiceStatus(str, enum.Enum):
    PENDING = 'pending'
    PREPARING = 'preparing'
    SERVED = 'served'
    ON_HOLD = 'on_hold'


# =========================================================================
# 2. CORE INVENTORY SCHEMAS
# =========================================================================


# SUPPLIERS TABLE: It links a supplier to the ingredients needed
class Supplier(db.Model):
    __tablename__ = 'supplier'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    
    # ONE-TO-MANY RELATIONSHIP: This lets us run `some_supplier.ingredients` 
    # to get a list of all items they supply.
    ingredients = db.relationship('Ingredient', backref='supplier', lazy=True)


# INGREDIENTS TABLE
class Ingredient(db.Model):
    __tablename__ = 'ingredient'
    
    # SECURITY / DEFENSIVE CODDING - TEXT ID: Explicitly assigned by DB manager as a unique string identifier
    id = db.Column(db.String(50), primary_key=True) 
    # id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)   

    # PORTION TRACKING COLUMNS: Portion Details
    portion = db.Column(db.Float, default=1.0, nullable=False) 
    # unit_type: The type of measurement unit for the portions (i.e. 'grams', 'mg', 'units', 'oz')
    unit_type = db.Column(db.String(50), default="portion", nullable=False) 
    # Ingredient portion cost
    cost = db.Column(db.Float, default=0.00, nullable=False) 
 
    # INVENTORY TRACKING COLUMNS: Inventory Metrics
    # Tracks the count of minimum portions currently on shelf  
    current_stock = db.Column(db.Integer, default=50, nullable=False) 
    # reorder_stok: Safety threshold count before triggering inventory warnings
    reorder_stock = db.Column(db.Integer, default=20, nullable=False) 
    # Absolute minimum stock count
    minimum_stock = db.Column(db.Integer, default=10, nullable=False) 
   
    # RELATIONSHIP: The Foreign Key links this ingredient directly to a supplier row.
    # Safe fallback configuration: Defaults to None completely behind the scenes.
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), default=None, nullable=True)

    def reduce_stock(self, amount):
        """Funtion that check the current inentory stock and issues a warninig if it is below reorder or min bountdairs"""
       
        if self.current_stock <= amount:
            raise ValueError(f"Insufficient stock for {self.name}. Available: {self.current_stock} {self.unit_type}.")

        self.current_stock -= amount
        # if self.current_stock <= self.reorder_stock:
            # print(f" WARNING: It's time to reorder{self.name} - current_stock: {self.current_stock} portions!")
        
        return True

    def get_stock_values(self):
        """ Function that returns the stock values for give ingredient """

        stock_values = [self.current_stock, self.reorder_stock, self.minimum_stock]

        return f"< Ingredient { self.name } - Stock Status- Current: {self.current_stock}, Reorder: {self.reorder_stock}, Minimum: {self.minimum_stock} >"

    def __repr__(self):
        return f"<Ingredient {self.name} has {self.current_stock} portions available>"


# =========================================================================
# 3. STOREFRONT CONFIGURATION SCHEMAS
# =========================================================================


class Smoothie(db.Model):
    __tablename__ = 'smoothie'

    # NUMERIC ID: Completely managed and autoincremented automatically by the server
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    slogan = db.Column(db.Text, nullable=True)

    # Added profit price beyond the cost of the ingredients
    profit_margin = db.Column(db.Float, default=3.0, nullable=False)

    # A standard column that stores the dynamically calculated price
    base_price = db.Column(db.Float, default=0.00, nullable=False)

    # SCHEMA #5 RELATIONSHIPS (Each choices block maps to its own dedicated table)
    recipe_items = db.relationship('SmoothieRecipeItem', backref='smoothie', cascade="all, delete-orphan")
    sub_items = db.relationship('SmoothieSubItem', backref='smoothie', cascade="all, delete-orphan")
    addon_items = db.relationship('SmoothieAddonItem', backref='smoothie', cascade="all, delete-orphan")

    # SECURITY: DEFENSIVE CODING - DYNAMIC PRICING ENGINE
    # The back-end smoothie base_price calculation DYNAMICALLY fetches the ingredient.cost and ingredient_quanity
    # from the Database, preventing user or processing errors.
    def calculate_and_save_price(self):
        """Calculates default base price using Section 1 recipe lines 
        AND Section 2 default substitution selections."""
        total_ingredient_cost = 0.0
        
        # --- Section 1: Standard Recipe Items ---
        for item in self.recipe_items:
            if item.ingredient:
                cost = float(item.ingredient.cost) if item.ingredient.cost else 0.00
                quantity = int(item.ingredient_quantity) if item.ingredient_quantity else 1
                total_ingredient_cost += cost * quantity

        # --- Section 2: Default Substitutions (New Rule) ---
        # Look at the relationship sub_items and filter for the checked defaults
        for sub_item in self.sub_items:
            if sub_item.is_default and sub_item.ingredient:
                cost = float(sub_item.ingredient.cost) if sub_item.ingredient.cost else 0.00
                # Substitutions default to a quantity of 1 behind the scene
                total_ingredient_cost += cost * 1

        margin = float(self.profit_margin) if self.profit_margin else 0.0
        self.base_price = round(total_ingredient_cost + margin, 2)
        db.session.commit()
        return self.base_price

    def __repr__(self):
        return f"<Smoothie '{self.name}' - Base Price: ${self.base_price:.2f}>"


class SmoothieRecipeItem(db.Model):
    """SECTION 1: Pure default recipe components. Included in base_price.
    - Displayed as pre-selected checkboxes with no quantity/price on screen."""

    __tablename__ = 'smoothie_recipe_item'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    smoothie_id = db.Column(db.Integer, db.ForeignKey('smoothie.id', ondelete='CASCADE'), nullable=False)
    ingredient_id = db.Column(db.String(50), db.ForeignKey('ingredient.id', ondelete='CASCADE'), nullable=False)

    ingredient_quantity = db.Column(db.Integer, default=1, nullable=False)
    
    # RELATIONSHIP for easy access
    ingredient = db.relationship("Ingredient")


class SmoothieSubItem(db.Model):
    """SECTION 2: Free substitution radio groups.
    - Every option alternative is stored as its own clean row line item.
    - Grouped on the screen via matching 'group_name' keys."""

    __tablename__ = 'smoothie_sub_item'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    smoothie_id = db.Column(db.Integer, db.ForeignKey('smoothie.id', ondelete='CASCADE'), nullable=False)
    
    # Shared tag bundles radios together seamlessly (e.g., 'base', 'topping', 'flakes')
    group_name = db.Column(db.String(50), nullable=False)
    ingredient_id = db.Column(db.String(50), db.ForeignKey('ingredient.id', ondelete='CASCADE'), nullable=False)

    
    # Pre-checks the baseline recipe choice alternative item automatically
    is_default = db.Column(db.Boolean, default=False, nullable=False)

    # RELATIONSHIP
    ingredient = db.relationship("Ingredient")


class SmoothieAddonItem(db.Model):
    """SECTION 3: Premium checkbox items with upcharges.
    - Every available addon gets its own clean line item row.
    - quantity defaults to 1 automatically behind the scenes for future scalability."""

    __tablename__ = 'smoothie_addon_item'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    smoothie_id = db.Column(db.Integer, db.ForeignKey('smoothie.id', ondelete='CASCADE'), nullable=False)
    ingredient_id = db.Column(db.String(50), db.ForeignKey('ingredient.id', ondelete='CASCADE'), nullable=False)
    
    ingredient_quantity = db.Column(db.Integer, default=1, nullable=False)

    # RELATIONSHIP
    ingredient = db.relationship("Ingredient")


# =========================================================================
# 4. USER & SECURITY AUTHENTICATION SCHEMAS
# =========================================================================


class User(db.Model, UserMixin):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False) # Long string to store the scrambled password
    role = db.Column(db.String(20), nullable=False, default='employee') # 'employee' or 'manager'

    # Added this explicit constructor method so Pylance understand the inputs
    def __init__(self, username, role='employee'):
        self.username = username
        self.role = role

    # SECURITY: Password Hashing. Only the hashed password gets stored (not the input string)
    # Helper method to scramble and set passwords securely
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    # Helper method to verify credentials during login checks
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


# =========================================================================
# 5. TRANSACTIONAL LOGISTICS SCHEMAS
# =========================================================================


# ORDERS TABLE: Total price and Payment / Service Status
class Order(db.Model):
    __tablename__ = 'order'
    
    id = db.Column(db.Integer, primary_key=True)
    total_price = db.Column(db.Float, nullable=False)
    
    # Pass the Enum class directly into db.Enum()
    payment_status = db.Column(db.Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)
    service_status = db.Column(db.Enum(ServiceStatus), default=ServiceStatus.PENDING, nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Establishes a relationship link to the line items easily
    order_items = db.relationship('OrderItem', backref='order', lazy=True)

    def __repr__(self):
        status = f"Payment: {self.payment_status.value}, Service: {self.service_status.value}"
        return f"<Order id: {self.id} - Total Invoice Price: {self.total_price}, {status}>"
       

# ORDER LINE ITEMS TABLE
class OrderItem(db.Model):
    __tablename__ = 'order_item'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    smoothie_id = db.Column(db.Integer, db.ForeignKey('smoothie.id'), nullable=False)
    ingredient_id = db.Column(db.String(50), db.ForeignKey('ingredient.id'), nullable=False)
    
    ingredient_quantity = db.Column(db.Integer, nullable=False, default=1)  
    
    # Flag for the Kitchen ticket - TRUE means ADD item and FALSE means REMOVE item
    add_ingredient = db.Column(db.Boolean, default=False, nullable=False)

    # Numbers each smoothie cup in the order (1, 2, 3...)
    smoothie_number = db.Column(db.Integer, nullable=False, default=1)
    smoothie_price = db.Column(db.Float, nullable=False) 

    # RELATIONSHIPS
    smoothie = db.relationship("Smoothie")
    ingredient = db.relationship("Ingredient")


    # To print a line item
    def __repr__(self):
        return (
            f"< Order id: {self.order_id}, "
            f"Smoothie id: {self.smoothie_id}, "
            f"Ingredient id: {self.ingredient_id}, "
            f"ingredient quantity {self.ingredient_quantity}, "
            f"add_ingredient: {self.add_ingredient}, "
            f"smoothie_number: {self.smoothie_number}, "
            f"smoothie_price: {self.smoothie_price}>"
        )
