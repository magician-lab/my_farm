
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from models import db, CalfRegistry, Insemination, AssetsRegistry, ExpensesRegistry, EmployeesRegistry, ShopRegistry, UserRegistry, FeedsRegistry, MilkRegistry, MilkSalesRegistry, CarRegistry, CarExpense, AnimalRegistry, MilkingHerd, CarSales, Treatment,Farm,Payment, MilkDailyRemaining, Admin, FeedsOrderV2, FeedsDeliveryV2, FeedsOrderItemV2, MilkPrice,CowShed,AnimalMovement
from sqlalchemy.exc import IntegrityError
from decimal import Decimal

from datetime import date, datetime
from sqlalchemy import extract, func
import os
from flask_mail import Mail, Message
import pandas as pd
import os
import random
import os
# from dotenv import load_dotenv

# load_dotenv()

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = (
    os.environ.get("DATABASE_URL") or "sqlite:///database.db"
)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'supersecretkey123'

app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
    "pool_recycle": 300
}

db.init_app(app)

# =========================================================
# CREATE TABLES + DEFAULT ADMIN
# =========================================================

with app.app_context():

    # Create tables
    db.create_all()

    # =====================================================
    # MIGRATIONS (additive columns, safe on SQLite + PostgreSQL)
    # Adds any model column missing from the database and
    # backfills farm_id (existing data = Murang'a farm) and
    # car active = TRUE. NEVER drops or rewrites data.
    # =====================================================

    from sqlalchemy import inspect as sa_inspect, text

    insp = sa_inspect(db.engine)

    # per-column backfill values for newly added columns
    PG = db.engine.dialect.name == "postgresql"

    def backfill_literal(col_name):
        if col_name == "farm_id":
            return "1"
        return "TRUE" if PG else "1"

    for table in db.metadata.sorted_tables:

        try:
            existing = {c["name"] for c in insp.get_columns(table.name)}
        except Exception:
            continue

        for col in table.columns:

            if col.name in existing:
                continue

            col_type = col.type.compile(db.engine.dialect)

            ddl = 'ALTER TABLE "%s" ADD COLUMN "%s" %s' % (
                table.name,
                col.name,
                col_type
            )

            with db.engine.connect() as conn:
                conn.execute(text(ddl))
                conn.commit()

            if col.name in ("farm_id", "active"):
                with db.engine.connect() as conn:
                    conn.execute(text(
                        'UPDATE "%s" SET "%s" = %s WHERE "%s" IS NULL' % (
                            table.name,
                            col.name,
                            backfill_literal(col.name),
                            col.name
                        )
                    ))
                    conn.commit()

            print("Migration: added %s.%s" % (table.name, col.name))

    # =====================================================
    # CHECK IF ADMIN EXISTS
    # =====================================================

    existing_admin = Admin.query.filter_by(
        username="admin"
    ).first()

    # =====================================================
    # CREATE DEFAULT ADMIN ONLY ONCE
    # =====================================================

    if not existing_admin:

        admin = Admin(

            username="admin",

            email="kephakimathikanyola@gmail.com",

            password=generate_password_hash("admin123"),

            role="admin"
        )

        db.session.add(admin)

        db.session.commit()

        print("Created admin Default admin created")

    else:

        print("Created admin Admin already exists")

    # =====================================================
    # DEFAULT FARMS
    # =====================================================

    default_farms = ["Murang'a", "Meru"]

    for fname in default_farms:

        if not Farm.query.filter_by(name=fname).first():
            db.session.add(Farm(name=fname))

    db.session.commit()

    # =====================================================
    # DEFAULT USERS PER FARM
    # =====================================================

    default_users = [
        # (username, email, password, role, farm_name)
        ("muranga", "muranga.farm@gmail.com", "muranga123", "user", "Murang'a"),
        ("meru", "meru.farm@gmail.com", "meru123", "user", "Meru"),
    ]

    for uname, uemail, upass, urole, farm_name in default_users:

        existing_user = Admin.query.filter_by(username=uname).first()

        if not existing_user:

            farm = Farm.query.filter_by(name=farm_name).first()

            db.session.add(Admin(
                username=uname,
                email=uemail,
                password=generate_password_hash(upass),
                role=urole,
                farm_id=farm.id if farm else None
            ))

    db.session.commit()


@app.before_request
def require_login():

    if request.endpoint is None:
        return

    allowed = [
        "landing",
        "login",
        "forgot",
        "verify_otp",
        "reset_password",
        "logout",
        "static"
    ]

    # Skip static files
    if request.endpoint.startswith("static"):
        return

    # If not logged in
    if not session.get("logged_in") and request.endpoint not in allowed:
        return redirect(url_for("login"))


# =========================================================
# TEMPLATE CONTEXT (farms, current farm, role helpers)
# =========================================================

@app.context_processor
def inject_farm_context():

    if session.get("logged_in"):

        farms = Farm.query.order_by(Farm.name).all()

        is_admin = session.get("role") == "admin"

        # Admin farm context: session farm_id (0/None = all farms)
        if is_admin:
            current_farm_id = session.get("farm_id")
        else:
            current_farm_id = session.get("farm_id")

        current_farm = None
        if current_farm_id:
            current_farm = Farm.query.get(current_farm_id)

        return dict(
            farms=farms,
            current_farm=current_farm,
            current_farm_id=current_farm_id,
            is_admin=is_admin
        )

    return dict(farms=[], current_farm=None, current_farm_id=None, is_admin=False)


# =========================================================
# FARM HELPER
# =========================================================

def current_entry_farm_id():
    """
    Returns the farm a new record should be associated with:
    - Non-admin users: their assigned farm (locked)
    - Admin: the farm context selected in the switcher,
      otherwise defaults to the first farm (Murang'a)
    """
    farm_id = session.get("farm_id")

    if farm_id:
        return farm_id

    first = Farm.query.order_by(Farm.id).first()

    return first.id if first else None


# =========================================================
# LANDING PAGE
# =========================================================

@app.route("/")
def landing():

    # If already logged in, go straight to the dashboard
    if session.get("logged_in"):
        return redirect(url_for("main_dashboard"))

    farms = Farm.query.order_by(Farm.name).all()

    return render_template("landing.html", farms=farms)


# =========================================================
# LOGIN REQUIRED DECORATOR
# =========================================================

def login_required(f):

    @wraps(f)
    def wrapper(*args, **kwargs):

        if not session.get("logged_in"):
            return redirect(url_for("login"))

        return f(*args, **kwargs)

    return wrapper


# =========================================================
# ROLE REQUIRED DECORATOR
# =========================================================

def role_required(*roles):

    def decorator(f):

        @wraps(f)
        def wrapper(*args, **kwargs):

            # Not logged in
            if not session.get("logged_in"):
                return redirect(url_for("login"))

            user_role = session.get("role")

            # Access denied
            if user_role not in roles:

                flash(
                    "Access denied. You are not authorized.",
                    "error"
                )

                return redirect(url_for("access_denied"))

            # Farm permission check for non-admin users
            user_farm_id = session.get("farm_id")
            if user_role != "admin" and user_farm_id:
                # Check if the route has a farm_id parameter or if the
                # function needs farm context
                if "farm_id" in kwargs:
                    if kwargs["farm_id"] != user_farm_id:
                        flash(
                            "Access denied. You don't have permission for this farm.",
                            "error"
                        )
                        return redirect(url_for("select_farm"))
                elif "farm_id" in args:
                    if args[args.index("farm_id") + 1] != user_farm_id:
                        flash(
                            "Access denied. You don't have permission for this farm.",
                            "error"
                        )
                        return redirect(url_for("select_farm"))

            return f(*args, **kwargs)

        return wrapper

    return decorator


# =========================================================
# ACCESS DENIED PAGE
# =========================================================

@app.route("/access_denied")
@login_required
def access_denied():
    return render_template("access_denied.html")


# =========================================================
# FARM SELECTION
# =========================================================

@app.route("/select-farm", methods=["GET", "POST"])
def select_farm():

    # Users with an assigned farm skip selection
    if session.get("farm_id"):
        return redirect(url_for("main_dashboard"))

    farms = Farm.query.all()

    if request.method == "POST":
        farm_id = request.form.get("farm_id")
        if farm_id:
            session["farm_id"] = int(farm_id)
            flash("Farm selected successfully", "success")
            return redirect(url_for("main_dashboard"))

    return render_template("select_farm.html", farms=farms)


# =========================================================
# FARM SWITCHER (admin can switch farm context)
# =========================================================

@app.route("/set-farm/<int:farm_id>")
@login_required
def set_farm(farm_id):

    # farm_id = 0 means all farms (admin)
    if farm_id == 0:
        session.pop("farm_id", None)
        flash("Showing all farms", "success")
    else:
        farm = Farm.query.get(farm_id)
        if farm:
            session["farm_id"] = farm_id
            flash(f"Now viewing: {farm.name}", "success")

    return redirect(request.referrer or url_for("main_dashboard"))


# =========================================================
# MAIN DASHBOARD (with farm context)
# =========================================================

@app.route("/dashboard")
@login_required
def main_dashboard():

    from datetime import date

    # Date filter: default today, driven by ?filter_date=
    date_str = request.args.get("filter_date")
    if date_str:
        try:
            selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            selected_date = date.today()
    else:
        selected_date = date.today()

    # Farm context: admin can switch farms via the switcher,
    # farm users are locked to their assigned farm
    farm_id = session.get("farm_id")

    # One analytics engine call handles production + sales + stock,
    # all filtered by date and farm
    analytics = get_milk_sales(
        selected_date.strftime("%Y-%m-%d"),
        farm_id
    )

    # Farm counts
    if farm_id:
        total_animals = AnimalRegistry.query.filter_by(farm_id=farm_id).count()
        recent_insem = Insemination.query.filter_by(farm_id=farm_id).order_by(
            Insemination.date_served.desc()
        ).limit(5).all()
    else:
        total_animals = AnimalRegistry.query.count()
        recent_insem = Insemination.query.order_by(
            Insemination.date_served.desc()
        ).limit(5).all()

    farms = Farm.query.all()

    # Per-farm stats for admin overview
    animals_by_farm = {}

    if session.get("role") == "admin":

        for f in Farm.query.all():

            animals_by_farm[f.id] = {
                "animals": AnimalRegistry.query.filter_by(
                    farm_id=f.id
                ).count(),
                "milk": MilkRegistry.query.filter_by(
                    farm_id=f.id
                ).count()
            }

    return render_template(
        "main_dashboard.html",
        total_animals=total_animals,
        recent_insem=recent_insem,
        farms=farms,
        is_admin=session.get("role") == "admin",
        animals_by_farm=animals_by_farm,
        **analytics
    )


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        user = Admin.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):

            # =========================
            # CREATE SESSION
            # =========================

            session["logged_in"] = True
            session["user_id"] = user.id
            session["username"] = user.username
            session["role"] = user.role
            session["farm_id"] = user.farm_id

            print("LOGIN SUCCESS")

            # If admin, go to main dashboard (all farms); farm users go
            # straight to their farm dashboard; users without a farm pick one
            if user.role == "admin":
                return redirect(url_for("main_dashboard"))
            elif user.farm_id:
                return redirect(url_for("main_dashboard"))
            else:
                return redirect(url_for("select_farm"))

        else:

            print("LOGIN FAILED")

            flash(
                "Invalid username or password",
                "error"
            )

    return render_template("login.html")


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
@login_required
def logout():

    session.clear()

    flash(
        "Logged out successfully",
        "success"
    )

    return redirect(url_for("login"))


# =========================================================
# USER MANAGEMENT
# =========================================================

@app.route("/users", methods=["GET", "POST"])
@login_required
@role_required("admin")
def manage_users():

    # =====================================================
    # ADD USER
    # =====================================================

    if request.method == "POST":

        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        role = request.form.get("role")
        farm_id = request.form.get("farm_id")

        # =================================================
        # VALIDATION
        # =================================================

        if not username or not email or not password or not role:

            flash(
                "All fields are required",
                "error"
            )

            return redirect(url_for("manage_users"))

        # =================================================
        # CHECK DUPLICATE EMAIL
        # =================================================

        existing_email = Admin.query.filter_by(email=email).first()

        if existing_email:

            flash(
                "Email already exists",
                "error"
            )

            return redirect(url_for("manage_users"))

        # =================================================
        # CHECK DUPLICATE USERNAME
        # =================================================

        existing_user = Admin.query.filter_by(username=username).first()

        if existing_user:

            flash(
                "Username already exists",
                "error"
            )

            return redirect(url_for("manage_users"))

        # =================================================
        # CREATE USER
        # =================================================

        new_user = Admin(
            username=username,
            email=email,
            password=generate_password_hash(password),
            role=role,
            farm_id=int(farm_id) if farm_id else None
        )

        db.session.add(new_user)
        db.session.commit()

        flash(
            "User added successfully",
            "success"
        )

        return redirect(url_for("manage_users"))

    # =====================================================
    # VIEW USERS
    # =====================================================

    users = Admin.query.all()
    farms = Farm.query.all()

    return render_template(
        "users.html",
        users=users,
        farms=farms
    )


# =========================================================
# EDIT USER
# =========================================================

@app.route("/edit_user/<int:id>", methods=["POST"])
@login_required
@role_required("admin")
def edit_user(id):

    user = Admin.query.get_or_404(id)

    username = request.form.get("username")
    email = request.form.get("email")
    password = request.form.get("password")
    role = request.form.get("role")
    farm_id = request.form.get("farm_id")

    # =====================================================
    # VALIDATION
    # =====================================================

    if not username or not email or not role:

        flash(
            "Username, email and role are required",
            "error"
        )

        return redirect(url_for("manage_users"))

    # =====================================================
    # CHECK DUPLICATE EMAIL
    # =====================================================

    existing_email = Admin.query.filter_by(email=email).first()

    if existing_email and existing_email.id != user.id:

        flash(
            "Email already exists",
            "error"
        )

        return redirect(url_for("manage_users"))

    # =====================================================
    # CHECK DUPLICATE USERNAME
    # =====================================================

    existing_username = Admin.query.filter_by(username=username).first()

    if existing_username and existing_username.id != user.id:

        flash(
            "Username already exists",
            "error"
        )

        return redirect(url_for("manage_users"))

    # =====================================================
    # UPDATE USER
    # =====================================================

    user.username = username
    user.email = email
    user.role = role
    user.farm_id = int(farm_id) if farm_id else None

    # Only update password if entered
    if password:
        user.password = generate_password_hash(password)

    db.session.commit()

    flash(
        "User updated successfully",
        "success"
    )

    return redirect(url_for("manage_users"))


# =========================================================
# DELETE USER
# =========================================================

@app.route("/delete_user/<int:id>", methods=["POST"])
@login_required
@role_required("admin")
def delete_user(id):

    user = Admin.query.get_or_404(id)

    # =====================================================
    # PREVENT SELF DELETE
    # =====================================================

    if session.get("user_id") == user.id:

        flash(
            "You cannot delete your own account",
            "error"
        )

        return redirect(url_for("manage_users"))

    db.session.delete(user)
    db.session.commit()

    flash(
        "User deleted successfully",
        "success"
    )

    return redirect(url_for("manage_users"))


# =========================================================
# FORGOT PASSWORD
# =========================================================

@app.route("/forgot", methods=["GET", "POST"])
def forgot():

    if request.method == "POST":

        email = request.form.get("email")

        user = Admin.query.filter_by(email=email).first()

        if user:

            # =================================================
            # GENERATE OTP
            # =================================================

            otp = str(random.randint(100000, 999999))

            user.otp_code = otp
            user.otp_expiration = datetime.utcnow() + timedelta(minutes=10)

            db.session.commit()

            # =================================================
            # SEND EMAIL
            # =================================================

            msg = Message(
                subject="Password Reset OTP",
                recipients=[email]
            )

            msg.body = f"""
Your OTP is: {otp}

It expires in 10 minutes.
"""

            mail.send(msg)

            session["reset_email"] = email

            flash(
                "OTP sent to your email",
                "success"
            )

            return redirect(url_for("verify_otp"))

        else:

            flash(
                "Email not found",
                "error"
            )

    return render_template("forgot.html")


# =========================================================
# VERIFY OTP
# =========================================================

@app.route("/verify_otp", methods=["GET", "POST"])
def verify_otp():

    if request.method == "POST":

        otp = request.form.get("otp")

        email = session.get("reset_email")

        if not email:

            flash(
                "Session expired",
                "error"
            )

            return redirect(url_for("forgot"))

        user = Admin.query.filter_by(email=email).first()

        if user and user.otp_code == otp:

            # =============================================
            # CHECK OTP EXPIRATION
            # =============================================

            if datetime.utcnow() <= user.otp_expiration:

                session["otp_verified"] = True

                flash(
                    "OTP verified successfully",
                    "success"
                )

                return redirect(url_for("reset_password"))

            else:

                flash(
                    "OTP expired",
                    "error"
                )

        else:

            flash(
                "Invalid OTP",
                "error"
            )

    return render_template("verify_otp.html")


# =========================================================
# RESET PASSWORD
# =========================================================

@app.route("/reset_password", methods=["GET", "POST"])
def reset_password():

    # =====================================================
    # CHECK OTP VERIFIED
    # =====================================================

    if not session.get("otp_verified"):
        return redirect(url_for("login"))

    if request.method == "POST":

        new_password = request.form.get("password")

        email = session.get("reset_email")

        if not email:

            flash(
                "Session expired",
                "error"
            )

            return redirect(url_for("forgot"))

        user = Admin.query.filter_by(email=email).first()

        if not user:

            flash(
                "User not found",
                "error"
            )

            return redirect(url_for("forgot"))

        # =================================================
        # UPDATE PASSWORD
        # =================================================

        user.password = generate_password_hash(new_password)

        # CLEAR OTP
        user.otp_code = None
        user.otp_expiration = None

        db.session.commit()

        # CLEAR SESSION
        session.clear()

        flash(
            "Password reset successful",
            "success"
        )

        return redirect(url_for("login"))

    return render_template("reset.html")


from datetime import datetime
from sqlalchemy import func

# ================================
# 🔹 GENERATE ORDER REF
# ================================
def generate_order_ref():
    today_str = datetime.now().strftime("%Y%m%d")

    last = FeedsOrderV2.query.filter(
        FeedsOrderV2.order_ref.like(f"FR-{today_str}-%")
    ).order_by(FeedsOrderV2.id.desc()).first()

    if last:
        num = int(last.order_ref.split("-")[-1]) + 1
    else:
        num = 1

    return f"FR-{today_str}-{str(num).zfill(3)}"


