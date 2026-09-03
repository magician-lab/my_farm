# MY FARM - Complete System Documentation

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Functional Requirements](#2-functional-requirements)
3. [Non-Functional Requirements](#3-non-functional-requirements)
4. [Domain Requirements](#4-domain-requirements)
5. [Use Case Documentation](#5-use-case-documentation)
6. [Data Modelling](#6-data-modelling)
7. [Full Flow of Each Functionality](#7-full-flow-of-each-functionality)

---

## 1. System Overview

### 1.1 Project Name
**MY FARM** - Dairy Farm Management ERP System

### 1.2 Purpose
A centralized web-based ERP system for managing dairy farm operations across multiple farm locations. The system tracks animal registries, milk production and sales, veterinary treatments, insemination records, feed orders and deliveries, vehicle management, employee records, financial transactions, and generates analytical reports and PDFs.

### 1.3 Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3, Flask 3.1.2 |
| **ORM / Database** | SQLAlchemy 2.0.46, Flask-SQLAlchemy 3.1.1 |
| **Database Support** | PostgreSQL (production via psycopg2-binary), SQLite (development fallback) |
| **Frontend** | Jinja2 Templates, HTML/CSS/JS |
| **PDF Generation** | WeasyPrint 69.0 |
| **Excel Import/Export** | pandas 3.0.2, openpyxl 3.1.5 |
| **Email** | Flask-Mail 0.10.0 (Gmail SMTP) |
| **Authentication** | Werkzeug password hashing, Flask session-based auth |
| **Deployment** | Gunicorn 26.0.0, Heroku (Procfile, ping.yml) |

### 1.4 Architecture
- **Pattern**: Server-side rendered MVC (Model-View-Controller)
- **Multi-tenancy**: Farm-based isolation (admin sees all farms; farm users see only their assigned farm)
- **Roles**: `admin` (full access, farm switching) and `user` (restricted to assigned farm)
- **Session Management**: Server-side Flask sessions with `logged_in`, `user_id`, `username`, `role`, `farm_id`

### 1.5 Default Configuration
- Default farms: **Murang'a**, **Meru**
- Default admin: `admin` / `admin123`
- Default farm users: `muranga` / `muranga123`, `meru` / `meru123`
- Database: PostgreSQL (production), SQLite fallback (`database.db`)

---

## 2. Functional Requirements

### 2.1 Authentication & User Management

| ID | Requirement | Priority |
|---|---|---|
| FR-AUTH-01 | Users must authenticate with username/password to access the system | High |
| FR-AUTH-02 | Admin can create, edit, and delete user accounts | High |
| FR-AUTH-03 | Admin can assign roles (admin/user) and farm access to users | High |
| FR-AUTH-04 | Password reset via OTP sent to registered email (6-digit code, 10-min expiry) | High |
| FR-AUTH-05 | Session-based authentication with automatic redirect to login if unauthenticated | High |
| FR-AUTH-06 | Admin cannot delete their own account | Medium |
| FR-AUTH-07 | Duplicate username/email validation on user creation | High |
| FR-AUTH-08 | Role-based access control via `@role_required` decorator | High |
| FR-AUTH-09 | Farm-level permission check: non-admin users cannot access other farm data | High |

### 2.2 Farm Management

| ID | Requirement | Priority |
|---|---|---|
| FR-FARM-01 | Admin can create, edit, and delete farms | High |
| FR-FARM-02 | Admin can switch between farms using a farm context switcher | High |
| FR-FARM-03 | Farm users are locked to their assigned farm | High |
| FR-FARM-04 | Admin can view "All Farms" by clearing the farm filter | Medium |
| FR-FARM-05 | All data records (milk, animals, orders, etc.) are scoped to a farm_id | High |

### 2.3 Animal/Cow Registry

| ID | Requirement | Priority |
|---|---|---|
| FR-ANIM-01 | Register new animals with name, breed, DOB, category, sex, mother | High |
| FR-ANIM-02 | Edit existing animal records | High |
| FR-ANIM-03 | Delete animals from registry | Medium |
| FR-ANIM-04 | Filter animals by category (milker, dry, calf, bull, incalf-heifer, yearling, weaner, steamer, Bullying-heifer) | High |
| FR-ANIM-05 | Duplicate animal name validation | High |
| FR-ANIM-06 | Farm-scoped animal listing | High |
| FR-ANIM-07 | Animal category counts (total, milkers, dry cows, calves, bulls, etc.) | Medium |
| FR-ANIM-08 | Calf registry with mother linkage and mother existence validation | High |
| FR-ANIM-09 | Cow dashboard showing animal counts by farm | Medium |
| FR-ANIM-10 | Mark animals as "nolonger_exist" category (soft delete from active counts) | Medium |

### 2.4 Cow Shed Management

| ID | Requirement | Priority |
|---|---|---|
| FR-SHED-01 | Create, edit, and delete cow sheds | High |
| FR-SHED-02 | Each shed has: name, capacity, category_allowed, color, description | High |
| FR-SHED-03 | Assign animals to sheds with capacity check | High |
| FR-SHED-04 | Remove animals from sheds | High |
| FR-SHED-05 | Move animals between sheds with movement history logging | High |
| FR-SHED-06 | Shed occupancy report (occupied, remaining, occupancy rate) | High |
| FR-SHED-07 | Duplicate shed name validation | Medium |
| FR-SHED-08 | Shed full-check before assignment | High |

### 2.5 Milking Herd Management

| ID | Requirement | Priority |
|---|---|---|
| FR-MILK-01 | Add animals to the milking herd (for milk recording) | High |
| FR-MILK-02 | Remove animals from the milking herd | High |
| FR-MILK-03 | Bulk add/remove via checkbox selection | Medium |
| FR-MILK-04 | Only animals in the milking herd appear in milk recording forms | High |
| FR-MILK-05 | Farm-scoped milking herd display | Medium |

### 2.6 Milk Production Recording

| ID | Requirement | Priority |
|---|---|---|
| FR-PROD-01 | Record milk production per cow per day (morning, noon, evening sessions) | High |
| FR-PROD-02 | Auto-calculate total per cow (morning + noon + evening) | High |
| FR-PROD-03 | Upsert: if record exists for cow+date, update instead of duplicate | High |
| FR-PROD-04 | Excel template export for bulk milk entry | Medium |
| FR-PROD-05 | Excel import with confirmation review step | High |
| FR-PROD-06 | Farm-scoped production recording | High |
| FR-PROD-07 | Edit individual milk records | Medium |
| FR-PROD-08 | Delete individual milk records | Medium |
| FR-PROD-09 | Date-filtered milk production reports | High |

### 2.7 Milk Sales Management

| ID | Requirement | Priority |
|---|---|---|
| FR-SALES-01 | Record milk sales per session (morning, noon, evening) to shops (shop1, shop2, shop3) | High |
| FR-SALES-02 | Record milk used at home and for calf feeding | High |
| FR-SALES-03 | Track actual remaining milk per day | High |
| FR-SALES-04 | Edit and delete sales records | Medium |
| FR-SALES-05 | Monthly sales aggregation report | High |
| FR-SALES-06 | Sales by session (morning/noon/evening) breakdown | Medium |

### 2.8 Milk Stock Tracking

| ID | Requirement | Priority |
|---|---|---|
| FR-STOCK-01 | Calculate system remaining milk (running balance from production and usage) | High |
| FR-STOCK-02 | Track actual remaining milk (manual entry per day) | High |
| FR-STOCK-03 | Calculate variance between system and actual remaining | High |
| FR-STOCK-04 | Calculate percentage conversion (shop sales / available) | Medium |
| FR-STOCK-05 | Calculate percentage error (variance / system remaining) | Medium |
| FR-STOCK-06 | Previous day's remaining as baseline for current day | High |

### 2.9 Milk Pricing

| ID | Requirement | Priority |
|---|---|---|
| FR-PRICE-01 | Admin can set milk prices with effective dates | High |
| FR-PRICE-02 | Price lookup uses binary search for the effective price on any given date | High |
| FR-PRICE-03 | Revenue calculations use date-aware pricing | High |
| FR-PRICE-04 | Edit and delete price records | Medium |
| FR-PRICE-05 | Farm-scoped pricing (currently Murang'a only) | Low |

### 2.10 Insemination Management

| ID | Requirement | Priority |
|---|---|---|
| FR-INSEM-01 | Record insemination: animal, date served, confirmation method | High |
| FR-INSEM-02 | Auto-calculate confirmation date based on method (heat observation: 21 days, ultrasound: 30 days, manual check: 90 days) | High |
| FR-INSEM-03 | Track status: pending, confirmed, delivered, aborted | High |
| FR-INSEM-04 | Auto-calculate calving date (date_served + 283 days) for confirmed | High |
| FR-INSEM-05 | Filter by status, month, year | High |
| FR-INSEM-06 | Edit insemination records with status-based calving date logic | Medium |
| FR-INSEM-07 | Delete insemination records | Medium |
| FR-INSEM-08 | Farm-scoped insemination records | High |

### 2.11 Treatment Management

| ID | Requirement | Priority |
|---|---|---|
| FR-TREAT-01 | Record treatment: animal, date, illness, cost, vet, status | High |
| FR-TREAT-02 | Track treatment status (healed/recovering) | High |
| FR-TREAT-03 | Cost calculations: daily, monthly, quarterly, yearly | Medium |
| FR-TREAT-04 | Status counts (healed, recovering) | Medium |
| FR-TREAT-05 | Date and status filtering | High |
| FR-TREAT-06 | Edit treatment records (status, cost) | Medium |
| FR-TREAT-07 | Delete individual or bulk selected treatments | Medium |
| FR-TREAT-08 | Farm-scoped treatment records | High |

### 2.12 Feeds Order Management (V2)

| ID | Requirement | Priority |
|---|---|---|
| FR-FEED-01 | Create feeds orders with auto-generated reference (FR-YYYYMMDD-NNN) | High |
| FR-FEED-02 | Add multiple feed items per order (feed_name, quantity, price_per_unit, total_cost) | High |
| FR-FEED-03 | Add/edit/delete items within an order | High |
| FR-FEED-04 | Track delivery status per item (Pending, Partial, Full) | High |
| FR-FEED-05 | Record partial deliveries with pieces and unit_weight (auto-calculates quantity_delivered) | High |
| FR-FEED-06 | Delivery validation: cannot exceed ordered quantity | High |
| FR-FEED-07 | Track payment status per order (Debt/Cleared) | High |
| FR-FEED-08 | Make partial payments against orders | High |
| FR-FEED-09 | Edit and delete deliveries and payments | Medium |
| FR-FEED-10 | Feed name search autocomplete from FeedsRegistry | Medium |
| FR-FEED-11 | Price comparison: current order price vs previous FeedsRegistry price | Low |
| FR-FEED-12 | Farm-scoped order listing | High |

### 2.13 Vehicle Management

| ID | Requirement | Priority |
|---|---|---|
| FR-CAR-01 | Register vehicles with plate number, model, driver | High |
| FR-CAR-02 | Track active/inactive vehicle status | High |
| FR-CAR-03 | Deactivate/reactivate vehicles | Medium |
| FR-CAR-04 | Record vehicle expenses (fuel, repair, insurance, etc.) | High |
| FR-CAR-05 | Record vehicle sales (FULL day = 10000, HALF day = 5000) | High |
| FR-CAR-06 | Vehicle expense and sales reports (date-filtered) | High |
| FR-CAR-07 | Vehicle analytics: per-car sales, expenses, profit for a month | Medium |
| FR-CAR-08 | Overall fleet totals (sales, expenses, profit) | Medium |
| FR-CAR-09 | Edit/delete vehicle expenses and sales | Medium |

### 2.14 Employee Management

| ID | Requirement | Priority |
|---|---|---|
| FR-EMP-01 | Register employees with name, ID number, phone, salary, role | High |
| FR-EMP-02 | Edit employee records | Medium |
| FR-EMP-03 | Delete employees (individual or bulk) | Medium |
| FR-EMP-04 | Calculate total salary expenditure | Medium |
| FR-EMP-05 | Admin-only access to employee management | High |

### 2.15 Asset Management

| ID | Requirement | Priority |
|---|---|---|
| FR-ASSET-01 | Register assets with name, purpose, bought date, cost, origin | High |
| FR-ASSET-02 | Delete assets (individual or bulk) | Medium |
| FR-ASSET-03 | Admin-only access to asset management | High |

### 2.16 Financial Transaction Management

| ID | Requirement | Priority |
|---|---|---|
| FR-PAY-01 | Record payments with date, amount, account, purpose, purpose_type (feeds/other) | High |
| FR-PAY-02 | Farm users can add payments but cannot view history | Medium |
| FR-PAY-03 | Admin can view all payment history with filters (date, month, purpose, farm) | High |
| FR-PAY-04 | Period payment totals (daily, monthly, quarterly, yearly) | Medium |
| FR-PAY-05 | Separate feed expense and other expense tracking | Medium |
| FR-PAY-06 | Edit and delete payment records | Medium |

### 2.17 Financial Dashboard

| ID | Requirement | Priority |
|---|---|---|
| FR-FIN-01 | Aggregate revenue from milk sales + vehicle sales | High |
| FR-FIN-02 | Aggregate expenses from feed, other, vehicle, and salary | High |
| FR-FIN-03 | Calculate net profit and profit margin percentage | High |
| FR-FIN-04 | Independent date filters per data source (milk, vehicle, expense) | Medium |
| FR-FIN-05 | Admin-only access | High |

### 2.18 PDF Report Generation

| ID | Requirement | Priority |
|---|---|---|
| FR-PDF-01 | Generate PDF reports for: milk, car expenses, car sales, animals, shed report, treatment, insemination, milk sale, transactions, cow analysis, milk sales monthly, feeds orders, order detail, delivery, payments, employees | High |
| FR-PDF-02 | PDF download as attachment | High |
| FR-PDF-03 | Reports use date/category/status filters from query parameters | Medium |

### 2.19 Email Integration

| ID | Requirement | Priority |
|---|---|---|
| FR-EMAIL-01 | Send password reset OTP via Gmail SMTP | Medium |
| FR-EMAIL-02 | Configure mail server, port, SSL, credentials via Flask-Mail | Medium |

### 2.20 Data Migration

| ID | Requirement | Priority |
|---|---|---|
| FR-MIG-01 | Auto-additive migrations: add missing columns without dropping data | High |
| FR-MIG-02 | Backfill new columns with safe defaults (farm_id=1, active=TRUE) | High |
| FR-MIG-03 | Support both SQLite and PostgreSQL dialects | High |

---

## 3. Non-Functional Requirements

### 3.1 Performance

| ID | Requirement | Target |
|---|---|---|
| NFR-PERF-01 | Database connection pool with pre-ping and recycle | Pool recycle: 300s, pre_ping enabled |
| NFR-PERF-02 | Milk analytics engine executes in 4-5 SQL queries max | O(1) queries for report generation |
| NFR-PERF-03 | Price lookup uses binary search (bisect_right) for O(log n) | Efficient date-based price resolution |
| NFR-PERF-04 | History loading uses only 3 SQL queries (production, sales, remaining) | Optimized batch loading |
| NFR-PERF-05 | Cow shed occupancy calculated via count queries | Acceptable for small-to-medium datasets |

### 3.2 Security

| ID | Requirement | Detail |
|---|---|---|
| NFR-SEC-01 | Password hashing via Werkzeug | generate_password_hash / check_password_hash |
| NFR-SEC-02 | CSRF protection via Flask session | Secret key configured |
| NFR-SEC-03 | Role-based access control | @role_required decorator |
| NFR-SEC-04 | Farm-level data isolation | Non-admin users cannot access other farm data |
| NFR-SEC-05 | OTP-based password reset with time expiry | 10-minute expiry window |
| NFR-SEC-06 | Admin self-deletion prevention | Cannot delete own account |
| NFR-SEC-07 | Duplicate validation on user creation | Username and email uniqueness |

### 3.3 Reliability

| ID | Requirement | Detail |
|---|---|---|
| NFR-REL-01 | Database fallback: PostgreSQL primary, SQLite fallback | Automatic fallback |
| NFR-REL-02 | Connection pool pre-ping | Validates connections before use |
| NFR-REL-03 | Transaction rollback on errors | db.session.rollback() on exceptions |
| NFR-REL-04 | Health check endpoint | `/health` returns "OK" |
| NFR-REL-05 | Heroku keep-alive via ping.yml | Prevents dyno sleeping |

### 3.4 Usability

| ID | Requirement | Detail |
|---|---|---|
| NFR-USE-01 | Server-side rendered HTML with Jinja2 templates | No SPA framework required |
| NFR-USE-02 | Flash messages for success/error feedback | Categorized: success, error, warning, danger |
| NFR-USE-03 | Date picker filters on all report pages | Consistent filter UI |
| NFR-USE-04 | Landing page redirects to dashboard if logged in | Seamless UX |
| NFR-USE-05 | Farm context displayed in UI | Current farm shown in navigation |

### 3.5 Maintainability

| ID | Requirement | Detail |
|---|---|---|
| NFR-MNT-01 | Single-file application (app.py) with models in separate file | Easy to understand and modify |
| NFR-MNT-02 | Reusable data functions (get_milk_sales, get_transactions_data, etc.) | DRY principle |
| NFR-MNT-03 | Template inheritance via base_erp.html | Consistent layout |
| NFR-MNT-04 | Auto-migration on startup | No manual migration steps needed |

### 3.6 Compatibility

| ID | Requirement | Detail |
|---|---|---|
| NFR-CMP-01 | Cross-platform: Windows, Linux, macOS | Python/Flask |
| NFR-CMP-02 | Dual database support: PostgreSQL and SQLite | SQLAlchemy dialect handling |
| NFR-CMP-03 | PDF generation via WeasyPrint (HTML to PDF) | Browser-independent PDF output |
| NFR-CMP-04 | Excel import/export via pandas + openpyxl | .xlsx format support |

---

## 4. Domain Requirements

### 4.1 Dairy Farm Operations

| ID | Requirement | Detail |
|---|---|---|
| DR-01 | Multi-farm support | System must support operations across multiple farm locations with data isolation |
| DR-02 | Animal lifecycle management | Track animals from calf through yearling to milker/dry cow |
| DR-03 | Milking herd segregation | Only designated milking herd animals can have production recorded |
| DR-04 | Milk production tracking | Record morning, noon, evening milking sessions per cow |
| DR-05 | Milk distribution tracking | Track milk sold to shops, used at home, fed to calves |
| DR-06 | Stock reconciliation | System must compare calculated remaining vs actual remaining milk |
| DR-07 | Reproduction management | Track insemination, pregnancy confirmation, and calving |
| DR-08 | Health management | Track veterinary treatments, costs, and recovery status |

### 4.2 Financial Management

| ID | Requirement | Detail |
|---|---|---|
| DR-09 | Revenue tracking | Milk sales revenue calculated using date-aware pricing |
| DR-10 | Expense categorization | Separate feed expenses from other operational expenses |
| DR-11 | Vehicle economics | Track per-vehicle revenue vs expenses for profitability |
| DR-12 | Salary tracking | Employee salary as a fixed expense component |
| DR-13 | Feeds order lifecycle | Track from order creation through delivery to payment |
| DR-14 | Payment reconciliation | Balance = total order cost - total payments made |

### 4.3 Operational Constraints

| ID | Requirement | Detail |
|---|---|---|
| DR-15 | Default milk price per farm | Each farm may have different milk prices |
| DR-16 | Vehicle hire rates | FULL day = KES 10,000, HALF day = KES 5,000 |
| DR-17 | Confirmation method durations | Heat observation: 21 days, Ultrasound: 30 days, Manual check: 90 days |
| DR-18 | Gestation period | 283 days from insemination to calving |
| DR-19 | Feed order reference format | FR-YYYYMMDD-NNN (auto-incrementing daily) |
| DR-20 | Cow categories | milker, dry, calf, bull, incalf-heifer, yearling, weaner, steamer, Bullying-heifer, nolonger_exist |

---

## 5. Use Case Documentation

### UC-01: User Login

| Attribute | Value |
|---|---|
| **Actor** | User (Admin or Farm User) |
| **Precondition** | User has an account; browser is open |
| **Trigger** | User navigates to `/` or `/login` |
| **Main Flow** | 1. System displays login form<br>2. User enters username and password<br>3. System validates credentials against Admin table<br>4. System creates session with: logged_in, user_id, username, role, farm_id<br>5. Admin -> redirect to main_dashboard<br>6. Farm user with farm_id -> redirect to main_dashboard<br>7. Farm user without farm_id -> redirect to select_farm |
| **Alternative Flow** | 3a. Invalid credentials -> flash "Invalid username or password" -> re-render login |
| **Postcondition** | User is authenticated and sees the appropriate dashboard |

### UC-02: Password Reset via OTP

| Attribute | Value |
|---|---|
| **Actor** | User |
| **Precondition** | User has a registered email |
| **Trigger** | User clicks "Forgot Password" |
| **Main Flow** | 1. User enters email on `/forgot`<br>2. System generates 6-digit OTP, stores in Admin.otp_code with 10-min expiry<br>3. System sends OTP via Gmail SMTP<br>4. User enters OTP on `/verify_otp`<br>5. System validates OTP and expiry<br>6. System sets session `otp_verified = True`<br>7. User enters new password on `/reset_password`<br>8. System hashes and updates password, clears OTP fields<br>9. Session cleared, redirect to login |
| **Alternative Flow** | 4a. Invalid OTP -> flash error<br>4b. Expired OTP -> flash "OTP expired"<br>2a. Email not found -> flash "Email not found" |

### UC-03: Farm Management (Admin)

| Attribute | Value |
|---|---|
| **Actor** | Admin |
| **Precondition** | Admin is logged in |
| **Trigger** | Admin navigates to `/farms` |
| **Main Flow** | 1. System displays list of farms<br>2. Admin can **Add** farm: enters name -> validates uniqueness -> creates Farm<br>3. Admin can **Edit** farm: selects farm -> changes name -> validates uniqueness -> updates<br>4. Admin can **Delete** farm: selects farm -> checks for associated feeds -> deletes if safe |
| **Alternative Flow** | 4a. Farm has associated feeds -> block deletion with message |

### UC-04: Farm Context Switching

| Attribute | Value |
|---|---|
| **Actor** | Admin |
| **Precondition** | Admin is logged in |
| **Trigger** | Admin clicks farm switcher |
| **Main Flow** | 1. Admin selects a farm from the switcher<br>2. System sets `session["farm_id"]` to selected farm<br>3. All subsequent data queries filter by this farm_id<br>4. Admin can select "All Farms" (farm_id=0) to clear filter |
| **Postcondition** | All displayed data is scoped to the selected farm |

### UC-05: Register New Animal

| Attribute | Value |
|---|---|
| **Actor** | User (any role) |
| **Precondition** | User is logged in; on animal registration page |
| **Trigger** | User navigates to `/cow_registry` |
| **Main Flow** | 1. System displays registration form<br>2. User enters: name, breed, DOB, category, sex, mother<br>3. System validates: all required fields, duplicate name check<br>4. System creates AnimalRegistry record with farm_id from current context<br>5. Flash "Successfully added" |
| **Alternative Flow** | 3a. Name already exists -> flash "A cow with that name already exist"<br>3b. Missing required fields -> flash "All fields are required" |

### UC-06: Register Calf

| Attribute | Value |
|---|---|
| **Actor** | User |
| **Precondition** | User is logged in; mother cow exists in registry |
| **Trigger** | User navigates to `/calf_registry` |
| **Main Flow** | 1. System displays calf registration form<br>2. User enters: calf name, breed, DOB, level (category), mother name<br>3. System validates: required fields, unique name, mother exists in AnimalRegistry<br>4. System creates AnimalRegistry record with category = level, mother = mother name<br>5. Flash "Successfully added" |
| **Alternative Flow** | 3a. Calf name exists -> flash "Another livestock bears the same name"<br>3b. Mother not found -> flash "The mother you entered does not exist" |

### UC-07: Manage Cow Sheds

| Attribute | Value |
|---|---|
| **Actor** | User |
| **Precondition** | User is logged in |
| **Trigger** | User navigates to `/sheds` |
| **Main Flow** | 1. System displays list of sheds with occupancy info<br>2. User can **Create** shed: name, capacity, category_allowed, color, description<br>3. User can **Edit** shed: modify any field<br>4. User can **Manage** shed: assign/remove animals<br>5. System checks capacity before assignment<br>6. System logs movements in AnimalMovement table |
| **Alternative Flow** | 4a. Shed is full -> flash "Shed is full"<br>4b. Duplicate name -> flash "Shed already exists" |

### UC-08: Move Animal Between Sheds

| Attribute | Value |
|---|---|
| **Actor** | User |
| **Precondition** | Animal is in a shed; target shed exists and is not full |
| **Trigger** | User initiates move action |
| **Main Flow** | 1. User selects animal and target shed<br>2. User provides reason for move<br>3. System checks target shed capacity<br>4. System updates animal's current_shed_id<br>5. System creates AnimalMovement record (from_shed, to_shed, reason, timestamp)<br>6. Flash "Animal moved successfully" |
| **Alternative Flow** | 3a. Target shed full -> flash error, block move |

### UC-09: Manage Milking Herd

| Attribute | Value |
|---|---|
| **Actor** | User |
| **Precondition** | User is logged in; animals exist |
| **Trigger** | User navigates to `/manage_milking` |
| **Main Flow** | 1. System displays all non-deleted animals and current milking herd<br>2. User selects animals via checkboxes<br>3. User clicks "Add Selected" -> adds to MilkingHerd (skips duplicates)<br>4. User clicks "Remove Selected" -> removes from MilkingHerd<br>5. Farm-scoped: only animals belonging to current farm shown |
| **Postcondition** | Milking herd list updated for milk recording |

### UC-10: Record Milk Production

| Attribute | Value |
|---|---|
| **Actor** | User |
| **Precondition** | Milking herd is configured; date is selected |
| **Trigger** | User navigates to `/milk_registry` |
| **Main Flow** | 1. System displays all milking herd cows with input fields for morning, noon, evening<br>2. User selects date<br>3. User enters production values per cow<br>4. System processes each cow: calculates total = morning + noon + evening<br>5. If record exists for cow+date: updates existing record<br>6. If new and total > 0: creates new MilkRegistry record<br>7. Flash "Milk records saved successfully" |
| **Alternative Flow** | 5a. Empty values treated as 0 |

### UC-11: Import Milk Data from Excel

| Attribute | Value |
|---|---|
| **Actor** | User |
| **Precondition** | Excel template exported and filled |
| **Trigger** | User uploads Excel on `/milk_registry/import` |
| **Main Flow** | 1. User downloads Excel template via `/milk_registry/export_template`<br>2. Template contains cow IDs and names from milking herd<br>3. User fills in morning, noon, evening values<br>4. User uploads Excel with selected date<br>5. System parses Excel, validates cow IDs against MilkingHerd<br>6. System shows confirmation page with parsed records and total milk<br>7. User confirms -> system saves all records to MilkRegistry |
| **Alternative Flow** | 4a. Invalid cow ID -> silently skipped<br>4b. No file selected -> flash "Please select an Excel file" |

### UC-12: Record Milk Sales

| Attribute | Value |
|---|---|
| **Actor** | User |
| **Precondition** | User is logged in |
| **Trigger** | User navigates to `/milk_sales_entry` |
| **Main Flow** | 1. System displays sales entry form for morning, noon, evening sessions<br>2. User selects date<br>3. For each session, user enters: shop1, shop2, shop3, home, calf<br>4. User enters actual remaining milk<br>5. System creates MilkSalesRegistry records for each session with data<br>6. System updates/creates MilkDailyRemaining record<br>7. Redirects to sales entry page |

### UC-13: View Milk Sales Report with Stock

| Attribute | Value |
|---|---|
| **Actor** | User (Admin or Farm User) |
| **Precondition** | Milk production and sales data exist |
| **Trigger** | User navigates to `/milk_sales_report` or `/milk_dashboard` |
| **Main Flow** | 1. System executes get_milk_sales() analytics engine<br>2. Calculates: today's production (morning/noon/evening/total)<br>3. Calculates: today's sales (shop1-3, home, calf, total sold, total used)<br>4. Calculates: daily/monthly/quarterly/yearly sales and revenue<br>5. Calculates: system remaining vs actual remaining (stock tracking)<br>6. Calculates: variance, conversion %, error %<br>7. Renders dashboard with all metrics |

### UC-14: Track Insemination

| Attribute | Value |
|---|---|
| **Actor** | User |
| **Precondition** | Animal exists in registry |
| **Trigger** | User navigates to `/insemination/add` |
| **Main Flow** | 1. User selects animal, date served, confirmation method<br>2. System calculates confirmation_date = date_served + method_days<br>3. System creates Insemination record with status="pending"<br>4. User later edits record to update status:<br>&nbsp;&nbsp;- "confirmed" -> calving_date = date_served + 283 days<br>&nbsp;&nbsp;- "aborted" -> calving_date = None<br>&nbsp;&nbsp;- "delivered" -> calving_date = today (if not set)<br>5. Insemination list shows records filtered by status/month/year |
| **Postcondition** | Reproduction cycle tracked from insemination to calving |

### UC-15: Record Treatment

| Attribute | Value |
|---|---|
| **Actor** | User |
| **Precondition** | Animal exists |
| **Trigger** | User navigates to `/add_treatment` |
| **Main Flow** | 1. User selects animal, date treated, illness description, cost, vet name, status (healed/recovering)<br>2. System creates Treatment record with farm_id<br>3. Treatment list shows records with cost summaries (daily/monthly/quarterly/yearly)<br>4. User can filter by date and status<br>5. User can edit status and cost<br>6. User can bulk delete selected treatments |

### UC-16: Create Feeds Order

| Attribute | Value |
|---|---|
| **Actor** | Admin |
| **Precondition** | Admin is logged in |
| **Trigger** | Admin navigates to `/feeds_v2/create` |
| **Main Flow** | 1. System displays order creation form<br>2. Admin selects farm, enters date<br>3. Admin adds feed items: feed_name (autocomplete), quantity (kg), price_per_unit<br>4. System auto-generates order_ref: FR-YYYYMMDD-NNN<br>5. System creates FeedsOrderV2 header + FeedsOrderItemV2 line items<br>6. Redirects to orders list |
| **Postcondition** | Order created with status Pending |

### UC-17: Deliver Feeds Order Items

| Attribute | Value |
|---|---|
| **Actor** | Admin |
| **Precondition** | Order exists with pending items |
| **Trigger** | Admin clicks "Deliver" on an order item |
| **Main Flow** | 1. System shows item with remaining quantity<br>2. Admin enters: pieces, unit_weight (auto-calculates quantity_delivered = pieces * unit_weight)<br>3. System validates: quantity_delivered <= remaining quantity<br>4. System creates FeedsDeliveryV2 record<br>5. Order delivery status updates: Pending -> Partial -> Full |
| **Alternative Flow** | 3a. Exceeds remaining -> flash error, block delivery |

### UC-18: Pay Feeds Order

| Attribute | Value |
|---|---|
| **Actor** | Admin |
| **Precondition** | Order exists with outstanding balance |
| **Trigger** | Admin clicks "Pay" on an order |
| **Main Flow** | 1. System shows order total, amount paid, balance<br>2. Admin enters: date_paid, amount, account<br>3. System creates Payment record with purpose_type="feeds", purpose="Feeds Order {order_ref}"<br>4. Payment status updates: Debt -> Cleared |
| **Postcondition** | Order balance reduced by payment amount |

### UC-19: Vehicle Management

| Attribute | Value |
|---|---|
| **Actor** | Admin |
| **Precondition** | Admin is logged in |
| **Trigger** | Admin navigates to `/car_registry` |
| **Main Flow** | 1. Admin registers vehicles with plate, model, driver<br>2. Admin records expenses (fuel, repair, etc.) per vehicle per date<br>3. Admin records sales per vehicle per date (FULL/HALF day)<br>4. System auto-calculates sale amount: FULL=10000, HALF=5000<br>5. Vehicle analytics shows per-car and fleet-wide metrics |

### UC-20: Financial Dashboard

| Attribute | Value |
|---|---|
| **Actor** | Admin |
| **Precondition** | Data exists across modules |
| **Trigger** | Admin navigates to `/financial_dashboard` |
| **Main Flow** | 1. System aggregates: milk revenue, vehicle revenue, vehicle expenses, feed expenses, other expenses, employee salaries<br>2. Calculates: total revenue, total expense, net profit, profit margin %<br>3. Independent date filters per data source<br>4. Displays consolidated financial view |

### UC-21: Generate PDF Report

| Attribute | Value |
|---|---|
| **Actor** | User |
| **Precondition** | Data exists for the report type |
| **Trigger** | User clicks "Download PDF" on any report page |
| **Main Flow** | 1. System receives report_type and filter parameters via query string<br>2. System loads appropriate data function<br>3. System renders HTML template with data<br>4. WeasyPrint converts HTML to PDF<br>5. PDF sent as downloadable attachment |

---

## 6. Data Modelling

### 6.1 Entity-Relationship Diagram (Textual)

```
Farm (1) ----< (N) AnimalRegistry
Farm (1) ----< (N) MilkRegistry
Farm (1) ----< (N) MilkSalesRegistry
Farm (1) ----< (N) MilkPrice
Farm (1) ----< (N) FeedsRegistry
Farm (1) ----< (N) FeedsOrderV2
Farm (1) ----< (N) Payment
Farm (1) ----< (N) Treatment
Farm (1) ----< (N) Insemination
Farm (1) ----< (N) Admin

AnimalRegistry (1) ----< (N) MilkRegistry
AnimalRegistry (1) ----< (N) Insemination
AnimalRegistry (1) ----< (N) Treatment
AnimalRegistry (1) ----< (N) MilkingHerd
AnimalRegistry (N) >---- (1) CowShed (current_shed_id)

CowShed (1) ----< (N) AnimalMovement (from_shed)
CowShed (1) ----< (N) AnimalMovement (to_shed)
AnimalRegistry (1) ----< (N) AnimalMovement

FeedsOrderV2 (1) ----< (N) FeedsOrderItemV2
FeedsOrderV2 (1) ----< (N) FeedsDeliveryV2
FeedsOrderV2 (1) ----< (N) PaymentV2

CarRegistry (1) ----< (N) CarExpense
CarRegistry (1) ----< (N) CarSales
```

### 6.2 Database Schema

#### 6.2.1 Farm

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | Integer | PK, Auto | Farm identifier |
| name | String(100) | Unique, Not Null | Farm name |

#### 6.2.2 Admin (User Accounts)

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | Integer | PK, Auto | User identifier |
| username | String(100) | Unique, Not Null | Login username |
| email | String(120) | Unique, Not Null | Email address |
| password | String(255) | Not Null | Hashed password |
| role | String(50) | Default "user" | "admin" or "user" |
| farm_id | Integer | FK -> Farm.id, Nullable | Assigned farm (NULL = admin/all) |
| otp_code | String(6) | Nullable | Password reset OTP |
| otp_expiration | DateTime | Nullable | OTP expiry timestamp |
| created_at | DateTime | Default utcnow | Account creation date |

#### 6.2.3 AnimalRegistry

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | Integer | PK, Auto | Animal identifier |
| name | String(100) | Not Null | Animal name |
| breed | String(100) | Nullable | Breed name |
| dob | Date | Nullable | Date of birth |
| category | String(50) | Nullable | milker/dry/calf/bull/etc. |
| sex | String(20) | Default "cow" | Animal sex |
| mother | String(100) | Nullable | Mother's name |
| current_shed_id | Integer | FK -> CowShed.id, Nullable | Current shed assignment |
| farm_id | Integer | FK -> Farm.id, Nullable | Owning farm |

#### 6.2.4 CowShed

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | Integer | PK, Auto | Shed identifier |
| name | String(100) | Unique, Not Null | Shed name |
| category_allowed | String(50) | Nullable | Animal category allowed |
| capacity | Integer | Default 0 | Maximum animals |
| color | String(20) | Default "primary" | UI color |
| description | Text | Nullable | Description |
| created_at | DateTime | Default utcnow | Creation timestamp |

**Properties**: `occupied` (count), `remaining` (capacity - occupied), `is_full` (boolean)

#### 6.2.5 AnimalMovement

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | Integer | PK, Auto | Movement identifier |
| animal_id | Integer | FK -> AnimalRegistry.id | Animal moved |
| from_shed_id | Integer | FK -> CowShed.id, Nullable | Source shed |
| to_shed_id | Integer | FK -> CowShed.id | Destination shed |
| moved_at | DateTime | Default utcnow | Movement timestamp |
| reason | String(255) | Nullable | Reason for move |

#### 6.2.6 MilkingHerd

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | Integer | PK, Auto | Record identifier |
| animal_id | Integer | FK -> AnimalRegistry.id, Unique, Not Null | Animal in milking herd |

#### 6.2.7 MilkRegistry

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | Integer | PK, Auto | Record identifier |
| cow_id | Integer | FK -> AnimalRegistry.id, Not Null | Cow that produced milk |
| date | Date | Not Null | Production date |
| morning | Numeric(10,2) | Not Null | Morning milk (litres) |
| noon | Numeric(10,2) | Not Null | Noon milk (litres) |
| evening | Numeric(10,2) | Not Null | Evening milk (litres) |
| total | Numeric(10,2) | Not Null | Total daily milk |
| farm_id | Integer | FK -> Farm.id, Nullable | Owning farm |

#### 6.2.8 MilkSalesRegistry

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | Integer | PK, Auto | Record identifier |
| date | Date | Not Null | Sale date |
| session | String(20) | Not Null | Morning/Noon/Evening |
| shop1 | Numeric(10,2) | Default 0 | Shop 1 sales (litres) |
| shop2 | Numeric(10,2) | Default 0 | Shop 2 sales (litres) |
| shop3 | Numeric(10,2) | Default 0 | Shop 3 sales (litres) |
| home | Numeric(10,2) | Default 0 | Home use (litres) |
| calf | Numeric(10,2) | Default 0 | Calf feeding (litres) |
| price | Numeric(10,2) | Default 0 | Price per litre |
| farm_id | Integer | FK -> Farm.id, Nullable | Owning farm |

#### 6.2.9 MilkDailyRemaining

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | Integer | PK, Auto | Record identifier |
| date | Date | Unique, Not Null | Date |
| actual_remaining | Numeric(10,2) | Default 0 | Actual milk remaining (litres) |

#### 6.2.10 MilkPrice

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | Integer | PK, Auto | Record identifier |
| price | Numeric(10,2) | Not Null | Price per litre |
| effective_date | Date | Not Null | Date from which price applies |
| created_at | DateTime | Default utcnow | Record creation timestamp |
| farm_id | Integer | FK -> Farm.id, Nullable | Owning farm |

#### 6.2.11 Insemination

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | Integer | PK, Auto | Record identifier |
| animal_id | Integer | FK -> AnimalRegistry.id, Not Null | Inseminated animal |
| date_served | Date | Not Null | Date of insemination |
| confirmation_method | String(50) | Nullable | heat observation/ultrasound/manual check |
| confirmation_date | Date | Nullable | Auto-calculated confirmation date |
| status | String(20) | Default None | pending/confirmed/delivered/aborted |
| calving_date | Date | Nullable | Expected/actual calving date |
| farm_id | Integer | FK -> Farm.id, Nullable | Owning farm |

#### 6.2.12 Treatment

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | Integer | PK, Auto | Record identifier |
| animal_id | Integer | FK -> AnimalRegistry.id | Treated animal |
| date_treated | Date | Nullable | Treatment date |
| illness | String(200) | Nullable | Illness description |
| cost | Float | Nullable | Treatment cost |
| vet | String(100) | Nullable | Veterinarian name |
| status | String(20) | Nullable | healed/recovering |
| farm_id | Integer | FK -> Farm.id, Nullable | Owning farm |

#### 6.2.13 FeedsOrderV2

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | Integer | PK, Auto | Order identifier |
| order_ref | String(50) | Unique, Not Null | FR-YYYYMMDD-NNN |
| date_ordered | Date | Not Null | Order date |
| farm_id | Integer | FK -> Farm.id, Not Null | Ordering farm |

**Relationships**: items (FeedsOrderItemV2), deliveries (FeedsDeliveryV2), payments (PaymentV2)

#### 6.2.14 FeedsOrderItemV2

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | Integer | PK, Auto | Item identifier |
| order_id | Integer | FK -> FeedsOrderV2.id | Parent order |
| feed_name | String(100) | Not Null | Feed product name |
| quantity | Numeric(10,2) | Nullable | Ordered quantity (kg) |
| price_per_unit | Numeric(10,2) | Nullable | Price per kg |
| total_cost | Numeric(10,2) | Nullable | quantity * price_per_unit |

#### 6.2.15 FeedsDeliveryV2

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | Integer | PK, Auto | Delivery identifier |
| order_id | Integer | FK -> FeedsOrderV2.id | Parent order |
| item_id | Integer | FK -> FeedsOrderItemV2.id | Delivered item |
| date_delivered | Date | Not Null | Delivery date |
| pieces | Integer | Nullable | Number of pieces/bags |
| unit_weight | Numeric(10,2) | Nullable | Weight per piece (kg) |
| quantity_delivered | Numeric(10,2) | Nullable | pieces * unit_weight |

#### 6.2.16 Payment

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | Integer | PK, Auto | Payment identifier |
| date_paid | Date | Not Null | Payment date |
| amount | Numeric(10,2) | Not Null | Payment amount |
| account | String(100) | Not Null | Payment account/method |
| purpose_type | String(20) | Not Null | "feeds" or "other" |
| purpose | String(200) | Not Null | Payment purpose description |
| farm_id | Integer | FK -> Farm.id, Nullable | Owning farm |

#### 6.2.17 PaymentV2

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | Integer | PK, Auto | Payment identifier |
| order_id | Integer | FK -> FeedsOrderV2.id | Parent order |
| date_paid | Date | Not Null | Payment date |
| amount | Numeric(10,2) | Nullable | Payment amount |
| account | String(100) | Nullable | Payment account |
| purpose | String(200) | Nullable | Payment purpose |

#### 6.2.18 AssetsRegistry

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | Integer | PK, Auto | Asset identifier |
| AssetName | String(100) | Not Null | Asset name |
| Purpose | String(100) | Not Null | Asset purpose |
| Bought_date | Date | Not Null | Purchase date |
| cost | Numeric(10,2) | Not Null | Purchase cost |
| origin | String(100) | Not Null | Source/supplier |

#### 6.2.19 ExpensesRegistry

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | Integer | PK, Auto | Expense identifier |
| ExpenseName | String(100) | Not Null | Expense name |
| Description | String(100) | Not Null | Description |
| Incurred_date | Date | Not Null | Expense date |
| cost | Numeric(10,2) | Not Null | Expense cost |

#### 6.2.20 EmployeesRegistry

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | Integer | PK, Auto | Employee identifier |
| EmployeeName | String(100) | Not Null | Employee name |
| ID_Number | String(100) | Not Null | National ID number |
| phone | String(100) | Not Null | Phone number |
| salary | Numeric(10,2) | Not Null | Monthly salary |
| role | String(100) | Not Null | Job role |

#### 6.2.21 CarRegistry

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | Integer | PK, Auto | Vehicle identifier |
| plate_number | String(50) | Unique, Not Null | License plate |
| model | String(100) | Nullable | Vehicle model |
| driver | String(100) | Nullable | Assigned driver |
| active | Boolean | Default True | Active status |

#### 6.2.22 CarExpense

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | Integer | PK, Auto | Expense identifier |
| car_id | Integer | FK -> CarRegistry.id, Not Null | Vehicle |
| date | Date | Not Null | Expense date |
| expense_type | String(100) | Nullable | fuel/repair/insurance |
| description | String(200) | Nullable | Description |
| amount | Float | Not Null | Expense amount |

#### 6.2.23 CarSales

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | Integer | PK, Auto | Sale identifier |
| car_id | Integer | FK -> CarRegistry.id, Not Null | Vehicle |
| date | Date | Not Null | Sale date |
| length | String(15) | Nullable | FULL/HALF |
| amount | Float | Not Null | Sale amount (auto-calculated) |

#### 6.2.24 FeedsRegistry (Legacy)

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | Integer | PK, Auto | Record identifier |
| Date_bought | Date | Not Null | Purchase date |
| FeedName | String(100) | Not Null | Feed name |
| farm_id | Integer | FK -> Farm.id, Not Null | Owning farm |
| Quantity | Numeric(10,2) | Not Null | Quantity |
| Price | Numeric(10,2) | Not Null | Unit price |
| Total | Numeric(10,2) | Not Null | Total cost |

#### 6.2.25 CowRegistry (Legacy)

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | Integer | PK, Auto | Record identifier |
| CowName | String(100) | Not Null | Cow name |
| Breed | String(100) | Nullable | Breed |
| Date_bought | Date | Nullable | Purchase date |
| category | String(100) | Nullable | Category |

#### 6.2.26 CalfRegistry (Legacy)

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | Integer | PK, Auto | Record identifier |
| CalfName | String(100) | Not Null | Calf name |
| Breed | String(100) | Not Null | Breed |
| DOB | Date | Not Null | Date of birth |
| level | String(100) | Nullable | Category level |
| mother | String(100) | Not Null | Mother's name |

#### 6.2.27 ShopRegistry (Legacy)

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | Integer | PK, Auto | Record identifier |
| ShopName | String(100) | Not Null | Shop name |
| litres | Numeric(10,2) | Not Null | Litres sold |
| Date_sold | Date | Not Null | Sale date |
| location | String(100) | Not Null | Shop location |

#### 6.2.28 UserRegistry (Legacy)

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | Integer | PK, Auto | Record identifier |
| FirstName | String(100) | Not Null | First name |
| UserName | String(100) | Not Null | Username |
| role | String(100) | Not Null | Role |
| password | String(10) | Not Null | Password |

---

## 7. Full Flow of Each Functionality

### 7.1 Authentication Flow

```
User opens app (/)
    |
    v
[Is user logged in?]
    |--- YES ---> Redirect to /dashboard
    |--- NO  ---> Show landing.html
                      |
                      v
                  Click "Login"
                      |
                      v
                  /login page
                      |
                      v
                  Enter username + password
                      |
                      v
                  [Validate against Admin table]
                      |--- FAIL ---> Flash "Invalid username or password"
                      |               Re-render login.html
                      |--- PASS ---> Create session:
                                        logged_in=True
                                        user_id, username, role, farm_id
                                        |
                                        v
                                    [Is admin?]
                                        |--- YES ---> /dashboard (all farms)
                                        |--- NO  ---> [Has farm_id?]
                                                         |--- YES ---> /dashboard
                                                         |--- NO  ---> /select-farm
```

### 7.2 Password Reset Flow

```
User clicks "Forgot Password"
    |
    v
/forgot page
    |
    v
Enter email address
    |
    v
[Email exists in Admin?]
    |--- NO  ---> Flash "Email not found"
    |--- YES ---> Generate 6-digit OTP
                   Store in Admin.otp_code + otp_expiration (+10 min)
                   Send OTP via Gmail SMTP
                   Set session["reset_email"]
                   |
                   v
               /verify_otp page
                   |
                   v
               Enter OTP
                   |
                   v
               [OTP valid AND not expired?]
                   |--- NO  ---> Flash "Invalid OTP" / "OTP expired"
                   |--- YES ---> Set session["otp_verified"] = True
                                  |
                                  v
                              /reset_password page
                                  |
                                  v
                              Enter new password
                                  |
                                  v
                              Hash password (Werkzeug)
                              Update Admin.password
                              Clear otp_code, otp_expiration
                              Clear session
                              Flash "Password reset successful"
                              Redirect to /login
```

### 7.3 Farm Management Flow

```
Admin navigates to /farms
    |
    v
Display list of all farms
    |
    +--- ADD: Enter farm name
    |       |
    |       v
    |    [Name unique?]
    |       |--- NO  ---> Flash "Farm already exists"
    |       |--- YES ---> Create Farm record
    |                       Flash "Farm added successfully"
    |
    +--- EDIT: Select farm, change name
    |       |
    |       v
    |    [Name unique among others?]
    |       |--- NO  ---> Flash "Another farm with that name already exists"
    |       |--- YES ---> Update Farm.name
    |                       Flash "Farm updated successfully"
    |
    +--- DELETE: Select farm
            |
            v
         [Has associated feeds?]
            |--- YES ---> Block deletion, show warning
            |--- NO  ---> Delete Farm record
                           Flash "Farm deleted successfully"
```

### 7.4 Animal Registration Flow

```
User navigates to /cow_registry
    |
    v
Display cow registration form + existing cows list
    |
    v
[POST: Submit new cow]
    |
    v
Validate: name, breed, category (required)
    |--- FAIL ---> Flash error, re-render form
    |--- PASS ---> Check duplicate name
                    |--- EXISTS ---> Flash "A cow with that name already exist"
                    |--- UNIQUE --> Create AnimalRegistry:
                                       name, breed, dob, category, sex, mother
                                       farm_id = current_entry_farm_id()
                                       |
                                       v
                                   Flash "Successfully added"
                                   Show updated cow list
```

### 7.5 Calf Registration Flow

```
User navigates to /calf_registry
    |
    v
Display calf registration form + existing calves
    |
    v
[POST: Submit new calf]
    |
    v
Validate: name, breed, DOB, mother (required)
    |--- FAIL ---> Flash "All fields are required"
    |--- PASS ---> Check name uniqueness
                    |--- EXISTS ---> Flash "Another livestock bears the same name"
                    |--- UNIQUE --> Check mother exists in AnimalRegistry
                                     |--- MISSING --> Flash "The mother you entered does not exist"
                                     |--- EXISTS --> Create AnimalRegistry:
                                                        name, breed, dob
                                                        category = level
                                                        mother = mother_name
                                                        farm_id = current_entry_farm_id()
                                                        |
                                                        v
                                                    Flash "Successfully added"
```

### 7.6 Cow Shed Management Flow

```
User navigates to /sheds
    |
    v
Display sheds with occupancy + management panel
    |
    +--- CREATE SHED:
    |       Enter: name, capacity, category_allowed, color, description
    |       [Name exists?] ---> Flash warning
    |       [Unique] ---> Create CowShed record
    |
    +--- EDIT SHED:
    |       Select shed (via ?edit=id)
    |       Modify fields
    |       [Name conflicts?] ---> Flash warning
    |       [OK] ---> Update CowShed
    |
    +--- MANAGE SHED:
    |       Select shed (via ?manage=id)
    |       Show available cows + shed cows
    |
    +--- ASSIGN COW:
    |       /assign_shed/<cow_id>/<shed_id>
    |       [Shed full?] ---> Flash "Shed is full"
    |       [Space] ---> Set cow.current_shed_id = shed.id
    |
    +--- REMOVE COW:
    |       /remove_from_shed/<cow_id>
    |       Set cow.current_shed_id = None
    |
    +--- MOVE COW:
            /move_animal/<animal_id>
            Enter: new_shed_id, reason
            [Target full?] ---> Flash error
            [OK] ---> Update cow.current_shed_id
                       Create AnimalMovement record
                       Flash "Animal moved successfully"
```

### 7.7 Milking Herd Management Flow

```
User navigates to /manage_milking
    |
    v
Display all animals + current milking herd (farm-scoped)
    |
    v
[POST: Bulk action]
    |
    +--- "Add Selected":
    |       For each selected animal_id:
    |           [Already in MilkingHerd?] ---> Skip
    |           [New] ---> Create MilkingHerd(animal_id=aid)
    |
    +--- "Remove Selected":
            For each selected animal_id:
                Find MilkingHerd record
                Delete it
    |
    v
Redirect to /manage_milking (refresh)
```

### 7.8 Milk Production Recording Flow

```
User navigates to /milk_registry
    |
    v
Display milking herd cows (farm-scoped)
with input fields: morning[], noon[], evening[]
    |
    v
User selects date + fills production values
    |
    v
[POST: Save milk records]
    |
    v
For each cow_id in form:
    |
    +--- Parse morning, noon, evening (empty = None)
    |       Calculate total = morning + noon + evening
    |
    +--- [Record exists for cow+date?]
    |       |--- YES ---> Update existing record fields
    |       |--- NO  ---> [total > 0?]
    |                       |--- YES ---> Create new MilkRegistry:
    |                                      cow_id, date, morning, noon, evening, total
    |                                      farm_id = current_entry_farm_id()
    |                       |--- NO  ---> Skip (no data)
    |
    v
db.session.commit()
Flash "Milk records saved successfully"
Redirect to /milk_registry
```

### 7.9 Milk Excel Import Flow

```
Step 1: Export Template
    /milk_registry/export_template
    |
    v
Load MilkingHerd cows
Generate Excel: Cow ID, Cow Name, Morning (empty), Noon (empty), Evening (empty)
    |
    v
Download milk_template.xlsx

Step 2: User fills Excel offline

Step 3: Upload
    /milk_registry/import (POST)
    |
    v
Read Excel file + selected date
    |
    v
For each row:
    Parse Cow ID, Morning, Noon, Evening
    Calculate total
    [Cow in MilkingHerd?]
        |--- YES ---> Add to imported_records list
        |--- NO  ---> Skip silently
    |
    v
Show confirm_milk_import.html:
    Table of parsed records + total milk
    |
    v
[User confirms]
    /milk_registry/confirm_import (POST)
    |
    v
For each confirmed record:
    [Record exists for cow+date?]
        |--- YES ---> Update
        |--- NO  ---> Create MilkRegistry
    |
    v
db.session.commit()
Flash "Imported milk records saved successfully"
```

### 7.10 Milk Sales Entry Flow

```
User navigates to /milk_sales_entry
    |
    v
Display sales form:
    Date picker
    Morning: shop1, shop2, shop3, home, calf, price
    Noon:    shop1, shop2, shop3, home, calf, price
    Evening: shop1, shop2, shop3, home, calf, price
    Actual Remaining: ___
    |
    v
[POST: Save sales]
    |
    v
For each session (Morning, Noon, Evening):
    Create MilkSalesRegistry:
        date, session, shop1-3, home, calf, price
        farm_id = current_entry_farm_id()
    [Only if any value > 0]
    |
    v
Save/update MilkDailyRemaining:
    date, actual_remaining
    |
    v
db.session.commit()
Redirect to /milk_sales_entry
```

### 7.11 Milk Stock Tracking Flow

```
[Called by get_milk_sales() and calculate_stock()]

1. LOAD ALL DATA (4 queries):
   - All production records (filtered by farm)
   - All sales records (filtered by farm)
   - All remaining records
   - All price records

2. BUILD PRICE CACHE:
   Sort prices by effective_date
   Store as parallel arrays for bisect_right lookup

3. CALCULATE TODAY'S PRODUCTION:
   For each record on selected_date:
       Sum morning, noon, evening, total
       Count cows, calculate average (for cows > 10L)

4. CALCULATE TODAY'S SALES:
   For each sales record on selected_date:
       Sum shop1-3 (sold), home, calf (used)
       Calculate revenue using date-aware pricing

5. CALCULATE STOCK:
   Build daily production map (date -> total)
   Build daily usage map (date -> total used)
   Build actual remaining map (date -> actual)
   
   For each date in chronological order:
       running_system += produced - used
       
       On selected_date:
           system_available_today = running_system
           actual_available_today = MilkDailyRemaining for that date
   
   variance = actual - system
   conversion% = (sold / available) * 100
   error% = (|variance| / system_available) * 100
```

### 7.12 Insemination Management Flow

```
ADD: /insemination/add
    |
    v
Select animal, date_served, confirmation_method
    |
    v
Calculate confirmation_date:
    heat observation -> +21 days
    ultrasound       -> +30 days
    manual check     -> +90 days
    |
    v
Create Insemination:
    animal_id, date_served, confirmation_method
    confirmation_date, status="pending"
    farm_id = animal.farm_id

LIST: /insemination
    |
    v
Filter by: status (default: confirmed), month, year, farm_id
Sort by: date_served DESC
Display: animal name, dates, status, calving_date

EDIT: /insemination/edit/<id>
    |
    v
Modify: animal, date_served, status
    |
    v
Status-based logic:
    "confirmed" -> calving_date = date_served + 283 days
    "aborted"   -> calving_date = None
    "delivered"  -> calving_date = today (if not set)
    "pending"   -> calving_date = None
```

### 7.13 Treatment Management Flow

```
ADD: /add_treatment
    |
    v
Select animal (farm-scoped for non-admin)
Enter: date, illness, cost, vet, status (healed/recovering)
    |
    v
Create Treatment:
    animal_id, date_treated, illness, cost, vet, status
    farm_id = current_entry_farm_id()

LIST: /treatment
    |
    v
Filter by: date, status, farm_id
Calculate: daily_total, month_total, quarter_total, year_total costs
Count: healed, recovering
Display: records with cost summaries

EDIT: /edit_treatment/<id>
    Modify: status, cost
    [Farm permission check for non-admin]

DELETE: /delete_treatment/<id> or bulk delete
```

### 7.14 Feeds Order Lifecycle Flow

```
CREATE ORDER: /feeds_v2/create
    |
    v
Select farm, date
Add feed items (name, qty, price)
Auto-generate order_ref: FR-YYYYMMDD-NNN
    |
    v
Create FeedsOrderV2 + FeedsOrderItemV2 records

DELIVER: /feeds_v2/delivery/<order_id>
    |
    v
Select item from order
Enter: pieces, unit_weight
Auto-calculate: quantity_delivered = pieces * unit_weight
    |
    v
[quantity_delivered <= remaining?]
    |--- NO  ---> Flash "Cannot exceed remaining"
    |--- YES ---> Create FeedsDeliveryV2
                   |
                   v
               Order status auto-updates:
                   Pending (no deliveries)
                   Partial (some delivered)
                   Full (all delivered)

PAY: /feeds_v2/payment/<order_id>
    |
    v
Enter: date_paid, amount, account
    |
    v
Create Payment:
    purpose_type = "feeds"
    purpose = "Feeds Order {order_ref}"
    farm_id = order.farm_id
    |
    v
Payment status auto-updates:
    Debt (balance > 0)
    Cleared (balance <= 0)

VIEW ORDER: /feeds_v2/view/<id>
    Show: items with delivery status + price comparison
          payment summary (total, paid, balance)
```

### 7.15 Vehicle Management Flow

```
REGISTER: /car_registry
    Enter: plate_number, model, driver
    Create CarRegistry(active=True)
    Display: active cars + inactive cars

EXPENSE: /add_car_expense
    Select active car, date, type, description, amount
    Create CarExpense record

SALE: /car_sales/add
    Select active car, date, length (FULL/HALF)
    Auto-calculate amount: FULL=10000, HALF=5000
    Create CarSales record

ANALYTICS: /vehicle_analytics
    Filter by: month, car
    Per-car: sales, expenses, profit, counts
    Overall: fleet totals
    Detailed breakdown for selected car
```

### 7.16 Financial Dashboard Flow

```
/financial_dashboard (Admin only)
    |
    v
INDEPENDENT DATE FILTERS:
    Milk Date (default: today)
    Vehicle Date (optional: all if empty)
    Expense Date (default: today)
    |
    v
AGGREGATE DATA:
    Milk Revenue = get_milk_sales(milk_date).daily_revenue
    Vehicle Revenue = get_sales_report_data(vehicle_date).total_sales
    Vehicle Expenses = get_car_expense_report_data(vehicle_date).total_expense
    Feed Expenses = get_transactions_data(expense_date).feed_daily
    Other Expenses = get_transactions_data(expense_date).other_daily
    Employee Salaries = sum(all employee salaries)
    |
    v
CALCULATE:
    Total Revenue = Milk Revenue + Vehicle Revenue
    Total Expense = Feed + Other + Vehicle + Salary
    Net Profit = Revenue - Expense
    Profit Margin = (Net Profit / Revenue) * 100
    |
    v
Render financial_dashboard.html with all data
```

### 7.17 PDF Report Generation Flow

```
User clicks "Download PDF" on any report page
    |
    v
GET /send_report/<report_type>?date=...&status=...
    |
    v
[Switch on report_type]:
    milk           -> get_milk_report_data()       -> milk_pdf.html
    car_expenses   -> get_car_expense_report_data() -> car_expenses_reportpdf.html
    car_sales      -> get_sales_report_data()      -> car_sales_reportpdf.html
    animals        -> get_animals_data()            -> animals_pdf.html
    shed_report    -> get_shed_report_data()        -> shed_report_pdf.html
    treatment      -> get_treatment_data()          -> treatment_pdf.html
    insemination   -> get_insemination_data()       -> insemination_pdf.html
    milk_sale      -> get_milk_sales()             -> milk_sales_reportpdf.html
    transactions   -> get_transactions_data()       -> transactions_pdf.html
    cow_analysis   -> get_monthly_cow_analysis()    -> cow_analysis_pdf.html
    milk_sales_monthly -> get_milk_sales_monthly()  -> milk_sales_monthly_pdf.html
    feeds_orders   -> get_orders()                 -> pdf/feeds_orders.html
    feeds_order_detail -> build_order_summary()    -> pdf/order_detail.html
    feeds_delivery -> query deliveries             -> pdf/delivery.html
    feeds_payments -> query payments               -> pdf/payments.html
    employees      -> get_employees_data()          -> employees_pdf.html
    |
    v
render_template(template_name, **data) -> HTML string
    |
    v
WeasyPrint: HTML(string=rendered_html).write_pdf(file_path)
    |
    v
send_file(pdf_path, as_attachment=True, mimetype="application/pdf")
```

### 7.18 Transaction/Payment Management Flow

```
ADD PAYMENT: /payments (POST)
    |
    v
Enter: date_paid, amount, account, purpose, purpose_type, farm_id
[All fields required?]
    |--- NO  ---> Flash "All fields required"
    |--- YES ---> Create Payment record
                   [Farm user?] -> Can add but cannot see history
                   [Admin?] -> Can see all history

VIEW HISTORY: /transactions (Admin only)
    |
    v
Filter by: date, month, purpose (feeds/other), farm_id
    |
    v
Calculate period totals: month, quarter, year
Separate feed vs other expenses
Display transaction list with summaries

EDIT: /edit_transaction/<id>
    Update: date, amount, account, purpose_type, purpose, farm_id
    Preserve filter context on redirect

DELETE: /delete_transaction/<id>
    Delete and return to filtered list
```

---

## Appendix: Route Summary

| Route | Method | Auth | Role | Description |
|---|---|---|---|---|
| `/` | GET | No | - | Landing page |
| `/login` | GET/POST | No | - | User login |
| `/logout` | GET | Yes | - | User logout |
| `/forgot` | GET/POST | No | - | Forgot password |
| `/verify_otp` | GET/POST | No | - | OTP verification |
| `/reset_password` | GET/POST | No | - | Password reset |
| `/dashboard` | GET | Yes | Any | Main dashboard |
| `/select-farm` | GET/POST | Yes | - | Farm selection |
| `/set-farm/<id>` | GET | Yes | Any | Farm context switch |
| `/users` | GET/POST | Yes | Admin | User management |
| `/edit_user/<id>` | POST | Yes | Admin | Edit user |
| `/delete_user/<id>` | POST | Yes | Admin | Delete user |
| `/farms` | GET/POST | Yes | Admin | Farm management |
| `/access_denied` | GET | Yes | - | Access denied page |
| `/cow_registry` | GET/POST | Yes | Any | Animal registration |
| `/animals` | GET | Yes | Any | Animal listing |
| `/edit_animal_record/<id>` | GET/POST | Yes | Any | Edit animal |
| `/delete_cow/<id>` | GET/POST | Yes | Any | Delete animal |
| `/calf_registry` | GET/POST | Yes | Any | Calf registration |
| `/sheds` | GET/POST | Yes | Any | Shed management |
| `/assign_shed/<cow_id>/<shed_id>` | GET | Yes | Any | Assign to shed |
| `/remove_from_shed/<cow_id>` | GET | Yes | Any | Remove from shed |
| `/move_animal/<animal_id>` | POST | Yes | Any | Move between sheds |
| `/shed_report` | GET | Yes | Any | Shed occupancy report |
| `/manage_milking` | GET/POST | Yes | Any | Milking herd mgmt |
| `/milk_registry` | GET/POST | Yes | Any | Milk production entry |
| `/milk_registry/export_template` | GET | Yes | Any | Export Excel template |
| `/milk_registry/import` | POST | Yes | Any | Import Excel |
| `/milk_registry/confirm_import` | POST | Yes | Any | Confirm import |
| `/milk` | GET/POST | Yes | Any | Milk records list |
| `/edit_milk/<id>` | GET/POST | Yes | Any | Edit milk record |
| `/delete_milk/<id>` | GET | Yes | Any | Delete milk record |
| `/cow-analysis` | GET | Yes | Any | Cow production analysis |
| `/milk_sales_entry` | GET/POST | Yes | Any | Sales entry |
| `/milk_sales_report` | GET | Yes | Any | Sales report |
| `/edit_milk_sale/<id>` | GET/POST | Yes | Any | Edit sale |
| `/delete_milk_sale/<id>` | GET | Yes | Any | Delete sale |
| `/milk_prices` | GET/POST | Yes | Admin | Milk price management |
| `/delete_milk_price/<id>` | GET | Yes | Admin | Delete price |
| `/milk_sales_monthly` | GET | Yes | Any | Monthly sales report |
| `/milk_dashboard` | GET | Yes | Any | Milk analytics dashboard |
| `/cow_dashboard` | GET | Yes | Any | Cow analytics dashboard |
| `/insemination` | GET | Yes | Any | Insemination list |
| `/insemination/add` | GET/POST | Yes | Any | Add insemination |
| `/insemination/edit/<id>` | GET/POST | Yes | Any | Edit insemination |
| `/insemination/delete/<id>` | GET | Yes | Any | Delete insemination |
| `/treatment` | GET/POST | Yes | Any | Treatment list |
| `/add_treatment` | GET/POST | Yes | Any | Add treatment |
| `/edit_treatment/<id>` | GET/POST | Yes | Any | Edit treatment |
| `/delete_treatment/<id>` | GET | Yes | Any | Delete treatment |
| `/feeds_v2/orders` | GET | Yes | Admin | Orders list |
| `/feeds_v2/create` | GET/POST | Yes | Admin | Create order |
| `/feeds_v2/view/<id>` | GET | Yes | Admin | View order |
| `/feeds_v2/delete/<id>` | POST | Yes | Admin | Delete order |
| `/feeds_v2/item/add/<id>` | GET/POST | Yes | Admin | Add item |
| `/feeds_v2/item/edit/<id>` | GET/POST | Yes | Admin | Edit item |
| `/feeds_v2/item/delete/<id>` | POST | Yes | Admin | Delete item |
| `/feeds_v2/delivery/<id>` | GET/POST | Yes | Admin | Record delivery |
| `/feeds_v2/delivery_report` | GET | Yes | Admin | Delivery report |
| `/feeds_v2/delivery/edit/<id>` | GET/POST | Yes | Admin | Edit delivery |
| `/feeds_v2/delivery/delete/<id>` | POST | Yes | Admin | Delete delivery |
| `/feeds_v2/payment/<id>` | GET/POST | Yes | Admin | Record payment |
| `/feeds_v2/payment_report` | GET | Yes | Admin | Payment report |
| `/feeds_v2/payment/edit/<id>` | GET/POST | Yes | Admin | Edit payment |
| `/feeds_v2/payment/delete/<id>` | POST | Yes | Admin | Delete payment |
| `/feeds_v2/search_feed` | GET | Yes | Admin | Feed name search |
| `/car_registry` | GET/POST | Yes | Admin | Vehicle registration |
| `/cars/edit/<id>` | POST | Yes | Admin | Edit vehicle |
| `/cars/deactivate/<id>` | POST | Yes | Admin | Deactivate vehicle |
| `/cars/reactivate/<id>` | POST | Yes | Admin | Reactivate vehicle |
| `/add_car_expense` | GET/POST | Yes | Admin | Add car expense |
| `/car_expense_report` | GET | Yes | Admin | Car expense report |
| `/edit_car_expense/<id>` | GET/POST | Yes | Admin | Edit car expense |
| `/delete_car_expense/<id>` | GET | Yes | Admin | Delete car expense |
| `/car_sales/add` | GET/POST | Yes | Admin | Add car sale |
| `/car_sales_report` | GET | Yes | Admin | Car sales report |
| `/edit_car_sale/<id>` | GET/POST | Yes | Admin | Edit car sale |
| `/delete_car_sale/<id>` | GET | Yes | Admin | Delete car sale |
| `/vehicle_analytics` | GET | Yes | Admin | Vehicle analytics |
| `/employee_registry` | GET/POST | Yes | Admin | Employee registration |
| `/Employees` | GET/POST | Yes | Admin | Employee list |
| `/employees/edit/<id>` | GET/POST | Yes | Admin | Edit employee |
| `/employees/delete/<id>` | POST | Yes | Admin | Delete employee |
| `/asset_registry` | GET/POST | Yes | Any | Asset registration |
| `/Assets` | GET/POST | Yes | Admin | Asset list |
| `/payments` | GET/POST | Yes | Any | Payment entry |
| `/transactions` | GET | Yes | Admin | Transaction history |
| `/edit_transaction/<id>` | GET/POST | Yes | Admin | Edit transaction |
| `/delete_transaction/<id>` | GET | Yes | Admin | Delete transaction |
| `/financial_dashboard` | GET | Yes | Admin | Financial dashboard |
| `/send_report/<type>` | GET | Yes | Any | PDF report download |
| `/health` | GET | No | - | Health check |

---

*Document generated on: 2026-09-03*
*System: MY FARM ERP v1.0*
*Total Models: 28 | Total Routes: 80+ | Total Templates: 78*
