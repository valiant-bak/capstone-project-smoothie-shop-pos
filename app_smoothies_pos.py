# app_oasis_smoothie_shop.py

# D424 Software Engineering Capstone
# Task 3: Full Stack Application
# Web Application: Automated Point of Service and Inventory Management System
# Business: Oasis Smoothie Shop
# Student: 
# Date:

import re, os, secrets, logging, uuid, enum, copy
from datetime import datetime

from flask import Flask, flash, jsonify, redirect, render_template, request, url_for, session, current_app
from flask_login import LoginManager, current_user, UserMixin, login_required, login_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf.csrf import CSRFProtect
from sqlalchemy.orm import joinedload
from sqlalchemy import select

# Import everything needed from the local files
from extensions import db
from models import *
from seed_db import seed_initial_data 
from sqlalchemy.exc import SQLAlchemyError     


app = Flask(__name__)

# 1. SECURITY CONFIGURATION

# 1.1. Load the app secret key securely from environment variables at runtime

# Read the SECRET_KEY from Render's environment variables in production, 
# while still falling back to os.urandom(24) on your local computer:
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24)
# FALLBACK: FORCE LOCAL COMPUTER TO RE-GENERATE EVERY SINGLE TIME
# app.secret_key = os.urandom(24)
# 1.2. Rubric / Scanner compliance setup
API_KEY = os.environ.get("API_KEY", "MOCK_DEV_KEY_123")  # Simple standard fallback

# 1.3. Check environment variables, but fall back to True for local computer development
DEBUG_MODE = os.environ.get("FLASK_DEBUG", "True").lower() in ("true", "1")

# 1.4. SECURITY: Initialize the protection suite alongside the Flask app configuration
csrf = CSRFProtect(app)   # This automatically secures all POST requests

# GLOBAL INVENTORY EXCLUSIONS: Abstract concepts excluded from tracking constraints
INVENTORY_EXCLUSIONS = ['crushed_ice', 'light_ice', 'no_ice', 'no_sugar']

# TERMINAL ANSI COLOR CODES
RED = "\033[91m"
ORANGE = "\033[38;5;208m"  # 256-color true orange (supported in VS Code terminal)
RESET = "\033[0m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"

# 2. LOGGER CONFIGURATION

# 1. Configure the root logger with %(name)s included
logging.basicConfig(
    filename="Oasis_Smoothie_Shop_Report.log",
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# 2. Create specific named category loggers
db_logger = logging.getLogger("DATABASE")
auth_logger = logging.getLogger("SECURITY")
sys_logger = logging.getLogger("SYSTEM")


# 3. DATABASE CONFIGURATION

# 3.1. Configure the SQLite database file location
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# 3.2. Configure the SQLite database file location
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(BASE_DIR, 'app_smoothies_pos.db')}"
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///oasis_smoothie_shop.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 4. INITIALIZE EXTENSIONS
# This connects the app to the db instance imported from extensions.py
db.init_app(app)

# 5. LOGIN MANAGER CONFIGURATION

# 5.1. Initialize the extension instance
login_manager = LoginManager()
login_manager.init_app(app)

# 5.2. Configure session security strength. This applies the security rule immediately after initialization
# If anything about the server or browser connection shifts, Flask logs them out
login_manager.session_protection = "strong" 

# 5.3. Set security guard redirection targets
# If a customer manually types /checkout, Flask blocks them and boots them back here
login_manager.login_view = "login" # type: ignore
login_manager.login_message_category = "error" # Formats standard warning boxes red

# 5.4. Configure the session loader lookup engine
@login_manager.user_loader
def load_user(user_id):
    """Tells Flask-Login how to look up a user object using their session ID."""
    # OLD CODE: return User.query.get(int(user_id))
    # NEW CODE: Clears the 2.0 legacy warning completely
    return db.session.get(User, int(user_id))


# 6. RUN BOOTSTRAP and SEED DATA
with app.app_context():
    # 6.1. Generate tables using the imported models (from models.py)
    db.create_all()   

# 6.2 Run the initial data populator script          
seed_initial_data(app)          

#=============================================================================================#

# PUBLIC MENU SCREEN
@app.route("/")
def home():
    """Public customer facing home page showing available smoothie options."""
    smoothies = Smoothie.query.all()
    return render_template('index.html', smoothies=smoothies)


# 6.2. STAFF AUTHENTICATION ENTRIES
@app.route("/login", methods=["GET", "POST"])
def login():
    """Handles staff authentication for employees and managers."""
    # 1. If they already logged in, send them straight to the checkout POS terminal
    if current_user.is_authenticated:
        return redirect(url_for('view_menu'))

    # 2. Process form data when they hit the "Login" button (POST request)
    if request.method == "POST":
        # Pull text box data using the 'name' attributes from the HTML form
        username_input = request.form.get("username", "").strip()
        password_input = request.form.get("password", "")

        # SECURITY: DEFENSIVE INPUT VALIDATION
        # Rule: Only allow letters, numbers, and underscores between 3-20 characters long
        if not re.match(r"^[a-zA-Z0-9_]{3,20}$", username_input):
            flash("Invalid username structure. Use only 3-20 alphanumeric characters.", "danger")
            return redirect(url_for("login"))
        
        # Lookup user profile in the database
        user = User.query.filter_by(username=username_input).first()

        # Secure validation: Check if user exists AND verify the hashed password matches
        if user and user.check_password(password_input):
            # Log them into the session safely
            login_user(user)
            flash(f"Welcome back, {user.username}! POS session authorized.", "success")
            
            # Direct them to the correct dashboard based on their access clearance role
            if user.role == "manager":
                return redirect(url_for("display_inventory_dashboard"))
            else:
                return redirect(url_for("view_menu"))
        
        # Security Best Practice: Use a generic error message 
        # (Don't reveal if the username was correct but the password was wrong)
        flash("Invalid username or password configuration.", "danger")

    # 3. If it's a GET request, just display the HTML login skin
    return render_template("login.html")

# ----------------------------------------------------------------------------------------------- #
# HELPER FUNCTIONS
# ----------------------------------------------------------------------------------------------- #
def build_smoothie_radio_groups(smoothie):
    """
    Helper function to wrap a single database smoothie object 
    into a structured layout dictionary with safe sub-item scoping.
    """

    # SECURITY: INPUT VALIDATION - Verify the input smoothie is a Database Smoothie object
    input_smoothie = db.session.get(Smoothie, smoothie.id)
    # SECURITY - FAIL FAST
    if not input_smoothie: return []

    # Create a radio_group dictionary
    radio_groups = {}
    for sub_item in smoothie.sub_items:
        if sub_item.group_name not in radio_groups:
            radio_groups[sub_item.group_name] = []
        radio_groups[sub_item.group_name].append(sub_item)
        
    return {
        'smoothie': smoothie,
        'recipe_items': smoothie.recipe_items,
        'radio_groups': radio_groups, # dictionary
        'addon_items': smoothie.addon_items
    }


def get_recipe_ingredient_data(recipe_id):
    """Fetches a single SmoothieRecipeItem and returns (Ingredient, quantity)."""
    if not recipe_id:
        return None, 0
    recipe = db.session.get(SmoothieRecipeItem, int(recipe_id))
    if not recipe or not recipe.ingredient_id:
        return None, 0
    ing = db.session.get(Ingredient, recipe.ingredient_id)
    return ing, (recipe.ingredient_quantity or 0)


def get_sub_ingredient_data(sub_id):
    """Fetches a single SmoothieSubItem and returns (Ingredient, quantity)."""
    if not sub_id:
        return None, 0
    sub = db.session.get(SmoothieSubItem, int(sub_id))
    if not sub or not sub.ingredient_id:
        return None, 0
    ing = db.session.get(Ingredient, sub.ingredient_id)
    return ing, 1


def get_addon_ingredient_data(addon_id):
    """Fetches a single SmoothieAddonItem and returns (Ingredient, quantity)."""
    if not addon_id:
        return None, 0
    addon = db.session.get(SmoothieAddonItem, int(addon_id))
    if not addon or not addon.ingredient_id:
        return None, 0
    ing = db.session.get(Ingredient, addon.ingredient_id)
    return ing, (addon.ingredient_quantity or 0)


def process_cart_items(cart_list: list) -> tuple[list, float]:
    """Cart Level: Numbers each smoothie, translates ingredients, and calculates the grand total."""
    if not cart_list:
        return [], 0.00

    new_items = []
    grand_total = 0.00

    for smoothie_num, custom_smoothie in enumerate(cart_list, start=1):
        # 1. Translate smoothie items into Ingredient objects & prices
        smoothie_ings = translate_custom_smoothie_into_ingredients(custom_smoothie)

        # 2. Attach the cart-level number and accumulate the total
        if smoothie_ings:
            smoothie_ings['smoothie_number'] = smoothie_num
            grand_total += smoothie_ings.get('smoothie_price', 0.0)
            new_items.append(smoothie_ings)

    grand_total = round(grand_total, 2)

    return new_items, grand_total