# ================================
# 🔹 DELIVERY STATUS (ORDER LEVEL)
# ================================
def get_delivery_status(order):

    total_ordered = sum(float(i.quantity or 0) for i in order.items)

    total_delivered = sum(
        float(d.quantity_delivered or 0)
        for d in order.deliveries
    )

    remaining = total_ordered - total_delivered

    if total_delivered == 0:
        status = "Pending"
    elif remaining > 0:
        status = "Partial"
    else:
        status = "Full"

    return total_delivered, remaining, status


# ================================
# 🔹 PAYMENT STATUS (FIXED)
# ================================
def get_payment_status(order):

    total_cost = sum(float(i.total_cost or 0) for i in order.items)

    # 🔥 USE EXACT MATCH (SAFE)
    payments = Payment.query.filter(
        Payment.purpose == f"Feeds Order {order.order_ref}"
    ).all()

    paid = sum(float(p.amount or 0) for p in payments)

    balance = total_cost - paid

    if balance > 0:
        status = "Debt"
        color = "red"
    else:
        status = "Cleared"
        color = "green"

    return total_cost, paid, balance, status, color


# ================================
# 🔹 BUILD ORDER SUMMARY (FIXED)
# ================================
def build_order_summary(order):

    # 🔥 PAYMENT (CONSISTENT)
    total_cost = sum(float(i.total_cost or 0) for i in order.items)

    payments = Payment.query.filter(
        Payment.purpose == f"Feeds Order {order.order_ref}"
    ).all()

    paid = sum(float(p.amount or 0) for p in payments)

    balance = total_cost - paid

    if balance > 0:
        p_status = "Debt"
        p_color = "red"
    else:
        p_status = "Cleared"
        p_color = "green"

    # 🔥 DELIVERY
    total_ordered = 0
    total_delivered = 0

    full_items = 0
    partial_items = 0
    pending_items = 0

    for item in order.items:

        ordered = float(item.quantity or 0)

        delivered = sum(
            float(d.quantity_delivered or 0)
            for d in order.deliveries
            if d.item_id == item.id
        )

        remaining = ordered - delivered

        total_ordered += ordered
        total_delivered += delivered

        if delivered == 0:
            pending_items += 1
        elif remaining > 0:
            partial_items += 1
        else:
            full_items += 1

    # 🔥 FINAL DELIVERY STATUS
    if pending_items == len(order.items):
        d_status = "Pending"
        d_color = "red"
    elif full_items == len(order.items):
        d_status = "Full"
        d_color = "green"
    else:
        d_status = "Partial"
        d_color = "orange"

    return {
        "order": order,

        "total": round(total_cost, 2),
        "paid": round(paid, 2),
        "balance": round(balance, 2),

        "delivered": round(total_delivered, 2),
        "remaining": round(total_ordered - total_delivered, 2),

        "delivery_status": d_status,
        "delivery_color": d_color,

        "payment_status": p_status,
        "payment_color": p_color
    }


# ================================
# 🔹 GET ORDERS (FILTERED)
# ================================
def get_orders(date_filter=None, farm_id=None):

    query = FeedsOrderV2.query

    if date_filter:
        try:
            selected_date = datetime.strptime(date_filter, "%Y-%m-%d").date()
            query = query.filter_by(date_ordered=selected_date)
        except:
            pass

    if farm_id:
        try:
            query = query.filter_by(farm_id=int(farm_id))
        except:
            pass

    orders = query.order_by(FeedsOrderV2.date_ordered.desc()).all()

    return [build_order_summary(o) for o in orders]


# ================================
# 🔹 ITEM DELIVERY (NO CHANGE)
# ================================
def calc_item_delivery(item):

    delivered = sum(
        float(d.quantity_delivered or 0)
        for d in item.order.deliveries
        if d.item_id == item.id
    )

    ordered = float(item.quantity or 0)
    remaining = ordered - delivered

    if delivered == 0:
        status = "Pending"
        color = "red"
    elif remaining > 0:
        status = "Partial"
        color = "orange"
    else:
        status = "Full"
        color = "green"

    return delivered, remaining, status, color


# ================================
# 🔹 PAYMENT CALCULATION (FIXED)
# ================================
def calc_payment(order):

    total_cost = sum(float(i.total_cost or 0) for i in order.items)

    # 🔥 EXACT MATCH (NO LIKE)
    payments = Payment.query.filter(
        Payment.purpose == f"Feeds Order {order.order_ref}"
    ).all()

    paid = sum(float(p.amount or 0) for p in payments)

    balance = total_cost - paid

    if balance > 0:
        status = "Debt"
        color = "red"
    else:
        status = "Cleared"
        color = "green"

    return total_cost, paid, balance, status, color
