from datetime import date, datetime

from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from models import db, CalfRegistry, Insemination, AssetsRegistry, ExpensesRegistry, EmployeesRegistry, ShopRegistry, UserRegistry, FeedsRegistry, MilkRegistry, MilkSalesRegistry, CarRegistry, CarExpense, AnimalRegistry, MilkingHerd, CarSales, Treatment,Farm,Payment, MilkDailyRemaining, Admin, FeedsOrderV2, FeedsDeliveryV2, FeedsOrderItemV2, MilkPrice,CowShed,AnimalMovement
from sqlalchemy.exc import IntegrityError
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy import extract, func
import pdfkit
import os
from flask_mail import Mail, Message
import pandas as pd
import os
import random

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///database.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'supersecretkey123'

db.init_app(app)

# =========================================================
# CREATE TABLES + DEFAULT ADMIN
# =========================================================

with app.app_context():

    # Create tables
    db.create_all()

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

        print("✅ Default admin created")

    else:

        print("✅ Admin already exists")

@app.before_request
def require_login():

    if request.endpoint is None:
        return

    allowed = [
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

            print("LOGIN SUCCESS")

            return redirect(url_for("main_dashboard"))

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
            role=role
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

    return render_template(
        "users.html",
        users=users
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
def get_treatment_data(date_str=None, status=None):

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
    # STATUS FILTER
    # -------------------------
    if status:
        query = query.filter(db.func.lower(Treatment.status) == status.lower())

    records = query.order_by(AnimalRegistry.name.asc()).all()

    # STATUS COUNTS
    healed_count = Treatment.query.filter(
        Treatment.status == "healed"
    ).count()

    recovering_count = Treatment.query.filter(
        Treatment.status == "recovering"
    ).count()

    # -------------------------
    # COST CALCULATIONS
    # -------------------------

    if selected_date:
        base_query = Treatment.query.filter(
            Treatment.date_treated == selected_date
        )
    else:
        base_query = Treatment.query  # 👈 ALL DATA

    daily_total = sum(r.cost for r in base_query.all())

    # MONTH
    if selected_date:
        month_total = sum(
            r.cost for r in Treatment.query.filter(
                extract('month', Treatment.date_treated) == selected_date.month,
                extract('year', Treatment.date_treated) == selected_date.year
            ).all()
        )
    else:
        month_total = daily_total

    # QUARTER
    if selected_date:
        quarter = (selected_date.month - 1)//3 + 1

        quarter_total = sum(
            r.cost for r in Treatment.query.filter(
                extract('year', Treatment.date_treated) == selected_date.year
            ).all()
            if ((r.date_treated.month-1)//3+1) == quarter
        )
    else:
        quarter_total = daily_total

    # YEAR
    if selected_date:
        year_total = sum(
            r.cost for r in Treatment.query.filter(
                extract('year', Treatment.date_treated) == selected_date.year
            ).all()
        )
    else:
        year_total = daily_total

        # -------------------------
# STATUS COUNTS (SAFE FIX)
# -------------------------

    filtered = records   # ✅ ALWAYS use already filtered records

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


def get_milk_report_data(date_str=None):

    if date_str:
        selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    else:
        selected_date = date.today()

    # ---- DAILY RECORDS ----
    records = MilkRegistry.query.filter_by(date=selected_date).all()
 
    total_morning = sum(r.morning for r in records)
    total_noon = sum(r.noon for r in records)
    total_evening = sum(r.evening for r in records)
    grand_total = sum(r.total for r in records)
    above_10_litres_total = sum(r.total for r in records if r.total > 10)
    cow_count = len(records)
    above_10_litres = sum(1 for r in records if r.total > 10)
    average_production = above_10_litres_total / above_10_litres if cow_count > 0 else 0

    # ---- MONTHLY TOTAL ----
    monthly_records = MilkRegistry.query.filter(
        extract('month', MilkRegistry.date) == selected_date.month,
        extract('year', MilkRegistry.date) == selected_date.year
    ).all()

    monthly_total = sum(r.total for r in monthly_records)

    # ---- QUARTERLY TOTAL ----
    quarter = (selected_date.month - 1) // 3 + 1

    quarterly_records = MilkRegistry.query.filter(
        extract('year', MilkRegistry.date) == selected_date.year
    ).all()

    quarterly_total = sum(
        r.total for r in quarterly_records
        if ((r.date.month - 1) // 3 + 1) == quarter
    )

    # ---- YEARLY TOTAL ----
    yearly_records = MilkRegistry.query.filter(
        extract('year', MilkRegistry.date) == selected_date.year
    ).all()

    yearly_total = sum(r.total for r in yearly_records)

    return {
        "records": records,
        "selected_date": selected_date,
        "total_morning": total_morning,
        "total_noon": total_noon,
        "total_evening": total_evening,
        "grand_total": grand_total,
        "average_production": round(average_production, 2),
        "monthly_total": monthly_total,
        "quarterly_total": quarterly_total,
        "yearly_total": yearly_total,
        "cow_count": cow_count
    }



def get_monthly_cow_analysis(date_str=None):

    if date_str:
        selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    else:
        selected_date = date.today()

    # ✅ FIXED: use cow_id + direct relationship
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


def get_animals_data(category=None):
    base_query = AnimalRegistry.query.filter(
        AnimalRegistry.category.ilike("nolonger_exist") == False
    )
    query = AnimalRegistry.query

    # HANDLE EMPTY / NONE / ALL
    if (
        category
        and str(category).strip().lower() not in ["all", "none", ""]
    ):
        query = query.filter(
            AnimalRegistry.category.ilike(category)
        )

    animals = query.all()
    return {
        "animals": animals,
        "existing": base_query,
        "total_animals": AnimalRegistry.query.count(),
        "existing_animals": base_query.count(),
        "milkers": AnimalRegistry.query.filter(
            AnimalRegistry.category.ilike("milker")
        ).count(),

        "dry_cows": AnimalRegistry.query.filter(
            AnimalRegistry.category.ilike("dry")
        ).count(),

        "calves": AnimalRegistry.query.filter(
            AnimalRegistry.category.ilike("calf")
        ).count(),

        "bulls": AnimalRegistry.query.filter(
            AnimalRegistry.category.ilike("bull")
        ).count(),

        "incalf_heifers": AnimalRegistry.query.filter(
            AnimalRegistry.category.ilike("incalf-heifer")
        ).count(),

        "yearlings": AnimalRegistry.query.filter(
            AnimalRegistry.category.ilike("yearing")
        ).count(),

        "weaners": AnimalRegistry.query.filter(
            AnimalRegistry.category.ilike("weaner")
        ).count(),

        "Bullying_heifer": AnimalRegistry.query.filter(
            AnimalRegistry.category.ilike("Bullying-Heifer")
        ).count(),

        "steamers": AnimalRegistry.query.filter(
            AnimalRegistry.category.ilike("steamer")
        ).count(),

        "nolonger_exist": AnimalRegistry.query.filter(
            AnimalRegistry.category.ilike("nolonger_exist")
        ).count(),

    }


def get_insemination_data(status=None, month=None, year=None):

    from datetime import datetime

    query = db.session.query(Insemination).join(AnimalRegistry)

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

from datetime import datetime, date, timedelta
from sqlalchemy import func

def to_float(val):
    return float(val or 0)

def get_milk_sales(selected_date=None):

    from datetime import datetime, date
    from sqlalchemy import extract

    def to_float(val):
        return float(val or 0)


    def get_effective_milk_price(target_date):

        price_record = MilkPrice.query.filter(
            MilkPrice.effective_date <= target_date
        ).order_by(
            MilkPrice.effective_date.desc(),
            MilkPrice.id.desc()
        ).first()

        if price_record:
            return to_float(price_record.price)

        return 0

    # =========================================================
    # DATE
    # =========================================================

    if selected_date:

        selected_date = datetime.strptime(
            selected_date,
            "%Y-%m-%d"
        ).date()

    else:

        selected_date = date.today()

    # =========================================================
    # DATE DETAILS
    # =========================================================

    month = selected_date.month
    year = selected_date.year

    quarter = ((month - 1) // 3) + 1

    # =========================================================
    # PREVIOUS DATES
    # =========================================================

    previous_dates = db.session.query(
        MilkRegistry.date
    ).filter(
        MilkRegistry.date < selected_date
    ).distinct().order_by(
        MilkRegistry.date
    ).all()

    system_running = 0
    actual_running = 0

    # =========================================================
    # LOOP THROUGH HISTORY
    # =========================================================

    for d in previous_dates:

        current_day = d[0]

        production = sum(
            to_float(r.total)
            for r in MilkRegistry.query.filter_by(
                date=current_day
            ).all()
        )

        sales = MilkSalesRegistry.query.filter_by(
            date=current_day
        ).all()

        used = sum(
            to_float(r.shop1) +
            to_float(r.shop2) +
            to_float(r.shop3) +
            to_float(r.calf) +
            to_float(r.home)
            for r in sales
        )

        # SYSTEM FLOW

        system_available = (
            system_running + production
        )

        system_running = max(
            system_available - used,
            0
        )

        # ACTUAL FLOW

        actual_record = MilkDailyRemaining.query.filter_by(
            date=current_day
        ).first()

        if actual_record:

            actual_running = to_float(
                actual_record.actual_remaining
            )

        else:

            actual_available = (
                actual_running + production
            )

            actual_running = max(
                actual_available - used,
                0
            )

    previous_system_remaining = system_running
    previous_actual_remaining = actual_running

    # =========================================================
    # TODAY SALES
    # =========================================================

    today_sales = MilkSalesRegistry.query.filter_by(
        date=selected_date
    ).all()

    today_production = sum(
        to_float(r.total)
        for r in MilkRegistry.query.filter_by(
            date=selected_date
        ).all()
    )

    # =========================================================
    # TOTALS
    # =========================================================

    total_shop1 = sum(
        to_float(r.shop1)
        for r in today_sales
    )

    total_shop2 = sum(
        to_float(r.shop2)
        for r in today_sales
    )

    total_shop3 = sum(
        to_float(r.shop3)
        for r in today_sales
    )

    total_calf = sum(
        to_float(r.calf)
        for r in today_sales
    )

    total_home = sum(
        to_float(r.home)
        for r in today_sales
    )

    total_sold_shops = (
        total_shop1 +
        total_shop2 +
        total_shop3
    )

    total_used = (
        total_sold_shops +
        total_calf +
        total_home
    )

    other_uses = (
        total_used -
        total_sold_shops
    )

    percentage_conversion = (
        (total_sold_shops / total_used) * 100
        if total_used else 0
    )

    # =========================================================
    # TODAY EFFECTIVE PRICE
    # =========================================================

    active_price = get_effective_milk_price(
        selected_date
    )

    total_cash = (
        total_sold_shops *
        active_price
    )

    avg_price = active_price

    # =========================================================
    # MONTHLY SALES
    # =========================================================
    # CRITICAL:
    # Every record uses ITS OWN historical price.
    # =========================================================

    monthly_sales_records = MilkSalesRegistry.query.filter(
        extract(
            'month',
            MilkSalesRegistry.date
        ) == month,

        extract(
            'year',
            MilkSalesRegistry.date
        ) == year

    ).all()

    monthly_total_sales = 0
    monthly_total_litres = 0

    for r in monthly_sales_records:

        litres = (
            to_float(r.shop1) +
            to_float(r.shop2) +
            to_float(r.shop3)
        )

        # IMPORTANT:
        # Get price for THAT EXACT DATE
        historical_price = get_effective_milk_price(
            r.date
        )

        sale_amount = (
            litres * historical_price
        )

        monthly_total_sales += sale_amount
        monthly_total_litres += litres

    # =========================================================
    # QUARTERLY SALES
    # =========================================================

    yearly_sales_records = MilkSalesRegistry.query.filter(
        extract(
            'year',
            MilkSalesRegistry.date
        ) == year
    ).all()

    quarterly_total_sales = 0
    quarterly_total_litres = 0

    for r in yearly_sales_records:

        record_quarter = (
            (r.date.month - 1) // 3
        ) + 1

        if record_quarter == quarter:

            litres = (
                to_float(r.shop1) +
                to_float(r.shop2) +
                to_float(r.shop3)
            )

            # Historical price for THAT DATE
            historical_price = get_effective_milk_price(
                r.date
            )

            sale_amount = (
                litres * historical_price
            )

            quarterly_total_sales += sale_amount
            quarterly_total_litres += litres

    # =========================================================
    # YEARLY SALES
    # =========================================================

    yearly_total_sales = 0
    yearly_total_litres = 0

    for r in yearly_sales_records:

        litres = (
            to_float(r.shop1) +
            to_float(r.shop2) +
            to_float(r.shop3)
        )

        # Historical price for THAT DATE
        historical_price = get_effective_milk_price(
            r.date
        )

        sale_amount = (
            litres * historical_price
        )

        yearly_total_sales += sale_amount
        yearly_total_litres += litres

    # =========================================================
    # SESSION BREAKDOWN
    # =========================================================

    def session_sum(session, field):

        return sum(
            to_float(getattr(r, field))
            for r in today_sales
            if r.session == session
        )

    morning_shop = (
        session_sum("Morning", "shop1") +
        session_sum("Morning", "shop2") +
        session_sum("Morning", "shop3")
    )

    noon_shop = (
        session_sum("Noon", "shop1") +
        session_sum("Noon", "shop2") +
        session_sum("Noon", "shop3")
    )

    evening_shop = (
        session_sum("Evening", "shop1") +
        session_sum("Evening", "shop2") +
        session_sum("Evening", "shop3")
    )

    morning_calf = session_sum(
        "Morning",
        "calf"
    )

    noon_calf = session_sum(
        "Noon",
        "calf"
    )

    evening_calf = session_sum(
        "Evening",
        "calf"
    )

    morning_home = session_sum(
        "Morning",
        "home"
    )

    noon_home = session_sum(
        "Noon",
        "home"
    )

    evening_home = session_sum(
        "Evening",
        "home"
    )

    # =========================================================
    # SYSTEM FLOW TODAY
    # =========================================================

    system_available_today = (
        previous_system_remaining +
        today_production
    )

    system_remaining = max(
        system_available_today -
        total_used,
        0
    )

    # =========================================================
    # ACTUAL FLOW TODAY
    # =========================================================

    actual_available_today = (
        previous_actual_remaining +
        today_production
    )

    actual_record_today = MilkDailyRemaining.query.filter_by(
        date=selected_date
    ).first()

    actual_remaining = (
        to_float(
            actual_record_today.actual_remaining
        )
        if actual_record_today else 0
    )

    # =========================================================
    # VARIANCES
    # =========================================================

    variance = (
        actual_remaining -
        system_remaining
    )

    prev_variance = (
        previous_actual_remaining -
        previous_system_remaining
    )

    avail_variance = (
        actual_available_today -
        system_available_today
    )

    pavail_variance = (
        system_available_today -
        actual_available_today
    )

    percentage_error = (
        (pavail_variance / system_available_today) * 100
        if system_available_today > 0 else 0
    )

    # =========================================================
    # RETURN
    # =========================================================

    return {

        "selected_date": selected_date,

        "sales_records": today_sales,

        # STOCK FLOW

        "previous_system_remaining": round(
            previous_system_remaining, 2
        ),

        "previous_actual_remaining": round(
            previous_actual_remaining, 2
        ),

        "system_available_today": round(
            system_available_today, 2
        ),

        "actual_available_today": round(
            actual_available_today, 2
        ),

        "system_remaining": round(
            system_remaining, 2
        ),

        "actual_remaining": round(
            actual_remaining, 2
        ),

        # PRODUCTION

        "total_production": round(
            today_production, 2
        ),

        # USAGE

        "total_used": round(
            total_used, 2
        ),

        "total_sold_shops": round(
            total_sold_shops, 2
        ),

        "total_calf_used": round(
            total_calf, 2
        ),

        "total_home_used": round(
            total_home, 2
        ),

        "other_uses": round(
            other_uses, 2
        ),

        # SALES

        "total_cash": round(
            total_cash, 2
        ),

        "monthly_total_sales": round(
            monthly_total_sales, 2
        ),

        "quarterly_total_sales": round(
            quarterly_total_sales, 2
        ),

        "yearly_total_sales": round(
            yearly_total_sales, 2
        ),

        # LITRES SUMMARY

        "monthly_total_litres": round(
            monthly_total_litres, 2
        ),

        "quarterly_total_litres": round(
            quarterly_total_litres, 2
        ),

        "yearly_total_litres": round(
            yearly_total_litres, 2
        ),

        # PRICE

        "average_price": round(
            avg_price, 2
        ),

        "active_price": round(
            active_price, 2
        ),

        # VARIANCES

        "variance": round(
            variance, 2
        ),

        "prev_variance": round(
            prev_variance, 2
        ),

        "avail_variance": round(
            avail_variance, 2
        ),

        "pavail_variance": round(
            pavail_variance, 2
        ),

        "percentage_error": round(
            percentage_error, 2
        ),

        # CONVERSION

        "percentage_conversion": round(
            percentage_conversion, 2
        ),

        # SESSION SALES

        "morning_shop_total": round(
            morning_shop, 2
        ),

        "noon_shop_total": round(
            noon_shop, 2
        ),

        "evening_shop_total": round(
            evening_shop, 2
        ),

        # SESSION CALF

        "morning_calf": round(
            morning_calf, 2
        ),

        "noon_calf": round(
            noon_calf, 2
        ),

        "evening_calf": round(
            evening_calf, 2
        ),

        # SESSION HOME

        "morning_home": round(
            morning_home, 2
        ),

        "noon_home": round(
            noon_home, 2
        ),

        "evening_home": round(
            evening_home, 2
        )

    }

from datetime import datetime


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

    base_date = None

    if selected_date:

        base_date = selected_date

    elif selected_month:

        base_date = selected_month

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

    if base_date:

        quarter = (
            (base_date.month - 1) // 3
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
            ) == base_date.month,

            extract(
                'year',
                Payment.date_paid
            ) == base_date.year

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
            ) == base_date.year

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

            Payment.date_paid == base_date,

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
            ) == base_date.month,

            extract(
                'year',
                Payment.date_paid
            ) == base_date.year,

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
            ) == base_date.year,

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

            Payment.date_paid == base_date,

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
            ) == base_date.month,

            extract(
                'year',
                Payment.date_paid
            ) == base_date.year,

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
            ) == base_date.year,

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