def validate_cart(session_cart):
    """
    Guarantees DATA INTEGRITY, removes duplicate tracking items, and prevents
    flickering crashes caused by uncalled functional methods or string case variances.
    """

    # Track overall validation status
    report = {"error_flag": False, "error_message": ""}

    # Each item in the cart is a customized smoothie
    for item in session_cart:

        # ==========================================================================================
        # 1. FETCH THE ITEMS FROM THE session_cart AND SANITIZE THE DATA (romove duplicats, if any)
        # ===========================================================================================

        smoothie_id = item.get('smoothie_id')
        if not smoothie_id:
            return {"error_flag": True, "error_message": "No smoothie selected."}

        smoothie = db.session.get(Smoothie, smoothie_id)
        if not smoothie:
            return {"error_flag": True, "error_message": "Selected smoothie not found."}
        
        # ===================================================================================================
        # 2. SECURITY - INPUT SANITATION. Unpack and convert the lists to sets to drop any duplicate inputs
        # ===================================================================================================
       
        recipe_inclusions = set(item.get('recipe_inclusions') or [])
        recipe_exclusions = set(item.get('recipe_exclusions') or [])
        sub_inclusions = set(item.get('sub_inclusions') or [])
        sub_exclusions = set(item.get('sub_exclusions') or [])
        addon_inclusions = set(item.get('addon_inclusions') or [])
      
        # =======================================================================================================
        # 3. EXTRACT THE INGREDIENT IDS FROM THE SmoothieRecipeItem, SmoothieSubItem and SmoothieAddonItem objects
        # ========================================================================================================
        recipe_ing_ids = []
        sub_ing_ids = []
        addon_ing_ids = []
        recipe_excl_ids = []
        sub_excl_ids = []

        for recipe_id in recipe_inclusions:
            ing, ing_qty = get_recipe_ingredient_data(recipe_id)
            if not ing:
                return {"error_flag": True, "error_message": f"Invalid recipe item ID: {recipe_id}"}
            recipe_ing_ids.append(ing.id)

        for sub_id in sub_inclusions:
            ing, ing_qty = get_sub_ingredient_data(sub_id)    # ing_qty = 1 always
            if not ing:
                return {"error_flag": True, "error_message": f"Invalid substitution ID: {sub_id}"}
            sub_ing_ids.append(ing.id)

        for addon_id in addon_inclusions:
            ing, ing_qty = get_addon_ingredient_data(addon_id)
            if not ing:
                return {"error_flag": True, "error_message": f"Invalid add-on ID: {addon_id}"}
            addon_ing_ids.append(ing.id)

        for recipe_id in recipe_exclusions:
            ing, ing_qty = get_recipe_ingredient_data(recipe_id)
            if not ing:
                return {"error_flag": True, "error_message": f"Invalid recipe exclusion ID: {recipe_id}"}
            recipe_excl_ids.append(ing.id)
        
        for sub_id in sub_exclusions:
            ing, ing_qty = get_sub_ingredient_data(sub_id)
            if not ing:
                return {"error_flag": True, "error_message": f"Invalid substitution exclusion ID: {sub_id}"}
            sub_excl_ids.append(ing.id)


        # =========================================================================
        # 2. SECURITY: REFERENTIAL INTEGRITY AND SANITATION OF THE INGREDIENTS
        # =========================================================================

        # Verify the ingredient ids are valid in the Database / filter invalid data

        valid_ingredients_ids = {id for (id,) in Ingredient.query.with_entities(Ingredient.id).all()}
       
        # SECURITY: DEFENSIVE CODING /  DATA SANITATION: Strip out any forged or fake IDs
        recipe_ing_ids = {rid for rid in recipe_ing_ids if rid in valid_ingredients_ids}
        recipe_excl_ids = {rid for rid in recipe_excl_ids if rid in valid_ingredients_ids}

        # SECURITY: DEFENSIVE CODING / DATA SANITATION: Strip out any forged or fake IDs
        sub_ing_ids = {sid for sid in sub_ing_ids if sid in valid_ingredients_ids}
        sub_excl_ids = {sid for sid in sub_excl_ids if sid in valid_ingredients_ids}

        # SECURITY: DEFENSIVE CODING / DATA SANITATION: Strip out any forged or fake IDs
        addon_ing_ids = {aid for aid in addon_ing_ids if aid in valid_ingredients_ids}

        # ========================================================================================
        # 3. SECURITY: DATA INTEGRITY - VALIDATE THE INGREDIENTS AGAINST THE DATABASE 
        # INGREDIENTS FOR RECIPE, SUBSTITUTION AND ADDON INGREDIENTS
        # ========================================================================================
        
        # Pull actual ingredient_ids from SmoothieRecipeItem Database table
        recipe_ingredient_ids = {
            ing_id for (ing_id,) in SmoothieRecipeItem.query
            .filter(SmoothieRecipeItem.id.in_(recipe_inclusions))
            .with_entities(SmoothieRecipeItem.ingredient_id).all()
        }
        # Verify the ingredient ids belong to these Database ingredients in the SmoothieRecipeItem entity
        # print(f"recipe_ing_ids: {recipe_ing_ids}")
        # print(f"recipe_ingredient_ids: {recipe_ingredient_ids}")
        if recipe_ing_ids != recipe_ingredient_ids:
            report["error_flag"] = True
            report["error_message"] = "Invalid recipe ingredients."
            print(f"report: {report}")
            return report

        # Pull actual ingredient_ids from SmoothieSubItem Databse table
        sub_ingredient_ids = {
            ing_id for (ing_id,) in SmoothieSubItem.query
            .filter(SmoothieSubItem.id.in_(sub_inclusions))
            .with_entities(SmoothieSubItem.ingredient_id).all()
        }
        # Verify the ingredient ids belong to these Database ingredients for the SmoothieSubItem entity
        # print(f"sub_ing_ids: {sub_ing_ids}")
        # print(f"sub_ingredient_ids: {sub_ingredient_ids}")
        if sub_ing_ids != sub_ingredient_ids:
            report["error_flag"] = True
            report["error_message"] = "Invalid Substitution ingredients."
            print(f"report: {report}")
            return report

        # Pull actual ingredient_ids from SmoothieAddonItem Database table
        addon_ingredient_ids = {
            ing_id for (ing_id,) in SmoothieAddonItem.query
            .filter(SmoothieAddonItem.id.in_(addon_inclusions))
            .with_entities(SmoothieAddonItem.ingredient_id).all()
        }
        # Verify the ingredient ids belong to these Database ingredients for the SmoothieSubItem entity
        # print(f"addon_ing_ids: {addon_ing_ids}")
        # print(f"addon_ingredient_ids: {addon_ingredient_ids}")
        if addon_ing_ids != addon_ingredient_ids:
            report["error_flag"] = True
            report["error_message"] = "Invalid Addon ingredients."
            print(f"report: {report}")
            return report

        # =====================================================================================
        # 4. MAKE THE DATA SERIALIZABLE: Convert sets back to lists for JSON session safety!
        # =====================================================================================

        set_keys = [
            "recipe_inclusions", "recipe_exclusions", 
            "sub_inclusions", "sub_exclusions", 
            "addon_inclusions"
        ]
        for key in set_keys:
            if key in item and isinstance(item[key], set):
                item[key] = list(item[key])

        # ===============================================================================================
        # 5. SECURITY: DATA INTEGRITY - INGREDIENTS CROSS CHECK (Comparing Actual Physical Ingredients)
        # ===============================================================================================
        # if disjoint is True when there is no common ingredient (no duplicate) between the sets

        # Build master core INGREDIENT inclusion and exclusion sets
        all_inclusions = recipe_ing_ids | sub_ing_ids | addon_ing_ids
        all_exclusions = recipe_excl_ids | sub_excl_ids

        # Paradox Prevention: Making sure they didn't add and exclude the same item
        is_disjoint_paradox = all_inclusions.isdisjoint(all_exclusions)

        # Cross-Lists Duplication Verification
        is_disjoint_recipe_sub   = recipe_ing_ids.isdisjoint(sub_ing_ids)
        is_disjoint_recipe_addon = recipe_ing_ids.isdisjoint(addon_ing_ids)
        is_disjoint_sub_addon    = sub_ing_ids.isdisjoint(addon_ing_ids)

        # Cross-List Duplication Verification
        total_elements = len(recipe_ing_ids) + len(sub_ing_ids) + len(addon_ing_ids)
        has_no_duplicates = len(all_inclusions) == total_elements

        # ====================================================================================
        # 6. HANDLE VALIDATION ERRORS LOUDLY, adn RETURN 'error_flag'=True with ERROR MESSAGES
        # ====================================================================================

        if not is_disjoint_paradox:
            report["error_flag"] = True
            report["error_message"] = f"Paradox error: You cannot add and exclude the same ingredient in custom {smoothie.name} smoothie!"
            print(f"report: {report}")
            return report # Break out early!

        if not is_disjoint_recipe_sub:
            report["error_flag"] = True
            report["error_message"] = f"Duplicate ingredient ids error in recipe_inclusions and sub_inclusions in custom {smoothie.name} smoothie!"
            print(f"report: {report}")
            return report 

        if not is_disjoint_recipe_addon:
            report["error_flag"] = True
            report["error_message"] = f"Duplicate ingredient ids error in recipe_inclusions and addon_inclusions in custom {smoothie.name} smoothie!"
            print(f"report: {report}")
            return report 

        if not is_disjoint_sub_addon:
            report["error_flag"] = True
            report["error_message"] = f"Duplicate ingredient ids error in sub_inclusions and addon_inclusions in custom {smoothie.name} smoothie!"
            print(f"report: {report}")
            return report

        # Check cross-list duplication (e.g. adding an item as both a sub and an addon)
        total_elements = len(recipe_ingredient_ids) + len(sub_ingredient_ids) + len(addon_ingredient_ids)
        if len(all_inclusions) != total_elements:
            report["error_flag"] = True
            report["error_message"] = "Duplicate ingredients detected across categories (between recipe, subs and addons)."
            print(f"report: {report}")
            return report

        # ==============================================================================================
        # CART VALIDATION PASSED!! RETURN TO THE ROUTE
        # ===============================================================================================
        
        # If the loop finishes with zero failures, return clean bill of health
        return report

def translate_custom_smoothie_into_ingredients(custom_smoothie: dict): 
    """Translates a single custom smoothie into full ingredient details and pricing.
        Returns a list of recipe core ingredients, substituted items and premium addonss,
        as well as subtotal pricing for each customized smoothie
        Practical function for creating a customer receipt 
    """
    
    if not custom_smoothie or not isinstance(custom_smoothie, dict):
        return None

    if custom_smoothie.get('error_flag'):
        return None

    smoothie_id = custom_smoothie.get('smoothie_id')
    smoothie = db.session.get(Smoothie, smoothie_id)
    if not smoothie: return None

    recipe_ingredients = []
    sub_ingredients = []
    addon_ingredients = []

    # 1. Standard Recipe Ingredients
    for r_id in custom_smoothie.get('recipe_inclusions', []):
        ing, qty = get_recipe_ingredient_data(r_id)
        if ing:
            recipe_ingredients.append(ing)

    # 2. Substituted / Swapped Ingredients
    for sub_id in custom_smoothie.get('sub_inclusions', []):
        ing, qty = get_sub_ingredient_data(sub_id)
        if ing:
            sub_ingredients.append(ing)

    # 3. Premium Add-ons
    for a_id in custom_smoothie.get('addon_inclusions', []):
        ing, qty = get_addon_ingredient_data(a_id)
        if ing:
            addon_ingredients.append({
                'name': ing.name,
                'cost': float(ing.cost or 0.0)
            })

    addon_total = sum(a['cost'] for a in addon_ingredients)
    smoothie_subtotal = float(smoothie.base_price or 0.0) + addon_total

    return {
        'smoothie_id': smoothie.id,
        'smoothie_name': smoothie.name, 
        'smoothie_base_price': smoothie.base_price,
        'smoothie_price': smoothie_subtotal,
        'recipe_ingredients': recipe_ingredients,
        'sub_ingredients': sub_ingredients,
        'addon_ingredients': addon_ingredients
    }


