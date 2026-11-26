
# seed_db.py
from extensions import db
from models import (
    PaymentStatus, ServiceStatus, Supplier, Ingredient,
    Smoothie, SmoothieRecipeItem, SmoothieSubItem, SmoothieAddonItem, 
    User, Order, OrderItem
)

def seed_initial_data(app):
    """Populates the database with initial workstation data if empty."""
    with app.app_context():

        # IMPORTANT: COMMENT OUT THIS BLOCK TO PREVENT OVEWRITTING THE DATA
        # FORCE RESET THE DATABASE ON STARTUP
        # Clear previous table structures to prevent migration errors
        # =========================================================================
        # print("🧹 Cleaning out old tables to start with a fresh slate...")
        # db.drop_all()
        # db.create_all()
        # print("✅ Database tables successfully generated.")

        # ==========================================================================
        # 1. MASTER INVENTORY / SUPPLY REGISTER
        # ==========================================================================

        # SECURITY: DATA INTEGRITY - Check whether the Supplier table is completely empty
        if Supplier.query.first() is None:
          
            print("🌱 Seeding a clean Supplier record...")

            # --- SUPPLIER LIST ---
            oasis_supply = Supplier(name="Oasis Fresh Distribution", email="supply@oasis.com", phone="555-0199")
            fruit_garden = Supplier(name="Fruit Garden Suppliers", email="customer_support@fruitgarden.com", phone="888-314-4818")
            farmers_group = Supplier(name="Farmers Group", email="customer_support@farmers.com", phone="313-288-4758")
            healthy_options = Supplier(name="Healthy Options", email="customer_support@healthyoptions.com", phone="917-222-9596")
        
            suppliers_list = [ oasis_supply, fruit_garden, farmers_group, healthy_options]
            db.session.add_all(suppliers_list)
            db.session.flush()

            print("The Supplier table has been successfully seeded!")

        else:
            print("The Supplier table has already been populated. Skipping seeding loop.")


        # ================================================================================= #

        # SECURITY: DATA INTEGRITY - Check whether the supplier table is completely empty
        if Ingredient.query.first() is None:

            print("🌱 Seeding the Ingredient table...")
            
            # --- INVENTORY STOCK Declarations ---  

            ingredients_list = [

                Ingredient(id='milk', name="Milk", portion=8, unit_type="fl oz", cost=0.5, current_stock=70, reorder_stock=20, minimum_stock=3, supplier_id=oasis_supply.id),
                Ingredient(id='soy_milk', name="Soy Milk", portion=8, unit_type="fl oz", cost=1.0, current_stock=56, reorder_stock=8, minimum_stock=3, supplier_id=fruit_garden.id),            
                Ingredient(id='frozen_yogurt', name="Frozen Yogurt", portion=8, unit_type="fl oz", cost=1.0, current_stock=150, reorder_stock=20, minimum_stock=5, supplier_id=healthy_options.id),
                Ingredient(id='strawberries', name="Strawberries", portion=80, unit_type="grams", cost=1.0, current_stock=30, reorder_stock=10, minimum_stock=1, supplier_id=fruit_garden.id),
                Ingredient(id='blueberries', name="Blueberries", portion=80, unit_type="grams", cost=0.5, current_stock=50, reorder_stock=20, minimum_stock=2, supplier_id=fruit_garden.id),
                Ingredient(id='acai_berries', name="Acai Berries", portion=40, unit_type="grams", cost=1.0, current_stock=30, reorder_stock=10, minimum_stock=2, supplier_id=fruit_garden.id),
                Ingredient(id='banana', name="Banana", portion=1, unit_type="unit", cost=0.50, current_stock=50, reorder_stock=10, minimum_stock=2, supplier_id=fruit_garden.id),
                Ingredient(id='mango', name="Mango", portion=1, unit_type="unit", cost=1.0, current_stock=30, reorder_stock=10, minimum_stock=2, supplier_id=farmers_group.id),
                Ingredient(id='pineapple', name="Pineapple", portion=1, unit_type="scoop", cost=1.0, current_stock=30, reorder_stock=10, minimum_stock=2, supplier_id=healthy_options.id),
                Ingredient(id='whey_protein', name="Whey Protein", portion=1, unit_type="can", cost=1.0, current_stock=100, reorder_stock=10, minimum_stock=2, supplier_id=healthy_options.id),
                Ingredient(id='coconut_milk', name="Coconut Milk", portion=4, unit_type="fl oz", cost=1.5, current_stock=30, reorder_stock=10, minimum_stock=2, supplier_id=healthy_options.id),
                Ingredient(id='iced_coffee', name="Iced Coffee", portion=8, unit_type="fl oz", cost=0.5, current_stock=80, reorder_stock=20, minimum_stock=10, supplier_id=healthy_options.id),
                Ingredient(id='espresso_shot', name="Espresso Shot", portion=1, unit_type="fl oz", cost=0.5, current_stock=60, reorder_stock=10, minimum_stock=2, supplier_id=healthy_options.id),
                Ingredient(id='coffee_creamer', name="Coffee Creamer", portion=1, unit_type="can", cost=0.6, current_stock=80, reorder_stock=10, minimum_stock=2, supplier_id=healthy_options.id),
                Ingredient(id='chocolate_flavor', name="Chocolate Flavor", portion=2, unit_type="fl oz", cost=0.5, current_stock=70, reorder_stock=20, minimum_stock=5, supplier_id=oasis_supply.id),
                Ingredient(id='vanilla_flavor', name="Vanilla Flavor", portion=2, unit_type="fl oz", cost=0.5, current_stock=70, reorder_stock=20, minimum_stock=5, supplier_id=oasis_supply.id),
                Ingredient(id='strawberry_flavor', name="Strawberry Flavor", portion=2, unit_type="fl oz", cost=0.5, current_stock=70, reorder_stock=20, minimum_stock=5, supplier_id=oasis_supply.id), 
                Ingredient(id='choco_chips', name="Choco Chips", portion=4, unit_type="grams", cost=0.5, current_stock=40, reorder_stock=10, minimum_stock=4, supplier_id=oasis_supply.id),
                Ingredient(id='crunchy_caramel', name="Crunchy Caramel", portion=4, unit_type="grams", cost=1.0, current_stock=50, reorder_stock=20, minimum_stock=5, supplier_id=oasis_supply.id),
                Ingredient(id='crunchy_oats', name="Crunchy Oats", portion=4, unit_type="grams", cost=0.6, current_stock=44, reorder_stock=20, minimum_stock=5, supplier_id=oasis_supply.id),
                Ingredient(id='coconut_flakes', name="Coconut Flakes", portion=2, unit_type="grams", cost=0.5, current_stock=44, reorder_stock=20, minimum_stock=5, supplier_id=oasis_supply.id),
                Ingredient(id='whipped_cream', name="Whipped Cream", portion=3, unit_type="fl oz", cost=0.5, current_stock=70, reorder_stock=20, minimum_stock=5, supplier_id=oasis_supply.id),
                Ingredient(id='caramel_topping', name="Caramel Topping", portion=2, unit_type="fl oz", cost=0.5, current_stock=50, reorder_stock=20, minimum_stock=5, supplier_id=oasis_supply.id),
                Ingredient(id='chocolate_topping', name="Chocolate Topping", portion=2, unit_type="fl oz", cost=0.5, current_stock=50, reorder_stock=20, minimum_stock=5, supplier_id=oasis_supply.id),
                Ingredient(id='strawberry_topping', name="Strawberry Topping", portion=2, unit_type="fl oz", cost=0.5, current_stock=50, reorder_stock=20, minimum_stock=5, supplier_id=oasis_supply.id),
                Ingredient(id='cinammon', name="Cinammon", portion=1, unit_type="grams", cost=0.2, current_stock=40, reorder_stock=10, minimum_stock=5, supplier_id=oasis_supply.id),
                Ingredient(id='sugar', name="Sugar", portion=2, unit_type="teaspoons", cost=0.2, current_stock=130, reorder_stock=30, minimum_stock=10, supplier_id=oasis_supply.id),
                Ingredient(id='no_sugar', name="No Sugar", portion=2, unit_type="teaspoons", cost=0.0, current_stock=100, reorder_stock=10, minimum_stock=1),
                Ingredient(id='splenda', name="Splenda", portion=2, unit_type="mg", cost=0.0, current_stock=200, reorder_stock=50, minimum_stock=20, supplier_id=oasis_supply.id),
                Ingredient(id='crushed_ice',name="Crushed Ice", portion=0, unit_type="fl oz", cost=0.0, current_stock=100, reorder_stock=10, minimum_stock=1),
                Ingredient(id='light_ice', name="LIght Ice", portion=0, unit_type="fl oz", cost=0.0, current_stock=100, reorder_stock=10, minimum_stock=1),
                Ingredient(id='no_ice', name="No Ice", portion=0, unit_type="fl oz", cost=0.0, current_stock=100, reorder_stock=10, minimum_stock=1),

            ]

            # DEFENSIVE SORTING: Order by your custom text ID keys alphabetically
            ingredients_list.sort(key=lambda ing: ing.id.lower())
            db.session.add_all(ingredients_list)
            db.session.flush()  # Syncs strings directly into current session memory
            print("✅ Alphabetized master inventory registry loaded.")

            print("The Ingredient table has been successfully seeded!")

        else:

            print("The Ingredient table has already been populated. Skipping seeding loop.")
            

        # =======================================================================
        # 3. BASE SMOOTHIE CORE DEFINITIONS
        # =======================================================================

        # --- SMOOTHIE NAME: "Very Berry" ---

        # SECURITY: DATA INTEGRITY: Check specifically if the 'Very Berry' smoothie already exists in your table records
        very_berry_exists = Smoothie.query.filter_by(name="Very Berry").first()

        if not very_berry_exists:

            print("🍹 'Seeding daata for 'Very Berry' Smoothie and building contextual relationships...")
           
            very_berry = Smoothie(
                name="Very Berry", 
                slogan="Very Berry... Legendary!", 
                profit_margin=2.00
            )
            db.session.add(very_berry)
            # flush() Resolves very_berry.id instantly for child foreign keys
            db.session.flush()  

            # ===============================================================================
            # 4. SECTION 1 SEEDING: STANDARD CORE RECIPE ITEMS
            # Flat list entries that represent what is included in the base_price.
            # ===============================================================================
            
            db.session.add_all([
                SmoothieRecipeItem(smoothie_id=very_berry.id, ingredient_id='strawberries', ingredient_quantity=2),
                SmoothieRecipeItem(smoothie_id=very_berry.id, ingredient_id='blueberries', ingredient_quantity=1),
                SmoothieRecipeItem(smoothie_id=very_berry.id, ingredient_id='acai_berries', ingredient_quantity=1),
                SmoothieRecipeItem(smoothie_id=very_berry.id, ingredient_id='whipped_cream', ingredient_quantity=1),
                
            ])
            print("✅ Section 1 (Static Base Recipes) mapped cleanly.")

            # =======================================================================
            # 5. SECTION 2 SEEDING: SUBSTITUTION RADIO OPTIONS
            # Every option alternative gets its own dedicated row line.
            # Linked by a group_name text label (like 'base' or 'topping').
            # =======================================================================
            
            db.session.add_all([
                # Group 'starter' Radio Choices
                SmoothieSubItem(smoothie_id=very_berry.id, group_name='starter', ingredient_id='frozen_yogurt', is_default=True),
                SmoothieSubItem(smoothie_id=very_berry.id, group_name='starter', ingredient_id='milk', is_default=False),
                SmoothieSubItem(smoothie_id=very_berry.id, group_name='starter', ingredient_id='soy_milk', is_default=False),

                # Group 'flavor' Radio Choices
                SmoothieSubItem(smoothie_id=very_berry.id, group_name='flavor', ingredient_id='strawberry_flavor', is_default=True),
                SmoothieSubItem(smoothie_id=very_berry.id, group_name='flavor', ingredient_id='vanilla_flavor', is_default=False),
                SmoothieSubItem(smoothie_id=very_berry.id, group_name='flavor', ingredient_id='chocolate_flavor', is_default=False),

                # Group 'topping' Radio Choices
                SmoothieSubItem(smoothie_id=very_berry.id, group_name='topping', ingredient_id='crunchy_oats', is_default=True),
                SmoothieSubItem(smoothie_id=very_berry.id, group_name='topping', ingredient_id='crunchy_caramel', is_default=False),
                SmoothieSubItem(smoothie_id=very_berry.id, group_name='topping', ingredient_id='choco_chips', is_default=False),

                # Group 'sweetener' Radio Choices
                SmoothieSubItem(smoothie_id=very_berry.id, group_name='sweetener', ingredient_id='sugar', is_default=True),
                SmoothieSubItem(smoothie_id=very_berry.id, group_name='sweetener', ingredient_id='splenda', is_default=False),
                SmoothieSubItem(smoothie_id=very_berry.id, group_name='sweetener', ingredient_id='no_sugar', is_default=False),
            
                # Group 'ice' Radio Choices
                SmoothieSubItem(smoothie_id=very_berry.id, group_name='ice', ingredient_id='crushed_ice', is_default=True),
                SmoothieSubItem(smoothie_id=very_berry.id, group_name='ice', ingredient_id='light_ice', is_default=False),
                SmoothieSubItem(smoothie_id=very_berry.id, group_name='ice', ingredient_id='no_ice', is_default=False),
            ])

            print("✅ Section 2 (Line Substitution Rows) mapped cleanly.")

            # =======================================================================
            # 6. SECTION 3 SEEDING: PREMIUM UPGRADES & ADD-ONS
            # Every addon gets its own clean row line.
            # Quantity maps behind the scenes to default 1 automatically.
            # =======================================================================
            
            db.session.add_all([
                SmoothieAddonItem(smoothie_id=very_berry.id, ingredient_id='banana'),
                SmoothieAddonItem(smoothie_id=very_berry.id, ingredient_id='whey_protein'),
                SmoothieAddonItem(smoothie_id=very_berry.id, ingredient_id='espresso_shot'),
                SmoothieAddonItem(smoothie_id=very_berry.id, ingredient_id='coconut_flakes'),

            ])
            print("✅ Section 3 (Future-Proof Premium Addons) mapped cleanly.")

            # ============================================================================
            # 7. AUTOMATED PRICING MOTOR COMMIT
            # Calls your dynamic engine to run calculations before final database save
            # ============================================================================
            very_berry.calculate_and_save_price()
            print(f"✅ Seeding Complete! '{very_berry.name}' retail price calculated at: ${very_berry.base_price}")
            
            db.session.commit()

            print("🎉 The 'Very Berry' Smoothie tables have been successfully updated!")

        else:

            print("The 'Very Berry' Smoothie tables have already been populated. Skipping seeding loop.")


        # --- SMOOTHIE NAME: "Berry Banny" ---
        berry_banny_exists = Smoothie.query.filter_by(name="Berry Banny").first()

        if not berry_banny_exists:
            print("🍹 Seeding data for 'Berry Banny' Smoothie...")
            berry_banny = Smoothie(
                name="Berry Banny", 
                slogan="It's Uncanny!", 
                profit_margin=1.50
            )
            db.session.add(berry_banny)
            db.session.flush()  

            # Section 1 Setup
            db.session.add_all([
                SmoothieRecipeItem(smoothie_id=berry_banny.id, ingredient_id='strawberries', ingredient_quantity=1),
                SmoothieRecipeItem(smoothie_id=berry_banny.id, ingredient_id='banana', ingredient_quantity=2),
                SmoothieRecipeItem(smoothie_id=berry_banny.id, ingredient_id='whipped_cream', ingredient_quantity=1),
            ])

            # Section 2 Setup (Reuses your existing master substitution row records!)
            db.session.add_all([

                # Group 'starter' Radio Choices
                SmoothieSubItem(smoothie_id=berry_banny.id, group_name='starter', ingredient_id='frozen_yogurt', is_default=True),
                SmoothieSubItem(smoothie_id=berry_banny.id, group_name='starter', ingredient_id='milk', is_default=False),
                SmoothieSubItem(smoothie_id=berry_banny.id, group_name='starter', ingredient_id='soy_milk', is_default=False),
                
                # Group 'flavor' Radio Choices
                SmoothieSubItem(smoothie_id=berry_banny.id, group_name='flavor', ingredient_id='strawberry_flavor', is_default=True),
                SmoothieSubItem(smoothie_id=berry_banny.id, group_name='flavor', ingredient_id='vanilla_flavor', is_default=False),
                SmoothieSubItem(smoothie_id=berry_banny.id, group_name='flavor', ingredient_id='chocolate_flavor', is_default=False),

                # Group 'topping' Radio Choices
                SmoothieSubItem(smoothie_id=berry_banny.id, group_name='topping', ingredient_id='crunchy_oats', is_default=True),
                SmoothieSubItem(smoothie_id=berry_banny.id, group_name='topping', ingredient_id='crunchy_caramel', is_default=False),
                SmoothieSubItem(smoothie_id=berry_banny.id, group_name='topping', ingredient_id='choco_chips', is_default=False),

                # Group 'sweetener' Radio Choices
                SmoothieSubItem(smoothie_id=berry_banny.id, group_name='sweetener', ingredient_id='sugar', is_default=True),
                SmoothieSubItem(smoothie_id=berry_banny.id, group_name='sweetener', ingredient_id='splenda', is_default=False),
                SmoothieSubItem(smoothie_id=berry_banny.id, group_name='sweetener', ingredient_id='no_sugar', is_default=False),
                
                # Group 'ice' Radio Choices
                SmoothieSubItem(smoothie_id=berry_banny.id, group_name='ice', ingredient_id='crushed_ice', is_default=True),
                SmoothieSubItem(smoothie_id=berry_banny.id, group_name='ice', ingredient_id='light_ice', is_default=False),
                SmoothieSubItem(smoothie_id=berry_banny.id, group_name='ice', ingredient_id='no_ice', is_default=False),
            ])

            # Section 3 Setup
            db.session.add_all([
                SmoothieAddonItem(smoothie_id=berry_banny.id, ingredient_id='blueberries'),
                SmoothieAddonItem(smoothie_id=berry_banny.id, ingredient_id='whey_protein'),
                SmoothieAddonItem(smoothie_id=berry_banny.id, ingredient_id='coconut_flakes'),
            ])

            # Fire calculation calculation routines
            berry_banny.calculate_and_save_price()
            print(f"✅ Seeding Complete! '{berry_banny.name}' retail price calculated at: ${berry_banny.base_price}")
            db.session.commit()

            print("🎉 The 'Berry Banny' Smoothie tables have been successfully initialized!")

        else:

            print("The 'Berry Banny' Smoothie tables have already been populated. Skipping seeding loop.")

        
        # SECURITY: DATA INTEGRITY - Check whether the user table is completely empty
        if User.query.filter_by(username='manager1').first() is None: 

            print("🌱 Seeding a user table with secure staff profiles...")
            
            # 1. Instantiate the manager account profiles
            admin1 = User(username='manager1', role='manager')
            admin2 = User(username='manager2', role='manager')

            # The User class runs generate_password_hash internally on this text string!
            admin1.set_password('admin123')  # Automatically gets converted to a secure hash
            admin2.set_password('admin456')

            # Wrapped multi-object additions into an array list using add_all()
            db.session.add_all([admin1, admin2])

            # 2. Instantiate the standard staff profiles
            staff1 = User(username='employee1', role='employee')
            staff2 = User(username='employee2', role='employee')

            # Automatically hashes passwords safely into the database file
            staff1.set_password('user123')
            staff2.set_password('user456')
            
            # FIX: Wrapped multi-object additions into an array list using add_all()
            db.session.add_all([staff1, staff2])
            
            db.session.commit()
            
            print("✅ Default employee profiles seeded securely into tracking tables!")

        else:
            print("User table already populated. Skipping seeding loop.")


        # --- SMOOTHIE NAME: "Mango Tango" ---
        mango_tango_exists = Smoothie.query.filter_by(name="Mango Tango").first()

        if not mango_tango_exists:
            print("🍹 Seeding data for 'Mango Tango' Smoothie...")
            mango_tango = Smoothie(
                name="Mango Tango",
                slogan="Tropical Rhythm in Every Sip!",
                profit_margin=2.00
            )
            db.session.add(mango_tango)
            db.session.flush()

            # Section 1: Standard Core Recipe Items
            db.session.add_all([
                SmoothieRecipeItem(smoothie_id=mango_tango.id, ingredient_id='mango', ingredient_quantity=2),
                SmoothieRecipeItem(smoothie_id=mango_tango.id, ingredient_id='pineapple', ingredient_quantity=1),
                SmoothieRecipeItem(smoothie_id=mango_tango.id, ingredient_id='banana', ingredient_quantity=1),
                SmoothieRecipeItem(smoothie_id=mango_tango.id, ingredient_id='whipped_cream', ingredient_quantity=1),
            ])

            # Section 2: Substitution Radio Options
            db.session.add_all([
                # Group 'starter' Radio Choices
                SmoothieSubItem(smoothie_id=mango_tango.id, group_name='starter', ingredient_id='frozen_yogurt', is_default=True),
                SmoothieSubItem(smoothie_id=mango_tango.id, group_name='starter', ingredient_id='coconut_milk', is_default=False),
                SmoothieSubItem(smoothie_id=mango_tango.id, group_name='starter', ingredient_id='soy_milk', is_default=False),

                # Group 'flavor' Radio Choices
                SmoothieSubItem(smoothie_id=mango_tango.id, group_name='flavor', ingredient_id='vanilla_flavor', is_default=True),
                SmoothieSubItem(smoothie_id=mango_tango.id, group_name='flavor', ingredient_id='strawberry_flavor', is_default=False),
                SmoothieSubItem(smoothie_id=mango_tango.id, group_name='flavor', ingredient_id='chocolate_flavor', is_default=False),

                # Group 'topping' Radio Choices
                SmoothieSubItem(smoothie_id=mango_tango.id, group_name='topping', ingredient_id='coconut_flakes', is_default=True),
                SmoothieSubItem(smoothie_id=mango_tango.id, group_name='topping', ingredient_id='crunchy_oats', is_default=False),
                SmoothieSubItem(smoothie_id=mango_tango.id, group_name='topping', ingredient_id='crunchy_caramel', is_default=False),

                # Group 'sweetener' Radio Choices
                SmoothieSubItem(smoothie_id=mango_tango.id, group_name='sweetener', ingredient_id='sugar', is_default=True),
                SmoothieSubItem(smoothie_id=mango_tango.id, group_name='sweetener', ingredient_id='splenda', is_default=False),
                SmoothieSubItem(smoothie_id=mango_tango.id, group_name='sweetener', ingredient_id='no_sugar', is_default=False),

                # Group 'ice' Radio Choices
                SmoothieSubItem(smoothie_id=mango_tango.id, group_name='ice', ingredient_id='crushed_ice', is_default=True),
                SmoothieSubItem(smoothie_id=mango_tango.id, group_name='ice', ingredient_id='light_ice', is_default=False),
                SmoothieSubItem(smoothie_id=mango_tango.id, group_name='ice', ingredient_id='no_ice', is_default=False),
            ])

            # Section 3: Premium Add-ons
            db.session.add_all([
                SmoothieAddonItem(smoothie_id=mango_tango.id, ingredient_id='strawberries'),
                SmoothieAddonItem(smoothie_id=mango_tango.id, ingredient_id='whey_protein'),
                SmoothieAddonItem(smoothie_id=mango_tango.id, ingredient_id='acai_berries'),
            ])

            mango_tango.calculate_and_save_price()
            print(f"✅ Seeding Complete! '{mango_tango.name}' retail price calculated at: ${mango_tango.base_price}")
            
            db.session.commit()
            
            print("🎉 The 'Mango Tango' Smoothie tables have been successfully initialized!")

        else:
            print("The 'Mango Tango' Smoothie tables have already been populated. Skipping seeding loop.")


        # --- SMOOTHIE NAME: "Choco Loco" ---
        choco_loco_exists = Smoothie.query.filter_by(name="Choco Loco").first()

        if not choco_loco_exists:
            print("🍹 Seeding data for 'Choco Loco' Smoothie...")
            choco_loco = Smoothie(
                name="Choco Loco",
                slogan="Pure Chocolate Madness!",
                profit_margin=2.25
            )
            db.session.add(choco_loco)
            db.session.flush()

            # Section 1: Standard Core Recipe Items
            db.session.add_all([
                SmoothieRecipeItem(smoothie_id=choco_loco.id, ingredient_id='banana', ingredient_quantity=1),
                SmoothieRecipeItem(smoothie_id=choco_loco.id, ingredient_id='chocolate_topping', ingredient_quantity=1),
                SmoothieRecipeItem(smoothie_id=choco_loco.id, ingredient_id='choco_chips', ingredient_quantity=1),
                SmoothieRecipeItem(smoothie_id=choco_loco.id, ingredient_id='whipped_cream', ingredient_quantity=1),
            ])

            # Section 2: Substitution Radio Options
            db.session.add_all([

                # Group 'starter' Radio Choices
                SmoothieSubItem(smoothie_id=choco_loco.id, group_name='starter', ingredient_id='milk', is_default=True),
                SmoothieSubItem(smoothie_id=choco_loco.id, group_name='starter', ingredient_id='frozen_yogurt', is_default=False),
                SmoothieSubItem(smoothie_id=choco_loco.id, group_name='starter', ingredient_id='soy_milk', is_default=False),

                # Group 'flavor' Radio Choices
                SmoothieSubItem(smoothie_id=choco_loco.id, group_name='flavor', ingredient_id='chocolate_flavor', is_default=True),
                SmoothieSubItem(smoothie_id=choco_loco.id, group_name='flavor', ingredient_id='vanilla_flavor', is_default=False),
                SmoothieSubItem(smoothie_id=choco_loco.id, group_name='flavor', ingredient_id='strawberry_flavor', is_default=False),

                # Group 'topping' Radio Choices
                SmoothieSubItem(smoothie_id=choco_loco.id, group_name='topping', ingredient_id='crunchy_caramel', is_default=True),
                SmoothieSubItem(smoothie_id=choco_loco.id, group_name='topping', ingredient_id='crunchy_oats', is_default=False),
                SmoothieSubItem(smoothie_id=choco_loco.id, group_name='topping', ingredient_id='coconut_flakes', is_default=False),

                # Group 'sweetener' Radio Choices
                SmoothieSubItem(smoothie_id=choco_loco.id, group_name='sweetener', ingredient_id='sugar', is_default=True),
                SmoothieSubItem(smoothie_id=choco_loco.id, group_name='sweetener', ingredient_id='splenda', is_default=False),
                SmoothieSubItem(smoothie_id=choco_loco.id, group_name='sweetener', ingredient_id='no_sugar', is_default=False),

                # Group 'ice' Radio Choices
                SmoothieSubItem(smoothie_id=choco_loco.id, group_name='ice', ingredient_id='crushed_ice', is_default=True),
                SmoothieSubItem(smoothie_id=choco_loco.id, group_name='ice', ingredient_id='light_ice', is_default=False),
                SmoothieSubItem(smoothie_id=choco_loco.id, group_name='ice', ingredient_id='no_ice', is_default=False),
            ])

            # Section 3: Premium Add-ons
            db.session.add_all([
                SmoothieAddonItem(smoothie_id=choco_loco.id, ingredient_id='espresso_shot'),
                SmoothieAddonItem(smoothie_id=choco_loco.id, ingredient_id='whey_protein'),
                SmoothieAddonItem(smoothie_id=choco_loco.id, ingredient_id='strawberries'),
                SmoothieAddonItem(smoothie_id=choco_loco.id, ingredient_id='cinammon'),
            ])

            choco_loco.calculate_and_save_price()
            print(f"✅ Seeding Complete! '{choco_loco.name}' retail price calculated at: ${choco_loco.base_price}")
            
            db.session.commit()
            
            print("🎉 The 'Choco Loco' Smoothie tables have been successfully initialized!")

        else:
            print("The 'Choco Loco' Smoothie tables have already been populated. Skipping seeding loop.")


        # --- SMOOTHIE NAME: "Tropical Oasis" ---
        tropical_oasis_exists = Smoothie.query.filter_by(name="Tropical Oasis").first()

        if not tropical_oasis_exists:
            print("🍹 Seeding data for 'Tropical Oasis' Smoothie...")
            tropical_oasis = Smoothie(
                name="Tropical Oasis",
                slogan="Your Island Escape in a Cup!",
                profit_margin=2.50
            )
            db.session.add(tropical_oasis)
            db.session.flush()

            # Section 1: Standard Core Recipe Items
            db.session.add_all([
                SmoothieRecipeItem(smoothie_id=tropical_oasis.id, ingredient_id='pineapple', ingredient_quantity=2),
                SmoothieRecipeItem(smoothie_id=tropical_oasis.id, ingredient_id='mango', ingredient_quantity=1),
                SmoothieRecipeItem(smoothie_id=tropical_oasis.id, ingredient_id='strawberries', ingredient_quantity=1),
                SmoothieRecipeItem(smoothie_id=tropical_oasis.id, ingredient_id='coconut_flakes', ingredient_quantity=1),
            ])

            # Section 2: Substitution Radio Options
            db.session.add_all([
                # Group 'starter' Radio Choices
                SmoothieSubItem(smoothie_id=tropical_oasis.id, group_name='starter', ingredient_id='coconut_milk', is_default=True),
                SmoothieSubItem(smoothie_id=tropical_oasis.id, group_name='starter', ingredient_id='frozen_yogurt', is_default=False),
                SmoothieSubItem(smoothie_id=tropical_oasis.id, group_name='starter', ingredient_id='soy_milk', is_default=False),

                # Group 'flavor' Radio Choices
                SmoothieSubItem(smoothie_id=tropical_oasis.id, group_name='flavor', ingredient_id='vanilla_flavor', is_default=True),
                SmoothieSubItem(smoothie_id=tropical_oasis.id, group_name='flavor', ingredient_id='strawberry_flavor', is_default=False),
                SmoothieSubItem(smoothie_id=tropical_oasis.id, group_name='flavor', ingredient_id='chocolate_flavor', is_default=False),
                
                # Group 'topping' Radio Choices
                SmoothieSubItem(smoothie_id=tropical_oasis.id, group_name='topping', ingredient_id='crunchy_oats', is_default=True),
                SmoothieSubItem(smoothie_id=tropical_oasis.id, group_name='topping', ingredient_id='crunchy_caramel', is_default=False),
                SmoothieSubItem(smoothie_id=tropical_oasis.id, group_name='topping', ingredient_id='choco_chips', is_default=False),
                
                # Group 'sweetener' Radio Choices
                SmoothieSubItem(smoothie_id=tropical_oasis.id, group_name='sweetener', ingredient_id='sugar', is_default=True),
                SmoothieSubItem(smoothie_id=tropical_oasis.id, group_name='sweetener', ingredient_id='splenda', is_default=False),
                SmoothieSubItem(smoothie_id=tropical_oasis.id, group_name='sweetener', ingredient_id='no_sugar', is_default=False),
                
                # Group 'ice' Radio Choices
                SmoothieSubItem(smoothie_id=tropical_oasis.id, group_name='ice', ingredient_id='crushed_ice', is_default=True),
                SmoothieSubItem(smoothie_id=tropical_oasis.id, group_name='ice', ingredient_id='light_ice', is_default=False),
                SmoothieSubItem(smoothie_id=tropical_oasis.id, group_name='ice', ingredient_id='no_ice', is_default=False),
            ])

            # Section 3: Premium Add-ons
            db.session.add_all([
                SmoothieAddonItem(smoothie_id=tropical_oasis.id, ingredient_id='banana'),
                SmoothieAddonItem(smoothie_id=tropical_oasis.id, ingredient_id='blueberries'),
                SmoothieAddonItem(smoothie_id=tropical_oasis.id, ingredient_id='whey_protein'),
                SmoothieAddonItem(smoothie_id=tropical_oasis.id, ingredient_id='whipped_cream'),
            ])

            tropical_oasis.calculate_and_save_price()
            print(f"✅ Seeding Complete! '{tropical_oasis.name}' retail price calculated at: ${tropical_oasis.base_price}")
            
            db.session.commit()
            
            print("🎉 The 'Tropical Oasis' Smoothie tables have been successfully initialized!")
        
        else:
            print("The 'Tropical Oasis' Smoothie tables have already been populated. Skipping seeding loop.")

        # --- SMOOTHIE NAME: "Coffee Taffy" ---
        coffee_taffy_exists = Smoothie.query.filter_by(name="Coffee Taffy").first()

        if not coffee_taffy_exists:
            print("🍹 Seeding data for 'Coffee Taffy' Smoothie...")
            coffee_taffy = Smoothie(
                name="Coffee Taffy",
                slogan="Sweet and Fluffy!",
                profit_margin=2.25
            )
            db.session.add(coffee_taffy)
            db.session.flush()

            # Section 1: Standard Core Recipe Items
            db.session.add_all([
                SmoothieRecipeItem(smoothie_id=coffee_taffy.id, ingredient_id='iced_coffee', ingredient_quantity=1),
                SmoothieRecipeItem(smoothie_id=coffee_taffy.id, ingredient_id='espresso_shot', ingredient_quantity=1),
                SmoothieRecipeItem(smoothie_id=coffee_taffy.id, ingredient_id='banana', ingredient_quantity=1),
                SmoothieRecipeItem(smoothie_id=coffee_taffy.id, ingredient_id='whipped_cream', ingredient_quantity=1),
            ])

            # Section 2: Substitution Radio Options
            db.session.add_all([
                # Group 'starter' Radio Choices
                SmoothieSubItem(smoothie_id=coffee_taffy.id, group_name='starter', ingredient_id='coffee_creamer', is_default=True),
                SmoothieSubItem(smoothie_id=coffee_taffy.id, group_name='starter', ingredient_id='milk', is_default=False),
                SmoothieSubItem(smoothie_id=coffee_taffy.id, group_name='starter', ingredient_id='soy_milk', is_default=False),

                # Group 'flavor' Radio Choices
                SmoothieSubItem(smoothie_id=coffee_taffy.id, group_name='flavor', ingredient_id='vanilla_flavor', is_default=True),
                SmoothieSubItem(smoothie_id=coffee_taffy.id, group_name='flavor', ingredient_id='chocolate_flavor', is_default=False),
                SmoothieSubItem(smoothie_id=coffee_taffy.id, group_name='flavor', ingredient_id='strawberry_flavor', is_default=False),

                # Group 'topping' Radio Choices
                SmoothieSubItem(smoothie_id=coffee_taffy.id, group_name='topping', ingredient_id='crunchy_caramel', is_default=True),
                SmoothieSubItem(smoothie_id=coffee_taffy.id, group_name='topping', ingredient_id='choco_chips', is_default=False),
                SmoothieSubItem(smoothie_id=coffee_taffy.id, group_name='topping', ingredient_id='crunchy_oats', is_default=False),

                # Group 'sweetener' Radio Choices
                SmoothieSubItem(smoothie_id=coffee_taffy.id, group_name='sweetener', ingredient_id='sugar', is_default=True),
                SmoothieSubItem(smoothie_id=coffee_taffy.id, group_name='sweetener', ingredient_id='splenda', is_default=False),
                SmoothieSubItem(smoothie_id=coffee_taffy.id, group_name='sweetener', ingredient_id='no_sugar', is_default=False),

                # Group 'ice' Radio Choices
                SmoothieSubItem(smoothie_id=coffee_taffy.id, group_name='ice', ingredient_id='crushed_ice', is_default=True),
                SmoothieSubItem(smoothie_id=coffee_taffy.id, group_name='ice', ingredient_id='light_ice', is_default=False),
                SmoothieSubItem(smoothie_id=coffee_taffy.id, group_name='ice', ingredient_id='no_ice', is_default=False),
            ])

            # Section 3: Premium Add-ons
            db.session.add_all([
                SmoothieAddonItem(smoothie_id=coffee_taffy.id, ingredient_id='caramel_topping'),
                SmoothieAddonItem(smoothie_id=coffee_taffy.id, ingredient_id='whey_protein'),
                SmoothieAddonItem(smoothie_id=coffee_taffy.id, ingredient_id='cinammon'),
                SmoothieAddonItem(smoothie_id=coffee_taffy.id, ingredient_id='choco_chips'),
            ])

            coffee_taffy.calculate_and_save_price()
            print(f"✅ Seeding Complete! '{coffee_taffy.name}' retail price calculated at: ${coffee_taffy.base_price}")

            db.session.commit()

            print("🎉 The 'Coffee Taffy' Smoothie tables have been successfully initialized!")

        else:
            print("The 'Coffee Taffy' Smoothie tables have already been populated. Skipping seeding loop.")