def get_milk_sales_monthly(selected_date_str=None):

    from datetime import datetime, date
    from sqlalchemy import extract, func

    if selected_date_str:
        selected_date = datetime.strptime(selected_date_str, "%Y-%m-%d").date()
    else:
        selected_date = date.today()

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
app.config['MAIL_PASSWORD'] = 'rjgp cifh gqim wkln'
app.config['MAIL_DEFAULT_SENDER'] = 'MY FARM <magicdevelopers9@gmail.com>'

mail = Mail(app)

# PDFKit configuration
# config = pdfkit.configuration(
#     wkhtmltopdf=r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
# )

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

# def generate_pdf(template_name, context, filename):
#     """Generate PDF from HTML template"""
#     rendered_html = render_template(template_name, **context)

#     folder = os.path.join("static", "reports")
#     os.makedirs(folder, exist_ok=True)

#     file_path = os.path.join(folder, filename)

#     pdfkit.from_string(
#         rendered_html,
#         file_path,
#         configuration=config
#     )
    
#     return file_path

from weasyprint import HTML
from flask import render_template, current_app
import os


def generate_pdf(template_name, context, filename):
    """Generate PDF from HTML template using WeasyPrint"""

    rendered_html = render_template(
        template_name,
        **context
    )

    reports_dir = os.path.join(
        current_app.root_path,
        "static",
        "reports"
    )

    os.makedirs(reports_dir, exist_ok=True)

    file_path = os.path.join(
        reports_dir,
        filename
    )

    HTML(
        string=rendered_html,
        base_url=current_app.root_path
    ).write_pdf(
        target=file_path
    )

    return file_path