def get_cart_ingredients(cart_or_item):

    """
    Accepts either a single smoothie dict OR a list of smoothie dicts.
    Returns {ingredient_id: total_quantity_needed}.
    practical function for inventory reconciliation and chicken ticket

    """

    if not cart_or_item: return {}

    # Items can represent a single cart item or a list of cart items [cart_or_item]
    items = cart_or_item if isinstance(cart_or_item, list) else [cart_or_item]
    
    ingredients_needed = {} # dictionary key: ingredient_id , value: ingredient_quantity

    # SECURITY: FAIL FAST - If not a dict or has an error-flag or there's no smoothie_id 
    # or smoothie found, continue
    for item in items:
  
        if not isinstance(item, dict) or item.get('error_flag'): continue

        smoothie_id = item.get('smoothie_id')
        if not smoothie_id or not db.session.get(Smoothie, smoothie_id): continue

        # Section 1: Standard Recipe
        for recipe_id in item.get('recipe_inclusions', []):
            ing, qty = get_recipe_ingredient_data(recipe_id)
            if ing and qty > 0:
                ingredients_needed[ing.id] = ingredients_needed.get(ing.id, 0) + qty

        # Section 2: Substitutions
        for sub_id in item.get('sub_inclusions', []):
            ing, qty = get_sub_ingredient_data(sub_id)
            if ing and qty > 0:
                ingredients_needed[ing.id] = ingredients_needed.get(ing.id, 0) + qty

        # Section 3: Add-ons
        for addon_id in item.get('addon_inclusions', []):
            ing, qty = get_addon_ingredient_data(addon_id)
            if ing and qty > 0:
                ingredients_needed[ing.id] = ingredients_needed.get(ing.id, 0) + qty

        # Section 1: Standard Recipe Exclusions (Not needed)
        for recipe_id in item.get('recipe_exclusions', []):
            ing, qty = get_recipe_ingredient_data(recipe_id)
            if ing:
                ingredients_needed[ing.id] = 0

        # Section 2: Substitutions Not Needed. Only interested on the default sub that has been switched
        for sub_id in item.get('sub_exclusions', []):
            if not sub_id: continue
            sub = db.session.get(SmoothieSubItem, sub_id)
            if not sub or not sub.is_default: 
                continue  # Skip non-default unselected options
            
            if sub.ingredient_id:
                ingredients_needed[sub.ingredient_id] = 0
       
    return ingredients_needed # dictionary ingredients_needed[ing_id]: amount_needed


def check_stock_quantities_vs_demand(required_ingredients):
    """
    Checks the currens stock inventory for the require ingredients dictionary.
    required_ings_dict[ing_id] = ingredient quantity
    """
    # Unified output targets matching the deduction gate checks
    has_hard_stop = False
    
    # Keep the existent list of disabled ingredients for this custom smoothie
    disabled_ings_list = []
    # Collects all tracked ingredients for the smoothie order
    ing_stock_list = []  
    out_of_stock_list = []
    insufficient_stock_list = []
    order_soon_list = []
    
    
    print("=========================== INVENTORY STOCK VERIFICATION ============================")

    x = ""
    print("\n|-----------------------------------------------------------------------|")
    print(f"| Ingredient{x:<11} | Amount Needed | Current Stock | Minimum Stock |")
    print("|-----------------------------------------------------------------------|")
        
    for ing_id, ing_amount_needed in required_ingredients.items():

        # Fetch the ingredient object (ing) form the Database
        ingredient = db.session.get(Ingredient, ing_id)

        # INVENTORY EXCLUSIONS ingredients are not tracked by the INVENTORY ENGINE (e.g. 'ice', 'no_suger', etc.)
        if not ingredient or ingredient.id in INVENTORY_EXCLUSIONS:
            continue

        # ==================================================================================
        # CATEGORIZE THE INGREDIENTS LISTS AS OUT-TO-STOCK, INSSUFFICIENT OR ORDER-SOON
        # ===================================================================================
      
        ing_stock = ingredient.current_stock
        ing_min_stock = ingredient.minimum_stock
        ing_reorder_stock = ingredient.reorder_stock

        # ============================================================================================
        # LIST ALL THE INGREDIENTS IN THE CART WITH THEIR AMOUNT NEEDED AND CURRENT STOCK
        # If the ingredient is out-of-stock or insufficient, raise a flag: 'has_hard_stop'=True
        # ===========================================================================================

        # Append the list showing all igredients needed with their stock values
        ing_stock_list.append([ing_id, ing_amount_needed, ing_stock, ing_reorder_stock, ing_min_stock])

        projected_stock = ing_stock - ing_amount_needed

        # PRINT A TABLE ROW SHOWING THE INGREDIENTS DATA
        
        if ing_id in disabled_ings_list:
            continue

        if ing_amount_needed == 0:
            disabled_ings_list.append(ing_id) # out_of_stock or insufficient_stop already accounted for
            print(f"| {GREEN}{ing_id:<21} | {ing_amount_needed:<13} | {ing_stock:<13} | {ing_min_stock:<13} {RESET}|")
        elif ing_stock <= ing_min_stock:
            out_of_stock_list.append(ing_id)
            print(f"| {RED}{ing_id:<21} | {ing_amount_needed:<13} | {ing_stock:<13} | {ing_min_stock:<13} {RESET}|")
        elif ing_amount_needed > ing_stock - ing_min_stock:
            insufficient_stock_list.append(ing_id)
            print(f"| {ORANGE}{ing_id:<21} | {ing_amount_needed:<13} | {ing_stock:<13} | {ing_min_stock:<13} {RESET}|")
        elif projected_stock < ing_min_stock:
            insufficient_stock_list.append(ing_id)
            print(f"| {ORANGE}{ing_id:<21} | {ing_amount_needed:<13} | {ing_stock:<13} | {ing_min_stock:<13} {RESET}|")     
        else: # no stock deficiencies
            print(f"| {ing_id:<21} | {ing_amount_needed:<13} | {ing_stock:<13} | {ing_min_stock:<13} |")
      
        print("|-----------------------------------------------------------------------|")
        
    print("\n============================= INVENTORY SUMMARY REPORT =============================\n")

    if out_of_stock_list or insufficient_stock_list:
        has_hard_stop = True

    if has_hard_stop:
        print(f"{RED}THE INVENTORY HAS A HARD STOP:{RESET}")
    else: 
        print(f"{GREEN}ALL THE REQUIRED INGREDIENTS ARE AVAILABLE. INVENTORY VERIFICATION SUCCESSFUL!{RESET}")
   
    print(f"{RED}out_of_stock_list: {out_of_stock_list}{RESET}")
    print(f"{RED}insufficient_stock_list: {insufficient_stock_list}{RESET}")
    print(f"{ORANGE}order_soon_list: {order_soon_list}{RESET}")
    print(f"{GREEN}disabled_ings_list: {disabled_ings_list}{RESET}")

    print("\n======================== END OF INVENTORY SUMMARY REPORT =============================\n")   
    
    return { # return a dictionary 
        'has_hard_stop': has_hard_stop,
        'disabled_ings_list': disabled_ings_list,
        'ing_stock': ing_stock,
        'out_of_stock_list': out_of_stock_list,
        'insufficient_stock_list': insufficient_stock_list,
        'order_soon_list': order_soon_list
    }
 
def verify_inventory(session_cart):
    """
    Aggregates required ingredient portions across all customized items,
    simulates stock impact, and categorizes problematic items based on safety metrics.
    
    It uses the helper functions:  
        1. get_cart_ingredients(session_cart): returns a list of ingredients needed
        2. check_stock_quantities_vs_demand(required_ingredients): returns a table with the
            ingredients needed and the amount needed for each ingredient in ghe cart

    SECURITY - DATA INTEGRITY
    PURE LOOKUP ONLY - NEVER ALTERS OR COMMITS DATABASE CHANGES.
    """

    # =======================================================================================
    # 1. COUNTING ALL REQUIRED INGREDIENTS 
    # =======================================================================================

    # Dictionary to hold the ammount to deduct for each listed ingredientt(the key)
    ingredients_to_deduct = {}

    # Helper function that counts the ingredients in the cart and their quantities needed
    cart_ingredients = get_cart_ingredients(session_cart)
    # cart_ingredients is a dictionary -- key: ing_id, value:amount_needed
              
    # =======================================================================================
    # 2. CHECK THE CART INGREDIENTS NEEDED AGAINST THE INVENTORY STOCK AVAILABLE
    # =======================================================================================

    # Helper function to verify the required ingredients for the order have enough stock available
    inventory_report = check_stock_quantities_vs_demand(cart_ingredients)

    return inventory_report

    # inventory_report { 
    #     'has_hard_stop': has_hard_stop,
    #     'disabled_ings_list': disabled_ings_list,
    #     'ing_stock': ing_stock,
    #     'out_of_stock_list': out_of_stock_list,
    #     'insufficient_stock_list': insufficient_stock_list,
    #     'order_soon_list': order_soon_list
    # }
   
    # # Unpack the inventory check lists
    # has_hard_stop = inventory_check['has_hard_stop']
    # disabled_ings_list = inventory_check['disabled_ings_list']
    # ing_stock = inventory_check['ing_stock']
    # out_of_stock_list = inventory_check['out_of_stock_list']
    # insufficient_stock_list = inventory_check['insufficient_stock_list']
    # order_soon_list = inventory_check['order_soon_list']


    # print(f"ing_stock: {ing_stock}")
    # # Categorize the stock deficiencies
    # for ing_id, ing_amount_needed, ing_stock, ing_reorder_stock, ing_min_stock in ing_stock:

    #     projected_stock = ing_stock - ing_amount_needed

    #     if ing_amount_needed == 0: # the stock issue was adresed and the ingredient is not tracked
    #         if ing_id not in disabled_ings_list:
    #             disabled_ings_list.append(ing_id)
    #             print(f"Ingredient {ing_id} has been added to the disabled_ings_list: {disabled_ings_list}")
    #         continue

    #     elif ing_stock <= ing_min_stock:
    #         if ing_id not in out_of_stock_list:
    #             out_of_stock_list.append(ing_id)
    #             print(f"Ingredient {ing_id} has been added to the out_of_stock_list: {out_of_stock_list}")
    #             continue

    #     elif ing_amount_needed > ing_stock - ing_min_stock:
    #         if ing_id not in insufficient_stock_list:
    #             insufficient_stock_list.append(ing_id)
    #             print(f"Ingredient {ing_id} has been added to the insufficient_stock_list: {insufficient_stock_list}")
    #             continue

    #     elif projected_stock < ing_min_stock:
    #          if ing_id not in insufficient_stock_list:
    #             insufficient_stock_list.append(ing_id)
    #             print(f"Ingredient {ing_id} has been added to the insufficient_stock_list: {insufficient_stock_list}")
    #             continue

    #     elif ing_amount_needed > ing_reorder_stock - ing_min_stock:
    #         if ing_id not in order_soon_list:
    #             order_soon_list.append(ing_id)
    #             print(f"Ingredient {ing_id} has been added to the reorder_soon_list: {order_soon_list}")
    #             continue

    # inventory_report = {
       
    #     'has_hard_stop': has_hard_stop,
    #     'disabled_ings_ist': disabled_ings_list,
    #     'ing_stock': ing_stock,
    #     'out_of_stock_list': out_of_stock_list,
    #     'insufficient_stock': insufficient_stock_list,
    #     'order_soon_list': order_soon_list
    # }

    


