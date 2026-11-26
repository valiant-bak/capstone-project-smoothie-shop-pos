## Oasis Smoothie Shop — Point-of-Sale (POS) & Inventory Management System

A full-stack web Point-of-Sale (POS) and real-time inventory management application built with **Python**, **Flask**, **SQLAlchemy**, **SQLite**, **Jinja2**, **Javascript**, and **Bootstrap 5** for the WGU D424 Software Engineering Capstone.

- **Live Hosted Application (Render):** `https://smoothie-shop-pos.onrender.com/`
- **GitLab Repository:** `https://gitlab.com/wgu-gitlab-environment/student-repos/vbake45/d424-software-engineering-capstone.git` (`working-branch )

---

## Operational User Workflows

The application supports five distinct end-to-end operational paths tailored to real-world smoothie bar stations:

1. **Self-Service Guest Kiosk Path (Unauthenticated):**
   - Customers browse the dynamic smoothie menu (`/checkout/menu`), customize base ingredients, select substitutions or paid add-ons, and submit orders into the `pending_payment` queue for staff processing.
2. **Employee Full-Service POS Line Path (`employee` role):**
   - Counter staff build and customize orders directly on the POS line, immediately collect payment, generate a kitchen service ticket, serve the completed smoothie, and close the transaction end-to-end.
3. **Employee Payment Station Path (`employee` role):**
   - Cashier staff monitor the `/orders/pending-payment` queue, verify itemized customer kiosk orders, process payments, and transition paid tickets to the kitchen service queue (`pending_served`).
4. **Employee Kitchen Service Station Path (`employee` role):**
   - Prep staff work from the `/orders/pending-service` queue to fulfill active kitchen tickets, mark orders as served, trigger automated stock deductions, and finalize order completion (`completed`).
5. **Manager Inventory Reconciliation Path (`manager` role):**
   - Administrators hold full access to all kiosk, POS, payment, and service workflows, plus exclusive access to `/admin/inventory/update` to perform bulk **Inventory Reconciliation**, adjust stock thresholds, and log ingredient restocks.

## Core Features

- **Customer Kiosk & Dynamic Smoothie Customization (`/checkout/menu`):**
  - **Dynamic Menu & Recipe Builder:** Renders database-driven menu cards featuring removable base recipe ingredients, grouped substitution radio selectors, and optional paid add-ons.
  - **Pre-Checkout Inventory Guarantee (`verify_inventory`):** Performs real-time ingredient depletion checks before order submission, guaranteeing that every customized smoothie in the cart has sufficient stock to be fulfilled and alerting customers immediately if an item is unavailable.
  - **Concurrency-Safe Stock Deduction & Line-Item Persistence:** Persists granular `OrderItem` customization records to the database for historical reporting and receipt lookups, while acquiring database row-level locks (`with_for_update()`) during inventory deduction transactions to prevent race conditions from concurrent checkout requests.

- **User-Friendly GUI & Contextual Feedback:**
  - **Role-Aware Navigation & Visual Cues:** Dynamically renders the Bootstrap 5 top navigation bar based on the active session role (**Guest**, **Employee**, **Manager**) with intuitive visual icons (`💳 Pending Payments`, `🥤 Pending Service`, `🔍 Find Order`, `📊 Inventory`) so users only see actions relevant to their station.
  - **Explicit Action Confirmations:** Displays high-visibility green Bootstrap alert banners (`flash(..., "success")`) confirming completed state changes—including database inventory saves, collected payments, served orders, and cart additions.
  - **Actionable Error Recovery & Form State Preservation:** Renders plain-English `warning` and `danger` alerts (`flash(..., "warning" / "danger")`) explaining exact rejection reasons while preserving entered form values to prevent retyping (e.g., flagging specific ingredient IDs violating `current_stock >= minimum_stock`, prompting out-of-stock substitutions, or reporting unmatched `Order #` lookups).

- **Role-Based Access Control (3-Tier RBAC):**
  - **Customer / Guest (Unauthenticated):** Browse and customize smoothies and submit kiosk orders.
  - **Employee (`employee` role):** Collect payments (`/orders/pending-payment`), fulfill kitchen orders (`/orders/pending-service`), search/filter orders (`/orders/find-order`), and monitor real-time stock levels (`/inventory-dashboard`).
  - **Manager (`manager` role):** Full employee access plus bulk inventory updates (`/admin/inventory/update`) with cross-field relational validation (`current_stock >= minimum_stock` and `reorder_stock > minimum_stock`) and atomic rollback on invalid input.
- **Real-Time Reporting & Audit Logs:**
  - **Filtered Orders Report (`/orders/find-order`):** Searchable multi-column onscreen report filterable by `Order #` or status (`pending_payment`, `pending_served`, `on_hold`, `completed`), displaying itemized receipts, `created_at` timestamps, payment/service statuses, and contextual workflow actions (**Collect Payment** or **Serve Order**).
  - **Real-Time Inventory Dashboard (`/inventory-dashboard`):** Live multi-row stock report tracking current ingredient levels, reorder thresholds, and minimum stock alerts across all tracked items.
  - **Console Diagnostic & Stock Deficiency Tables:** Color-coded terminal output tables comparing real-time ingredient demand against current stock and minimum stock limits, alongside live tracking of inventory deductions, restock updates, and input validation events.
  - **Automated Application Audit Log (`Oasis_Smoothie_Shop_Report.log`):** Persistent timestamped log file recording system events, inventory evaluations, and transaction milestones.

- **Object-Oriented Domain Architecture (`models.py` & `seed_db.py`):**
  - **Inheritance, Polymorphism & Encapsulation:** Implements an abstract `SmoothieComponent` superclass inherited by `SmoothieRecipeItem`, `SmoothieSubItem`, and `SmoothieAddonItem` to share polymorphic component behavior, while encapsulating business logic—such as dynamic pricing calculations, stock deduction methods, password hashing, and sanitized `__repr__()` debug serialization—directly within domain models.
  - **Relational Integrity & Cascading Lifecycles:** Maps normalized one-to-many and many-to-many associations via explicit `db.ForeignKey` constraints and bidirectional `db.relationship()` back-references, enabling seamless object-graph traversal (e.g., `order.items`, `smoothie.recipe_items`) and `cascade="all, delete-orphan"` cleanup to prevent orphaned child records.
  - **Idempotent Database Seeding (`seed_db.py`):** Protects existing production or test records using guard checks prior to initialization, ensuring `seed_db.py` safely populates baseline suppliers, ingredients, recipes, and RBAC accounts without overwriting live database state.

- **Relational Database, Input Validation & Inventory Verification:**
  - **Full CRUD Persistence (`models.py`):** Powered by **SQLite** and **SQLAlchemy ORM** across nine normalized models (`Supplier`, `Ingredient`, `Smoothie`, `SmoothieRecipeItem`, `SmoothieSubItem`, `SmoothieAddonItem`, `User`, `Order`, and `OrderItem`) supporting `db.session.add()`, `db.session.commit()`, and `db.session.delete()`.
  - **Input Validation & Fail-Fast Guardrails:** Applies whitespace normalization (`.strip()`), strict type casting (`type=int`), and numeric checks (`.isdigit()`), enforcing **Fail-Fast** guardrails to reject `None`, empty strings, or negative numbers before processing and prevent runtime `AttributeError` or `ValueError` crashes.
  - **Inventory Verification & Reconciliation:** Enforces cross-field relational rules during manager reconciliation in `update_inventory()` (`current_stock >= minimum_stock`, `reorder_stock > minimum_stock`) alongside cart integrity checks (`validate_cart()`) and real-time depletion gating (`verify_inventory()`).

- **Security & Defensive Coding:**
  - **Defensive Coding & Exception Handling:** Wraps database transactions and critical execution blocks in structured `try / except` handlers with atomic `db.session.rollback()` recovery to prevent application crashes and maintain database consistency on invalid input.
  - **User Authentication & Session Hardening:** Secures `/login` with `werkzeug.security` salted password hashing (`generate_password_hash` / `check_password_hash`), `Flask-Login` (`session_protection = "strong"`), `Flask-WTF` CSRF tokens on all `POST` forms, and an environment-injected `SECRET_KEY`.
  - **SQL Injection Prevention:** Executes all queries via parameterized SQLAlchemy ORM statements rather than raw string concatenation.
  - **Cross-Site Scripting (XSS) Mitigation:** Leverages Jinja2's default contextual HTML auto-escaping across all rendered templates alongside sanitized model `__repr__()` outputs to prevent script injection in both UI views and console logs.
  - **Defense-in-Depth RBAC:** Enforces 3-tier authorization (**Guest**, **Employee**, **Manager**) across both Jinja2 UI navigation rendering and server-side route guards (`@login_required` + `403 Forbidden`).

- **Extensibility & Adherence to the Open/Closed Principle:**
  - **Data-Driven Architecture:** Follows the SOLID **Open/Closed Principle** by keeping the application open for menu expansion while closed to modifications in core Python routes or Jinja2 HTML templates.
  - **Zero-Code Menu Expansion:** Adding new signature smoothies (such as  *Very Berry*, *Berry Banny*, *Mango Tango*, *Choco Loco*, *Tropical Oasis*, or *Coffee Taffy*) or new substitution groups to `seed_db.py` automatically propagates across the entire system without touching source code.
  - **End-to-End Dynamic Ingestion:** New database records are seamlessly picked up by the homepage showcase (`index.html`), the customization kiosk (`menu.html`), the polymorphic pricing engine (`calculate_and_save_price()`), and the real-time stock verification pipeline (`verify_inventory()`).

---
## Project Structure

```text
d424-software-engineering-capstone/
├── app_smoothies_pos.py               # Main Flask app, routes, RBAC guards, validation & reports
├── models.py                          # SQLAlchemy ORM models, OOP hierarchy & status enums
├── extensions.py                      # Flask extension instances (db, login_manager, csrf)
├── seed_db.py                         # Idempotent initial menu, ingredient, supplier & user seeder
├── test_app.py                        # Automated pytest suite (23 unit & integration tests)
├── app_smoothies_pos.db               # SQLite relational database file (auto-generated on startup)
├── Oasis_Smoothie_Shop_Report.log     # Persistent audit log for transactions, stock changes & errors
├── requirements.txt                   # Pinned Python dependencies (Flask, SQLAlchemy, Gunicorn, pytest)
├── README.md                          # Developer setup, architecture & maintenance documentation
├── .gitignore                         # Git exclusion rules (.venv, __pycache__, local environment files)
├── static/                            # Static frontend assets
│   ├── css/
│   │   ├── bootstrap.min.css          # Local Bootstrap 5 stylesheet
│   │   └── main.css                   # Custom storefront & workstation styles
│   ├── img/
│   │   ├── berry-banny-smoothie.jpeg  # Signature smoothie product images
│   │   ├── choco-loco-smoothie.jpeg
│   │   ├── coffee-taffy-smoothie.jpeg
│   │   ├── mango-tango-smoothie.jpeg
│   │   ├── tropical-oasis-smoothie.jpeg
│   │   ├── very-berry-smoothie.jpeg
│   │   ├── cart.ico                   # Browser favicon
│   │   └── cart.png                   # Storefront & cart icon
│   ├── js/
│   |   └── bootstrap.bundle.min.js    # Local Bootstrap 5 JavaScript bundle
|   └── sitemap.xml
|
└── templates/                         # Jinja2 HTML views (Bootstrap 5)
    ├── base.html                      # Master layout, navigation bar & flash message container
    ├── index.html                     # Storefront hero banner, featured carousel & full menu grid
    ├── menu.html                      # Interactive smoothie customization kiosk & POS selector
    ├── cart.html                      # Shopping cart review, item removal & live stock verification
    ├── login.html                     # Role-based staff & manager authentication portal
    ├── order.html                     # Single-order lookup & itemized status inspection view
    ├── order_confirmation.html        # Guest kiosk order submission confirmation screen
    ├── order_secure_payment.html      # Simulated PayPal / POS payment authorization interface
    ├── payment_confirmation.html      # Paid order receipt & POS-line bridge to service
    ├── pending_payment_orders.html    # Cashier queue for unpaid kiosk & counter orders
    ├── order_service_ticket.html      # Kitchen preparation ticket & ingredient checklist
    ├── pending_service_orders.html    # Kitchen prep queue for paid orders awaiting fulfillment
    ├── service_confirmation.html      # Final order completion & stock deduction confirmation
    ├── inventory_dashboard.html       # Real-time stock status & supplier summary dashboard
    └── inventory.html                 # Manager bulk inventory reconciliation & threshold editor
```



## Live Cloud Deployment (Render)

- **Live Production URL:** [https://onrender.com](https://onrender.com)
- **Hosting Platform:** Render Web Service (Python 3 runtime, Ohio region) with automatic CI/CD deployment from the `main` branch.
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn app_smoothies_pos:app`
- **Cold-Start Note:** On Render's free tier, the container spins down after 15 minutes of inactivity. The initial page load may take **45–60 seconds** while the instance wakes up; subsequent requests respond immediately.

---

## Local Installation & Testing

### Prerequisites
- **Python 3.11+** (tested on Python 3.12) & **Git**

### Setup & Run
1. **Clone the repository and enter the project directory:**
   ```bash
   git clone https://github.com
   cd capstone-project-smoothie-shop-pos
   ```

2. **Create and activate a virtual environment:**
   - **Windows (PowerShell):**
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```
   - **macOS / Linux:**
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the automated test suite (`pytest`):**
   ```bash
   pytest -v
   ```
   All unit and integration tests run against an isolated in-memory SQLite database (`sqlite:///:memory:`) without touching local files.

5. **Start the local development server:**
   ```bash
   python app_smoothies_pos.py
   ```
   On first startup, SQLAlchemy initializes `app_smoothies_pos.db` and seeds initial suppliers, ingredients, signature smoothies, and role-based accounts (`seed_db.py`). Open **[http://127.0.0](http://127.0.0)** in your browser.

> *Note: Demo workstation login credentials are provided separately in the accompanying User Guide documentation to maintain repository security hygiene.*

---

## Deployment & Maintenance Workflow

1. Implement code updates locally and verify zero regressions with `pytest -v`.
2. If dependencies change, update `requirements.txt` via `pip freeze > requirements.txt`.
3. Ensure `SECRET_KEY` is configured in Render's **Environment** settings.
4. Commit and push to `main` (`git push origin main`) to trigger an automatic Render build and Gunicorn redeploy.