def send_email_with_pdf(subject, recipients, body, pdf_path):

    msg = Message(subject=subject, recipients=recipients)
    msg.body = body

    with open(pdf_path, "rb") as f:
        msg.attach(
            filename=os.path.basename(pdf_path),
            content_type="application/pdf",
            data=f.read()
        )

    mail.send(msg)



@app.route('/send_report/<report_type>', methods=['GET', 'POST'])
@login_required
def send_report(report_type):

    selected_date = request.args.get("date")
    import re

    def is_valid_email(email):
        pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        return re.match(pattern, email)

    # 🔥 Get emails from UI
    emails = request.args.getlist("emails")

    if not emails:
        return """
        <script>
            alert("❌ Please enter at least one email");
            window.history.back();
        </script>
        """

    valid_emails = []
    invalid_emails = []

    for email in emails:
        email = email.strip()

        if email:
            if is_valid_email(email):
                valid_emails.append(email)
            else:
                invalid_emails.append(email)

    if not valid_emails:
        return f"""
        <script>
            alert("❌ No valid emails provided. Invalid: {', '.join(invalid_emails)}");
            window.history.back();
        </script>
        """

    recipients = valid_emails

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
        date = request.args.get("date")
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

        filter_date = request.args.get("filter_date")
        month = request.args.get("month")
        purpose = request.args.get("purpose")
        farm_id = request.args.get("farm_id")

        data = get_transactions_data(filter_date, month, purpose, farm_id)

        template = "transactions_pdf.html"
        filename = f"transactions_{month or filter_date or 'all'}.pdf"

    elif report_type == "cow_analysis":
        from datetime import datetime

        date_str = request.args.get("date")
        data = get_monthly_cow_analysis(date_str)

        cow_report = []
        for i, cow in enumerate(data["monthly_cows"], start=1):
            avg = cow.total_milk / cow.days_recorded if cow.days_recorded > 0 else 0

            cow_report.append({
                "no": i,
                "name": cow.cow_name,
                "total": float(cow.total_milk),
                "average": round(avg, 2)
            })

        month_name = "All Records"
        if date_str:
            try:
                month_name = datetime.strptime(date_str, "%Y-%m-%d").strftime("%B %Y")
            except:
                month_name = date_str

        data["cow_report"] = cow_report
        data["month_name"] = month_name

        template = "cow_analysis_pdf.html"
        filename = f"cow_analysis_{date_str or 'all'}.pdf"

    elif report_type == "milk_sales_monthly":
        selected_date = request.args.get("date")
        data = get_milk_sales_monthly(selected_date)

        from datetime import datetime

        month_name = "All Records"
        if selected_date:
            try:
                month_name = datetime.strptime(selected_date, "%Y-%m-%d").strftime("%B %Y")
            except:
                month_name = selected_date

        data["month_name"] = month_name

        template = "milk_sales_monthly_pdf.html"
        filename = f"milk_sales_monthly_{selected_date or 'all'}.pdf"

    # ===============================
    # FEEDS ORDERS PDF
    # ===============================
    elif report_type == "feeds_orders":

        month = request.args.get("month")
        farm_id = request.args.get("farm_id")

        orders = get_orders(month, farm_id)

        total_all = sum(o["total"] for o in orders)
        total_paid = sum(o["paid"] for o in orders)
        total_debt = total_all - total_paid

        data = {
            "orders": orders,
            "selected_month": month,
            "total_all": total_all,
            "total_paid": total_paid,
            "total_debt": total_debt
        }

        template = "pdf/feeds_orders.html"
        filename = f"feeds_orders_{month or 'all'}.pdf"


    # ===============================
    # ORDER DETAIL PDF
    # ===============================
    elif report_type == "feeds_order_detail":

        order_id = request.args.get("order_id")
        order = FeedsOrderV2.query.get_or_404(order_id)

        summary = build_order_summary(order)

        items = []
        for item in order.items:
            delivered, remaining, status, color = calc_item_delivery(item)

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


    # ===============================
    # DELIVERY PDF
    # ===============================
    elif report_type == "feeds_delivery":

        order_id = request.args.get("order_id")

        deliveries = FeedsDeliveryV2.query.filter_by(order_id=order_id).all()

        data = {
            "deliveries": deliveries
        }

        template = "pdf/delivery.html"
        filename = f"delivery_{order_id or 'all'}.pdf"


    # ===============================
    # PAYMENTS PDF
    # ===============================
    elif report_type == "feeds_payments":

        order_id = request.args.get("order_id")

        payments = payments.query.filter_by(order_id=order_id).all()

        total_paid = sum(p.amount for p in payments)

        data = {
            "payments": payments,
            "total_paid": total_paid
        }

        template = "pdf/payments.html"
        filename = f"payments_{order_id or 'all'}.pdf"

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

    # Generate + send
    pdf_path = generate_pdf(template, data, filename)

    send_email_with_pdf(
        subject=f"{report_type.capitalize()} Report",
        recipients=recipients,
        body="Attached report",
        pdf_path=pdf_path
    )

    # ✅ JS alert + redirect back
    return """
    <script>
        alert("✅ Report sent successfully!");
        window.history.back();
    </script>
    """