def report_inventory_status(inventory_report):
    """
    Consolidates inventory lists into a single unified flash notification.
    """
    has_hard_stop = inventory_report['has_hard_stop']

    # 1. Pull the direct lists out of our checked data metrics array
    raw_out = inventory_report['out_of_stock_list']
    raw_insufficient = inventory_report['insufficient_stock_list']

    # 2. Apply global INVENTORY_EXCLUSIONS array to passive warning layers
    order_soon = [i for i in inventory_report['order_soon_list'] if i not in INVENTORY_EXCLUSIONS]
    # report_reorder = [i for i in inventory_report.get('reorder_state', []) if i not in INVENTORY_EXCLUSIONS]

    if not has_hard_stop and order_soon:
        soon_ings = db.session.scalars(db.select(Ingredient).where(Ingredient.id.in_(order_soon))).all()
        names = ", ".join([ing.name for ing in soon_ings])
        flash(f"📝 Low in stock ingredients: [{names}]. Hurry to finalize checkout!<br>", "warning")
        return  
    
    errors_collected = []
    warnings_collected = []
    
    if raw_out:
        short_ings = db.session.scalars(db.select(Ingredient).where(Ingredient.id.in_(raw_out))).all()
        names = ", ".join([ing.name for ing in short_ings])
        errors_collected.append(f"Out of stock ingredients: [{names}].<br>")

    if raw_insufficient:
        min_ings = db.session.scalars(db.select(Ingredient).where(Ingredient.id.in_(raw_insufficient))).all()
        names = ", ".join([ing.name for ing in min_ings])
        errors_collected.append(f"Insufficient stock of [{names}] to complete the order!<br> ")

    if errors_collected or warnings_collected:
        message_parts = []
        if errors_collected:
            if request.endpoint == 'view_cart':
                message_parts.append("⚠️ " + " ".join(errors_collected) + 
                "Please DELETE the Smoothie with the shortage ingredients. Thank you!")
            else:
                message_parts.append("⚠️ " + " ".join(errors_collected) + 
                f"[{names}] disabled. Please select different Smoothie or Ingredients.")
        
        if warnings_collected:
            message_parts.append("📝 " + " ".join(warnings_collected) + "Hurry to finalize checkout!")
            
        final_flash_msg = " ".join(message_parts)
        category = "danger" if has_hard_stop else "warning"
        flash(final_flash_msg, category)

    return





def calculate_cart_total(session_cart):
    grand_total = 0.00
    new_items = []

    for custom_smoothie in session_cart:  # for each custom smoothie in the temp cart

        # 1. Call a helper function to TRANSLATE SMOOTHIE ITEMS INTO OBJ iNGREDIENT
        # SmoothieRecipeItems, SmoothieAddonItems and SmoothieSubItems into Ingredients
        smoothie_ings = translate_custom_smoothie_into_ingredients(custom_smoothie)
    
        # 2. Add each translated smoothie to the list
        new_items.append(smoothie_ings) # new_items list has each customized smoothie

    # Calculate the grand total safely
    grand_total = sum(item.get('smoothie_price', 0.0) for item in new_items)
  
    return grand_total


# =========================================================================
# SMOOTHIE ORDER FLOW - WITH CURRENT ORDER IN SESSION 
#=========================================================================

@app.route('/checkout/menu', methods=['GET'])
def view_menu():

    if 'cart' not in session:
        session['cart'] = []
        session.modified = True
    session_cart = session.get('cart', [])

    # Fetch the available smoothies for the database
    smoothies = Smoothie.query.all()

    menu_data = [build_smoothie_radio_groups(smoothie) for smoothie in smoothies]
    # menu_data =
        # 'smoothie': smoothie,
        # 'recipe_items': smoothie.recipe_items,
        # 'radio_groups': radio_groups, # dictionary
        # 'addon_items': smoothie.addon_items
    
    # print("=================================== OASIS AVALIABLE SMOOTHIES ====================================")

    # for index in [0, len(smoothies)-1]:  # two smoothies available right now
    #     print(f"Smoothie id: {menu_data[index]['smoothie'].id}")
    #     print(f"Smmothie name: {menu_data[index]['smoothie'].name}")
    #     print(f"Smoothie Recipe Items: {menu_data[index]['smoothie'].recipe_items}")
    #     print(f"Smoothie Sub Items: {menu_data[index]['smoothie'].sub_items}")
    #     print(f"Smoothie Addon Items: {menu_data[index]['smoothie'].addon_items}")
    #     print("---------------------------------------------------------------------------------------------- ")
    # print("WAITING TO CUSTOMIZE A NEW SMOOTHIE.........................\n") 

    # Create a fast dictionary matching ingredient.id to the ingredient object
    ingredients_map = {str(ing.id): ing for ing in Ingredient.query.all()}

    return render_template(
        'menu.html', 
        smoothies=smoothies, 
        menu_data=menu_data,
        ingredients_map=ingredients_map,
        error_ingredients= [],
        failed_smoothie_id= None
    )


@app.route('/checkout/menu/customize', methods=['POST'])
def customize_menu():

    if 'cart' not in session:
        session['cart'] = []
        session.modified = True
    session_cart = session.get('cart', [])

    # =============================================================================
    # Step 1: FETCH THE INPUT FIELDS AND PERFORM INPUT SANITATION (menu.html form)
    # =============================================================================
  
    # 2. Get the 'action' from the submitted form
    action = request.form.get('action')
    # SECURITY: FAIL FAST. ACTION: If the 'action' is not 'add_smoothie' return to the form
    if action != 'add_smoothie':
        flash("Invalid action command received.", "danger")
        return redirect(url_for('view_menu'))

    # 3. Get the smoothie id from the form
    smoothie_id = request.form.get('smoothie_id')
    # SECURITY - FAIL FAST: If did not get a smoothie_id, return the form with an error message.
    if not smoothie_id:
        flash("Invalid input. Please select a smoothie from the dropdown.", "danger")
        return redirect(url_for('view_menu'))

    # 4. SECURITY - DATABASE VERIFICATION: Core Entity Check. Find the smoothie object in the DB
    smoothie = db.session.get(Smoothie, smoothie_id) if smoothie_id else None
    # SECURITY - FAIL FAST: If the smoothie was not in the Database, return the form with an error message.
    if not smoothie:
        flash("The selected smoothie could not be found.", "danger")
        return redirect(url_for('view_menu'))

    print()
    print("================================ NEW CUSTOM SMOOTHIE ====================================\n")  
    print(f"Selected smoothie: {smoothie.name}")

    # ======================================================================================================
    # SECTION 1: RECIPE ITEMS (SmoohtieRecipeItem class)
    # ======================================================================================================

    # 1. SECURITY: INPUT VALIDATION / STRUCTURE VERIFICATION. Verify the incoming data is the correct Type.
    selected_recipe_ids = request.form.getlist(f"recipe_items-{smoothie.id}", type=int) or [] # list
    all_recipe_ids = { int(item.id) for item in smoothie.recipe_items } # set
    
    # 2. SECURITY: DATA SANITATION / DEFENSIVE CODING - PREVENT DATA DUPLICATES by converting a list to a set
    recipe_inclusions = set(selected_recipe_ids) # set of SmoothieRecipeItem integer ids
    recipe_exclusions = all_recipe_ids - recipe_inclusions # Data type: SmoothieRecipeItem integer ids

    # 3. SECURITY: SMOOTHIE RULES VALIDATION - Each custom smoothie should include at leas 2 main ingredients
    print(f"main ingredients quantity: {len(recipe_inclusions)}")
    # Return the form back to the user to adjsut the ingredients if the basic ingredients drop below 2
    if len(recipe_inclusions) < 2:
        flash(f"Error: A custom {smoothie.name} must include at least two main recipe ingredients!", "danger")
        return redirect(url_for('view_menu'))

    # ======================================================================================================
    # SECTION 2: SUB ITEMS (SmoothieSubItems class)
    # ======================================================================================================

    # 1. SECURITY: INPUT VALIDATION / STRUCTURE VERIFICATION. Verify the incoming data is the correct Type. 
    # Define the radio groups. New groups can get added here and in the seed_db.py boostrap file
    target_groups = ['starter', 'flavor', 'topping', 'sweetener', 'ice']

    # 2.SECURITY: DATA INTEGRITY - BUILD A RADIO GROUP DICTIONARY 
    # Directly grab the single value for each group using a comprehension
    active_groups = {
        sub.group_name 
        for sub in SmoothieSubItem.query.filter_by(smoothie_id=smoothie.id).all()
    }

    selected_subs_dict = {
        group: value
        for group in active_groups
        if (value := request.form.get(f"group_{group}_{smoothie.id}", type=int)) is not None
    }

    # 3. SECURITY: DATA SANITATION - CONVERT THE DICTIONARY TO A SET to remove possible duplicates
    selected_sub_ids = set(selected_subs_dict.values()) # set of the selected subs values
    all_sub_ids = { int(item.id) for item in smoothie.sub_items } # set, item is a SmoothieSubItem object   
    
    # 3. SECURITY: DATA SANITATION / DEFENSIVE CODING - PREVENT DATA DUPLICATES by converting a list to a set
    sub_inclusions = set(selected_sub_ids) # set of SmoothieSubItem integer ids
    sub_exclusions = all_sub_ids - sub_inclusions # Data type: SmoothieSubItem integer ids

    # ======================================================================================================
    # SECTION 3: ADDON ITEMS (SmooothieAddonItem class)
    # ======================================================================================================
   
    # 1. SECURITY: INPUT VALIDATION / STRUCTURE VERIFICATION. Verify the incoming data is the correct Type.
    selected_addon_ids = request.form.getlist(f"addon_items-{smoothie.id}", type=int) or [] # list
    all_addon_ids = { int(item.id) for item in smoothie.addon_items } # set, item is a SmoothieAddonItem object
   
    # 2. SECURITY: DATA SANITATION / DEFENSIVE CODING - PREVENT DATA DUPLICATES by converting a list to a set
    addon_inclusions = set(selected_addon_ids) # set of SmoothieRecipeItem integer ids
    addon_exclusions = all_addon_ids - addon_inclusions # Data type: SmoothieRecipeItem integer ids

    # ==================================================================================================
    # STEP 2: BUILD A CART ITEM WITH THE CUSTOM SMOOTHIE PARAMS 
    # ==================================================================================================
  
    # Ensure JSON serializable numeric type: Convert sets to lists
    cart_item = {
        "smoothie_id": smoothie.id,
        "smoothie_name": smoothie.name,
        "smoothie_price": float(smoothie.base_price), # no addons yet in the price
        "recipe_inclusions": list(recipe_inclusions), 
        "sub_inclusions": list(sub_inclusions),
        "addon_inclusions": list(addon_inclusions),
        "recipe_exclusions": list(recipe_exclusions),
        "sub_exclusions": list(sub_exclusions),
        # "paid": False,
        # "served": False,
        "error_flag": False
    }
    print("\n====================== CREATING A NEW CART ITEM (CUSTOM SMOOTHIE) ====================\n")
    print(f"cart_item: {cart_item} \n" )
    print("============================================================================================\n")
    # ====================================================================================
    # STEP 3: CART ITEM INPUT VALIDATION (CUSTOM_SMOOTHIE INPUT VALIDATION)
    # ====================================================================================
    
    # Calling a helper function to validate this cart_item
    # Only add to cart if validation SUCCEEDED (error_flag is False)
    validation_report = validate_cart([cart_item])
   
    # ==============================================================================================
    # STEP 4: CONDITIONAL EXECUTION - HALT ON ERROR VS COMMIT ON SUCCESS
    # ==============================================================================================
  
    # ======================================================================================================  
    # CASE A: IF INPUT VALIDATION FAILED!
    # =======================================================================================================
    # IF THE CURRENT CART FAILED VALIDATION: The error_flag is True. Re-render the form with error messages
    # =======================================================================================================
    if validation_report.get('error_flag') is True:
        error_msg = validation_report['error_message']
        flash(f"Validation Error: {error_msg}", "danger")
        print("=====================================================")
        print(f"INPUT VALIDATION FAILED! {error_msg}")
        print("=====================================================")

        # Fetch the available smoothies for the database and build their radio groups
        smoothies = Smoothie.query.all()
        menu_data = [build_smoothie_radio_groups(smoothie) for smoothie in smoothies]
        
        # Create a fast dictionary matching ingredient.id to the ingredient object
        ingredients_map = {str(ing.id): ing for ing in Ingredient.query.all()}

        # ======================================================================================
        # RE-RENDER THE MENU TEMLATE TO FIX THE ERRRORS 
        # ======================================================================================
        return render_template(
            'menu.html', 
            smoothies=smoothies, 
            menu_data=menu_data,
            ingredients_map=ingredients_map,
            error_ingredients= [],   
            failed_smoothie_id=int(smoothie_id)
        )

    # CASE B: INPUT VALIDATION PASSED! Keep moving forward to the inventory check
    # ===========================================================================================
    # The error_flag is False (no errors) - SAVE THE cart_item into the session_cart
    # THE SESSION CART PASSED INPUT VALIDATION!!! The error_flag is False (no errors) - CONTINUE
    # ===========================================================================================
    print(f"INPUT VALIDATION PASSED for smoothie {smoothie.name}!!\n")

    # =============================================================================================
    # SETP 4: INVENTORY VERIFICATION. Check if there are enough ingredients to fulfill the order
    # ==============================================================================================

    inventory_report = verify_inventory(session_cart + [cart_item])

    report_inventory_status(inventory_report)

    # inventory_report { 
    #     'has_hard_stop': has_hard_stop,
    #     'disabled_ings_list': disabled_ings_list,
    #     'ing_stock': ing_stock,
    #     'out_of_stock_list': out_of_stock_list,
    #     'insufficient_stock_list': insufficient_stock_list,
    #     'order_soon_list': order_soon_list
    # }

  
    # Unpack the lists from the inventory_report
    has_hard_stop = inventory_report['has_hard_stop'] # True/False
    disabled_ings_list = inventory_report['disabled_ings_list']

    # ALL the ingredients for the custom smoothie with their stock values
    ing_stock = inventory_report['ing_stock'] 
   
    out_of_stock_list = inventory_report['out_of_stock_list']
    insufficient_stock_list = inventory_report['insufficient_stock_list']
    order_soon_list = inventory_report['order_soon_list']

    # =================================================================================================
    # IF INVENTORY VERIFICATION FAILED: The 'has_hard_stop' flag is True. 
    # Add all the out_of_stock and insufficient ingredients into problematic_ids.
    # Re-render the form along with error messages, the failed_smoothie_id and problematic_ids.
    # =================================================================================================

    if has_hard_stop: 
    
        disabled_ings_list = set(out_of_stock_list + insufficient_stock_list)
        # The smoothie order will not include the dissabled ingredients
        print(f"{GREEN}disabled_ings_list: {disabled_ings_list}{RESET}")

        print("================== SKIPPING OUT_OF_STOCK / INSUFFICIENT INGREDIENTS =====================")

        # =====================================================================================
        # RETURN THE FORM WITH ERROR MESSAGES, HIGHLIGHTING THE INGREDIENTS WITH STOCK ISSUES
        # =====================================================================================

        # Fetch the available smoothies for the database and build their radio groups
        smoothies = Smoothie.query.all()
        menu_data = [build_smoothie_radio_groups(smoothie) for smoothie in smoothies]
        # Create a fast dictionary matching ingredient.id to the ingredient object
        ingredients_map = {str(ing.id): ing for ing in Ingredient.query.all()}

        # Re-render without changing session['cart']
        return render_template(
            'menu.html', 
            smoothies=smoothies, 
            menu_data=menu_data,
            ingredients_map=ingredients_map,  
            error_ingredients=disabled_ings_list,
            failed_smoothie_id=int(smoothie_id)
        )
        
    # Case B: INVENTORY VERIFICATION PASSED!
    # =============================================================================== #
    # SUCCESS PATH: THE CART PASSED INPUT VALIDATION AND INVENTORY VERIFICATION       #
    # FINAL SUCCESS SAFE ZONE (The only place the session gets updated!)              #
    # =============================================================================== #
    session_cart.append(cart_item)
    session.modified = True

    has_hard_stop = False

    print(f"SUCCESS: ADDED THE CUSTOM SMOOTHIE {smoothie.name} to the session_cart\n")
    # print(f"session_cart: {session_cart}")
    
    print(" \n============== INVENTORY VERIFICATION PASSED ==================\n")
    print(f" CUSTOM SMOOTHIE ADDED TO CART - NUMBER OF ITEMS IN THE CART: {len(session.get('cart', []))}\n") 
   
    flash(f"Successfully added custom {smoothie.name} to the cart!", "success")
    return redirect(url_for('view_menu'))