def get_treatment_data(date_str=None, status=None, farm_id=None):

    query = Treatment.query.join(AnimalRegistry)

    # -------------------------
    # DATE FILTER (ONLY IF GIVEN)
    # -------------------------
    if date_str:
        selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        query = query.filter(Treatment.date_treated == selected_date)
    else:
        selected_date = None   # 👈 no filtering

    # -------------------------
    # FARM FILTER
    # -------------------------
    if farm_id:
        query = query.filter(AnimalRegistry.farm_id == int(farm_id))

    # -------------------------
    # STATUS FILTER
    # -------------------------
    if status:
        query = query.filter(db.func.lower(Treatment.status) == status.lower())

    records = query.order_by(AnimalRegistry.name.asc()).all()

    # STATUS COUNTS (using filtered records)
    filtered = records

    healed_count = sum(1 for r in filtered if r.status == "healed")

    recovering_count = sum(1 for r in filtered if r.status == "recovering")

    # -------------------------
    # COST CALCULATIONS
    # -------------------------

    if selected_date:
        base_query = Treatment.query.filter(
            Treatment.date_treated == selected_date
        )
    else:
        base_query = Treatment.query  # 👈 ALL DATA

    if farm_id:
        base_query = base_query.filter(AnimalRegistry.farm_id == int(farm_id))

    daily_total = sum(r.cost for r in base_query.all())

    # MONTH
    if selected_date:
        month_query = Treatment.query.join(AnimalRegistry).filter(
            extract('month', Treatment.date_treated) == selected_date.month,
            extract('year', Treatment.date_treated) == selected_date.year
        )
        if farm_id:
            month_query = month_query.filter(AnimalRegistry.farm_id == int(farm_id))
        month_total = sum(r.cost for r in month_query.all())
    else:
        month_total = daily_total

    # QUARTER
    if selected_date:
        quarter = (selected_date.month - 1)//3 + 1

        quarter_query = Treatment.query.join(AnimalRegistry).filter(
            extract('year', Treatment.date_treated) == selected_date.year
        )
        if farm_id:
            quarter_query = quarter_query.filter(AnimalRegistry.farm_id == int(farm_id))

        quarter_total = sum(
            r.cost for r in quarter_query.all()
            if ((r.date_treated.month-1)//3+1) == quarter
        )
    else:
        quarter_total = daily_total

    # YEAR
    if selected_date:
        year_query = Treatment.query.join(AnimalRegistry).filter(
            extract('year', Treatment.date_treated) == selected_date.year
        )
        if farm_id:
            year_query = year_query.filter(AnimalRegistry.farm_id == int(farm_id))
        year_total = sum(r.cost for r in year_query.all())
    else:
        year_total = daily_total

        # -------------------------
# STATUS COUNTS (SAFE FIX)
# -------------------------

    filtered = records   # Created admin ALWAYS use already filtered records

    healed_count = sum(1 for r in filtered if r.status == "healed")
    recovering_count = sum(1 for r in filtered if r.status == "recovering")

    return {
        "records": records,
        "selected_date": selected_date,
        "status": status,
        "healed_count": healed_count,
        "recovering_count": recovering_count,
        "daily_total": round(daily_total, 2),
        "month_total": round(month_total, 2),
        "quarter_total": round(quarter_total, 2),
        "year_total": round(year_total, 2)
    }


def get_car_expense_report_data(selected_date=None):

    query = CarExpense.query.join(CarRegistry)

    if selected_date:
        selected_date_obj = datetime.strptime(selected_date, "%Y-%m-%d").date()
        query = query.filter(CarExpense.date == selected_date_obj)

    expenses = query.order_by(CarRegistry.plate_number.asc()).all()

    total = sum(e.amount for e in expenses)

    return {
        "expenses": expenses,
        "total_expense": total,
        "selected_date": selected_date
    }


def get_sales_report_data(selected_date=None):

    query = CarSales.query.join(CarRegistry)

    if selected_date:
        selected_date_obj = datetime.strptime(selected_date, "%Y-%m-%d").date()
        query = query.filter(CarSales.date == selected_date_obj)

    sales = query.order_by(CarRegistry.plate_number.asc()).all()

    total = sum(s.amount for s in sales)

    return {
        "sales": sales,
        "total_sales": total,
        "selected_date": selected_date
    }

from datetime import datetime, date

def normalize_date(selected_date=None):
    """
    Converts string date to python date object.
    """

    if isinstance(selected_date, date):
        return selected_date

    if selected_date:
        return datetime.strptime(
            selected_date,
            "%Y-%m-%d"
        ).date()

    return date.today()

from collections import defaultdict

def load_history(selected_date):
    """
    Loads all historical records using only THREE SQL queries.
    """

    # Production
    production_records = (
        MilkRegistry.query
        .filter(MilkRegistry.date < selected_date)
        .order_by(MilkRegistry.date)
        .all()
    )

    # Sales
    sales_records = (
        MilkSalesRegistry.query
        .filter(MilkSalesRegistry.date < selected_date)
        .order_by(MilkSalesRegistry.date)
        .all()
    )

    # Actual Remaining
    remaining_records = (
        MilkDailyRemaining.query
        .filter(MilkDailyRemaining.date < selected_date)
        .all()
    )

    return (
        production_records,
        sales_records,
        remaining_records
    )

from collections import defaultdict

def group_history(
    production_records,
    sales_records,
    remaining_records
):

    production = defaultdict(list)
    sales = defaultdict(list)
    remaining = {}

    for r in production_records:
        production[r.date].append(r)

    for r in sales_records:
        sales[r.date].append(r)

    for r in remaining_records:
        remaining[r.date] = r

    return production, sales, remaining

def calculate_history_stock(
    production,
    sales,
    remaining
):

    system_running = 0
    actual_running = 0

    all_dates = sorted(
        set(production.keys()) |
        set(sales.keys()) |
        set(remaining.keys())
    )

    for current_day in all_dates:

        produced = sum(
            float(r.total or 0)
            for r in production[current_day]
        )

        used = sum(
            float(r.shop1 or 0)
            + float(r.shop2 or 0)
            + float(r.shop3 or 0)
            + float(r.home or 0)
            + float(r.calf or 0)
            for r in sales[current_day]
        )

        system_running = max(
            system_running + produced - used,
            0
        )

        if current_day in remaining:

            actual_running = float(
                remaining[current_day].actual_remaining or 0
            )

        else:

            actual_running = max(
                actual_running + produced - used,
                0
            )

    return system_running, actual_running

from sqlalchemy.orm import joinedload

def load_today(selected_date):
    """
    Load all data needed for the selected day.

    Only 3 SQL queries are executed.
    """

    milk_records = (
        MilkRegistry.query
        .options(joinedload(MilkRegistry.cow))
        .filter(MilkRegistry.date == selected_date)
        .all()
    )

    sales_records = (
        MilkSalesRegistry.query
        .filter(MilkSalesRegistry.date == selected_date)
        .all()
    )

    remaining_record = (
        MilkDailyRemaining.query
        .filter(MilkDailyRemaining.date == selected_date)
        .first()
    )

    return {
        "milk_records": milk_records,
        "sales_records": sales_records,
        "remaining_record": remaining_record
    }

def calculate_today_production(milk_records):

    total_morning = 0
    total_noon = 0
    total_evening = 0
    grand_total = 0

    cow_count = len(milk_records)

    above10_total = 0
    above10_count = 0

    for milk in milk_records:

        morning = float(milk.morning or 0)
        noon = float(milk.noon or 0)
        evening = float(milk.evening or 0)
        total = float(milk.total or 0)

        total_morning += morning
        total_noon += noon
        total_evening += evening
        grand_total += total

        if total > 10:
            above10_total += total
            above10_count += 1

    average = (
        above10_total / above10_count
        if above10_count
        else 0
    )

    return {
        "total_morning": round(total_morning,2),
        "total_noon": round(total_noon,2),
        "total_evening": round(total_evening,2),
        "grand_total": round(grand_total,2),
        "cow_count": cow_count,
        "average_production": round(average,2)
    }

def calculate_today_sales(sales_records):

    shop1 = 0
    shop2 = 0
    shop3 = 0
    home = 0
    calf = 0

    morning_sales = 0
    noon_sales = 0
    evening_sales = 0

    for sale in sales_records:

        s1 = float(sale.shop1 or 0)
        s2 = float(sale.shop2 or 0)
        s3 = float(sale.shop3 or 0)
        hm = float(sale.home or 0)
        cf = float(sale.calf or 0)

        total = s1 + s2 + s3

        shop1 += s1
        shop2 += s2
        shop3 += s3
        home += hm
        calf += cf

        if sale.session == "Morning":
            morning_sales += total

        elif sale.session == "Noon":
            noon_sales += total

        elif sale.session == "Evening":
            evening_sales += total

    total_shop_sales = shop1 + shop2 + shop3
    total_used = total_shop_sales + home + calf

    return {

        "shop1": round(shop1,2),
        "shop2": round(shop2,2),
        "shop3": round(shop3,2),

        "home": round(home,2),
        "calf": round(calf,2),

        "morning_sales": round(morning_sales,2),
        "noon_sales": round(noon_sales,2),
        "evening_sales": round(evening_sales,2),

        "total_sold_shops": round(total_shop_sales,2),
        "total_used": round(total_used,2),
        "other_uses": round(home + calf,2)
    }

from bisect import bisect_right

def load_price_cache():
    """
    Loads every milk price into memory.

    Executes ONLY ONE SQL query.
    """

    prices = (
        MilkPrice.query
        .order_by(MilkPrice.effective_date)
        .all()
    )

    dates = []
    values = []

    for p in prices:

        dates.append(p.effective_date)
        values.append(float(p.price))

    return dates, values

from bisect import bisect_right

def get_price(price_dates, price_values, target_date):
    """
    Returns the price effective on target_date.

    O(log n)
    """

    if not price_dates:
        return 0

    index = bisect_right(
        price_dates,
        target_date
    ) - 1

    if index < 0:
        return 0

    return price_values[index]

def calculate_monthly_revenue(
    sales_records,
    price_dates,
    price_values
):

    revenue = 0

    for sale in sales_records:

        litres = (
            float(sale.shop1 or 0)
            + float(sale.shop2 or 0)
            + float(sale.shop3 or 0)
        )

        price = get_price(
            price_dates,
            price_values,
            sale.date
        )

        revenue += litres * price

    return round(revenue,2)

def calculate_today_revenue(
    sales_records,
    price_dates,
    price_values
):

    revenue = 0

    for sale in sales_records:

        litres = (
            float(sale.shop1 or 0)
            + float(sale.shop2 or 0)
            + float(sale.shop3 or 0)
        )

        price = get_price(
            price_dates,
            price_values,
            sale.date
        )

        revenue += litres * price

    return round(revenue,2)


def calculate_sales_summary(all_sales, selected_date):

    quarter = (selected_date.month - 1) // 3 + 1

    daily_sales = 0
    monthly_sales = 0
    quarterly_sales = 0
    yearly_sales = 0

    for sale in all_sales:

        litres = (
            float(sale.shop1 or 0)
            + float(sale.shop2 or 0)
            + float(sale.shop3 or 0)
        )

        # ----------------------------
        # Daily
        # ----------------------------

        if sale.date == selected_date:
            daily_sales += litres

        # ----------------------------
        # Monthly
        # ----------------------------

        if (
            sale.date.month == selected_date.month
            and sale.date.year == selected_date.year
        ):
            monthly_sales += litres

        # ----------------------------
        # Quarterly
        # ----------------------------

        if (
            sale.date.year == selected_date.year
            and ((sale.date.month - 1) // 3 + 1) == quarter
        ):
            quarterly_sales += litres

        # ----------------------------
        # Yearly
        # ----------------------------

        if sale.date.year == selected_date.year:
            yearly_sales += litres

    return {

        "daily_sales": round(daily_sales,2),

        "monthly_sales": round(monthly_sales,2),

        "quarterly_sales": round(quarterly_sales,2),

        "yearly_sales": round(yearly_sales,2)

    }

def calculate_revenue_summary(
    all_sales,
    selected_date,
    price_dates,
    price_values
):

    quarter = (selected_date.month - 1) // 3 + 1

    daily = 0
    monthly = 0
    quarterly = 0
    yearly = 0

    for sale in all_sales:

        litres = (
            float(sale.shop1 or 0)
            + float(sale.shop2 or 0)
            + float(sale.shop3 or 0)
        )

        price = get_price(
            price_dates,
            price_values,
            sale.date
        )

        revenue = litres * price

        if sale.date == selected_date:
            daily += revenue

        if (
            sale.date.month == selected_date.month
            and sale.date.year == selected_date.year
        ):
            monthly += revenue

        if (
            sale.date.year == selected_date.year
            and ((sale.date.month - 1)//3 + 1) == quarter
        ):
            quarterly += revenue

        if sale.date.year == selected_date.year:
            yearly += revenue

    return {

        "daily_revenue": round(daily,2),

        "monthly_revenue": round(monthly,2),

        "quarterly_revenue": round(quarterly,2),

        "yearly_revenue": round(yearly,2)

    }



from sqlalchemy import extract

def get_milk_report_data(date_str=None, farm_id=None):
    """
    Optimized Milk Report
    Only TWO SQL queries are executed.
    """

    # -------------------------------------------------------
    # Selected Date
    # -------------------------------------------------------

    selected_date = normalize_date(date_str)

    # -------------------------------------------------------
    # Today's Records (1 Query)
    # -------------------------------------------------------

    today_query = MilkRegistry.query.filter(
        MilkRegistry.date == selected_date
    )

    if farm_id:
        today_query = today_query.filter(
            MilkRegistry.farm_id == int(farm_id)
        )

    records = (
        today_query
        .order_by(MilkRegistry.total.desc())
        .all()
    )

    total_morning = 0
    total_noon = 0
    total_evening = 0
    grand_total = 0

    cow_count = len(records)

    above10_total = 0
    above10_count = 0

    for record in records:

        morning = float(record.morning or 0)
        noon = float(record.noon or 0)
        evening = float(record.evening or 0)
        total = float(record.total or 0)

        total_morning += morning
        total_noon += noon
        total_evening += evening
        grand_total += total

        if total > 10:
            above10_total += total
            above10_count += 1

    average_production = (
        above10_total / above10_count
        if above10_count > 0
        else 0
    )

    # -------------------------------------------------------
    # Entire Year's Records (1 Query)
    # -------------------------------------------------------

    year_query = MilkRegistry.query.filter(
        extract("year", MilkRegistry.date) == selected_date.year
    )

    if farm_id:
        year_query = year_query.filter(
            MilkRegistry.farm_id == int(farm_id)
        )

    year_records = year_query.all()

    monthly_total = 0
    quarterly_total = 0
    yearly_total = 0

    quarter = (selected_date.month - 1) // 3 + 1

    for record in year_records:

        total = float(record.total or 0)

        yearly_total += total

        if record.date.month == selected_date.month:
            monthly_total += total

        if ((record.date.month - 1) // 3 + 1) == quarter:
            quarterly_total += total

    # -------------------------------------------------------
    # Return
    # -------------------------------------------------------

    return {

        "records": records,

        "selected_date": selected_date,

        "total_morning": round(total_morning, 2),

        "total_noon": round(total_noon, 2),

        "total_evening": round(total_evening, 2),

        "grand_total": round(grand_total, 2),

        "average_production": round(average_production, 2),

        "monthly_total": round(monthly_total, 2),

        "quarterly_total": round(quarterly_total, 2),

        "yearly_total": round(yearly_total, 2),

        "cow_count": cow_count

    }

def get_shed_report_data():

    sheds = CowShed.query.all()

    report = []

    total_capacity = 0
    total_occupied = 0

    for shed in sheds:

        animals = AnimalRegistry.query.filter_by(
            current_shed_id=shed.id
        ).all()

        occupied = len(animals)

        capacity = shed.capacity or 0

        remaining = max(
            capacity - occupied,
            0
        )

        total_capacity += capacity
        total_occupied += occupied

        report.append({

            "shed": shed,

            "animals": animals,

            "occupied": occupied,

            "remaining": remaining

        })

    total_remaining = (
        total_capacity -
        total_occupied
    )

    occupancy_rate = 0

    if total_capacity > 0:

        occupancy_rate = round(
            (total_occupied / total_capacity)
            * 100,
            1
        )

    return {

        "report": report,

        "total_sheds": len(sheds),

        "total_capacity": total_capacity,

        "total_occupied": total_occupied,

        "total_remaining": total_remaining,

        "occupancy_rate": occupancy_rate,

        "now": datetime.now()

    }

def get_transactions_data(
    date_str=None,
    month_str=None,
    purpose=None,
    farm_id=None,
    order_id=None
):

    from datetime import datetime
    from sqlalchemy import extract

    selected_date = None
    selected_month = None

    # =========================================
    # HANDLE DATE
    # =========================================

    if date_str:

        try:
            selected_date = datetime.strptime(
                date_str,
                "%Y-%m-%d"
            ).date()

        except:
            selected_date = None

    # =========================================
    # HANDLE MONTH
    # =========================================

    if month_str:

        try:
            selected_month = datetime.strptime(
                month_str,
                "%Y-%m"
            )

        except:
            selected_month = None

    # =========================================
    # MAIN QUERY
    # =========================================

    query = Payment.query

    if selected_date:

        query = query.filter(
            Payment.date_paid == selected_date
        )

    if selected_month:

        query = query.filter(

            extract(
                'month',
                Payment.date_paid
            ) == selected_month.month,

            extract(
                'year',
                Payment.date_paid
            ) == selected_month.year

        )

    if purpose:

        query = query.filter(
            Payment.purpose_type == purpose
        )

    if farm_id:

        try:
            query = query.filter(
                Payment.farm_id == int(farm_id)
            )

        except:
            pass

    if order_id:

        try:
            query = query.filter(
                Payment.order_id == int(order_id)
            )

        except:
            pass

    # =========================================
    # MAIN DATA
    # =========================================

    transactions = query.order_by(
        Payment.date_paid.desc()
    ).all()

    total_paid = sum(
        float(t.amount or 0)
        for t in transactions
    )

    # =========================================
    # BASE DATE
    # =========================================

    base_date_str = None

    if selected_date:

        base_date_str = selected_date

    elif selected_month:

        base_date_str = selected_month

    # =========================================
    # PERIOD TOTALS
    # =========================================

    month_paid = 0
    quarter_paid = 0
    year_paid = 0

    # =========================================
    # DASHBOARD FIXED EXPENSES
    # =========================================

    feed_daily = 0
    feed_monthly = 0
    feed_quarterly = 0
    feed_yearly = 0

    other_daily = 0
    other_monthly = 0
    other_quarterly = 0
    other_yearly = 0

    # =========================================
    # PERIOD CALCULATIONS
    # =========================================

    if base_date_str:

        quarter = (
            (base_date_str.month - 1) // 3
        ) + 1

        # =====================================
        # DYNAMIC QUERY
        # =====================================

        period_query = Payment.query

        if purpose:

            period_query = period_query.filter(
                Payment.purpose_type == purpose
            )

        if farm_id:

            try:
                period_query = period_query.filter(
                    Payment.farm_id == int(farm_id)
                )

            except:
                pass

        if order_id:

            try:
                period_query = period_query.filter(
                    Payment.order_id == int(order_id)
                )

            except:
                pass

        # =====================================
        # MONTH
        # =====================================

        month_records = period_query.filter(

            extract(
                'month',
                Payment.date_paid
            ) == base_date_str.month,

            extract(
                'year',
                Payment.date_paid
            ) == base_date_str.year

        ).all()

        month_paid = sum(
            float(p.amount or 0)
            for p in month_records
        )

        # =====================================
        # YEAR
        # =====================================

        year_records = period_query.filter(

            extract(
                'year',
                Payment.date_paid
            ) == base_date_str.year

        ).all()

        year_paid = sum(
            float(p.amount or 0)
            for p in year_records
        )

        # =====================================
        # QUARTER
        # =====================================

        quarter_paid = sum(

            float(p.amount or 0)

            for p in year_records

            if (
                ((p.date_paid.month - 1)//3) + 1
            ) == quarter

        )

        # =====================================
        # FEED EXPENSES
        # =====================================

        feed_daily_records = Payment.query.filter(

            Payment.date_paid == base_date_str,

            Payment.purpose_type.ilike("%feed%")

        ).all()

        feed_daily = sum(
            float(p.amount or 0)
            for p in feed_daily_records
        )

        feed_month_records = Payment.query.filter(

            extract(
                'month',
                Payment.date_paid
            ) == base_date_str.month,

            extract(
                'year',
                Payment.date_paid
            ) == base_date_str.year,

            Payment.purpose_type.ilike("%feed%")

        ).all()

        feed_monthly = sum(
            float(p.amount or 0)
            for p in feed_month_records
        )

        feed_year_records = Payment.query.filter(

            extract(
                'year',
                Payment.date_paid
            ) == base_date_str.year,

            Payment.purpose_type.ilike("%feed%")

        ).all()

        feed_yearly = sum(
            float(p.amount or 0)
            for p in feed_year_records
        )

        feed_quarterly = sum(

            float(p.amount or 0)

            for p in feed_year_records

            if (
                ((p.date_paid.month - 1)//3) + 1
            ) == quarter

        )

        # =====================================
        # OTHER EXPENSES
        # =====================================

        other_daily_records = Payment.query.filter(

            Payment.date_paid == base_date_str,

            ~Payment.purpose_type.ilike("%feed%")

        ).all()

        other_daily = sum(
            float(p.amount or 0)
            for p in other_daily_records
        )

        other_month_records = Payment.query.filter(

            extract(
                'month',
                Payment.date_paid
            ) == base_date_str.month,

            extract(
                'year',
                Payment.date_paid
            ) == base_date_str.year,

            ~Payment.purpose_type.ilike("%feed%")

        ).all()

        other_monthly = sum(
            float(p.amount or 0)
            for p in other_month_records
        )

        other_year_records = Payment.query.filter(

            extract(
                'year',
                Payment.date_paid
            ) == base_date_str.year,

            ~Payment.purpose_type.ilike("%feed%")

        ).all()

        other_yearly = sum(
            float(p.amount or 0)
            for p in other_year_records
        )

        other_quarterly = sum(

            float(p.amount or 0)

            for p in other_year_records

            if (
                ((p.date_paid.month - 1)//3) + 1
            ) == quarter

        )

    # =========================================
    # RETURN
    # =========================================

    return {

        # ORIGINAL FUNCTIONALITY

        "transactions": transactions,

        "selected_date": selected_date,

        "selected_month": month_str,

        "total_paid": round(total_paid, 2),

        "month_paid": round(month_paid, 2),

        "quarter_paid": round(quarter_paid, 2),

        "year_paid": round(year_paid, 2),

        "purpose": purpose,

        "farm_id": farm_id,

        # DASHBOARD FEED TOTALS

        "feed_daily": round(feed_daily, 2),

        "feed_monthly": round(feed_monthly, 2),

        "feed_quarterly": round(feed_quarterly, 2),

        "feed_yearly": round(feed_yearly, 2),

        # DASHBOARD OTHER TOTALS

        "other_daily": round(other_daily, 2),

        "other_monthly": round(other_monthly, 2),

        "other_quarterly": round(other_quarterly, 2),

        "other_yearly": round(other_yearly, 2)

    }

def get_monthly_cow_analysis(date_str=None):

    if date_str:
        selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    else:
        from datetime import date; selected_date = __import__('datetime').date.today()

    # Created admin FIXED: use cow_id + direct relationship
    monthly_cows = db.session.query(
        AnimalRegistry.name.label("cow_name"),
        func.sum(MilkRegistry.total).label("total_milk"),
        func.count(MilkRegistry.date).label("days_recorded")
    ).join(
        AnimalRegistry, AnimalRegistry.id == MilkRegistry.cow_id
    ).filter(
        extract('month', MilkRegistry.date) == selected_date.month,
        extract('year', MilkRegistry.date) == selected_date.year
    ).group_by(AnimalRegistry.name).all()

    cow_count = len(monthly_cows)
    overall_total = sum(c.total_milk for c in monthly_cows)

    overall_average = overall_total / cow_count if cow_count > 0 else 0

    return {
        "selected_date": selected_date,
        "monthly_cows": monthly_cows,
        "overall_average": round(overall_average, 2)
    }


def get_animals_data(category=None, farm_id=None):
    base_query = AnimalRegistry.query.filter(
        AnimalRegistry.category.ilike("nolonger_exist") == False
    )
    query = AnimalRegistry.query

    if farm_id:
        query = query.filter(AnimalRegistry.farm_id == int(farm_id))
        base_query = base_query.filter(AnimalRegistry.farm_id == int(farm_id))

    # HANDLE EMPTY / NONE / ALL
    if (
        category
        and str(category).strip().lower() not in ["all", "none", ""]
    ):
        query = query.filter(
            AnimalRegistry.category.ilike(category)
        )

    animals = query.all()

    # -------------------------------------------------------
    # FARM-AWARE COUNTS
    # -------------------------------------------------------

    def count_cat(cat):
        q = AnimalRegistry.query.filter(
            AnimalRegistry.category.ilike(cat)
        )
        if farm_id:
            q = q.filter(AnimalRegistry.farm_id == int(farm_id))
        return q.count()

    return {
        "animals": animals,
        "existing": base_query,
        "total_animals": count_cat("%") if not farm_id else AnimalRegistry.query.filter_by(farm_id=farm_id).count(),
        "existing_animals": base_query.count(),
        "milkers": count_cat("milker"),

        "dry_cows": count_cat("dry"),

        "calves": count_cat("calf"),

        "bulls": count_cat("bull"),

        "incalf_heifers": count_cat("incalf-heifer"),

        "yearlings": count_cat("yearing"),

        "weaners": count_cat("weaner"),

        "Bullying_heifer": count_cat("Bullying-Heifer"),

        "steamers": count_cat("steamer"),

        "nolonger_exist": count_cat("nolonger_exist"),

    }


def get_insemination_data(status=None, month=None, year=None, farm_id=None):

    from datetime import datetime

    query = db.session.query(Insemination).join(AnimalRegistry)

    # =========================
    # 🔹 DEFAULT TO CONFIRMED (EXPECTANT MOTHERS)
    # =========================
    if status is None:
        status = "confirmed"

    # =========================
    # 🔹 STATUS FILTER
    # =========================
    if status:
        status = status.lower()

        if status == "confirmed":
            query = query.filter(Insemination.status == "confirmed")

        elif status == "delivered":
            query = query.filter(Insemination.status == "delivered")

        elif status == "pending":
            query = query.filter(
                (Insemination.status == None) | (Insemination.status == "pending")
            )

        elif status == "aborted":
            query = query.filter(Insemination.status == "aborted")

    # =========================
    # 🔹 FARM FILTER
    # =========================
    if farm_id:
        query = query.filter(Insemination.farm_id == int(farm_id))

    # =========================
    # 🔹 MONTH FILTER (YYYY-MM)
    # =========================
    if month:
        try:
            y, m = month.split("-")
            query = query.filter(
                db.extract('year', Insemination.date_served) == int(y),
                db.extract('month', Insemination.date_served) == int(m)
            )
        except:
            pass

    # =========================
    # 🔹 YEAR FILTER (YYYY)
    # =========================
    elif year:
        try:
            query = query.filter(
                db.extract('year', Insemination.date_served) == int(year)
            )
        except:
            pass

    # =========================
    # 🔥 SORT (LATEST → OLDEST)
    # =========================
    records = query.order_by(Insemination.date_served.desc()).all()

    # =========================
    # 🔹 FORMAT MONTH NAME
    # =========================
    month_name = None
    if month:
        try:
            month_name = datetime.strptime(month, "%Y-%m").strftime("%B %Y")
        except:
            month_name = month

    return {
        "records": records,
        "status": status,
        "month": month,
        "year": year,
        "month_name": month_name,
        "now": datetime.now()
    }



def to_float(val):
    return float(val or 0)

from datetime import datetime, date

def normalize_date(date_str=None):
    """
    Converts string date to a Python date object.
    """

    if isinstance(date_str, date):
        return date_str

    if date_str:
        return datetime.strptime(
            date_str,
            "%Y-%m-%d"
        ).date()

    return date.today()

def load_milk_data(farm_id=None):

    if farm_id:
        production = MilkRegistry.query.filter_by(
            farm_id=farm_id
        ).all()

        sales = MilkSalesRegistry.query.filter_by(
            farm_id=farm_id
        ).all()
    else:
        production = MilkRegistry.query.all()

        sales = MilkSalesRegistry.query.all()

    remaining = (
        MilkDailyRemaining.query
        .order_by(MilkDailyRemaining.date)
        .all()
    )

    prices = (
        MilkPrice.query
        .order_by(MilkPrice.effective_date)
        .all()
    )

    return {
        "production": production,
        "sales": sales,
        "remaining": remaining,
        "prices": prices
    }

from bisect import bisect_right


def build_price_cache(prices):

    price_dates = []
    price_values = []

    for p in prices:

        price_dates.append(
            p.effective_date
        )

        price_values.append(
            float(p.price)
        )

    return price_dates, price_values

def get_price(
    price_dates,
    price_values,
    target_date
):

    index = bisect_right(
        price_dates,
        target_date
    ) - 1

    if index < 0:
        return 0

    return price_values[index]



def calculate_production(production, selected_date):

    month = selected_date.month
    year = selected_date.year
    quarter = ((month - 1) // 3) + 1

    total_morning = 0
    total_noon = 0
    total_evening = 0

    grand_total = 0
    cow_count = 0

    monthly_total = 0
    quarterly_total = 0
    yearly_total = 0

    above_10_total = 0
    above_10_count = 0

    today_records = []

    for record in production:

        record_month = record.date.month
        record_year = record.date.year
        record_quarter = ((record_month - 1) // 3) + 1

        # --------------------------------
        # TODAY
        # --------------------------------

        if record.date == selected_date:

            today_records.append(record)

            total_morning += to_float(record.morning)
            total_noon += to_float(record.noon)
            total_evening += to_float(record.evening)

            grand_total += to_float(record.total)

            cow_count += 1

            if to_float(record.total) > 10:

                above_10_total += to_float(record.total)
                above_10_count += 1

        # --------------------------------
        # YEAR
        # --------------------------------

        if record_year == year:

            yearly_total += to_float(record.total)

            # ----------------------------
            # MONTH
            # ----------------------------

            if record_month == month:
                monthly_total += to_float(record.total)

            # ----------------------------
            # QUARTER
            # ----------------------------

            if record_quarter == quarter:
                quarterly_total += to_float(record.total)

    average_production = (
        above_10_total / above_10_count
        if above_10_count else 0
    )

    return {

        "records": today_records,

        "total_morning": round(total_morning,2),
        "total_noon": round(total_noon,2),
        "total_evening": round(total_evening,2),

        "grand_total": round(grand_total,2),

        "monthly_total": round(monthly_total,2),
        "quarterly_total": round(quarterly_total,2),
        "yearly_total": round(yearly_total,2),

        "cow_count": cow_count,

        "average_production": round(
            average_production,
            2
        )
    }

def calculate_sales(
    sales,
    selected_date,
    price_dates,
    price_values
):

    month = selected_date.month
    year = selected_date.year
    quarter = ((month - 1) // 3) + 1

    # =====================================================
    # DAILY TOTALS
    # =====================================================

    total_shop1 = 0
    total_shop2 = 0
    total_shop3 = 0

    total_home = 0
    total_calf = 0

    total_sold = 0
    total_used = 0

    # =====================================================
    # SALES ANALYTICS
    # =====================================================

    daily_total_sales = 0
    monthly_total_sales = 0
    quarterly_total_sales = 0
    yearly_total_sales = 0

    daily_total_litres = 0
    monthly_total_litres = 0
    quarterly_total_litres = 0
    yearly_total_litres = 0

    # =====================================================
    # TABLE DATA
    # =====================================================

    monthly_data = []
    daily_records=[]
    # =====================================================
    # LOOP
    # =====================================================



    for sale in sales:

        record_month = sale.date.month
        record_year = sale.date.year
        record_quarter = ((record_month - 1) // 3) + 1

        shop1 = to_float(sale.shop1)
        shop2 = to_float(sale.shop2)
        shop3 = to_float(sale.shop3)

        calf = to_float(sale.calf)
        home = to_float(sale.home)

        litres = shop1 + shop2 + shop3

        used = litres + calf + home

        price = get_price(
            price_dates,
            price_values,
            sale.date
        )

        revenue = litres * price

        # =================================================
        # TODAY
        # =================================================

        if sale.date == selected_date:

            total_shop1 += shop1
            total_shop2 += shop2
            total_shop3 += shop3

            total_home += home
            total_calf += calf

            total_sold += litres
            total_used += used

            daily_total_sales += revenue
            daily_total_litres += litres
            daily_records.append(sale)
        # =================================================
        # YEAR
        # =================================================

        if record_year == year:

            yearly_total_sales += revenue
            yearly_total_litres += litres

            # =============================================
            # MONTH
            # =============================================

            if record_month == month:

                monthly_total_sales += revenue
                monthly_total_litres += litres

                monthly_data.append(sale)

            # =============================================
            # QUARTER
            # =============================================

            if record_quarter == quarter:

                quarterly_total_sales += revenue
                quarterly_total_litres += litres

    # =====================================================
    # RETURN
    # =====================================================

    return {

        # TABLE

        "monthly_data": monthly_data,
        "daily_records":daily_records,
        # DAILY

        "total_shop1": round(total_shop1,2),
        "total_shop2": round(total_shop2,2),
        "total_shop3": round(total_shop3,2),

        "total_home": round(total_home,2),
        "total_calf": round(total_calf,2),

        "total_sold_shops": round(total_sold,2),
        "total_used": round(total_used,2),

        "other_uses": round(
            total_home + total_calf,
            2
        ),

        # LITRES

        "daily_sales": round(daily_total_litres,2),
        "monthly_sales": round(monthly_total_litres,2),
        "quarterly_sales": round(quarterly_total_litres,2),
        "yearly_sales": round(yearly_total_litres,2),

        # REVENUE

        "daily_revenue": round(daily_total_sales,2),
        "monthly_revenue": round(monthly_total_sales,2),
        "quarterly_revenue": round(quarterly_total_sales,2),
        "yearly_revenue": round(yearly_total_sales,2)

    }

def calculate_stock(
    production,
    sales,
    remaining,
    selected_date,
    grand_total,
    total_sold_shops,
    total_used
):
    """
    Computes the running milk stock.

    System Remaining =
        Yesterday System
        + Today's Production
        - Today's Usage

    Actual Remaining is read from MilkDailyRemaining.

    Returns stock analytics for the selected date.
    """

    # ==========================================
    # BUILD DAILY PRODUCTION
    # ==========================================

    production_by_date_str = {}

    for p in production:

        production_by_date_str[p.date] = (
            production_by_date_str.get(p.date, 0)
            + to_float(p.total)
        )

    # ==========================================
    # BUILD DAILY USAGE
    # ==========================================

    usage_by_date_str = {}

    for s in sales:

        used = (

            to_float(s.shop1)

            + to_float(s.shop2)

            + to_float(s.shop3)

            + to_float(s.home)

            + to_float(s.calf)

        )

        usage_by_date_str[s.date] = (
            usage_by_date_str.get(s.date, 0)
            + used
        )

    # ==========================================
    # BUILD ACTUAL REMAINING
    # ==========================================

    actual_remaining_by_date_str = {}

    for r in remaining:

        actual_remaining_by_date_str[r.date] = (
            to_float(r.actual_remaining)
        )
    # ==========================================
    # PREVIOUS DAY ACTUAL REMAINING
    # ==========================================

    previous_actual_remaining = 0

    previous_dates = [
        d for d in actual_remaining_by_date_str.keys()
        if d < selected_date
    ]

    if previous_dates:

        latest_previous = max(previous_dates)

        previous_actual_remaining = actual_remaining_by_date_str.get(
            latest_previous,
            0
        )
    # ==========================================
    # ALL DATES
    # ==========================================

    all_dates = sorted(

        set(production_by_date_str.keys())

        | set(usage_by_date_str.keys())

        | set(actual_remaining_by_date_str.keys())

    )

    # ==========================================
    # RUNNING SYSTEM STOCK
    # ==========================================

    running_system = 0

    previous_system_remaining = 0

    system_available_today = 0

    actual_available_today = 0

    for day in all_dates:

        produced = production_by_date_str.get(day, 0)

        used = usage_by_date_str.get(day, 0)

        previous_system_remaining = running_system

        running_system = (

            running_system

            + produced

            - used

        )

        if day == selected_date:

            system_available_today = running_system

            actual_available_today = (

                actual_remaining_by_date_str.get(
                    day,
                    0
                )

            )

            break

    # ==========================================
    # VARIANCE
    # ==========================================

    pavail_variance = (

        actual_available_today

        - system_available_today

    )

    # ==========================================
    # CONVERSION %
    # ==========================================
    total_available=grand_total +actual_available_today
    total_system_available=system_available_today+grand_total
    actual_remaining=total_available-total_used
    remaining_system=total_system_available-total_used
   
    if total_available:

        percentage_conversion = (

            total_sold_shops

            / total_available

        ) * 100

    else:

        percentage_conversion = 0

    # ==========================================
    # ERROR %
    # ==========================================

    if system_available_today:

        percentage_error = (

            abs(pavail_variance)

            / system_available_today

        ) * 100

    else:

        percentage_error = 0

    # ==========================================
    # RETURN
    # ==========================================

    return {

        "previous_system_remaining":
            round(previous_system_remaining, 2),

        "system_available_today":
            round(system_available_today, 2),

        "total_system_available":
            round(total_system_available, 2),

        "remaining_system":
            round(remaining_system, 2),

        "total_available":
            round(total_available, 2),

        "actual_available_today":
            round(actual_available_today, 2),

        "previous_actual_remaining":
            round(previous_actual_remaining, 2),

        "pavail_variance":
            round(pavail_variance, 2),
        "actual_remaining":
            round(actual_remaining, 2),
        "percentage_conversion":
            round(percentage_conversion, 2),

        "percentage_error":
            round(percentage_error, 2)

    }

def get_milk_sales(date_str=None, farm_id=None):
    """
    Main Milk Analytics Engine

    Returns all milk sales, production and stock analytics
    for dashboards, reports and PDFs.
    """

    # =====================================================
    # NORMALIZE DATE
    # =====================================================

    selected_date = normalize_date(date_str)

    # =====================================================
    # LOAD ALL DATA (ONLY 4 DATABASE QUERIES)
    # =====================================================

    data = load_milk_data(farm_id)

    production = data["production"]
    sales = data["sales"]
    remaining = data["remaining"]
    prices = data["prices"]
    
    # =====================================================
    # BUILD PRICE CACHE
    # =====================================================

    price_dates, price_values = build_price_cache(
        prices
    )

    # =====================================================
    # PRODUCTION ENGINE
    # =====================================================

    production_data = calculate_production(
        production,
        selected_date
    )

    # =====================================================
    # SALES ENGINE
    # =====================================================

    sales_data = calculate_sales(
        sales,
        selected_date,
        price_dates,
        price_values,
        
    )

    # =====================================================
    # STOCK ENGINE
    # =====================================================

    stock_data = calculate_stock(
        production,
        sales,
        remaining,
        selected_date,
        production_data["grand_total"],
        sales_data["total_sold_shops"],
        sales_data["total_used"]
    )

    # =====================================================
    # PERFORMANCE METRICS
    # =====================================================
    total_used=sales_data["total_used"]
    total_sold = sales_data["total_sold_shops"]
    grand_total = production_data["grand_total"]

    if grand_total > 0:

        sales_percentage = round(
            (total_sold / grand_total) * 100,
            2
        )

    else:

        sales_percentage = 0

    # =====================================================
    # FINAL RETURN
    # =====================================================

    return {

        # Date

        "selected_date": selected_date,

        # ----------------------------------------
        # Production
        # ----------------------------------------

        **production_data,

        # ----------------------------------------
        # Sales
        # ----------------------------------------

        **sales_data,

        # ----------------------------------------
        # Stock
        # ----------------------------------------

        **stock_data,

        # ----------------------------------------
        # Dashboard Extras
        # ----------------------------------------

        "sales_percentage": sales_percentage

    }


def get_shed_report_data():

    sheds = CowShed.query.all()

    report = []

    total_capacity = 0
    total_occupied = 0

    for shed in sheds:

        animals = AnimalRegistry.query.filter_by(
            current_shed_id=shed.id
        ).all()

        occupied = len(animals)

        capacity = shed.capacity or 0

        remaining = max(
            capacity - occupied,
            0
        )

        total_capacity += capacity
        total_occupied += occupied

        report.append({

            "shed": shed,

            "animals": animals,

            "occupied": occupied,

            "remaining": remaining

        })

    total_remaining = (
        total_capacity -
        total_occupied
    )

    occupancy_rate = 0

    if total_capacity > 0:

        occupancy_rate = round(
            (total_occupied / total_capacity)
            * 100,
            1
        )

    return {

        "report": report,

        "total_sheds": len(sheds),

        "total_capacity": total_capacity,

        "total_occupied": total_occupied,

        "total_remaining": total_remaining,

        "occupancy_rate": occupancy_rate,

        "now": datetime.now()

    }



def get_milk_sales_monthly(selected_date=None):

    from datetime import datetime, date
    from sqlalchemy import extract, func

    if selected_date:
        selected_date = datetime.strptime(selected_date, "%Y-%m-%d").date()
    else:
        from datetime import date; selected_date = __import__('datetime').date.today()

    month = selected_date.month
    year = selected_date.year

    records = db.session.query(
        MilkSalesRegistry.date,
        func.sum(MilkSalesRegistry.shop1).label("shop1"),
        func.sum(MilkSalesRegistry.shop2).label("shop2"),
        func.sum(MilkSalesRegistry.shop3).label("shop3"),
        func.sum(MilkSalesRegistry.calf).label("calf"),
        func.sum(MilkSalesRegistry.home).label("home")
    ).filter(
        extract("month", MilkSalesRegistry.date) == month,
        extract("year", MilkSalesRegistry.date) == year
    ).group_by(
        MilkSalesRegistry.date
    ).order_by(
        MilkSalesRegistry.date
    ).all()

    monthly_data = []

    total_shop1 = total_shop2 = total_shop3 = 0.0
    total_calf = total_home = 0.0
    total_sold = total_use = 0.0

    for i, r in enumerate(records, 1):

        shop1 = float(r.shop1 or 0)
        shop2 = float(r.shop2 or 0)
        shop3 = float(r.shop3 or 0)
        calf = float(r.calf or 0)
        home = float(r.home or 0)

        total_sold_day = shop1 + shop2 + shop3
        total_use_day = total_sold_day + calf + home

        monthly_data.append({
            "no": i,
            "date": r.date,
            "shop1": round(shop1, 2),
            "shop2": round(shop2, 2),
            "shop3": round(shop3, 2),
            "calf": round(calf, 2),
            "home": round(home, 2),
            "total_sold": round(total_sold_day, 2),
            "total_use": round(total_use_day, 2)
        })

        total_shop1 += shop1
        total_shop2 += shop2
        total_shop3 += shop3
        total_calf += calf
        total_home += home
        total_sold += total_sold_day
        total_use += total_use_day

    return {
        "monthly_data": monthly_data,
        "selected_date": selected_date,

        "total_shop1": round(total_shop1, 2),
        "total_shop2": round(total_shop2, 2),
        "total_shop3": round(total_shop3, 2),
        "total_calf": round(total_calf, 2),
        "total_home": round(total_home, 2),
        "total_sold": round(total_sold, 2),
        "total_use": round(total_use, 2)
    }

from datetime import date

def get_financial_dashboard_data(selected_date=None):

    # =====================================
    # DEFAULT DATE
    # =====================================

    if not selected_date:
        from datetime import date; selected_date = __import__('datetime').date.today().strftime("%Y-%m-%d")

    # =====================================
    # LOAD ALL MODULES
    # =====================================

    milk = get_milk_sales(selected_date)

    vehicle_sales = get_sales_report_data(selected_date)

    vehicle_expenses = get_car_expense_report_data(selected_date)

    payments = get_transactions_data(selected_date)

    employees_data = get_employees_data()

    # =====================================
    # SALARY
    # =====================================

    total_salary = sum(

        emp["salary"]

        for emp in employees_data["employees"]

    )

    # =====================================
    # REVENUE
    # =====================================

    milk_revenue = milk.get("daily_revenue", 0)

    vehicle_revenue = vehicle_sales.get("total_sales", 0)

    total_revenue = (

        milk_revenue

        + vehicle_revenue

    )

    # =====================================
    # EXPENSES
    # =====================================

    feed_expense = payments.get(

        "feed_daily",

        0

    )

    other_expense = payments.get(

        "other_daily",

        0

    )

    vehicle_expense = vehicle_expenses.get(

        "total_expense",

        0

    )

    total_expense = (

        feed_expense

        + other_expense

        + vehicle_expense

        + total_salary

    )

    # =====================================
    # PROFIT
    # =====================================

    net_profit = (

        total_revenue

        - total_expense

    )

    # =====================================
    # PROFIT %
    # =====================================

    if total_revenue:

        profit_margin = round(

            (net_profit / total_revenue) * 100,

            2

        )

    else:

        profit_margin = 0

    # =====================================
    # FINAL DATA
    # =====================================

    return {

        "selected_date": selected_date,

        "total_revenue": round(total_revenue,2),

        "total_expense": round(total_expense,2),

        "net_profit": round(net_profit,2),

        "profit_margin": profit_margin,

        **milk,

        **vehicle_sales,

        **vehicle_expenses,

        **payments,

        **employees_data

    }
    
CONFIRMATION_METHODS = {
    "heat observation": 21,
    "ultrasound": 30,
    "manual check": 90
}

# from sqlalchemy import desc

# def get_price_for_date(sale_date):

#     price = MilkPrice.query.filter(
#         MilkPrice.effective_date <= sale_date
#     ).order_by(
#         MilkPrice.effective_date.desc()
#     ).first()

#     return float(price.price) if price else 0

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'magicdevelopers9@gmail.com'
app.config['MAIL_PASSWORD'] = 'rhif qhmm hvnk tjhv'
app.config['MAIL_DEFAULT_SENDER'] = 'MY FARM <magicdevelopers9@gmail.com>'

mail = Mail(app)

def get_employees_data():

    employees = EmployeesRegistry.query.all()

    data = []

    for i, emp in enumerate(employees, start=1):
        data.append({
            "id": emp.id,
            "name": emp.EmployeeName,   # 🔥 mapped here
            "id_number": emp.ID_Number,
            "phone": emp.phone,
            "salary": float(emp.salary or 0),
            "role": emp.role
        })

    return {"employees": data}

# ================= UNIVERSAL REPORT ENGINE ================= #

def generate_pdf(template_name, context, filename):
    """Generate PDF from HTML template using WeasyPrint"""
    from weasyprint import HTML

    rendered_html = render_template(template_name, **context)

    folder = os.path.join("static", "reports")
    os.makedirs(folder, exist_ok=True)

    file_path = os.path.join(folder, filename)

    HTML(
        string=rendered_html,
        base_url=os.getcwd()
    ).write_pdf(
        target=file_path
    )

    return file_path

@app.route('/send_report/<report_type>')
@login_required
def send_report(report_type):

    selected_date = request.args.get("date")

    if report_type == "milk":
        data = get_milk_report_data(selected_date)
        template = "milk_pdf.html"
        filename = f"milk_{selected_date or 'today'}.pdf"

    elif report_type == "car_expenses":
        data = get_car_expense_report_data(selected_date)
        template = "car_expenses_reportpdf.html"
        filename = f"car_expenses_{selected_date or 'all'}.pdf"

    elif report_type == "car_sales":
        data = get_sales_report_data(selected_date)
        template = "car_sales_reportpdf.html"
        filename = f"sales_{selected_date or 'all'}.pdf"

    elif report_type == "animals":
        category = request.args.get("category")
        data = get_animals_data(category)
        template = "animals_pdf.html"
        filename = f"animals_{category or 'all'}.pdf"

    elif report_type == "shed_report":

        data = get_shed_report_data()

        template = "shed_report_pdf.html"

        filename = "shed_report.pdf"

    elif report_type == "treatment":

        date_str = request.args.get("date")
        status = request.args.get("status")

        data = get_treatment_data(date, status)

        from datetime import datetime
        data["now"] = datetime.now()

        template = "treatment_pdf.html"

        filename = f"treatment_{date or 'all'}_{status or 'all'}.pdf"

    elif report_type == "insemination":

        status = request.args.get("status")
        month = request.args.get("month")
        year = request.args.get("year")

        data = get_insemination_data(status, month, year)

        template = "insemination_pdf.html"

        filename = f"insemination_{status or 'all'}_{month or year or 'all'}.pdf"

    elif report_type == "milk_sale":

        data = get_milk_sales(selected_date)

        template = "milk_sales_reportpdf.html"

        filename = f"milk_sale_{selected_date or 'all'}.pdf"

    elif report_type == "transactions":

        filter_date_str = request.args.get("filter_date")
        month = request.args.get("month")
        purpose = request.args.get("purpose")
        farm_id = request.args.get("farm_id")

        data = get_transactions_data(
            filter_date_str,
            month,
            purpose,
            farm_id
        )

        template = "transactions_pdf.html"

        filename = f"transactions_{month or filter_date_str or 'all'}.pdf"

    elif report_type == "cow_analysis":

        from datetime import datetime

        date_str = request.args.get("date")

        data = get_monthly_cow_analysis(date_str)

        cow_report = []

        for i, cow in enumerate(
            data["monthly_cows"],
            start=1
        ):

            avg = (
                cow.total_milk /
                cow.days_recorded
            ) if cow.days_recorded > 0 else 0

            cow_report.append({
                "no": i,
                "name": cow.cow_name,
                "total": float(cow.total_milk),
                "average": round(avg, 2)
            })

        month_name = "All Records"

        if date_str:
            try:
                month_name = datetime.strptime(
                    date_str,
                    "%Y-%m-%d"
                ).strftime("%B %Y")
            except:
                month_name = date_str

        data["cow_report"] = cow_report
        data["month_name"] = month_name

        template = "cow_analysis_pdf.html"

        filename = f"cow_analysis_{date_str or 'all'}.pdf"

    elif report_type == "milk_sales_monthly":

        selected_date = request.args.get("date")

        data = get_milk_sales_monthly(
            selected_date
        )

        from datetime import datetime

        month_name = "All Records"

        if selected_date:
            try:
                month_name = datetime.strptime(
                    selected_date,
                    "%Y-%m-%d"
                ).strftime("%B %Y")
            except:
                month_name = selected_date

        data["month_name"] = month_name

        template = "milk_sales_monthly_pdf.html"

        filename = f"milk_sales_monthly_{selected_date or 'all'}.pdf"

    elif report_type == "feeds_orders":

        month = request.args.get("month")
        farm_id = request.args.get("farm_id")

        orders = get_orders(month, farm_id)

        total_all = sum(
            o["total"]
            for o in orders
        )

        total_paid = sum(
            o["paid"]
            for o in orders
        )

        total_debt = (
            total_all -
            total_paid
        )

        data = {
            "orders": orders,
            "selected_month": month,
            "total_all": total_all,
            "total_paid": total_paid,
            "total_debt": total_debt
        }

        template = "pdf/feeds_orders.html"

        filename = f"feeds_orders_{month or 'all'}.pdf"

    elif report_type == "feeds_order_detail":

        order_id = request.args.get("order_id")

        order = FeedsOrderV2.query.get_or_404(
            order_id
        )

        summary = build_order_summary(
            order
        )

        items = []

        for item in order.items:

            delivered, remaining, status, color = (
                calc_item_delivery(item)
            )

            items.append({
                "name": item.feed_name,
                "quantity": item.quantity,
                "price": item.price_per_unit,
                "total": item.total_cost,
                "delivered": delivered,
                "remaining": remaining,
                "status": status
            })

        data = {
            "order": order,
            "summary": summary,
            "items": items
        }

        template = "pdf/order_detail.html"

        filename = f"order_{order.order_ref}.pdf"

    elif report_type == "feeds_delivery":

        order_id = request.args.get("order_id")

        deliveries = (
            FeedsDeliveryV2.query
            .filter_by(order_id=order_id)
            .all()
        )

        data = {
            "deliveries": deliveries
        }

        template = "pdf/delivery.html"

        filename = f"delivery_{order_id or 'all'}.pdf"

    elif report_type == "feeds_payments":

        order_id = request.args.get("order_id")

        order = FeedsOrderV2.query.get_or_404(order_id)

        payments = (
            Payment.query
            .filter_by(
                purpose_type="feeds",
                purpose=f"Feeds Order {order.order_ref}"
            )
            .order_by(Payment.date_paid.desc())
            .all()
        )

        total_paid = sum(
            float(p.amount or 0)
            for p in payments
        )

        data = {
            "order": order,
            "payments": payments,
            "total_paid": total_paid
        }

        template = "pdf/payments.html"

        filename = f"payments_{order.order_ref}.pdf"

    elif report_type == "employees":

        data = get_employees_data()

        template = "employees_pdf.html"

        filename = "employees_report.pdf"

    else:

        return """
        <script>
            alert("❌ Invalid report type");
            window.history.back();
        </script>
        """

    pdf_path = generate_pdf(
        template,
        data,
        filename
    )

    return send_file(
        pdf_path,
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf"
    )
@app.route("/cow_registry", methods=["GET", "POST"])
@login_required

def cow_registry():
    message = None

    # Farm context: list only cows of the current farm
    farm_id = session.get("farm_id")

    if request.method == "POST":
        new_name = request.form.get("name")
        breed = request.form.get("breed")
        dob = request.form.get("dob")
        category = request.form.get("category")
        sex = request.form.get("sex")
        mother = request.form.get("mother")
        

        #category=request.form["category"]
        

        # 🔍 VALIDATION
        if not new_name or not breed or not category:
            message = "All fields are required"
            return render_template("cow_registry.html", message=message)

        if dob:
            dob = datetime.strptime(dob, "%Y-%m-%d").date()
        else: dob=None

        if mother:
            mother = mother
        else: mother=None
        # Convert date string to date object
        #date_bought_obj = datetime.strptime(date_bought, "%Y-%m-%d").date()
        # Convert cost to float
        #cost_val = float(cost)

        cow_names = AnimalRegistry.query.filter_by(name=new_name).all()
        if cow_names:
            message="A cow with that name already exist"
            return render_template("cow_registry.html", message=message)


        new_registry = AnimalRegistry(
            name=new_name,
            breed=breed,
            dob=dob,
            category=category,
            sex=sex,
            mother=mother,
            farm_id=current_entry_farm_id()
        )

        db.session.add(new_registry)
        db.session.commit()
        message="Succesifully added"
        
    # List cows of current farm only
    if farm_id:
        cows = AnimalRegistry.query.filter_by(farm_id=farm_id).all()
    else:
        cows = AnimalRegistry.query.all()

    return render_template("cow_registry.html", message=message, cows=cows)


@app.route("/animals")
@login_required
def animals():

    category = request.args.get("category")

    data = get_animals_data(category, session.get("farm_id"))

    return render_template(
        "animals.html",
        category=category,
        **data
    )



@app.route("/delete_cow/<int:id>", methods=["GET", "POST"])
@login_required
def delete_animal(id):

    animal = AnimalRegistry.query.get_or_404(id)

    db.session.delete(animal)
    db.session.commit()

    return redirect(url_for("animals"))






    # ================= POST =================
@app.route("/edit_animal_record/<int:id>", methods=["GET", "POST"])
@login_required
def edit_animal_record(id):

    animal = AnimalRegistry.query.get_or_404(id)

    if request.method == "POST":

        animal.name = request.form.get("name")
        animal.breed = request.form.get("breed")
        
        # Safer date handling
        date_value = request.form.get("dob")
        if date_value:
            animal.dob = datetime.strptime(date_value, "%Y-%m-%d").date()
        else: animal.dob=None

        animal.category = request.form.get("category")
        animal.sex = request.form.get("sex")
        sex = request.form.get("sex")
        if sex:
            animal.sex = sex
        else: animal.sex=None
        animal.mother = request.form.get("mother")
        mother = request.form.get("mother")
        if mother:
            animal.mother = mother

        db.session.commit()

        return redirect(url_for("animals"))

    return render_template("edit_animal_record.html", animal=animal)

@app.route("/sheds", methods=["GET", "POST"])
@login_required
def sheds():

    edit_shed = None

    # =========================
    # EDIT MODE
    # =========================

    edit_id = request.args.get("edit")

    if edit_id:

        edit_shed = CowShed.query.get(edit_id)

    # =========================
    # SAVE / UPDATE
    # =========================

    if request.method == "POST":

        try:

            shed_id = request.form.get("shed_id")

            name = request.form.get("name")
            capacity = request.form.get("capacity")
            category_allowed = request.form.get(
                "category_allowed"
            )
            color = request.form.get("color")
            description = request.form.get(
                "description"
            )

            # =========================
            # UPDATE EXISTING
            # =========================

            if shed_id:

                shed = CowShed.query.get(shed_id)

                existing = CowShed.query.filter(
                    CowShed.name.ilike(name),
                    CowShed.id != shed.id
                ).first()

                if existing:

                    flash(
                        "Another shed with that "
                        "name already exists",
                        "warning"
                    )

                    return redirect(
                        url_for(
                            "sheds",
                            edit=shed.id
                        )
                    )

                shed.name = name
                shed.capacity = int(capacity or 0)
                shed.category_allowed = category_allowed
                shed.color = color
                shed.description = description

                flash(
                    "Shed updated successfully",
                    "success"
                )

            # =========================
            # CREATE NEW
            # =========================

            else:

                existing = CowShed.query.filter(
                    CowShed.name.ilike(name)
                ).first()

                if existing:

                    flash(
                        "Shed already exists",
                        "warning"
                    )

                    return redirect(
                        url_for("sheds")
                    )

                shed = CowShed(
                    name=name,
                    capacity=int(capacity or 0),
                    category_allowed=category_allowed,
                    color=color,
                    description=description
                )

                db.session.add(shed)

                flash(
                    "Shed added successfully",
                    "success"
                )

            db.session.commit()

            return redirect(url_for("sheds"))

        except Exception as e:

            db.session.rollback()

            flash(
                f"Error: {str(e)}",
                "danger"
            )

    sheds = CowShed.query.order_by(
        CowShed.id.desc()
    ).all()
    manage_shed = None
    available_cows = []
    shed_cows = []

    manage_id = request.args.get("manage")

    if manage_id:

        manage_shed = CowShed.query.get(manage_id)

        # cows NOT in any shed OR in different shed
        available_cows = AnimalRegistry.query.filter(
            (AnimalRegistry.current_shed_id == None) |
            (AnimalRegistry.current_shed_id != manage_shed.id)
        ).all()

        # cows currently in this shed
        shed_cows = AnimalRegistry.query.filter_by(
            current_shed_id=manage_shed.id
        ).all()
    return render_template(
        "sheds.html",
        sheds=sheds,
        edit_shed=edit_shed,
        manage_shed=manage_shed,
        available_cows=available_cows,
        shed_cows=shed_cows
    )
@app.route("/assign_shed/<int:cow_id>/<int:shed_id>")
@login_required
def assign_shed(cow_id, shed_id):

    cow = AnimalRegistry.query.get_or_404(cow_id)
    shed = CowShed.query.get_or_404(shed_id)

    # CAPACITY CHECK
    if shed.occupied >= shed.capacity:

        flash("Shed is full", "danger")
        return redirect(request.referrer)

    cow.current_shed_id = shed.id

    db.session.commit()

    flash(f"{cow.name} added to {shed.name}", "success")

    return redirect(request.referrer)


@app.route("/remove_from_shed/<int:cow_id>")
@login_required
def remove_from_shed(cow_id):

    cow = AnimalRegistry.query.get_or_404(cow_id)

    cow.current_shed_id = None

    db.session.commit()

    flash(f"{cow.name} removed from shed", "warning")

    return redirect(request.referrer)
@app.route("/move_animal/<int:animal_id>", methods=["POST"])
@login_required
def move_animal(animal_id):

    animal = AnimalRegistry.query.get_or_404(animal_id)

    new_shed_id = request.form.get("new_shed_id")

    reason = request.form.get("reason")

    new_shed = CowShed.query.get(new_shed_id)

    if not new_shed:
        flash("Invalid shed selected", "danger")
        return redirect(request.referrer)

    # FULL CHECK
    if new_shed.is_full:

        flash(
            f"{new_shed.name} is already full",
            "danger"
        )

        return redirect(request.referrer)

    old_shed_id = animal.current_shed_id

    animal.current_shed_id = new_shed.id

    movement = AnimalMovement(
        animal_id=animal.id,
        from_shed_id=old_shed_id,
        to_shed_id=new_shed.id,
        reason=reason
    )

    db.session.add(movement)

    db.session.commit()

    flash(
        f"{animal.name} moved successfully",
        "success"
    )

    return redirect(request.referrer)

@app.route("/shed_report")
@login_required
def shed_report():

    return render_template(
        "shed_report.html",
        **get_shed_report_data()
    )


@app.route("/treatment", methods=["GET", "POST"])

@login_required
def treatment():

    # Farm permission check: non-admin users are locked to their farm,
    # admin follows the farm context selected in the switcher
    farm_id = session.get("farm_id")

    if request.method == "POST":

        selected_ids = request.form.getlist("treatment_ids")

        if "delete_selected" in request.form:
            for rid in selected_ids:
                rec = Treatment.query.get(int(rid))
                if rec:
                    # Check farm permission
                    if farm_id and rec.farm_id != farm_id:
                        flash("Access denied. You don't have permission for this treatment.", "error")
                        return redirect(url_for("treatment"))
                    db.session.delete(rec)

            db.session.commit()

        return redirect(url_for("treatment"))

    date_str = request.args.get("date")
    status = request.args.get("status")  # Status navigation

    # Farm filtering
    if farm_id:
        if status:
            data = get_treatment_data(date_str, status, farm_id=farm_id)
        else:
            data = get_treatment_data(date_str, farm_id=farm_id)
    else:
        if status:
            data = get_treatment_data(date_str, status)
        else:
            data = get_treatment_data(date_str)

    return render_template("treatment.html", **data)

@app.route("/add_treatment", methods=["GET","POST"])
@login_required
def add_treatment():

    # Farm filtering for non-admin users
    animals = AnimalRegistry.query.all()

    if session.get("role") != "admin":
        farm_id = session.get("farm_id")
        if farm_id:
            animals = [a for a in animals if a.farm_id == farm_id]

    if request.method == "POST":

        record = Treatment(
            animal_id=request.form.get("animal_id"),
            date_treated=datetime.strptime(request.form.get("date"), "%Y-%m-%d"),
            illness=request.form.get("illness"),
            cost=float(request.form.get("cost")),
            vet=request.form.get("vet"),
            status=request.form.get("status"),
            farm_id=current_entry_farm_id()
        )

        db.session.add(record)
        db.session.commit()

        return redirect(url_for("treatment"))

    return render_template("add_treatment.html", animals=animals)

@app.route("/edit_treatment/<int:id>", methods=["GET","POST"])
@login_required
def edit_treatment(id):

    rec = Treatment.query.get_or_404(id)

    # Farm permission check
    if session.get("role") != "admin" and session.get("farm_id"):
        if rec.animal.farm_id != session["farm_id"]:
            flash("Access denied. You don't have permission for this treatment.", "error")
            return redirect(url_for("treatment"))

    if request.method == "POST":
        rec.status = request.form.get("status")
        rec.cost = float(request.form.get("cost"))
        db.session.commit()
        return redirect(url_for("treatment"))

    return render_template("edit_treatment.html", rec=rec)


@app.route("/delete_treatment/<int:id>")
@login_required
def delete_treatment(id):

    rec = Treatment.query.get_or_404(id)
    db.session.delete(rec)
    db.session.commit()

    return redirect(url_for("treatment"))

@app.route("/calf_registry", methods=["GET", "POST"])
@login_required
def calf_registry():
    message = None

    farm_id = session.get("farm_id")

    if request.method == "POST":
        calf_name = request.form.get("name")
        breed = request.form.get("breed")
        birth_day = request.form.get("birth_day")
        level = request.form.get("level")
        mother=request.form.get("mother")

        # 🔍 VALIDATION
        if not calf_name or not breed or not birth_day or not mother:
            message = "All fields are required"
            return render_template("calf_registry.html", message=message)
        exist_records=AnimalRegistry.query.filter_by(name=calf_name).all()
        exist_mother=AnimalRegistry.query.filter_by(name=mother).all()
        if exist_records:
            message="Another livestock bears the same name"
            return render_template("calf_registry.html", message=message)
        if not exist_mother:
            message="The mother you entered does not exist"
            return render_template("calf_registry.html", message=message)
        
        
        #Convert date string to date object
        date_bought_obj = datetime.strptime(birth_day, "%Y-%m-%d").date()
        new_registry = AnimalRegistry(
            name=calf_name,
            breed=breed,
            dob=date_bought_obj,
            category=level,
            mother=mother,
            farm_id=current_entry_farm_id()
        )

        db.session.add(new_registry)
        db.session.commit()
        message="Succesifully added"
        
    # List calves of current farm only
    if farm_id:
        calves = AnimalRegistry.query.filter(
            AnimalRegistry.category.ilike("calf")
        ).filter_by(farm_id=farm_id).all()
    else:
        calves = AnimalRegistry.query.filter(
            AnimalRegistry.category.ilike("calf")
        ).all()

    return render_template("calf_registry.html", message=message, calves=calves)


@app.route("/insemination/add", methods=["GET","POST"])
@login_required
def add_insemination():

    animals = AnimalRegistry.query.all()

    # Set farm filtering for non-admin users
    if session.get("role") != "admin":
        farm_id = session.get("farm_id")
        if farm_id:
            animals = [a for a in animals if a.farm_id == farm_id]

    if request.method == "POST":

        animal_id = request.form["animal_id"]
        date_served = datetime.strptime(request.form["date_served"], "%Y-%m-%d")
        method = request.form["method"]

        days = CONFIRMATION_METHODS.get(method, 30)

        confirmation_date_str = date_served + timedelta(days=days)

        # Get the animal to set farm_id
        animal = AnimalRegistry.query.get(animal_id)
        record_farm_id = animal.farm_id if animal else None

        record = Insemination(
            animal_id=animal_id,
            date_served=date_served,
            confirmation_method=method,
            confirmation_date=confirmation_date_str,
            status="pending",
            calving_date=None,
            farm_id=record_farm_id
        )

        db.session.add(record)
        db.session.commit()

        return redirect("/insemination")

    return render_template("add_insemination.html", animals=animals)

from datetime import datetime

@app.route("/insemination")
@login_required
def insemination():

    # Default to showing confirmed/expectant mothers
    status = request.args.get("status") or "confirmed"
    month = request.args.get("month")
    year = request.args.get("year")

    # Farm filtering: non-admin locked to own farm, admin follows switcher
    farm_id = session.get("farm_id")

    data = get_insemination_data(status, month, year, farm_id)

    return render_template("insemination_list.html", **data)
@app.route("/insemination/delete/<int:id>")
@login_required
def delete_insemination(id):

    record = Insemination.query.get_or_404(id)

    db.session.delete(record)
    db.session.commit()

    return redirect("/insemination")

from datetime import datetime, timedelta

@app.route("/insemination/edit/<int:id>", methods=["GET","POST"])
@login_required
def edit_insemination(id):

    record = Insemination.query.get_or_404(id)
    animals = AnimalRegistry.query.all()

    # Farm filtering for non-admin users
    if session.get("role") != "admin":
        farm_id = session.get("farm_id")
        if farm_id:
            animals = [a for a in animals if a.farm_id == farm_id]

    if request.method == "POST":

        animal_id = request.form.get("animal_id")
        date_served = request.form.get("date_served")
        status = request.form.get("status")

        # 🔹 Get the animal to set farm_id
        animal = AnimalRegistry.query.get(animal_id) if animal_id else None
        record_farm_id = animal.farm_id if animal else session.get("farm_id")

        record.animal_id = animal_id
        record.status = status

        if date_served:
            record.date_served = datetime.strptime(date_served, "%Y-%m-%d").date()

        # 🔥 BUSINESS LOGIC
        if status == "confirmed":
            record.calving_date = record.date_served + timedelta(days=283)

        elif status == "aborted":
            record.calving_date = None

        elif status == "delivered":
            # keep existing calving date or set to today if missing
            if not record.calving_date:
                record.calving_date = datetime.now().date()

        else:
            # pending or empty
            record.calving_date = None

        record.farm_id = record_farm_id

        db.session.commit()

        return redirect("/insemination")

    return render_template(
        "edit_insemination.html",
        record=record,
        animals=animals
    )

   
@app.route("/asset_registry", methods=["GET", "POST"])
@login_required
def asset_registry():
    message = None

    if request.method == "POST":
        name = request.form.get("name")
        purpose = request.form.get("pupose")
        date_bought= request.form.get("date_bought")
        cost = request.form.get("cost")
        origin = request.form.get("origin")
        

        # 🔍 VALIDATION
        if not name or not purpose or not date_bought or not cost or not origin:
            message = "All fields are required"
            return render_template("asset_registry.html", message=message)

        # Convert date string to date object
        date_bought_obj = datetime.strptime(date_bought, "%Y-%m-%d").date()
        # Convert cost to float
        cost_val = float(cost)

        new_registry = AssetsRegistry(
            AssetName=name,
            Purpose=purpose,
            Bought_date=date_bought_obj,
            cost=cost_val,
            origin=origin
                      
        )

        db.session.add(new_registry)
        db.session.commit()
        message="Succesifully added"
        
    return render_template("asset_registry.html", message=message)

@app.route("/Assets", methods=["GET", "POST"])
@role_required("admin")
@login_required
def Assets():

    # ================= POST =================
    if request.method == "POST":

        selected_ids = request.form.getlist("AssetsRegistry_ids")

        if not selected_ids:
            return redirect(url_for("Assets"))


        # 🔹 DELETE
        if "delete_selected" in request.form:
            for aid in selected_ids:
                app_record = AssetsRegistry.query.get(int(aid))
                if app_record:
                    db.session.delete(app_record)

            db.session.commit()
            return redirect(url_for("Assets"))

    # ================= GET =================
    Assets = AssetsRegistry.query.all()
    current_date_str = date.today()

    return render_template(
        "Assets.html",
        Assets=Assets,
        current_date=current_date_str
    )


@app.route("/employee_registry", methods=["GET", "POST"])
@role_required("admin")
@login_required
def employee_registry():
    message = None

    if request.method == "POST":
        name = request.form.get("name")
        ID_Number = request.form.get("id_number")
        phone= request.form.get("phone")
        salary = request.form.get("salary")
        role = request.form.get("role")
        
        # 🔍 VALIDATION
        if not name or not ID_Number or not phone or not salary or not role:
            message = "All fields are required"
            return render_template("employee_registry.html", message=message)

        # Convert cost to float
        cost_val = float(salary)

        new_registry = EmployeesRegistry(
            EmployeeName=name,
            ID_Number=ID_Number,
            phone=phone,
            salary=cost_val,
            role=role,
            
                      
        )

        db.session.add(new_registry)
        db.session.commit()
        message="Succesifully added"
        
    return render_template("employee_registry.html", message=message)

@app.route("/Employees", methods=["GET", "POST"])
@login_required
@role_required("admin")
def Employees():

    if request.method == "POST":

        selected_ids = request.form.getlist("EmployeesRegistry_ids")

        if "delete_selected" in request.form:
            for eid in selected_ids:
                emp = EmployeesRegistry.query.get(int(eid))
                if emp:
                    db.session.delete(emp)

            db.session.commit()
            return redirect(url_for("Employees"))

    # 🔥 GET DATA
    Employees = EmployeesRegistry.query.all()
    current_date_str = date.today()

    # Created admin CALCULATE TOTAL SALARY
    total = sum(float(e.salary or 0) for e in Employees)

    return render_template(
        "Employees.html",
        Employees=Employees,
        current_date=current_date_str,
        total=total   # 🔥 FIX
    )

@app.route("/employees/edit/<int:id>", methods=["GET", "POST"])
@login_required
@role_required("admin")
def edit_employee(id):

    emp = EmployeesRegistry.query.get_or_404(id)

    if request.method == "POST":
        emp.EmployeeName = request.form.get("EmployeeName")
        emp.ID_Number = request.form.get("ID_Number")
        emp.phone = request.form.get("phone")

        # 🔥 SAFE salary handling
        salary = request.form.get("salary")
        emp.salary = float(salary) if salary else 0

        emp.role = request.form.get("role")

        db.session.commit()

        return redirect(url_for("Employees"))

    return render_template("edit_employee.html", emp=emp)

@app.route("/employees/delete/<int:id>", methods=["POST"])
@login_required
@role_required("admin")
def delete_employee(id):

    emp = EmployeesRegistry.query.get_or_404(id)

    db.session.delete(emp)
    db.session.commit()

    return redirect(url_for("Employees"))


@app.route("/farms", methods=["GET", "POST"])
@role_required("admin")
@login_required
def farms():

    message = None

    # ================= ADD FARM =================
    if request.method == "POST":

        action = request.form.get("action")

        # ---------- ADD ----------
        if action == "add":

            name = request.form.get("farm_name")

            if not name:
                message = "Farm name is required"

            else:
                existing = Farm.query.filter_by(name=name).first()

                if existing:
                    message = "Farm already exists"

                else:
                    new_farm = Farm(name=name)

                    db.session.add(new_farm)
                    db.session.commit()

                    message = "Farm added successfully"

        # ---------- EDIT ----------
        elif action == "edit":

            farm_id = request.form.get("farm_id")
            new_name = request.form.get("farm_name")

            farm = Farm.query.get(farm_id)

            if farm:

                existing = Farm.query.filter(
                    Farm.name == new_name,
                    Farm.id != farm.id
                ).first()

                if existing:
                    message = "Another farm with that name already exists"

                else:
                    farm.name = new_name

                    db.session.commit()

                    message = "Farm updated successfully"

        # ---------- DELETE ----------
        elif action == "delete":

            farm_id = request.form.get("farm_id")

            farm = Farm.query.get(farm_id)

            if farm:

                db.session.delete(farm)
                db.session.commit()

                message = "Farm deleted successfully"

    farms = Farm.query.order_by(Farm.id.desc()).all()

    return render_template(
        "farms.html",
        farms=farms,
        message=message
    )
from sqlalchemy import extract

@app.route("/feeds_v2/orders")
@role_required("admin")
def orders_v2():

    month = request.args.get("month")
    farm_id = request.args.get("farm_id")

    # Non-admin users only see their own farm orders
    if session.get("role") != "admin":
        farm_id = session.get("farm_id")

    query = FeedsOrderV2.query

    if month:
        year, m = month.split("-")
        query = query.filter(
            extract('year', FeedsOrderV2.date_ordered) == int(year),
            extract('month', FeedsOrderV2.date_ordered) == int(m)
        )

    if farm_id:
        query = query.filter_by(farm_id=int(farm_id))

    orders_raw = query.order_by(FeedsOrderV2.date_ordered.desc()).all()
    orders = [build_order_summary(o) for o in orders_raw]

    total_all = sum(o["total"] for o in orders)
    total_paid = sum(o["paid"] for o in orders)
    total_debt = sum(o["balance"] for o in orders)

    farms = Farm.query.all()

    return render_template(
        "v2/orders.html",
        orders=orders,
        total_all=total_all,
        total_paid=total_paid,
        total_debt=total_debt,
        selected_month=month,
        farms=farms
    )



@app.route("/feeds_v2/delete/<int:id>", methods=["POST"])
@role_required("admin")
def delete_order(id):

    order = FeedsOrderV2.query.get_or_404(id)

    db.session.delete(order)
    db.session.commit()

    return redirect("/feeds_v2/orders")


# =========================================================
# DELIVERY REPORT ROUTE
# =========================================================
@app.route("/feeds_v2/delivery_report")
@role_required("admin")
def delivery_report():

    date_filter = request.args.get("date")
    month_filter = request.args.get("month")
    order_id = request.args.get("order_id")

    query = FeedsDeliveryV2.query

    selected_date = None
    selected_month = None

    # =========================================
    # 🔍 DATE FILTER
    # =========================================
    if date_filter:
        try:

            selected_date = datetime.strptime(
                date_filter,
                "%Y-%m-%d"
            ).date()

            query = query.filter(
                FeedsDeliveryV2.date_delivered == selected_date
            )

        except:
            selected_date = None

    # =========================================
    # 🔍 MONTH FILTER
    # =========================================
    if month_filter:

        try:

            selected_month = datetime.strptime(
                month_filter,
                "%Y-%m"
            )

            query = query.filter(
                extract('month', FeedsDeliveryV2.date_delivered)
                == selected_month.month,

                extract('year', FeedsDeliveryV2.date_delivered)
                == selected_month.year
            )

        except:
            selected_month = None

    # =========================================
    # 🔍 ORDER FILTER
    # =========================================
    if order_id:

        try:
            query = query.filter_by(
                order_id=int(order_id)
            )
        except:
            pass

    # =========================================
    # 📦 GET DATA
    # =========================================
    deliveries = query.order_by(
        FeedsDeliveryV2.date_delivered.desc()
    ).all()

    # =========================================
    # 📊 TOTALS
    # =========================================
    total_delivered = sum(
        float(d.quantity_delivered or 0)
        for d in deliveries
    )

    total_pieces = sum(
        int(d.pieces or 0)
        for d in deliveries
    )

    return render_template(
        "v2/delivery_report.html",

        deliveries=deliveries,

        selected_date=selected_date,
        selected_month=month_filter,

        total_delivered=round(total_delivered, 2),
        total_pieces=total_pieces,

        order_id=order_id
    )


# =========================================================
# EDIT DELIVERY
# =========================================================

@app.route("/feeds_v2/delivery/edit/<int:id>", methods=["GET", "POST"])
@role_required("admin")
def edit_delivery(id):

    delivery = FeedsDeliveryV2.query.get_or_404(id)

    if request.method == "POST":

        # =========================================
        # 🔹 SAFE DATE
        # =========================================
        try:
            delivery.date_delivered = datetime.strptime(
                request.form.get("date_delivered"),
                "%Y-%m-%d"
            ).date()
        except:
            pass

        # =========================================
        # 🔹 PIECES
        # =========================================
        try:
            pieces = int(
                request.form.get("pieces") or 0
            )
        except:
            pieces = 0

        # =========================================
        # 🔹 UNIT WEIGHT
        # =========================================
        try:
            unit_weight = float(
                request.form.get("unit_weight") or 0
            )
        except:
            unit_weight = 0

        # =========================================
        # 🔥 AUTO CALCULATE TOTAL KG
        # =========================================
        quantity_delivered = pieces * unit_weight

        # =========================================
        # 🔥 VALIDATE AGAINST ORDER
        # =========================================

        item = delivery.item

        ordered_qty = float(item.quantity or 0)

        other_deliveries = sum(
            float(d.quantity_delivered or 0)
            for d in item.order.deliveries
            if d.id != delivery.id
            and d.item_id == item.id
        )

        remaining_allowed = ordered_qty - other_deliveries

        if quantity_delivered > remaining_allowed:

            flash(
                f"❌ Cannot exceed remaining quantity ({remaining_allowed:.2f} kg)",
                "danger"
            )

            return redirect(request.url)

        # =========================================
        # 🔥 SAVE
        # =========================================

        delivery.pieces = pieces
        delivery.unit_weight = unit_weight
        delivery.quantity_delivered = quantity_delivered

        db.session.commit()

        flash("Created admin Delivery updated successfully", "success")

        return redirect(url_for(
            "delivery_report",
            order_id=delivery.order_id
        ))

    return render_template(
        "v2/edit_delivery.html",
        delivery=delivery
    )


# =========================================================
# DELETE DELIVERY
# =========================================================

@app.route("/feeds_v2/delivery/delete/<int:id>", methods=["POST"])
@role_required("admin")
def delete_delivery(id):

    delivery = FeedsDeliveryV2.query.get_or_404(id)

    order_id = delivery.order_id

    db.session.delete(delivery)
    db.session.commit()

    flash("Created admin Delivery deleted successfully", "success")

    return redirect(url_for(
        "delivery_report",
        order_id=order_id
    ))

@app.route("/feeds_v2/search_feed")
@role_required("admin")
def search_feed():

    term = request.args.get("q", "").strip().lower()

    feeds = FeedsRegistry.query.filter(
        func.lower(FeedsRegistry.FeedName).like(f"%{term}%")
    ).with_entities(FeedsRegistry.FeedName).distinct().all()

    results = [f.FeedName for f in feeds]

    return {"results": results}

@app.route("/feeds_v2/create", methods=["GET", "POST"])
@role_required("admin")
def create_order():

    farms = Farm.query.all()

    if request.method == "POST":

        farm_id = request.form.get("farm_id") or current_entry_farm_id()

        order = FeedsOrderV2(
            order_ref=generate_order_ref(),
            date_ordered=datetime.strptime(request.form["date"], "%Y-%m-%d"),
            farm_id=int(farm_id)
        )

        db.session.add(order)
        db.session.flush()

        names = request.form.getlist("feed_name[]")
        qtys = request.form.getlist("quantity[]")
        prices = request.form.getlist("price[]")

        for i in range(len(names)):
            qty = float(qtys[i])
            price = float(prices[i])

            db.session.add(FeedsOrderItemV2(
                order_id=order.id,
                feed_name=names[i],
                quantity=qty,
                price_per_unit=price,
                total_cost=qty * price
            ))

        db.session.commit()
        return redirect("/feeds_v2/orders")

    return render_template("v2/create_order.html", farms=farms)

@app.route("/feeds_v2/delivery/<int:order_id>", methods=["GET", "POST"])
@role_required("admin")
def delivery_v2(order_id):

    order = FeedsOrderV2.query.get_or_404(order_id)
    item = FeedsOrderItemV2.query.get_or_404(request.args.get("item_id"))

    delivered = sum(
        d.quantity_delivered or 0
        for d in order.deliveries
        if d.item_id == item.id
    )

    remaining = float(item.quantity) - float(delivered)

    if request.method == "POST":

        qty = float(request.form.get("quantity"))
        pieces = int(request.form.get("pieces"))
        unit_weight = int(request.form.get("unit_weight"))

        if qty > remaining:
            flash("❌ Cannot exceed remaining", "danger")
            return redirect(request.url)

        db.session.add(FeedsDeliveryV2(
            order_id=order.id,
            item_id=item.id,
            date_delivered=datetime.today().date(),
            pieces=pieces,
            unit_weight=unit_weight,
            quantity_delivered=qty
        ))

        db.session.commit()
        return redirect(f"/feeds_v2/view/{order.id}")

    return render_template("v2/delivery.html", order=order, item=item, remaining=remaining)

@app.route("/feeds_v2/payment/<int:order_id>", methods=["GET", "POST"])
@role_required("admin")
def payment(order_id):

    order = FeedsOrderV2.query.get_or_404(order_id)

    if request.method == "POST":

        p = Payment(
            farm_id=order.farm_id,
            date_paid=datetime.today().date(),
            amount=float(request.form["amount"]),
            account=request.form["account"],

            # 🔥 AUTO VALUES
            purpose_type="feeds",
            purpose=f"Feeds Order {order.order_ref}"
        )

        db.session.add(p)
        db.session.commit()

        return redirect(f"/feeds_v2/view/{order.id}")

    total, paid, balance, status, color = get_payment_status(order)

    return render_template(
        "v2/payment.html",
        order=order,
        total=total,
        paid=paid,
        balance=balance
    )

@app.route("/feeds_v2/payment_report")
@role_required("admin")
def payment_report():

    order_id = request.args.get("order_id")
    order = None
    query = Payment.query

    if order_id:
        order = FeedsOrderV2.query.get(order_id)
        if order:
            query = query.filter(
                Payment.purpose == f"Feeds Order {order.order_ref}"
            )

    payments = query.order_by(Payment.date_paid.desc()).all()

    return render_template(
        "v2/payment_report.html",
        payments=payments,
        order_id=order_id,
        order=order
    )

@app.route("/feeds_v2/payment/delete/<int:id>", methods=["POST"])
@role_required("admin")
def delete_payment(id):

    payment = Payment.query.get_or_404(id)

    db.session.delete(payment)
    db.session.commit()

    return redirect(request.referrer or "/feeds_v2/orders")
from datetime import datetime

@app.route("/feeds_v2/payment/<int:order_id>", methods=["GET", "POST"])
@login_required
def add_feeds_payment(order_id):

    order = FeedsOrderV2.query.get_or_404(order_id)

    if request.method == "POST":

        try:
            date_paid = datetime.strptime(
                request.form.get("date_paid"), "%Y-%m-%d"
            ).date()
        except:
            date_paid = datetime.today().date()

        try:
            amount = float(request.form.get("amount"))
        except:
            amount = 0

        payment = Payment(
            farm_id=order.farm_id,
            date_paid=date_paid,
            amount=amount,
            account=request.form.get("account"),
            purpose_type="feeds",
            purpose=f"Feeds Order {order.order_ref}"
        )

        db.session.add(payment)
        db.session.commit()

        return redirect(url_for("view_order", id=order.id))

    total, paid, balance, status, color = calc_payment(order)

    return render_template(
        "v2/add_payment.html",
        order=order,
        total=total,
        paid=paid,
        balance=balance,
        current_date=datetime.today().strftime("%Y-%m-%d")
    )

@app.route("/feeds_v2/payment/edit/<int:id>", methods=["GET", "POST"])
@role_required("admin")
def edit_payment(id):

    # 🔹 GET PAYMENT
    payment = Payment.query.get_or_404(id)

    # 🔹 GET ORDER ID FROM URL
    order_id = request.args.get("order_id", type=int)

    # 🔹 LOAD ORDER SAFELY
    order = None

    if order_id:
        order = FeedsOrderV2.query.get(order_id)

    # 🔥 UPDATE
    if request.method == "POST":

        # DATE
        try:
            payment.date_paid = datetime.strptime(
                request.form.get("date_paid"),
                "%Y-%m-%d"
            ).date()
        except:
            pass

        # AMOUNT
        try:
            payment.amount = float(
                request.form.get("amount") or 0
            )
        except:
            payment.amount = 0

        # OTHER FIELDS
        payment.account = request.form.get("account")
        payment.purpose = request.form.get("purpose")

        db.session.commit()

        flash("Created admin Payment updated successfully", "success")

        # 🔥 GO BACK TO SAME PAYMENT REPORT
        if order:
            return redirect(
                url_for(
                    "payment_report",
                    order_id=order.id
                )
            )

        return redirect("/transactions")

    # 🔥 LOAD TEMPLATE
    return render_template(
        "v2/edit_payment.html",
        payment=payment,
        order=order
    )


@app.route("/feeds_v2/view/<int:id>")
@role_required("admin")
def view_order(id):

    order = FeedsOrderV2.query.get_or_404(id)
    summary = build_order_summary(order)

    items = []

    for item in order.items:

        delivered, remaining, status, color = calc_item_delivery(item)

        clean_name = (item.feed_name or "").strip().lower()

        latest_record = FeedsRegistry.query.filter(
            func.lower(func.trim(FeedsRegistry.FeedName)) == clean_name
        ).order_by(FeedsRegistry.id.desc()).first()

        prev_price = float(latest_record.Price) if latest_record and latest_record.Price else 0
        current_price = float(item.price_per_unit or 0)

        items.append({
            "item": item,
            "delivered": delivered,
            "remaining": remaining,
            "status": status,
            "color": color,
            "prev_price": round(prev_price, 2),
            "price_diff": round(current_price - prev_price, 2)
        })

    return render_template(
        "v2/view_order.html",
        #order=order,
        items=items,
        **summary
    )
@app.route("/feeds_v2/item/add/<int:order_id>", methods=["GET", "POST"])
@role_required("admin")
def add_item(order_id):

    order = FeedsOrderV2.query.get_or_404(order_id)

    if request.method == "POST":
        qty = float(request.form["quantity"])
        price = float(request.form["price"])

        item = FeedsOrderItemV2(
            order_id=order.id,
            feed_name=request.form["feed_name"],
            quantity=qty,
            price_per_unit=price,
            total_cost=qty * price
        )

        db.session.add(item)
        db.session.commit()

        return redirect(f"/feeds_v2/view/{order.id}")

    return render_template("v2/add_item.html", order=order)

@app.route("/feeds_v2/item/delete/<int:id>", methods=["POST"])
@role_required("admin")
def delete_item(id):

    item = FeedsOrderItemV2.query.get_or_404(id)

    db.session.delete(item)
    db.session.commit()

    return redirect(request.referrer or "/feeds_v2/orders")

@app.route("/feeds_v2/item/edit/<int:id>", methods=["GET", "POST"])
@role_required("admin")
def edit_item(id):

    item = FeedsOrderItemV2.query.get_or_404(id)

    if request.method == "POST":

        item.feed_name = request.form["feed_name"]
        item.quantity = float(request.form["quantity"])
        item.price_per_unit = float(request.form["price"])
        item.total_cost = item.quantity * item.price_per_unit

        db.session.commit()

        return redirect(f"/feeds_v2/view/{item.order_id}")

    return render_template("v2/edit_item.html", item=item)

@app.route("/delete_farm/<int:id>")
@login_required
@role_required("admin")
def delete_farm(id):

    farm = Farm.query.get_or_404(id)

    # Optional safety: prevent deleting if used
    if farm.feeds:
        return "⚠️ Cannot delete farm. It has associated feed records."

    db.session.delete(farm)
    db.session.commit()

    return redirect(url_for("farms"))


@app.route("/manage_milking", methods=["GET","POST"])
@login_required
def manage_milking():

    if request.method == "POST":

        selected_ids = request.form.getlist("animal_ids")

        if "add_selected" in request.form:

            for aid in selected_ids:

                exists = MilkingHerd.query.filter_by(animal_id=aid).first()

                if not exists:
                    new = MilkingHerd(animal_id=aid)
                    db.session.add(new)

            db.session.commit()


        if "remove_selected" in request.form:

            for aid in selected_ids:

                record = MilkingHerd.query.filter_by(animal_id=aid).first()

                if record:
                    db.session.delete(record)

            db.session.commit()

        return redirect(url_for("manage_milking"))

    animals = AnimalRegistry.query.filter(
        AnimalRegistry.category != "nolonger_exist"
    ).all()

    milking_cows = MilkingHerd.query.all()

    # Farm context: only cows belonging to the active farm
    farm_id = session.get("farm_id")

    if farm_id:
        animals = [
            a for a in animals
            if a.farm_id == farm_id
        ]
        milking_cows = [
            mh for mh in milking_cows
            if mh.animal and mh.animal.farm_id == farm_id
        ]

    return render_template(
        "manage_milking.html",
        animals=animals,
        milking_cows=milking_cows
    )

# =========================================================
# MILK REGISTRY MAIN ROUTE
# =========================================================

@app.route("/milk_registry", methods=["GET", "POST"])
@login_required
def milk_registry():

    if request.method == "POST":

        date_str = request.form.get("date")

        selected_date = datetime.strptime(
            date_str,
            "%Y-%m-%d"
        ).date()

        cow_ids = request.form.getlist("cow_id[]")
        mornings = request.form.getlist("morning[]")
        noons = request.form.getlist("noon[]")
        evenings = request.form.getlist("evening[]")

        for i in range(len(cow_ids)):

            try:

                cow_id = int(cow_ids[i])

                morning_raw = mornings[i].strip()
                noon_raw = noons[i].strip()
                evening_raw = evenings[i].strip()

                morning = (
                    float(morning_raw)
                    if morning_raw
                    else None
                )

                noon = (
                    float(noon_raw)
                    if noon_raw
                    else None
                )

                evening = (
                    float(evening_raw)
                    if evening_raw
                    else None
                )

                existing = MilkRegistry.query.filter_by(
                    cow_id=cow_id,
                    date=selected_date
                ).first()

                if existing:

                    if morning is not None:
                        existing.morning = morning

                    if noon is not None:
                        existing.noon = noon

                    if evening is not None:
                        existing.evening = evening

                    existing.total = (
                        float(existing.morning or 0) +
                        float(existing.noon or 0) +
                        float(existing.evening or 0)
                    )

                else:

                    total = (
                        float(morning or 0) +
                        float(noon or 0) +
                        float(evening or 0)
                    )

                    if total > 0:

                        record = MilkRegistry(
                            cow_id=cow_id,
                            date=selected_date,
                            morning=morning or 0,
                            noon=noon or 0,
                            evening=evening or 0,
                            total=total,
                            farm_id=current_entry_farm_id()
                        )

                        db.session.add(record)

            except Exception:
                continue

        db.session.commit()

        flash(
            "Milk records saved successfully.",
            "success"
        )

        return redirect(
            url_for("milk_registry")
        )

    cows = MilkingHerd.query.all()

    # Farm context: only cows belonging to the active farm
    farm_id = session.get("farm_id")

    if farm_id:
        cows = [
            mh for mh in cows
            if mh.animal and mh.animal.farm_id == farm_id
        ]

    current_date_str = date.today()

    return render_template(
        "milk_registry.html",
        cows=cows,
        current_date=current_date_str
    )


# =========================================================
# EXPORT EXCEL TEMPLATE
# =========================================================

@app.route("/milk_registry/export_template")
@login_required
def export_milk_template():

    cows = MilkingHerd.query.all()

    data = []

    for cow in cows:

        data.append({

            "Cow ID": cow.animal.id,
            "Cow Name": cow.animal.name,
            "Morning": "",
            "Noon": "",
            "Evening": ""

        })

    df = pd.DataFrame(data)

    os.makedirs("uploads", exist_ok=True)

    filepath = os.path.join(
        "uploads",
        "milk_template.xlsx"
    )

    df.to_excel(filepath, index=False)

    return send_file(
        filepath,
        as_attachment=True
    )


# =========================================================
# IMPORT EXCEL
# =========================================================

@app.route("/milk_registry/import", methods=["POST"])
@login_required
def import_milk_registry():

    file = request.files.get("excel_file")

    date_str = request.form.get("date")

    selected_date = datetime.strptime(
        date_str,
        "%Y-%m-%d"
    ).date()

    if not file:

        flash("Please select an Excel file.", "danger")

        return redirect(url_for("milk_registry"))

    df = pd.read_excel(file)

    imported_records = []

    total_milk = 0

    for _, row in df.iterrows():

        try:

            cow_id = int(row["Cow ID"])

            morning = float(row["Morning"] or 0)
            noon = float(row["Noon"] or 0)
            evening = float(row["Evening"] or 0)

            total = morning + noon + evening

            # ONLY ACCEPT COWS IN MILKING HERD
            cow = MilkingHerd.query.filter_by(
                animal_id=cow_id
            ).first()

            if cow:

                total_milk += total

                imported_records.append({

                    "cow_id": cow.animal.id,
                    "cow_name": cow.animal.name,
                    "morning": morning,
                    "noon": noon,
                    "evening": evening,
                    "total": total

                })

        except:
            continue

    return render_template(

        "confirm_milk_import.html",

        records=imported_records,
        selected_date=selected_date,
        total_milk=total_milk

    )


# =========================================================
# CONFIRM IMPORT SAVE
# =========================================================

@app.route(
    "/milk_registry/confirm_import",
    methods=["POST"]
)
@login_required
def confirm_import_milk():

    date_str = request.form.get("date")

    selected_date = datetime.strptime(
        date_str,
        "%Y-%m-%d"
    ).date()

    cow_ids = request.form.getlist("cow_id[]")
    mornings = request.form.getlist("morning[]")
    noons = request.form.getlist("noon[]")
    evenings = request.form.getlist("evening[]")

    for i in range(len(cow_ids)):

        cow_id = int(cow_ids[i])

        morning = float(mornings[i] or 0)
        noon = float(noons[i] or 0)
        evening = float(evenings[i] or 0)

        total = morning + noon + evening

        if total > 0:

            existing = MilkRegistry.query.filter_by(
                cow_id=cow_id,
                date_str=selected_date
            ).first()

            if existing:

                existing.morning = morning
                existing.noon = noon
                existing.evening = evening
                existing.total = total

            else:

                record = MilkRegistry(

                    cow_id=cow_id,
                    date_str=selected_date,
                    morning=morning,
                    noon=noon,
                    evening=evening,
                    total=total

                )

                db.session.add(record)

    db.session.commit()

    flash(
        "Imported milk records saved successfully.",
        "success"
    )

    return redirect(url_for("milk_registry"))



@app.route("/milk", methods=["GET", "POST"])
@login_required
def milk():

    # DELETE (unchanged)
    if request.method == "POST":

        selected_ids = request.form.getlist("MilkRegistry_ids")

        if "delete_selected" in request.form and selected_ids:

            for record_id in selected_ids:
                record = MilkRegistry.query.get(int(record_id))
                if record:
                    db.session.delete(record)

            db.session.commit()

        return redirect(url_for("milk"))

    # Created admin USE SHARED FUNCTION
    date_str = request.args.get("filter_date")

    data = get_milk_report_data(date_str, session.get("farm_id"))

    return render_template("milk.html", **data)

@app.route("/delete_milk/<int:id>")
@login_required
def delete_milk(id):

    record = MilkRegistry.query.get_or_404(id)
    selected_date = record.date
    db.session.delete(record)
    db.session.commit()

    return redirect(url_for("milk", filter_date_str=selected_date))

from decimal import Decimal

@app.route("/edit_milk/<int:id>", methods=["GET", "POST"])
@login_required
def edit_milk(id):

    record = MilkRegistry.query.get_or_404(id)
    selected_date = record.date
    if request.method == "POST":

        morning = Decimal(request.form.get("morning") or 0)
        noon = Decimal(request.form.get("noon") or 0)
        evening = Decimal(request.form.get("evening") or 0)

        record.morning = morning
        record.noon = noon
        record.evening = evening

        # Recalculate total safely using Decimal
        record.total = morning + noon + evening

        db.session.commit()

        return redirect(url_for("milk", filter_date_str=selected_date))

    return render_template("edit_milk.html", record=record)

from flask import request

@app.route("/cow-analysis")
@login_required
def cow_analysis():

    date_str = request.args.get("date")

    data = get_monthly_cow_analysis(date_str)

    cow_report = []

    for cow in data["monthly_cows"]:

        avg = (
            cow.total_milk / cow.days_recorded
            if cow.days_recorded > 0 else 0
        )

        cow_report.append({
            "name": cow.cow_name,
            "total": float(cow.total_milk),
            "average": round(avg, 2)
        })

    return render_template(
        "cow_analysis.html",
        cow_report=cow_report,
        data=data,              # Created admin THIS FIXES YOUR ERROR
        date_str=date_str
    )



@app.route("/milk_sales_entry", methods=["GET", "POST"])
@login_required
def milk_sales_entry():

    if request.method == "POST":

        date = datetime.strptime(request.form["date"], "%Y-%m-%d").date()

        entry_farm_id = current_entry_farm_id()

        def create_session(session_name, prefix):
            return MilkSalesRegistry(
                date=date,
                session=session_name,

                shop1=Decimal(request.form.get(f"{prefix}_shop1", 0) or 0),
                shop2=Decimal(request.form.get(f"{prefix}_shop2", 0) or 0),
                shop3=Decimal(request.form.get(f"{prefix}_shop3", 0) or 0),

                home=Decimal(request.form.get(f"{prefix}_home", 0) or 0),
                calf=Decimal(request.form.get(f"{prefix}_calf", 0) or 0),

                price=Decimal(request.form.get(f"{prefix}_price", 0) or 0),
                farm_id=entry_farm_id,
            )

        sessions = [
            create_session("Morning", "morning"),
            create_session("Noon", "noon"),
            create_session("Evening", "evening")
        ]

        for s in sessions:
            if any([s.shop1, s.shop2, s.shop3, s.home, s.calf]):
                db.session.add(s)

        # =========================
        # SAVE ACTUAL REMAINING
        # =========================
        actual_remaining = Decimal(request.form.get("actual_remaining", 0) or 0)

        existing = MilkDailyRemaining.query.filter_by(date=date).first()

        if existing:
            existing.actual_remaining = actual_remaining
        else:
            db.session.add(MilkDailyRemaining(
                date=date,
                actual_remaining=actual_remaining
            ))

        db.session.commit()

        return redirect(url_for("milk_sales_entry"))

    return render_template("milk_sales_entry.html")


@app.route("/milk_sales_report")
@login_required
def milk_sales_report():

    selected_date = request.args.get("date")

    data = get_milk_sales(selected_date)

    return render_template("milk_sales_report.html", **data)

@app.route("/delete_milk_sale/<int:id>")
@login_required
def delete_milk_sale(id):

    sale = MilkSalesRegistry.query.get_or_404(id)

    selected_date = sale.date

    db.session.delete(sale)
    db.session.commit()

    return redirect(url_for("milk_sales_report", date_str=selected_date))

@app.route("/edit_milk_sale/<int:id>", methods=["GET", "POST"])
@login_required
def edit_milk_sale_record(id):   # 👈 changed function name

    sale = MilkSalesRegistry.query.get_or_404(id)

    if request.method == "POST":

        sale.date_str = datetime.strptime(request.form["date"], "%Y-%m-%d").date()
        sale.session = request.form["session"]
        sale.shop1 = Decimal(request.form.get("shop1", 0) or 0)
        sale.shop2 = Decimal(request.form.get("shop2", 0) or 0)
        sale.shop3 = Decimal(request.form.get("shop3", 0) or 0)
        sale.calf = Decimal(request.form.get("calf", 0) or 0)
        sale.home = Decimal(request.form.get("home", 0) or 0)
        sale.price = Decimal(request.form.get("price", 0) or 0)

        db.session.commit()

        return redirect(url_for("milk_sales_report", date=sale.date))

    return render_template("edit_milk_sale.html", sale=sale)

@app.route('/update_actual_remaining', methods=['POST'])
@login_required
def update_actual_remaining():
    from datetime import datetime

    selected_date = datetime.strptime(
        request.form['date'], "%Y-%m-%d"
    ).date()

    value = float(request.form['actual_remaining'])

    record = MilkDailyRemaining.query.filter_by(date_str=selected_date).first()

    if record:
        record.actual_remaining = value
    else:
        record = MilkDailyRemaining(
            date_str=selected_date,
            actual_remaining=value
        )
        db.session.add(record)

    db.session.commit()

    return redirect(url_for("milk_sales_report", date_str=selected_date))

# =========================
# MILK PRICE ROUTES
# =========================

from datetime import datetime

@app.route("/milk_prices", methods=["GET", "POST"])
@role_required("admin")
def milk_prices():

    farm = Farm.query.filter_by(name="Murang'a").first()

    # ---------------- ADD / UPDATE ----------------
    if request.method == "POST":

        price_id = request.form.get("price_id")

        price = request.form.get("price")
        effective_date_str = request.form.get("effective_date")

        if price and effective_date_str:

            effective_date_str = datetime.strptime(
                effective_date_str,
                "%Y-%m-%d"
            ).date()

            # -------- EDIT --------
            if price_id:

                record = MilkPrice.query.get(price_id)

                if record:
                    record.price = price
                    record.effective_date = effective_date_str

            # -------- ADD --------
            else:

                new_price = MilkPrice(
                    price=price,
                    effective_date=effective_date_str,
                    farm_id=farm.id
                )

                db.session.add(new_price)

            db.session.commit()

            flash("Milk price saved successfully", "success")

        return redirect(url_for("milk_prices"))

    # ---------------- GET ALL ----------------
    prices = MilkPrice.query.filter(
        MilkPrice.farm_id == farm.id
    ).order_by(
        MilkPrice.effective_date.desc()
    ).all()

    return render_template(
        "milk_prices.html",
        prices=prices,
        farm=farm
    )


# =========================
# DELETE
# =========================

@app.route("/delete_milk_price/<int:id>")
@role_required("admin")
def delete_milk_price(id):

    record = MilkPrice.query.get_or_404(id)

    db.session.delete(record)

    db.session.commit()

    flash("Price deleted successfully", "danger")

    return redirect(url_for("milk_prices"))

@app.route("/milk_sales_monthly")
@login_required
def milk_sales_monthly():

    selected_date = request.args.get("date")

    # 🔹 use the reusable data function
    data = get_milk_sales_monthly(selected_date)

    return render_template(
        "milk_sales_monthly.html",
        monthly_data=data["monthly_data"],
        selected_date=data["selected_date"],

        total_shop1=data["total_shop1"],
        total_shop2=data["total_shop2"],
        total_shop3=data["total_shop3"],

        total_calf=data["total_calf"],
        total_home=data["total_home"],

        total_sold=data["total_sold"],
        total_use=data["total_use"]
    )
@app.route("/car_registry", methods=["GET", "POST"])
@role_required("admin")
def car_registry():

    if request.method == "POST":
        plate_number = request.form.get("plate_number")
        model = request.form.get("model")
        driver = request.form.get("driver")

        new_car = CarRegistry(
            plate_number=plate_number,
            model=model,
            driver=driver,
            active=True
        )

        db.session.add(new_car)
        db.session.commit()

        return redirect(url_for("car_registry"))

    active_cars = CarRegistry.query.filter_by(active=True).all()
    inactive_cars = CarRegistry.query.filter_by(active=False).all()

    return render_template(
        "car_registry.html",
        active_cars=active_cars,
        inactive_cars=inactive_cars
    )


@app.route("/cars/edit/<int:id>", methods=["POST"])
@role_required("admin")
def edit_car(id):

    car = CarRegistry.query.get_or_404(id)

    car.plate_number = request.form.get("plate_number") or car.plate_number
    car.model = request.form.get("model") or car.model
    car.driver = request.form.get("driver") or car.driver

    db.session.commit()

    flash("Vehicle updated successfully", "success")

    return redirect(url_for("car_registry"))


@app.route("/cars/deactivate/<int:id>", methods=["POST"])
@role_required("admin")
def deactivate_car(id):

    car = CarRegistry.query.get_or_404(id)

    car.active = False
    db.session.commit()

    flash(f"Vehicle {car.plate_number} deactivated", "success")

    return redirect(url_for("car_registry"))


@app.route("/cars/reactivate/<int:id>", methods=["POST"])
@role_required("admin")
def reactivate_car(id):

    car = CarRegistry.query.get_or_404(id)

    car.active = True
    db.session.commit()

    flash(f"Vehicle {car.plate_number} reactivated", "success")

    return redirect(url_for("car_registry"))

@app.route("/add_car_expense", methods=["GET", "POST"])
@role_required("admin")
def add_car_expense():

    if request.method == "POST":

        car_id = request.form.get("car_id")
        date_str = request.form.get("date")
        expense_type = request.form.get("expense_type")
        description = request.form.get("description")
        amount = float(request.form.get("amount"))

        selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()

        expense = CarExpense(
            car_id=car_id,
            date=selected_date,
            expense_type=expense_type,
            description=description,
            amount=amount
        )

        db.session.add(expense)
        db.session.commit()

        return redirect(url_for("add_car_expense"))

    cars = CarRegistry.query.filter_by(active=True).all()

    return render_template("add_car_expense.html", cars=cars)

@app.route("/car_expense_report")
@role_required("admin")
def car_expense_report():

    selected_date = request.args.get("date")

    data = get_car_expense_report_data(selected_date)

    return render_template("car_expense_report.html", **data)

@app.route("/delete_car_expense/<int:id>")
@role_required("admin")
def delete_car_expense(id):
    expense = CarExpense.query.get_or_404(id)

    db.session.delete(expense)
    db.session.commit()

    return redirect(url_for("car_expense_report"))

@app.route("/edit_car_expense/<int:id>", methods=["GET", "POST"])
@role_required("admin")
def edit_car_expense(id):

    expense = CarExpense.query.get_or_404(id)
    cars = CarRegistry.query.all()

    if request.method == "POST":
        expense.car_id = request.form.get("car_id")
        expense.date = datetime.strptime(request.form.get("date"), "%Y-%m-%d").date()
        expense.expense_type = request.form.get("expense_type")
        expense.description = request.form.get("description")
        expense.amount = float(request.form.get("amount"))

        db.session.commit()
        return redirect(url_for("car_expense_report"))

    return render_template(
        "edit_car_expense.html",
        expense=expense,
        cars=cars
    )

@app.route("/car_sales/add", methods=["GET", "POST"])
@role_required("admin")
def add_car_sale():

    # GET ALL ACTIVE CARS
    cars = CarRegistry.query.filter_by(active=True).all()

    if request.method == "POST":

        try:
            car_id = request.form.get("car_id")
            date_str = request.form.get("date")
            length = request.form.get("day_length")

            # ================= VALIDATION =================
            if not car_id or not date_str or not length:
                flash("Please fill all required fields.", "error")
                return redirect(url_for("add_car_sale"))

            # ================= DATE =================
            sale_date_str = datetime.strptime(date_str, "%Y-%m-%d").date()

            # ================= AUTO AMOUNT =================
            if length == "FULL":
                amount = 10000

            elif length == "HALF":
                amount = 5000

            else:
                flash("Invalid sale length selected.", "error")
                return redirect(url_for("add_car_sale"))

            # ================= SAVE =================
            new_sale = CarSales(
                car_id=int(car_id),
                date=sale_date_str,
                length=length,
                amount=amount
            )

            db.session.add(new_sale)
            db.session.commit()

            flash("Car sale added successfully.", "success")
            return redirect(url_for("add_car_sale"))

        except Exception as e:
            db.session.rollback()
            flash(f"Error saving sale: {str(e)}", "error")
            return redirect(url_for("add_car_sale"))

    return render_template(
        "add_car_sale.html",
        cars=cars
    )
@app.route("/car_sales_report")
@role_required("admin")
def car_sales_report():

    selected_date = request.args.get("date")

    data = get_sales_report_data(selected_date)

    return render_template("car_sales_report.html", **data)


@app.route("/delete_car_sale/<int:id>")
@role_required("admin")
def delete_car_sale(id):
    sale = CarSales.query.get_or_404(id)
    db.session.delete(sale)
    db.session.commit()
    return redirect(url_for("car_sales_report"))

@app.route("/edit_car_sale/<int:id>", methods=["GET", "POST"])
@role_required("admin")
def edit_car_sale(id):

    sale = CarSales.query.get_or_404(id)
    cars = CarRegistry.query.all()

    if request.method == "POST":
        sale.car_id = request.form.get("car_id")
        sale.date_str = datetime.strptime(request.form.get("date"), "%Y-%m-%d").date()
        sale.length = request.form.get("day_length")

        if sale.length == "HALF":
            sale.amount = 5000
        else:
            sale.amount = 10000

        db.session.commit()
        return redirect(url_for("car_sales_report"))

    return render_template("edit_car_sale.html", sale=sale, cars=cars)


# =========================================================
# VEHICLE ANALYTICS
# =========================================================

@app.route("/vehicle_analytics")
@role_required("admin")
def vehicle_analytics():

    # Month filter: default = current month
    month_str = request.args.get("month")

    if month_str and month_str.strip():
        try:
            year, month = [int(x) for x in month_str.split("-")]
        except Exception:
            month, year = date.today().month, date.today().year
    else:
        month, year = date.today().month, date.today().year

    # Car filter: default = first active car (or all)
    car_filter = request.args.get("car_id")
    selected_car = None
    cars = CarRegistry.query.all()

    if car_filter and str(car_filter).strip():
        selected_car = CarRegistry.query.get(int(car_filter))

    # -------- FILTERS --------
    start_date = datetime(year, month, 1).date()

    if month == 12:
        end_date = datetime(year + 1, 1, 1).date()
    else:
        end_date = datetime(year, month + 1, 1).date()

    def in_month(q, column):
        return q.filter(
            column >= start_date,
            column < end_date
        )

    # -------- PER-CAR ANALYTICS --------
    car_rows = []

    for car in cars:

        sales_q = in_month(CarSales.query.filter_by(car_id=car.id), CarSales.date)
        exp_q = in_month(CarExpense.query.filter_by(car_id=car.id), CarExpense.date)

        month_sales = sum(s.amount or 0 for s in sales_q.all())
        month_expenses = sum(e.amount or 0 for e in exp_q.all())

        month_sales_count = sales_q.count()
        month_expenses_count = exp_q.count()

        car_rows.append({
            "car": car,
            "sales": month_sales,
            "expenses": month_expenses,
            "profit": round(month_sales - month_expenses, 2),
            "sales_count": month_sales_count,
            "expenses_count": month_expenses_count
        })

    # -------- SELECTED CAR BREAKDOWN --------
    breakdown_sales = []
    breakdown_expenses = []
    totals = {
        "sales": 0,
        "expenses": 0,
        "profit": 0,
        "full_days": 0,
        "half_days": 0
    }

    if selected_car:

        breakdown_sales = (
            in_month(
                CarSales.query.filter_by(car_id=selected_car.id),
                CarSales.date
            )
            .order_by(CarSales.date.desc())
            .all()
        )

        breakdown_expenses = (
            in_month(
                CarExpense.query.filter_by(car_id=selected_car.id),
                CarExpense.date
            )
            .order_by(CarExpense.date.desc())
            .all()
        )

        totals["sales"] = round(sum(s.amount or 0 for s in breakdown_sales), 2)
        totals["expenses"] = round(sum(e.amount or 0 for e in breakdown_expenses), 2)
        totals["profit"] = round(totals["sales"] - totals["expenses"], 2)
        totals["full_days"] = sum(1 for s in breakdown_sales if (s.length or "").upper() == "FULL")
        totals["half_days"] = sum(1 for s in breakdown_sales if (s.length or "").upper() == "HALF")

    # Overall totals across all cars for the month
    overall = {
        "sales": round(sum(r["sales"] for r in car_rows), 2),
        "expenses": round(sum(r["expenses"] for r in car_rows), 2),
        "profit": round(sum(r["profit"] for r in car_rows), 2)
    }

    return render_template(
        "vehicle_analytics.html",
        cars=cars,
        selected_car=selected_car,
        car_rows=car_rows,
        breakdown_sales=breakdown_sales,
        breakdown_expenses=breakdown_expenses,
        totals=totals,
        overall=overall,
        month_str=f"{year:04d}-{month:02d}",
        month_name=datetime(year, month, 1).strftime("%B %Y")
    )




@app.route("/payments", methods=["GET", "POST"])
@login_required
def payments():
    message = None
    farms = Farm.query.all()

    is_admin = session.get("role") == "admin"

    # Non-admin users locked to their farm
    user_farm_id = session.get("farm_id") if not is_admin else None

    if request.method == "POST":
        date_str = request.form.get("date_paid")
        amount = request.form.get("amount")
        account = request.form.get("account")
        purpose = request.form.get("purpose")
        purpose_type = request.form.get("purpose_type")
        farm_id = request.form.get("farm_id") or current_entry_farm_id()

        if not date_str or not amount or not account or not purpose or not purpose_type:
            message = "All fields required"
        else:
            payment = Payment(
                date_paid=datetime.strptime(date_str, "%Y-%m-%d").date(),
                amount=float(amount),
                account=account,
                purpose=purpose,
                purpose_type=purpose_type,
                farm_id=int(farm_id) if farm_id else None
            )

            db.session.add(payment)
            db.session.commit()
            message = "Payment added successfully"

    # History is ADMIN ONLY - farm users may only ADD transactions
    if is_admin:
        payments_query = Payment.query

        if user_farm_id:
            payments_query = payments_query.filter_by(farm_id=user_farm_id)

        payments = payments_query.order_by(Payment.date_paid.desc()).all()
    else:
        payments = []

    return render_template(
        "payments.html",
        payments=payments,
        farms=farms,
        message=message,
        show_history=is_admin
    )

@app.route("/transactions")
@role_required("admin")
def transactions():

    filter_date_str = request.args.get("filter_date")
    month = request.args.get("month")
    purpose = request.args.get("purpose")
    farm_id = request.args.get("farm_id")
    order_id = request.args.get("order_id")   # Created admin ADD THIS

    data = get_transactions_data(filter_date_str, month, purpose, farm_id, order_id)

    farms = Farm.query.all()

    return render_template(
        "transactions.html",
        farms=farms,
        order_id=order_id,   # optional
        **data
    )
@app.route("/edit_transaction/<int:id>", methods=["GET", "POST"])
@role_required("admin")
def edit_transaction(id):

    transaction = Payment.query.get_or_404(id)

    if request.method == "POST":

        # 🔹 PRESERVE FILTERS
        selected_date = request.form.get("filter_date")
        selected_month = request.form.get("selected_month")
        purpose = request.form.get("purpose")
        farm_filter = request.form.get("farm_filter")

        # 🔹 UPDATE DATE
        try:
            transaction.date_paid = datetime.strptime(
                request.form.get("date_paid"),
                "%Y-%m-%d"
            ).date()
        except:
            pass

        # 🔹 UPDATE AMOUNT
        try:
            transaction.amount = float(
                request.form.get("amount") or 0
            )
        except:
            transaction.amount = 0

        # 🔹 UPDATE ACCOUNT
        transaction.account = request.form.get("account")

        # 🔹 UPDATE PURPOSE TYPE
        transaction.purpose_type = request.form.get("purpose_type")

        # 🔹 UPDATE PURPOSE
        transaction.purpose = request.form.get("purpose_text")

        # 🔹 UPDATE FARM
        farm_id = request.form.get("farm_id")

        if farm_id and str(farm_id).strip() != "":
            try:
                transaction.farm_id = int(farm_id)
            except:
                transaction.farm_id = None
        else:
            transaction.farm_id = None

        db.session.commit()

        flash("Created admin Transaction updated successfully", "success")

        # 🔥 RETURN TO SAME PAGE WITH FILTERS
        return redirect(url_for(
            "transactions",
            filter_date_str=selected_date,
            month=selected_month,
            purpose=purpose,
            farm_id=farm_filter
        ))

    # 🔹 GET FILTERS
    selected_date = request.args.get("filter_date")
    selected_month = request.args.get("month")
    purpose = request.args.get("purpose")
    farm_filter = request.args.get("farm_id")

    farms = Farm.query.all()

    return render_template(
        "edit_transaction.html",
        transaction=transaction,
        farms=farms,
        selected_date=selected_date,
        selected_month=selected_month,
        purpose=purpose,
        farm_filter=farm_filter
    )

@app.route("/delete_transaction/<int:id>")
@role_required("admin")
def delete_transaction(id):

    transaction = Payment.query.get_or_404(id)

    selected_date = request.args.get("filter_date")
    purpose = request.args.get("purpose")
    farm_id = request.args.get("farm_id")

    db.session.delete(transaction)
    db.session.commit()

    return redirect(url_for(
        "transactions",
        filter_date_str=selected_date,
        purpose=purpose,
        farm_id=farm_id
    ))


# @app.route("/routes")
# def list_routes():
#     return "<br>".join([str(r) for r in app.url_map.iter_rules()])
@app.route("/milk_dashboard")
@login_required
def milk_dashboard():

    date_str = request.args.get("filter_date")

    # Farm context: non-admin locked to own farm, admin follows switcher
    farm_id = session.get("farm_id")

    milk_data = get_milk_report_data(date_str, farm_id)

    sales_data = get_milk_sales(date_str, farm_id)

    combined_data = {
        **milk_data,
        **sales_data
    }

    return render_template(
        "milk_dashboard.html",
        **combined_data
    )

@app.route("/cow_dashboard")
@login_required
def cow_dashboard():

    data = get_animals_data(farm_id=session.get("farm_id"))

    return render_template(
        "cow_dashboard.html",
        **data
    )


@app.route("/financial_dashboard")
@role_required("admin")
def financial_dashboard():

    # =========================================
    # TODAY
    # =========================================

    today_str = date.today().strftime("%Y-%m-%d")

    # =========================================
    # INDEPENDENT FILTERS
    # =========================================

    # MILK FILTER
    milk_date_str = request.args.get(
        "milk_date",
        today_str
    )

    # VEHICLE SALES FILTER
    # OPTIONAL -> SHOW ALL IF EMPTY
    vehicle_date_str = request.args.get(
        "vehicle_date"
    )

    # GENERAL EXPENSE FILTER
    expense_date_str = request.args.get(
        "expense_date",
        today_str
    )

    # =========================================
    # MILK SALES
    # =========================================

    farm_id = session.get("farm_id")

    milk_sales_data = get_milk_sales(
        milk_date_str,
        farm_id
    )

    # =========================================
    # VEHICLE SALES ANALYTICS
    # COMPLETELY INDEPENDENT
    # =========================================

    if vehicle_date_str and vehicle_date_str.strip():

        # FILTER VEHICLE SALES ONLY
        car_sales_data = get_sales_report_data(
            vehicle_date_str
        )

    else:

        # NO FILTER -> SHOW ALL VEHICLE SALES
        car_sales_data = get_sales_report_data()

    # =========================================
    # CAR EXPENSES
    # COMPLETELY INDEPENDENT
    # NOT AFFECTED BY expense_date
    # =========================================

    if vehicle_date_str and vehicle_date_str.strip():

        # FILTER CAR EXPENSES ONLY
        car_expense_data = get_car_expense_report_data(
            vehicle_date_str
        )

    else:

        # SHOW ALL CAR EXPENSES
        car_expense_data = get_car_expense_report_data()

    # =========================================
    # GENERAL FARM / BUSINESS EXPENSES
    # INDEPENDENT FROM VEHICLE ANALYTICS
    # =========================================

    transaction_data = get_transactions_data(
        expense_date_str
    )

    # =========================================
    # EMPLOYEE DATA
    # =========================================

    salary_data = get_employees_data()

    # =========================================
    # COMBINE DATA
    # =========================================

    combined_data = {

        # MILK
        **milk_sales_data,

        # VEHICLE SALES
        **car_sales_data,

        # VEHICLE EXPENSES
        **car_expense_data,

        # GENERAL EXPENSES
        **transaction_data,

        # EMPLOYEES
        **salary_data,

        # FILTER VALUES
        "milk_date": milk_date_str,

        "vehicle_date": vehicle_date_str,

        "expense_date": expense_date_str

    }

    # =========================================
    # RENDER
    # =========================================

    return render_template(
        "financial_dashboard.html",
        **combined_data
    )
    
@login_required
def main_dashboard():

    date_str = request.args.get("filter_date")

    # ===============================
    # GET DATA FROM FUNCTIONS
    # ===============================

    milk_report_data = get_milk_report_data(date_str)

    milk_sales_data = get_milk_sales(date_str)

    # ===============================
    # COMBINE DATA
    # ===============================

    combined_data = {
        **milk_report_data,
        **milk_sales_data
    }

    # ===============================
    # RENDER TEMPLATE
    # ===============================

    return render_template(
        "main_dashboard.html",
        **combined_data
    )

@app.route("/health")
def health():
    return "OK", 200



if __name__ == "__main__":
    app.run(debug=True)