@app.route("/cow_registry", methods=["GET", "POST"])
@login_required

def cow_registry():
    message = None

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
            
                      
        )

        db.session.add(new_registry)
        db.session.commit()
        message="Succesifully added"
        
    return render_template("cow_registry.html", message=message)


@app.route("/animals")
@login_required
def animals():

    category = request.args.get("category")

    data = get_animals_data(category)

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

    if request.method == "POST":

        selected_ids = request.form.getlist("treatment_ids")

        if "delete_selected" in request.form:
            for rid in selected_ids:
                rec = Treatment.query.get(int(rid))
                if rec:
                    db.session.delete(rec)

            db.session.commit()

        return redirect(url_for("treatment"))

    date_str = request.args.get("date")
    status = request.args.get("status")

    data = get_treatment_data(date_str, status)

    return render_template("treatment.html", **data)

@app.route("/add_treatment", methods=["GET","POST"])
@login_required
def add_treatment():

    animals = AnimalRegistry.query.all()

    if request.method == "POST":

        record = Treatment(
            animal_id=request.form.get("animal_id"),
            date_treated=datetime.strptime(request.form.get("date"), "%Y-%m-%d"),
            illness=request.form.get("illness"),
            cost=float(request.form.get("cost")),
            vet=request.form.get("vet"),
            status=request.form.get("status")
        )

        db.session.add(record)
        db.session.commit()

        return redirect(url_for("treatment"))

    return render_template("add_treatment.html", animals=animals)