@app.route('/checkout/cart')
def view_cart():
    """ 
    Defensive Gatekeeper View:
    Runs look-ahead inventory checks. If a user triggers a POST order action 
    but a hard stop is found, it injects a flash message and stops execution.
    
    CRITICAL GATEKEEPER: Handles page loads (GET) and order validation submissions (POST).
    If stock metrics are broken, it kills the checkout execution early in this route.
    """
    if 'cart' not in session:
        session['cart'] = []
        session.modified = True
    session_cart = session.get('cart', [])

    cart_items, grand_total = process_cart_items(session_cart)

    session['cart_grand_total'] = grand_total
  

    return render_template(
        'cart.html',
        items=cart_items,  
        grand_total=grand_total,
        failed_smoothie_id=None,
        error_ingredients=None
    )


@app.route('/checkout/process_order', methods=['POST'])
def process_order():
    """
    Staging Gateway.
    Verifies there are enough stock ingredients to cover the order. Creates the Order and the OrderItem record.
    Uses the inventory reconciliation engine to deduct the required ingredients from the Inventory stock
    """
    # ====================================================================================
    # 1. VERIFY THERE'S A SESSION_CART AND IT HAS THE GRAND_TOTAL PRICE IN IT
    # ====================================================================================
    if 'cart' not in session:
        session['cart'] = []
        session.modified = True
    session_cart = session.get('cart', [])


    # 1.1. SECURITY: FAIL FAST if there's no session_cart
    if not session_cart:
        flash("Your cart is empty. Please select a smoothie from the dropdown list.", "warning")
        return redirect(url_for('view_menu'))

    # 1.2. SECURITY: FAIL FAST if there's no grand total saved
    grand_total = session.get('cart_grand_total', 0.00) 
    if not grand_total:
        flash("These was an unxpected issue with the cart. Please try again","danger")
        return redirect(url_for('view_cart'))

    # ========================================================================================================
    # 2. INVENTORY VERIFICATION: Check the inventory again BEFORE committing the order or dismissing the user
    # =======================================================================================================
    print("\n*********** VERIFYING THE INVENTORY AGAIN BEFORE THE DEDUCTION ENGINE *********\n")
    # 2.1. Verify there are enough ingredients in stock to cover the session_cart ingredients
    inventory_report = verify_inventory(session_cart)

    has_hard_stop = inventory_report['has_hard_stop'] 
    ing_stock = inventory_report['ing_stock']  
    disabled_ings_list = inventory_report['disabled_ings_list']
    out_of_stock_list = inventory_report['out_of_stock_list']
    insufficient_stock_list = inventory_report['insufficient_stock_list'] 
    order_soon_list = inventory_report['order_soon_list']

    # # 2.1 SECURITY: FAIL FAST. If there aren't enough ingredients to fullfill the order, redirect to view-cart
    if inventory_report['insufficient_stock_list'] or inventory_report['out_of_stock_list']:   
        return redirect(url_for('view_menu'))

    # ============================================================================================================
    # 3. IF INVENTORY VERIFICATION PASSED! Not having out-of-stock or insufficient ingredients in the order.
    # ================================================================================================================
    # AGGREGATE PORTIONS in 'recipe_inclusions', 'sub_inclusions' and 'addon_inclusions' to deduct from the inventory
    
    # 3.1. Setup a dictionary to hold the ammount to deduct for each listed ingredientt(the key)
    ingredients_to_deduct = {}

    # 3.2. Get the list of ingredient used in the cart (for all smoothies in teh cart)
    ingredients_to_deduct = get_cart_ingredients(session_cart)
     
    print("\n📦 =================== RUNNING INVENTORY DEDUCTION ENGINE ==================")
    print("🔒 Commencing row-level locking database verification process...")

    # 3.3. Create a table header for the Inventory Report
    x = ""
    print("\n|---------------------------------------------------------------|")
    print(f"| Ingredient{x:<11} | Old Stock | New Stock | Minimum Stock |")
    print("|---------------------------------------------------------------|")

    try:
        # ==================================================================================================
        # 4. Create a new Order object and add the grand_total and payment/ service status as PENDING
        # ==================================================================================================
        new_order = Order(
            total_price=round(float(grand_total), 2),
            payment_status = PaymentStatus.PENDING,
            service_status = ServiceStatus.PENDING
        )

        # 4.1. Add the new order to the Databese
        db.session.add(new_order)

        # 4.2.  Flush to generate new_order.id before adding items 
        db.session.flush() 

        # ====================================================================================================
        # 5. POPULATE ORDER_ITEM LINES: Iterate through session_cart items to populate OrderItem records
        # ====================================================================================================
        
        session_cart = session.get('cart', [])

        cart_items, grand_total = process_cart_items(session_cart)
        
        # Pair each numbered display item with its corresponding raw session_cart item
        for cart_item, raw_item in zip(cart_items, session_cart):

            print("====================================================================")
            print(f"cart_item: {cart_item}, cart_itemst: {cart_items}")
            print("====================================================================")
            print(f"raw_item: {raw_item}, session_cart: {session_cart}\n")


            if raw_item.get('error_flag'): continue

            smoothie_id = raw_item.get('smoothie_id')
            smoothie_number = cart_item['smoothie_number']
            smoothie_price = cart_item['smoothie_price']  


            if not smoothie_id or not db.session.get(Smoothie, smoothie_id): continue

            single_smoothie_quantities = get_cart_ingredients(raw_item)
            
            for ing_id, ing_qty in single_smoothie_quantities.items():
                if not ing_id or ing_qty < 0: continue

                db.session.add(OrderItem(
                    order_id=new_order.id,
                    smoothie_id=smoothie_id,
                    ingredient_id=ing_id,
                    ingredient_quantity=ing_qty,    # Exact portion if > 0, or 0 if removed
                    add_ingredient=(ing_qty > 0),      # True if > 0, False if == 0
                    smoothie_number=smoothie_number, 
                    smoothie_price=smoothie_price  
                ))

              
        # ===================================================================================================
        # 6. Begin row-level locking database verification process
        # ====================================================================================================
        
        for ingredient_id, deduction_amount in ingredients_to_deduct.items():

            # 5.1 SECURITY - FAIL FAST: Prevents crash from zero quantities or corrupt/missing primary keys
            if deduction_amount <= 0 or not ingredient_id: continue

            # ==============================================================================================
            # 5.2 SECURITY - CRITICAL STEP - SECURE ROW LOCK: Blocking the ingredient row of the required ingredient  
            # =============================================================================================================
            # with_for_update() blocks other threads until this transaction commits/rolls back
            ingredient = db.session.query(Ingredient).with_for_update().filter_by(id=ingredient_id).first()
            if not ingredient: continue
            
            if ingredient:

                # 5.3. Extract the ingredient.id for the ingredient object
                ing_id = ingredient.id
                # 5.4. Savve teh current_stock as old_stock
                old_stock = ingredient.current_stock
            
                # 5.5. EXECUTE THE CUSTOM REDUCE_STOCK LOGIC from the Ingredient model
                # ==================================================================================
                # 5.6 Reduce the stock by the deduction amount calculated in ingredients_to_deduct above
                ingredient.reduce_stock(deduction_amount)
              
                # 5.7. Establish the new stock value
                new_stock = ingredient.current_stock
            
                min_stock = ingredient.minimum_stock

                # 5.8 PRINT A TABLE shwoing the ingredients stock befor and after the deduction
                # ==================================================================================
                print(f"| {ing_id:<21} | {old_stock:<9} | {new_stock:<9} | {min_stock:<13} |")
      
                print("|---------------------------------------------------------------|")
        
      
        # =============================================================================================================
        # 7. SAVE THE DATABASE ENTIRE TRANSACTION AT ONCE! Commint the order and inventory deduction together
        # =============================================================================================================
        
        # 7.1. Commit the whole transaction to the Database
        db.session.commit()

        # 7.2. Log the info message into the logger
        db_logger.info(f"Order #{new_order.id} has been saved, and inventory has been reconciled.")
        print(f"\n==========================================================================")
        print(f"{GREEN}NEW ORDER CREATED SUCCESSFULLY - order_id: {new_order.id}{RESET}\n")

        # ==============================================================================================
        # 8. CLEAR THE CART so it can be used for the next transaction 
        # ==============================================================================================
       
        # 1. Create a backup cart (staged_cart) in the session to complete the order if there are payment issues
        # True read-only isolation (copy.deepcopy): independent copy unlinked form session{'cart']}
        session['staged_cart'] = copy.deepcopy(session.get('cart', []))
        staged_cart = session['staged_cart']
        # print(f"staged_cart: {staged_cart}")

        # 2. Clear the session['cart'] for the next order
        session.pop('cart', None)
        session.pop('cart_grand_total', None)
        session.modified = True
       
        print("The session_cart has been successfully cleared")
        print("----------------------------------------------------------------------------------------")
        print(F"{GREEN}Order number {new_order.id} has been succesfully saved in the Database{RESET}")
        print("========================================================================================\n")
        # =============================================================================================
        # 9. SECURITY: USER AUTHENTICATION - CHECK THE USER'S ROLE dictate frontend navigation patterns
        # =============================================================================================
    
        # 9.1. Check if the user is a logged in employee
        is_staff = current_user.is_authenticated and current_user.role in ['employee', 'manager']
        
        # 9.2. Dismiss the customer or route staff to process the payment
        if is_staff:
            return redirect(url_for('process_payment', order_id=new_order.id))
       
        return render_template(
            'order_confirmation.html', 
            order_id=new_order.id, 
            staged_cart=staged_cart,
            grand_total=grand_total
            
        )
   
    # ============================================================================================================
    # IF THE DATA FAILED THE DATABASE TRANSACTION, REVERSE THE THE ORDER STATE (ROLLBACK) AND REDIREC TO VIEW_MENU
    # ============================================================================================================ 
    
    except SQLAlchemyError as e:
        # 1. Undo ALL Database changes so the session isn't corrupted
        db.session.rollback()
        # 2. Red-flag failure under the DATABASE category with full error traceback
        db_logger.critical(f"Order & inventory transaction failed: {e}", exc_info=True)

        # 3. Show a friendly message to the user (keep their cart intact!)
        flash("We couldn't process the order properly. Please try again.", "danger")
        print("The order did not process properly. Session rollback. The session cart is stil available")
        return redirect(url_for('view_menu'))


@app.route('/checkout/payment/<int:order_id>', methods=['GET', 'POST'])
@login_required
def process_payment(order_id):
    """ Process the payment for the current order in the session."""

    # SECURITY - USER AUTHENTICATION - must be logged in and have a role of 'employee' or 'manager'
    if current_user.role not in ['employee', 'manager']: abort(403)

    # Fetch staged_order and grand_total ONCE at the top so both GET and POST can use them
    staged_order = db.session.get(Order, order_id)

    # SECURITY: FAIL FAST and redirect if the order is not found in the Database
    if not staged_order:
        flash("No active order found. Please try again", "danger")
        print(f"No active order found for staged_order_id: {order_id}")
        return redirect(url_for('view_cart'))

    grand_total = round(staged_order.total_price, 2)

    if request.method == 'GET':
        # Bring the PayPal payment screen to the customer
        return render_template('order_payment.html', order_id=staged_order.id, grand_total=grand_total)
       
    if request.method == 'POST':

        try:
            # Update the payment status as PAID
            staged_order.payment_status = PaymentStatus.PAID
            db.session.commit()
            flash(f"🎉 Payment successful! Charged ${grand_total:.2f}. Order #{staged_order.id} sent to kitchen queue.", "success")
            return redirect(url_for('confirm_payment', order_id=staged_order.id))
        
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Payment Processing Failure: {str(e)}")
            flash("There was an issue with the payment. Please try again.", "danger")
            
            
            # Fetch a fresh version of staged_order after the db.session.rollback()
            staged_order = db.session.get(Order, order_id)

            # Update the database to put the order on_hold
            staged_order.payment_status = PaymentStatus.ON_HOLD
            staged_order.service_status = ServiceStatus.ON_HOLD
            db.session.commit()

            # Redirect to the PayPal order payment form
            return redirect(url_for('process_payment', order_id=staged_order.id))



def build_receipt_from_db(order_id):
    order_items = (
        OrderItem.query
        .filter_by(order_id=order_id)
        .order_by(OrderItem.smoothie_number.asc(), OrderItem.id.asc())
        .all()
    )

    grouped_items = {}

    for row in order_items:
        # Skip removed ingredients
        if not row.add_ingredient or row.ingredient_quantity <= 0:
            continue

        num = row.smoothie_number
        if num not in grouped_items:
            # Collect all add-on ingredient IDs linked to this smoothie
            addon_ids = {addon.ingredient_id for addon in row.smoothie.addon_items}

            grouped_items[num] = {
                'smoothie_number': num,
                'smoothie_name': row.smoothie.name,
                'smoothie_base_price': row.smoothie.base_price,
                'smoothie_price': row.smoothie_price,
                'recipe_ingredients': [],
                'sub_ingredients': [],
                'addon_ingredients': [],
                '_addon_ids': addon_ids
            }

        ing = row.ingredient

        # Populate addon_ingredients with name & cost so the template renders the breakdown
        if row.ingredient_id in grouped_items[num]['_addon_ids']:
            grouped_items[num]['addon_ingredients'].append({
                'name': ing.name,
                'cost': round((ing.cost or 0.0) * row.ingredient_quantity, 2)
            })
        else:
            grouped_items[num]['recipe_ingredients'].append({
                'name': ing.name
            })

    items = list(grouped_items.values())
    grand_total = round(sum(item['smoothie_price'] for item in items), 2)

    return items, grand_total



@app.route('/checkout/payment_confirmation/<int:order_id>', methods=['GET'])
@login_required
def confirm_payment(order_id):

    """ Issue a confirmation receipt."""

    # SECURITY: AUTHENTICATION
    if current_user.role not in ['employee', 'manager']: abort(403)

    # Clear the staged_cart as all the needed data has been saved in the Database
    session.pop('staged_cart', None)

    order = db.session.get(Order, order_id)
    if not order:
        flash("Order not found.", "danger")
        return redirect(url_for('view_pending_payment_orders'))

    items, grand_total = build_receipt_from_db(order_id)

    return render_template(
        'payment_confirmation.html',
        order_id=order_id,
        items=items,
        grand_total=grand_total
    )


@app.route('/checkout/service/<int:order_id>', methods=['GET', 'POST'])
@login_required
def serve_order(order_id):

    """Serve the order and update the order service_status from 'pending' to 'served' in the Database."""
   
    # Safety Check: Ensure only authorized staff can mark an order as served
    if current_user.role not in ['employee', 'manager']: abort(403)

    # staged_cart = session['staged_cart']

    # Fetch staged_order and grand_total ONCE at the top so both GET and POST can use them
    staged_order = db.session.get(Order, order_id)
    # SECURITY: FAIL FAST and redierct if the order is not found in the Database
    if not staged_order:
        flash("No active order found. Please try again", "danger")
        print(f"No active order found for staged_order_id: {staged_order.id}")
        return redirect(url_for('view_Cart'))

    # 1. Query the Line Items in SQLAlchemy
    stmt = (
        select(OrderItem)
        .where(OrderItem.order_id == order_id)
        .order_by(OrderItem.smoothie_number, OrderItem.id)
    )
    line_items = db.session.scalars(stmt).all()

    # for item in line_items: print(f"line_item: {item}")

    # 2. Group the Rows by smoothie_number to create a  Service Ticket
    ticket_smoothies = {}

    for item in line_items:
        number = item.smoothie_number
        
        # Create a group for this number if it hasn't been seen yet
        if number not in ticket_smoothies:
            ticket_smoothies[number] = {
                'smoothie_number': number,
                'smoothie_name': item.smoothie.name if item.smoothie else f"Smoothie #{item.smoothie_id}",
                'ingredients': []
            }
        
        # Append each ingredient row into that cup's list
        ticket_smoothies[number]['ingredients'].append({
            'ingredient_name': item.ingredient.name if item.ingredient else item.ingredient_id,
            'ingredient_quantity': int(item.ingredient_quantity) or 0,
            'add_ingredient': item.add_ingredient
        })

    if request.method == 'GET':

        # print(f"ticket_smoothies: {ticket_smoothies}")

        return render_template(
            'order_service_ticket.html',
            order_id=order_id, 
            ticket_smoothies=ticket_smoothies, # dict
            grand_total=staged_order.total_price)

    if request.method == 'POST':

        try:
            # Update the payment status as PAID
            staged_order.service_status = ServiceStatus.SERVED
            db.session.commit()
            flash(f"🎉 Service successful! Order #{staged_order.id} complete!", "success")

            return render_template(
                'service_confirmation.html',
                order_id=order_id, 
                ticket_smoothies=ticket_smoothies, # dict
                grand_total=staged_order.total_price)
        
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Service Processing Failure: {str(e)}")
            print(f"Service Processing Failure: {e}")
            flash("There was an issue serving theis order. Please try again.", "danger")
            
            # Fetch a fresh version of staged_order aftet the db.session.rollback()
            staged_order = db.session.get(Order, order_id)

            # Redirect to the PayPal order payment form
            return redirect(url_for('serve_order', order_id=order_id))
   