@app.route("/edit_treatment/<int:id>", methods=["GET","POST"])
@login_required
def edit_treatment(id):

    rec = Treatment.query.get_or_404(id)

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
            mother=mother         
        )

        db.session.add(new_registry)
        db.session.commit()
        message="Succesifully added"
        
    return render_template("calf_registry.html", message=message)


@app.route("/insemination/add", methods=["GET","POST"])
@login_required
def add_insemination():

    animals = AnimalRegistry.query.all()

    if request.method == "POST":

        animal_id = request.form["animal_id"]
        date_served = datetime.strptime(request.form["date_served"], "%Y-%m-%d")
        method = request.form["method"]

        days = CONFIRMATION_METHODS.get(method, 30)

        confirmation_date = date_served + timedelta(days=days)

        record = Insemination(
            animal_id=animal_id,
            date_served=date_served,
            confirmation_method=method,
            confirmation_date=confirmation_date,
            status="pending",
            calving_date=None
        )

        db.session.add(record)
        db.session.commit()

        return redirect("/insemination")

    return render_template("add_insemination.html", animals=animals)

from datetime import datetime

@app.route("/insemination")
@login_required
def insemination():

    status = request.args.get("status")
    month = request.args.get("month")
    year = request.args.get("year")

    data = get_insemination_data(status, month, year)

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
    animals = AnimalRegistry.query.all()  # 🔥 for dropdown

    if request.method == "POST":

        # 🔹 Get form data
        animal_id = request.form.get("animal_id")
        date_served = request.form.get("date_served")
        status = request.form.get("status")

        # 🔹 Update fields
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
    current_date = date.today()

    return render_template(
        "Assets.html",
        Assets=Assets,
        current_date=current_date
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
    current_date = date.today()

    # ✅ CALCULATE TOTAL SALARY
    total = sum(float(e.salary or 0) for e in Employees)

    return render_template(
        "Employees.html",
        Employees=Employees,
        current_date=current_date,
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
@role_required("admin", "finance")
def orders_v2():

    month = request.args.get("month")
    farm_id = request.args.get("farm_id")

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
@role_required("admin", "finance")
def delete_order(id):

    order = FeedsOrderV2.query.get_or_404(id)

    db.session.delete(order)
    db.session.commit()

    return redirect("/feeds_v2/orders")


# =========================================================
# DELIVERY REPORT ROUTE
# =========================================================
@app.route("/feeds_v2/delivery_report")
@login_required
@role_required("admin", "finance")
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
@login_required
@role_required("admin", "finance")
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

        flash("✅ Delivery updated successfully", "success")

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
@login_required
@role_required("admin", "finance")
def delete_delivery(id):

    delivery = FeedsDeliveryV2.query.get_or_404(id)

    order_id = delivery.order_id

    db.session.delete(delivery)
    db.session.commit()

    flash("✅ Delivery deleted successfully", "success")

    return redirect(url_for(
        "delivery_report",
        order_id=order_id
    ))

@app.route("/feeds_v2/search_feed")
@login_required
def search_feed():

    term = request.args.get("q", "").strip().lower()

    feeds = FeedsRegistry.query.filter(
        func.lower(FeedsRegistry.FeedName).like(f"%{term}%")
    ).with_entities(FeedsRegistry.FeedName).distinct().all()

    results = [f.FeedName for f in feeds]

    return {"results": results}

@app.route("/feeds_v2/create", methods=["GET", "POST"])
@role_required("admin", "finance")
def create_order():

    farms = Farm.query.all()

    if request.method == "POST":

        order = FeedsOrderV2(
            order_ref=generate_order_ref(),
            date_ordered=datetime.strptime(request.form["date"], "%Y-%m-%d"),
            farm_id=int(request.form["farm_id"])
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
@login_required
@role_required("admin", "finance")
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
@login_required
@role_required("admin", "finance")
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
@login_required
@role_required("admin", "finance")
def payment_report():

    order_id = request.args.get("order_id")
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
@role_required("admin", "finance")
def delete_payment(id):

    payment = Payment.query.get_or_404(id)

    db.session.delete(payment)
    db.session.commit()

    return redirect(request.referrer or "/feeds_v2/orders")
from datetime import datetime

@app.route("/feeds_v2/payment/<int:order_id>", methods=["GET", "POST"])
@login_required
@role_required("admin", "finance")
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
@login_required
@role_required("admin", "finance")
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

        flash("✅ Payment updated successfully", "success")

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
@login_required
@role_required("admin", "finance")
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
@login_required
@role_required("admin", "finance")
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
@login_required
@role_required("admin", "finance")
def delete_item(id):

    item = FeedsOrderItemV2.query.get_or_404(id)

    db.session.delete(item)
    db.session.commit()

    return redirect(request.referrer or "/feeds_v2/orders")

@app.route("/feeds_v2/item/edit/<int:id>", methods=["GET", "POST"])
@login_required
@role_required("admin", "finance")
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

            cow_id = int(cow_ids[i])

            morning = float(mornings[i] or 0)
            noon = float(noons[i] or 0)
            evening = float(evenings[i] or 0)

            total = morning + noon + evening

            if total > 0:

                existing = MilkRegistry.query.filter_by(
                    cow_id=cow_id,
                    date=selected_date
                ).first()

                if existing:

                    existing.morning = morning
                    existing.noon = noon
                    existing.evening = evening
                    existing.total = total

                else:

                    record = MilkRegistry(
                        cow_id=cow_id,
                        date=selected_date,
                        morning=morning,
                        noon=noon,
                        evening=evening,
                        total=total
                    )

                    db.session.add(record)

        db.session.commit()

        flash("Milk records saved successfully.", "success")

        return redirect(url_for("milk_registry"))

    cows = MilkingHerd.query.all()

    current_date = date.today()

    return render_template(
        "milk_registry.html",
        cows=cows,
        current_date=current_date
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
                date=selected_date
            ).first()

            if existing:

                existing.morning = morning
                existing.noon = noon
                existing.evening = evening
                existing.total = total

            else:

                record = MilkRegistry(

                    cow_id=cow_id,
                    date=selected_date,
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

    # ✅ USE SHARED FUNCTION
    date_str = request.args.get("filter_date")

    data = get_milk_report_data(date_str)

    return render_template("milk.html", **data)

@app.route("/delete_milk/<int:id>")
@login_required
def delete_milk(id):

    record = MilkRegistry.query.get_or_404(id)
    selected_date = record.date
    db.session.delete(record)
    db.session.commit()

    return redirect(url_for("milk", filter_date=selected_date))

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

        return redirect(url_for("milk", filter_date=selected_date))

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
        data=data,              # ✅ THIS FIXES YOUR ERROR
        date_str=date_str
    )



@app.route("/milk_sales_entry", methods=["GET", "POST"])
@login_required
def milk_sales_entry():

    if request.method == "POST":

        date = datetime.strptime(request.form["date"], "%Y-%m-%d").date()

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

    return redirect(url_for("milk_sales_report", date=selected_date))

@app.route("/edit_milk_sale/<int:id>", methods=["GET", "POST"])
@login_required
def edit_milk_sale_record(id):   # 👈 changed function name

    sale = MilkSalesRegistry.query.get_or_404(id)

    if request.method == "POST":

        sale.date = datetime.strptime(request.form["date"], "%Y-%m-%d").date()
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

    record = MilkDailyRemaining.query.filter_by(date=selected_date).first()

    if record:
        record.actual_remaining = value
    else:
        record = MilkDailyRemaining(
            date=selected_date,
            actual_remaining=value
        )
        db.session.add(record)

    db.session.commit()

    return redirect(url_for("milk_sales_report", date=selected_date))

# =========================
# MILK PRICE ROUTES
# =========================

from datetime import datetime

@app.route("/milk_prices", methods=["GET", "POST"])
@login_required
@role_required("admin", "finance")
def milk_prices():

    # ---------------- ADD / UPDATE ----------------
    if request.method == "POST":

        price_id = request.form.get("price_id")

        price = request.form.get("price")
        effective_date = request.form.get("effective_date")

        if price and effective_date:

            effective_date = datetime.strptime(
                effective_date,
                "%Y-%m-%d"
            ).date()

            # -------- EDIT --------
            if price_id:

                record = MilkPrice.query.get(price_id)

                if record:
                    record.price = price
                    record.effective_date = effective_date

            # -------- ADD --------
            else:

                new_price = MilkPrice(
                    price=price,
                    effective_date=effective_date
                )

                db.session.add(new_price)

            db.session.commit()

            flash("Milk price saved successfully", "success")

        return redirect(url_for("milk_prices"))

    # ---------------- GET ALL ----------------
    prices = MilkPrice.query.order_by(
        MilkPrice.effective_date.desc()
    ).all()

    return render_template(
        "milk_prices.html",
        prices=prices
    )


# =========================
# DELETE
# =========================

@app.route("/delete_milk_price/<int:id>")
@login_required
@role_required("admin", "finance")
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
@login_required
@role_required("admin", "finance")
def car_registry():

    if request.method == "POST":
        plate_number = request.form.get("plate_number")
        model = request.form.get("model")
        driver = request.form.get("driver")

        new_car = CarRegistry(
            plate_number=plate_number,
            model=model,
            driver=driver
        )

        db.session.add(new_car)
        db.session.commit()

        return redirect(url_for("car_registry"))

    cars = CarRegistry.query.all()

    return render_template("car_registry.html", cars=cars)

@app.route("/add_car_expense", methods=["GET", "POST"])
@login_required
@role_required("admin", "finance")
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

    cars = CarRegistry.query.all()

    return render_template("add_car_expense.html", cars=cars)

@app.route("/car_expense_report")
@login_required
@role_required("admin", "finance")
def car_expense_report():

    selected_date = request.args.get("date")

    data = get_car_expense_report_data(selected_date)

    return render_template("car_expense_report.html", **data)

@app.route("/delete_car_expense/<int:id>")
@login_required
@role_required("admin", "finance")
def delete_car_expense(id):
    expense = CarExpense.query.get_or_404(id)

    db.session.delete(expense)
    db.session.commit()

    return redirect(url_for("car_expense_report"))

@app.route("/edit_car_expense/<int:id>", methods=["GET", "POST"])
@login_required
@role_required("admin", "finance")
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

@app.route("/car_sales/add", methods=["GET", "POST"])
@login_required
@role_required("admin", "finance")
def add_car_sale():

    # GET ALL CARS
    cars = CarRegistry.query.all()

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
            sale_date = datetime.strptime(date_str, "%Y-%m-%d").date()

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
                date=sale_date,
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
@login_required
@role_required("admin", "finance")
def car_sales_report():

    selected_date = request.args.get("date")

    data = get_sales_report_data(selected_date)

    return render_template("car_sales_report.html", **data)


@app.route("/delete_car_sale/<int:id>")
@login_required
@role_required("admin", "finance")
def delete_car_sale(id):
    sale = CarSales.query.get_or_404(id)
    db.session.delete(sale)
    db.session.commit()
    return redirect(url_for("car_sales_report"))

@app.route("/edit_car_sale/<int:id>", methods=["GET", "POST"])
@login_required
@role_required("admin", "finance")
def edit_car_sale(id):

    sale = CarSales.query.get_or_404(id)
    cars = CarRegistry.query.all()

    if request.method == "POST":
        sale.car_id = request.form.get("car_id")
        sale.date = datetime.strptime(request.form.get("date"), "%Y-%m-%d").date()
        sale.length = request.form.get("day_length")

        if sale.length == "HALF":
            sale.amount = 5000
        else:
            sale.amount = 10000

        db.session.commit()
        return redirect(url_for("car_sales_report"))

    return render_template("edit_car_sale.html", sale=sale, cars=cars)




@app.route("/payments", methods=["GET", "POST"])
@login_required
@role_required("admin", "finance")
def payments():
    message = None
    farms = Farm.query.all()

    if request.method == "POST":
        date_str = request.form.get("date_paid")
        amount = request.form.get("amount")
        account = request.form.get("account")
        purpose = request.form.get("purpose")
        purpose_type = request.form.get("purpose_type")
        farm_id = request.form.get("farm_id")

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

    payments = Payment.query.order_by(Payment.date_paid.desc()).all()

    return render_template("payments.html", payments=payments, farms=farms, message=message)

@app.route("/transactions")
@login_required
@role_required("admin", "finance")
def transactions():

    filter_date = request.args.get("filter_date")
    month = request.args.get("month")
    purpose = request.args.get("purpose")
    farm_id = request.args.get("farm_id")
    order_id = request.args.get("order_id")   # ✅ ADD THIS

    data = get_transactions_data(filter_date, month, purpose, farm_id, order_id)

    farms = Farm.query.all()

    return render_template(
        "transactions.html",
        farms=farms,
        order_id=order_id,   # optional
        **data
    )
@app.route("/edit_transaction/<int:id>", methods=["GET", "POST"])
@login_required
@role_required("admin", "finance")
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

        flash("✅ Transaction updated successfully", "success")

        # 🔥 RETURN TO SAME PAGE WITH FILTERS
        return redirect(url_for(
            "transactions",
            filter_date=selected_date,
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
@login_required
@role_required("admin", "finance")
def delete_transaction(id):

    transaction = Payment.query.get_or_404(id)

    selected_date = request.args.get("filter_date")
    purpose = request.args.get("purpose")
    farm_id = request.args.get("farm_id")

    db.session.delete(transaction)
    db.session.commit()

    return redirect(url_for(
        "transactions",
        filter_date=selected_date,
        purpose=purpose,
        farm_id=farm_id
    ))


# @app.route("/routes")
# def list_routes():
#     return "<br>".join([str(r) for r in app.url_map.iter_rules()])
@app.route("/milk_dashboard")
def milk_dashboard():

    date_str = request.args.get("filter_date")

    milk_data = get_milk_report_data(date_str)

    sales_data = get_milk_sales(date_str)

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

    data = get_animals_data()

    return render_template(
        "cow_dashboard.html",
        **data
    )


@app.route("/financial_dashboard")
@login_required
@role_required("admin", "finance")
def financial_dashboard():

    # =========================================
    # TODAY
    # =========================================

    today_str = date.today().strftime("%Y-%m-%d")

    # =========================================
    # INDEPENDENT FILTERS
    # =========================================

    # MILK FILTER
    milk_date = request.args.get(
        "milk_date",
        today_str
    )

    # VEHICLE SALES FILTER
    # OPTIONAL -> SHOW ALL IF EMPTY
    vehicle_date = request.args.get(
        "vehicle_date"
    )

    # GENERAL EXPENSE FILTER
    expense_date = request.args.get(
        "expense_date",
        today_str
    )

    # =========================================
    # MILK SALES
    # =========================================

    milk_sales_data = get_milk_sales(
        milk_date
    )

    # =========================================
    # VEHICLE SALES ANALYTICS
    # COMPLETELY INDEPENDENT
    # =========================================

    if vehicle_date and vehicle_date.strip():

        # FILTER VEHICLE SALES ONLY
        car_sales_data = get_sales_report_data(
            vehicle_date
        )

    else:

        # NO FILTER -> SHOW ALL VEHICLE SALES
        car_sales_data = get_sales_report_data()

    # =========================================
    # CAR EXPENSES
    # COMPLETELY INDEPENDENT
    # NOT AFFECTED BY expense_date
    # =========================================

    if vehicle_date and vehicle_date.strip():

        # FILTER CAR EXPENSES ONLY
        car_expense_data = get_car_expense_report_data(
            vehicle_date
        )

    else:

        # SHOW ALL CAR EXPENSES
        car_expense_data = get_car_expense_report_data()

    # =========================================
    # GENERAL FARM / BUSINESS EXPENSES
    # INDEPENDENT FROM VEHICLE ANALYTICS
    # =========================================

    transaction_data = get_transactions_data(
        expense_date
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
        "milk_date": milk_date,

        "vehicle_date": vehicle_date,

        "expense_date": expense_date

    }

    # =========================================
    # RENDER
    # =========================================

    return render_template(
        "financial_dashboard.html",
        **combined_data
    )
    
@app.route("/")
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
from sqlalchemy import inspect, text

if __name__ == "__main__":
    app.run(debug=True)