@app.route('/checkout/service_confirmation/<int:order_id>')
@login_required
def confirm_service(order_id):
    """ Confirm the smoothie order was served."""

    if current_user.role not in ['employee', 'manager']: abort(403)

    # staged_cart = session['staged_cart']

    # Fetch staged_order and grand_total ONCE at the top so both GET and POST can use them
    staged_order = db.session.get(Order, order_id)
    # SECURITY: FAIL FAST and redierct if the order is not found in the Database
    if not staged_order:
        flash("No active order found. Please try again", "danger")
        print(f"No active order found for staged_order_id: {staged_order.id}")
        return redirect(url_for('view_Cart'))

    served_items, grand_total = process_cart_items(staged_cart)

    # PURCHASE TRANSACTION COMPLETE!
    # Reset it back to a clean, empty list
    session['staged_cart'] = []
    session.modified = True  # Tells Flask to explicitly save the empty session state

    return render_template(
        'service_confirmation.html', 
        order_id=order_id, 
        grand_total=grand_total,
        items=served_items
    )
# ------------------------------------------------------------------------------------
# GET AND PROCESS TICKETS BY ORDER ID, accessing the DB tables: order and order_item
# ------------------------------------------------------------------------------------

@app.route('/orders/pending-payment', methods=['GET'])
@login_required
def view_pending_payment_orders():
    """ Shows all the orders that are waiting for Payment processing."""

    if current_user.role not in ['employee', 'manager']: abort(403)
    
    # Live database fetch for ticket that need payment
    pending_payment_orders= Order.query.filter_by(
        payment_status=PaymentStatus.PENDING, 
    ).all()

    return render_template ('pending_payment_orders.html', orders=pending_payment_orders)



@app.route('/orders/pending-service', methods=['GET'])
@login_required
def view_pending_service_orders():
  
    """ Shows all the orders that are waiting to be served."""

    if current_user.role not in ['employee', 'manager']: abort(403)
    
    # Find tickets that are paid but still need to be served by staff
    pending_service_orders = Order.query.filter_by(
        payment_status=PaymentStatus.PAID, 
        service_status=ServiceStatus.PENDING
    ).all()

    return render_template ('pending_service_orders.html', orders=pending_service_orders)


# @app.route('/orders/find-order/<int:order_id>', methods=['GET'])
# @login_required
# def find_order(order_id):
#     order = Order.query.get_or_404(order_id)
#     payment_status = order.payment_status
#     service_status = order.service_status

#     # 1. Generate the ticket dictionary for order id
#     ticket = generate_service_ticket(order_id)

#     # 2. Extract the items list
#     items_list = ticket['items']

#     # 3. Loop through each individual item dictionary
#     for item in items_list:
#         # Read the basic values using their dictionary keys
#         # qty = item['quantity']
#         smoothie_name = item['smoothie'].name
#         mods = item['modifications']
#         if mods:
#             print(f"modifications: {mods}")
#             for mod in mods:
#                 print(f"  -> MODIFICATION: {mod}")
#         else:
#             print("  -> (Standard Recipe (No Customizations)")
    
    # return render_template(
    #     'ticket_search_results.html', 
    #     order_id=order_id, 
    #     ticket_list=items_list
    # )



# ==========================================================================
# CART FUNCTIONS
# ==========================================================================

# REMOVE AN ITEM FROM CART
@app.route('/checkout/cart/remove/<int:item_index>', methods=['POST'])
def remove_from_cart(item_index):
    cart = session.get('cart', [])
    
    # Safely pop the item using its positional array index
    if 0 <= item_index < len(cart):
        removed_item = cart.pop(item_index)
        session['cart'] = cart
        session.modified = True
        flash("Item removed from the cart.", "info")
    
    return redirect(url_for('view_cart'))


@app.route('/checkout/clear_cart')
def clear_cart():

    session.clear()
    # session.pop('cart', None)   
    # session.pop('cart_grand_total', None)
    # flash("Your cart has been cleared.", "info")
    return redirect(url_for('view_menu'))  


@app.route('/inventory-dashboard', methods=['GET'])
@login_required
def display_inventory_dashboard():
    """ Authenticated users can acces the Inventory Dashboard to track ingredients stock."""
    
    # 1. Grab all items sorted alphabetically by name
    all_ingredients = Ingredient.query.order_by(Ingredient.name).all()
    
    # 2. Hand them off to the HTML template skin
    return render_template("inventory_dashboard.html", ingredients=all_ingredients)


@app.route('/admin/inventory/update', methods=['GET','POST'])
@login_required
def update_inventory():
    """
    Renders the inventory management layout.
    Pulls live ingredient records to display stock levels, reorder alerts, and usage.
    """
   
    # SECURITY: AUTHORIZATION REQUIRED - Defensive role check
    # Only managers can update the ingredients stock
    if current_user.role != 'manager':
        # abort(403)
        return "Access Denied: Managers Only", 403


    # Fetch all ingredients ordered cleanly by name from the DB
    ingredients = Ingredient.query.order_by(Ingredient.name.asc()).all()
  
    if request.method == 'POST':

        # initialize the lists
        invalid_current_stock_ings = []
        invalid_reorder_stock_ings = []
        invalid_minimum_stock_ings = []

        invalid_current_to_minimum_relationship_ings = []
        invalid_reorder_to_minimum_relationship_ings = []

        out_of_stock_ings = []
        low_in_stock_ings = []

       
        for ing in ingredients:

            # ==============================================================================
            # STEP 1: GATHER THE DATA SENT THROUGH THE FORM (inventory.html)
            # ==============================================================================

            # The form fields from inventory.html are:
            # name="current_stock_{{ ingredient.id }}" 
            # name="reorder_stock_{{ ingredient.id }}" 
            # name="minimum_stock_{{ ingredient.id }}" 

            # 1.Exclude the ingredients not tracked, like ice, no_sugar, etc.
            if ing.id in INVENTORY_EXCLUSIONS:
                continue

            # 2. Build the dynamic field keys matching these HTML 'name' attributes
            # name="current_stock_{{ ingredient.id }}" 
            current_stock_key = f"current_stock_{ing.id}"
            reorder_stock_key = f"reorder_stock_{ing.id}"
            minimum_stock_key = f"minimum_stock_{ing.id}"

            # 3. Read the (new) stock values from the HTML form inputs
            # SECURITY: INPUT VALIDATION AND TYPE CONVERSION
            # Added type=int to safely convert strings to numbers
            form_current_stock = request.form.get(current_stock_key, type=int)
            form_reorder_stock = request.form.get(reorder_stock_key, type=int)
            form_minimum_stock = request.form.get(minimum_stock_key, type=int)

            # 4. Print the values per ingredient
            print("--------------------------------------------------------")
            print(f"New form values for ingredient: {ing.name}")
            print(f"form_current_stock: {form_current_stock}")
            print(f"form_reorder_stock: {form_reorder_stock}")
            print(f"form_minimum_stock: {form_minimum_stock}")

            # ==============================================================================
            # STEP 3; INPUT VALIDATION and DEFENSIVE CODING to prevent crash and wrong data
            # ==============================================================================

            # ==========================================================================
            # SECURITY: INPUT VALIDATION: Only positive integer numbers are allowed
            # DATA INTEGRITY: BLCOK THE INVALID INPUT FIELDS IN THE SUBMITTED FORM 
            # =========================================================================
            
            # 1. REJECT EMPTY AND NON-NUMERIC INPUT FIELDS
            # Add the INVALID fields to the correspondent INVALID STOCK LIST
            # (The None or empty input fields get captrued and corrected in the html form front-end)
            # DEFENSIVE CODING: This is a FALLBACK check to prevent any NoneType from crashing the app

            # If an ingredient'sstock field has a 'None' value, add it to the list and move on to the next ingredient
            # SECURTIY: DEFENSIVE CODING to prevent crash due to NoneType ValueError
            if form_current_stock == None :
                invalid_current_stock_ings.append(ing.id)  
                print(f"{ing.name} is None or empty - Added to invalid_current_stock_ings list:{invalid_current_stock_ings}")  
                continue # exit the loop so the 'None' values would not crash on the steps that fllow.

            # Current_stock could be zero if the minimum_stock is zero
            if ( form_current_stock == 0  and form_current_stock != form_minimum_stock ): 
                invalid_current_stock_ings.append(ing.id)  
                print(f"{ing.name} is None or empty - Added to invalid_current_stock_ings list:{invalid_current_stock_ings}")  
                
            if form_reorder_stock == None :
                invalid_reorder_stock_ings.append(ing.id)  
                print(f"{ing.name} is None or empty - Added to invalid_reorder_stock_ings list:{invalid_reorder_stock_ings}")  
                continue

            # Decommissioned ingredieng reorder_stock can be zero if current_stock and minimim stock are zero too
            if form_reorder_stock == 0 and form_current_stock == 0 and form_minimum_stock == 0 :
                print(F"{ing.name} has been decommissioned! (form_reorder_stock=form_current_stock=fomr_minimum_stock=0)")
                continue

            if form_minimum_stock == None :
                invalid_minimum_stock_ings.append(ing.id)  
                print(f"{ing.name} is None or empty - Added to invalid_minimum_stock_ings list:{invalid_minimum_stock_ings}")  
                continue
        
            # 2. INTERCEPT INPUT FIELDS WITH NEGATIVE VALUES
            # (The INPUT from the html form is set to only accept 'positve numbers' and only 'digits 0-9')
            # DEFENSIVE CODING: The statements below are just FALLBACK checks.

            if form_current_stock < 0:       
                invalid_current_stock_ings.append(ing.id) 
                print(f"{ing.name} is negative! - Added to invalid_current_stock_ings list: {invalid_current_stock_ings}")
               
            if form_reorder_stock < 0: 
                invalid_new_reorder_stock_ings.append(ing.id) 
                print(f"{ing.name} is negative! - Added to invalid_reorder_stock_ings list: {invalid_reorder_stock_ings}")  
                
            if form_minimum_stock < 0:
                invalid_new_minimum_stock_ings.append(ing.id) 
                print(f"{ing.name} is negative! - Added to invalid_minimum_stock_ings list: {invalid_minimum_stock_ings}")
            

            # 3. ENFORCE STOCK RELATIONSHIP RULES
            # rule 1: current_stock should be above or at minimum_stock
            # rule 2: reorder_stock should be above minimum_stock
            if form_current_stock < form_minimum_stock: # rule 1
                invalid_current_to_minimum_relationship_ings.append(ing.id)
                print(f"{ing.name} added to invalid_curent_to_minimum_relationship_ings list: {invalid_current_to_minimum_relationship_ings}.")

            if form_reorder_stock <= form_minimum_stock:  # rule 2
                invalid_reorder_to_minimum_relationship_ings.append(ing.id)
                print(f"{ing.name} added to invalid_reorder_to_minimum_relationship_ings list: {invalid_reorder_to_minimum_relationship_ings}.")
            
            # ================================================================================
            # STEP 4: INVENTORY EVALUATION REPORT:  OUT OF STOCK AND LOW IN STOCK INGREDIENTS
            # ================================================================================

            if form_current_stock <= form_minimum_stock:
                out_of_stock_ings.append(ing.id)
                print(f"out_of_stock_ings: {out_of_stock_ings}")

            if form_current_stock <= form_reorder_stock:
                low_in_stock_ings.append(ing.id)
                print(f"low_in_stock_ings: {low_in_stock_ings}")

            # ======================================================================================
            # STEP 5: STORE THE FORM DATA INTO THEIR ORIGINAL STOCK FIELDS (DB NOT MODIFIED YET)
            # ======================================================================================

            # Temporarilty save the form updates (both valid and invalid stock fields)
            # NOT SEVING TO THE DATABASE YET - ONLY VALID INPUTS WILL BE SAVE (IF CORRECTED)
            ing.current_stock = form_current_stock
            ing.reorder_stock = form_reorder_stock
            ing.minimum_stock = form_minimum_stock

        # ---------------------------------- END OF FOR LOOP -----------------------------------
       
        # ====================================================================================
        # STEP 6: IF VALIDATION FAILED, SEND MESSAGES ABOUT INVALID FORM FIELDS VALUES
        # ===================================================================================
        
        # 1. No 'None', negative or Inventory Integrity violations
        if ( None in (invalid_current_stock_ings, invalid_reorder_stock_ings, invalid_minimum_stock_ings) or
            invalid_current_stock_ings or  # the list is not empty
            invalid_reorder_stock_ings or  # the list is not empty
            invalid_minimum_stock_ings or  # the list is not empty
            invalid_current_to_minimum_relationship_ings or
            invalid_reorder_to_minimum_relationship_ings ):
          
            print(" ========================================================================================== ")
            print("INVENTORY UPDATE HAS ABORTED! BECAUSE IT FAILED INPUT VALIDATION. Please re-submit fhe form.")
            flash("INVENTORY UPDATE HAS ABORTED! Please review the following messages: ", "danger")

            if None in (invalid_current_stock_ings, invalid_reorder_stock_ings, invalid_minimum_stock_ings): 
                flash("ALL stock fields must be filled out. NO EMPTY FIELDS ALLOWED!", "danger")

            if invalid_current_stock_ings:
                flash(f"Invalid CURRENT stock field for {invalid_current_stock_ings}.", "warning")
            if invalid_reorder_stock_ings:
                flash(f"Invalid REORDER stock field for {invalid_reorder_stock_ings}.", "warning")
            if invalid_minimum_stock_ings:
                flash(f"Invalid MINIMUM stock field for {invalid_minimum_stock_ings}.", "warning")

            if invalid_current_to_minimum_relationship_ings:
                flash(f"Invalid stock relationship: CURRENT stock MUST BE ABOVE or at MINIMUM STOCK \
                    for {invalid_current_to_minimum_relationship_ings}.", "warning")
            if invalid_reorder_to_minimum_relationship_ings:
                flash(f"Invalid stock relationship: REORDER stock MUST BE ABOVE or at MINIMUM stock \
                    for {invalid_reorder_to_minimum_relationship_ings}.", "warning")


            # ============================================================================================
            # STEP 7: RENDER THE TEMPLATE AGAIN, WITH THE ERROR MESSAGES ALONG THE SUBMITTED DATA
            # ============================================================================================

            return render_template(
                'inventory.html', 
                ingredients=ingredients, 
                invalid_current_stock_list=invalid_current_stock_ings,
                invalid_reorder_stock_list=invalid_reorder_stock_ings,
                invalid_minimum_stock_list=invalid_minimum_stock_ings,
                invalid_current_to_minimum_relationship_list=invalid_current_to_minimum_relationship_ings,
                invalid_reorder_to_minimum_relationship_list=invalid_reorder_to_minimum_relationship_ings,
                stock_exclusions=INVENTORY_EXCLUSIONS
            )
    
        else:

            # ============================================================================#
            #              SUCCESS!    THE INVENTORY VALIDATION PASSED!                   #
            #=============================================================================#
            
            # ================================================================================
            # STEP 8: REPORT OUT OF STOCK AND LOW IN STOCK INGREDIENTS OF VALIDATED INVENTORY
            # ================================================================================
            print(" ================== INVENTORY EVALUATION REPORT ===================")
         
            if not out_of_stock_ings:
                print("Good news! There are NO OUT OF STOCK INGREDIENTS.")
                flash("Good news! There are NO OUT OF STOCK INGREDIENTS.", "sucess")
            else: 
                print(f"There are {len(out_of_stock_ings)} OUT OF STOCK INGREDIENTS: {out_of_stock_ings}")
                flash(f"There are {len(out_of_stock_ings)} OUT OF STOCK INGREDIENTS: {out_of_stock_ings}", "info")

            if not low_in_stock_ings:
                print("Good news! There are NO LOW IN STOCK INGREDIENTS.")
                flash("Good news! There are NO LOW IN STOCK INGREDIENTS.", "success")
            else:
                # Eemove the low stock items already listed as out of stock
                for low_stock_ing in low_in_stock_ings:
                    if low_stock_ing in out_of_stock_ings:
                        low_in_stock_ings.remove(low_stock_ing)
                print(f"There are {len(low_in_stock_ings)} LOW IN STOCK INGREDIENTS: {low_in_stock_ings}")
                flash(f"There are {len(low_in_stock_ings)} LOW IN STOCK INGREDIENTS: {low_in_stock_ings}", "info")

        # ================================================================================
        # STEP 9: SAVE THE NEW UPDATED AND VALIDATED INVENTORY DATA TO THE DATABASE
        # ================================================================================
                    
        try:

            db.session.commit()

            flash("THE NEW INVENTORY DATA HAS BEEN UPDATED AND SAVED TO THE DATABSE.", "success")
            print("\nTHE NEW INVENTORY DATA HAS BEEN UPDATED AND SAVED TO THE DATABASE")

            # Redirect to display the updated inventory-dashboard.html
            return redirect(url_for('display_inventory_dashboard')) 

        except Exception as e:
            # ================================================================================
            # STEP 9 ALTERNATIVE: iF THE DATABSE TRANSACTION FAILED, ROLLBACK THE TRANSACTION
            #=================================================================================
            
            # 1. SECURITY BEST PRACTICE: Roll back the broken transaction immediately
            db.session.rollback()
            
            # 2. Log the error onto the screen to facilitate debugging
            print(f"DATABASE ERROR: {str(e)}") 
            
            flash("A Database error occurred while saving the updated Inventory. Please try again.", "danger")
            return redirect(url_for('update_inventory')) 
           
                
    # ----------------------------------------- GET METHOD ------------------------------------------ #
    
    # ===============================================================================================
    # STEP 1: RETRIEVE ANY INVALID ERROR LIST IF AVAILABLE (from the current session[])
    # ===============================================================================================

    # Pull the INVALID INGREDIENT IDs LISTS out of the session (defaults to empty list if none exist)

    return render_template(
        'inventory.html', 
        ingredients=ingredients, 
        invalid_current_stock_list= [],
        invalid_reorder_stock_list= [],
        invalid_minimum_stock_list= [],
        invalid_current_to_minimum_relationship_list= [],
        invalid_reorder_to_minimum_relationship_list= [],
        stock_exclusions=INVENTORY_EXCLUSIONS
    )
    

# # MANAGER OVERRIDE
# @app.route('/checkout/manager-override', methods=['POST'])
# @login_required
# def manager_override():
#     """Allows an authenticated manager to temporarily set an override flag in the session."""
#     # 1. Role Check: Only let verified managers execute this action
#     if current_user.role != 'manager':
#         flash("Unauthorized. Only managers can authorize overrides.", "danger")
#         return redirect(url_for('view_cart'))
    
#     # 2. Set the temporary override key in the top-level session dictionary
#     session['manager_override'] = True
#     session.modified = True
    
#     flash("Manager override activated for this transaction.", "warning")
#     return redirect(url_for('view_cart'))

# @app.errorhandler(403)
# def forbidden_error(error):
#     # Returns a beautiful, styled page instead of a blank white screen
#     return render_template('errors/403.html'), 403


@app.route("/logout")
@login_required
def logout():
    """Logs out the active employee and returns to the public home menu."""

    # Clear the cart    
    cart = session.get('cart', [])
    if  cart:
       session.cart = []

    logout_user()
    return redirect(url_for('home'))


@app.route('/admin/force-logout-all', methods=['POST'])
@login_required
def force_logout_all_users():
    """Administrative override route to clear active user sessions globally."""
    # Strict role check: Only managers or admins should be allowed to trigger this
    if current_user.role not in ['manager', 'admin']:
        abort(403)
        
    # 1. Log out the current administrator invoking the command cleanly
    logout_user()
    
    # 2. Drop all keys from the session container (wipes cookies across all connected clients)
    session.clear()
    
    # 3. Force the flag indicating the session dictionary was explicitly mutated
    session.modified = True
    
    flash("Global administrative reset triggered. All active user sessions have been terminated.", "warning")
    return redirect(url_for('login')) # Send them back to the login gateway page


@app.route('/admin/clear-all-sessions')
def clear_all_sessions():
    session.clear()
    return "All sessions cleared. Please log back in."


if __name__ == '__main__':
   
    # check and log the status of the API key SECURELY BEFORE starting the server loop
    if not API_KEY or API_KEY == "MOCK_DEV_KEY_123":
        print("DEVELOPMENT MODE Warning: Running with mock API key placeholder.")
        # Use .warning() instead of .info("WARNING: ...") so the severity column says WARNING
        auth_logger.warning("Application started in development mode using a placeholder API key.")
    else:
        auth_logger.info("Production API key detected and validated successfully.")

    # Controlled, guarded single-instance server execution
    try:
        sys_logger.info("Initializing application server system schema...")  
        # 'use_reloader=False' ensures secrets.token_hex(32) stays persistent during active runtime sessions
        app.run(debug=DEBUG_MODE, port=5000, use_reloader=False)
    except Exception as e:
        sys_logger.critical(f"Application server failed to bind or start: {e}", exc_info=True)


  