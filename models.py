from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta, date
from decimal import Decimal
db = SQLAlchemy()

class CowRegistry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    CowName = db.Column(db.String(100), nullable=False)
    Breed = db.Column(db.String(100), nullable=True)
    Date_bought = db.Column(db.Date, nullable=True)
    category = db.Column(db.String(100), nullable=True)

class Treatment(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    animal_id = db.Column(db.Integer, db.ForeignKey('animal_registry.id'))
    animal = db.relationship("AnimalRegistry")

    date_treated = db.Column(db.Date)
    illness = db.Column(db.String(200))
    cost = db.Column(db.Float)
    vet = db.Column(db.String(100))

    status = db.Column(db.String(20))  # healed / recovering

    farm_id = db.Column(db.Integer, db.ForeignKey('farm.id'), nullable=True)   

class CalfRegistry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    CalfName = db.Column(db.String(100), nullable=False)
    Breed = db.Column(db.String(100), nullable=False)
    DOB = db.Column(db.Date, nullable=False)
    level = db.Column(db.String(100), nullable=True)
    mother = db.Column(db.String(100), nullable=False)

from datetime import timedelta

class Insemination(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    animal_id = db.Column(
        db.Integer,
        db.ForeignKey("animal_registry.id"),
        nullable=False
    )

    animal = db.relationship("AnimalRegistry")

    date_served = db.Column(db.Date, nullable=False)

    # Bull used to serve the cow
    bull_name = db.Column(db.String(100), nullable=True)
    bull_breed = db.Column(db.String(100), nullable=True)

    confirmation_method = db.Column(db.String(50))

    confirmation_date = db.Column(db.Date)

    status = db.Column(db.String(20), default=None)

    calving_date = db.Column(db.Date)

    farm_id = db.Column(db.Integer, db.ForeignKey('farm.id'), nullable=True)

class AssetsRegistry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    AssetName = db.Column(db.String(100), nullable=False)
    Purpose = db.Column(db.String(100), nullable=False)
    Bought_date = db.Column(db.Date, nullable=False)
    cost = db.Column(db.Numeric(10,2), nullable=False)
    origin = db.Column(db.String(100), nullable=False)

class ExpensesRegistry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ExpenseName = db.Column(db.String(100), nullable=False)
    Description = db.Column(db.String(100), nullable=False)
    Incurred_date = db.Column(db.Date, nullable=False)
    cost = db.Column(db.Numeric(10,2), nullable=False)

class EmployeesRegistry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    EmployeeName = db.Column(db.String(100), nullable=False)
    ID_Number = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(100), nullable=False)
    salary = db.Column(db.Numeric(10,2), nullable=False)
    role = db.Column(db.String(100), nullable=False)

class ShopRegistry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ShopName = db.Column(db.String(100), nullable=False)
    litres = db.Column(db.Numeric(10,2), nullable=False)
    Date_sold = db.Column(db.Date, nullable=False)
    location = db.Column(db.String(100), nullable=False)

class UserRegistry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    FirstName = db.Column(db.String(100), nullable=False)
    UserName = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(10), nullable=False)

class Farm(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    feeds = db.relationship("FeedsRegistry", backref="farm", lazy=True)

    def __repr__(self):
        return f"<Farm {self.name}>"

class FeedsRegistry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    Date_bought = db.Column(db.Date, nullable=False)
    FeedName = db.Column(db.String(100), nullable=False)
    farm_id = db.Column(db.Integer, db.ForeignKey('farm.id'), nullable=False)
    Quantity = db.Column(db.Numeric(10,2), nullable=False)
    Price = db.Column(db.Numeric(10,2), nullable=False)
    Total = db.Column(db.Numeric(10,2), nullable=False)

class MilkRegistry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cow_id = db.Column(db.Integer, db.ForeignKey('animal_registry.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)

    morning = db.Column(db.Numeric(10,2), nullable=False, default=0)
    noon = db.Column(db.Numeric(10,2), nullable=False, default=0)
    evening = db.Column(db.Numeric(10,2), nullable=False, default=0)
    # New canonical milking sessions: Session 1 / 2 / 3
    # Kept alongside morning/noon/evening for backwards compat; new writes use session_1/2/3.
    session_1 = db.Column(db.Numeric(10,2), nullable=True, default=0)
    session_2 = db.Column(db.Numeric(10,2), nullable=True, default=0)
    session_3 = db.Column(db.Numeric(10,2), nullable=True, default=0)
    total = db.Column(db.Numeric(10,2), nullable=False)

    farm_id = db.Column(db.Integer, db.ForeignKey('farm.id'), nullable=True)

    cow = db.relationship('AnimalRegistry', backref='milk_records')

    def s1(self):
        from decimal import Decimal as _D
        if self.session_1 is not None:
            return float(self.session_1)
        return float(self.morning or 0)

    def s2(self):
        if self.session_2 is not None:
            return float(self.session_2)
        return float(self.noon or 0)

    def s3(self):
        if self.session_3 is not None:
            return float(self.session_3)
        return float(self.evening or 0)

class MilkSalesRegistry(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    date = db.Column(db.Date, nullable=False)
    session = db.Column(db.String(20), nullable=False)  # Morning / Noon / Evening

    shop1 = db.Column(db.Numeric(10,2), default=0)
    shop2 = db.Column(db.Numeric(10,2), default=0)
    shop3 = db.Column(db.Numeric(10,2), default=0)
    home = db.Column(db.Numeric(10,2), default=0)
    calf = db.Column(db.Numeric(10,2), default=0)
    price = db.Column(db.Numeric(10,2), default=0)

    farm_id = db.Column(db.Integer, db.ForeignKey('farm.id'), nullable=True)

class MilkPrice(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    price = db.Column(db.Numeric(10,2), nullable=False)

    # 🔥 when this price becomes active
    effective_date = db.Column(db.Date, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    farm_id = db.Column(db.Integer, db.ForeignKey('farm.id'), nullable=True)

class CarRegistry(db.Model):
    __tablename__ = "car_registry"

    id = db.Column(db.Integer, primary_key=True)
    plate_number = db.Column(db.String(50), unique=True, nullable=False)
    model = db.Column(db.String(100))
    driver = db.Column(db.String(100))
    active = db.Column(db.Boolean, default=True)

    expenses = db.relationship("CarExpense", backref="car", cascade="all, delete", lazy=True)
    sales = db.relationship("CarSales", backref="car", cascade="all, delete", lazy=True)

class CarExpense(db.Model):
    __tablename__ = "car_expense"

    id = db.Column(db.Integer, primary_key=True)
    car_id = db.Column(db.Integer, db.ForeignKey("car_registry.id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    expense_type = db.Column(db.String(100))   # fuel, repair, insurance etc
    description = db.Column(db.String(200))
    amount = db.Column(db.Float, nullable=False)

class CarSales(db.Model):
    __tablename__ = "car_sales"

    id = db.Column(db.Integer, primary_key=True)
    car_id = db.Column(db.Integer, db.ForeignKey("car_registry.id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    length = db.Column(db.String(15))   # fuel, repair, insurance etc
    amount = db.Column(db.Float, nullable=False)


class AnimalRegistry(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)

    breed = db.Column(db.String(100))

    dob = db.Column(db.Date, nullable=True)

    category = db.Column(db.String(50))

    sex = db.Column(db.String(20), default="cow")

    mother = db.Column(db.String(100), nullable=True)

    # NEW
    current_shed_id = db.Column(
        db.Integer,
        db.ForeignKey("cow_shed.id"),
        nullable=True
    )

    farm_id = db.Column(db.Integer, db.ForeignKey('farm.id'), nullable=True)

class CowShed(db.Model):

    __tablename__ = "cow_shed"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)

    category_allowed = db.Column(db.String(50))

    capacity = db.Column(db.Integer, default=0)

    color = db.Column(db.String(20), default="primary")

    description = db.Column(db.Text)

    farm_id = db.Column(db.Integer, db.ForeignKey('farm.id'), nullable=True)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    animals = db.relationship(
        "AnimalRegistry",
        backref="shed",
        lazy=True
    )

    @property
    def occupied(self):
        return AnimalRegistry.query.filter_by(
            current_shed_id=self.id
        ).count()

    @property
    def remaining(self):
        return self.capacity - self.occupied

    @property
    def is_full(self):
        return self.occupied >= self.capacity

class AnimalMovement(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    animal_id = db.Column(
        db.Integer,
        db.ForeignKey("animal_registry.id")
    )

    from_shed_id = db.Column(
        db.Integer,
        db.ForeignKey("cow_shed.id"),
        nullable=True
    )

    to_shed_id = db.Column(
        db.Integer,
        db.ForeignKey("cow_shed.id")
    )

    moved_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    reason = db.Column(db.String(255))

    animal = db.relationship(
        "AnimalRegistry"
    )

    from_shed = db.relationship(
        "CowShed",
        foreign_keys=[from_shed_id]
    )

    to_shed = db.relationship(
        "CowShed",
        foreign_keys=[to_shed_id]
    )

class MilkingHerd(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    animal_id = db.Column(
        db.Integer,
        db.ForeignKey("animal_registry.id"),
        unique=True,
        nullable=False
    )

    animal = db.relationship("AnimalRegistry")

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date_paid = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Numeric(10,2), nullable=False)
    account = db.Column(db.String(100), nullable=False)

    purpose_type = db.Column(db.String(20), nullable=False)  # feeds / other
    purpose = db.Column(db.String(200), nullable=False)

    farm_id = db.Column(db.Integer, db.ForeignKey('farm.id'), nullable=True)
    farm = db.relationship("Farm", backref="payments")

    def __repr__(self):
        return f"<Payment {self.amount}>"

class MilkDailyRemaining(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    actual_remaining = db.Column(db.Numeric(10,2), default=0)
    farm_id = db.Column(db.Integer, db.ForeignKey('farm.id'), nullable=True)
    __table_args__ = (db.UniqueConstraint('date', 'farm_id', name='uq_remaining_date_farm'),)

# =========================================================
# ADMIN MODEL
# =========================================================

class Admin(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(255),
        nullable=False
    )

    # =====================================================
    # ROLE / ACCESS LEVEL
    # =====================================================

    role = db.Column(
        db.String(50),
        default="user"
    )

    # Farm access: NULL = admin access to all farms, specific farm_id = restricted
    farm_id = db.Column(db.Integer, db.ForeignKey('farm.id'), nullable=True)

    # =====================================================
    # OTP RESET
    # =====================================================

    otp_code = db.Column(db.String(6))

    otp_expiration = db.Column(db.DateTime)

    # =====================================================
    # CREATED DATE
    # =====================================================

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


# 🔹 ORDER (HEADER)
class FeedsOrderV2(db.Model):
    __tablename__ = "feeds_order_v2"

    id = db.Column(db.Integer, primary_key=True)
    order_ref = db.Column(db.String(50), unique=True, nullable=False)
    date_ordered = db.Column(db.Date, nullable=False)
    farm_id = db.Column(db.Integer, db.ForeignKey('farm.id'), nullable=False)

    # 🔥 ADD THIS LINE
    farm = db.relationship("Farm", backref="feeds_orders")

    items = db.relationship("FeedsOrderItemV2", backref="order", cascade="all, delete-orphan")
    deliveries = db.relationship("FeedsDeliveryV2", backref="order", cascade="all, delete-orphan")
    payments = db.relationship("PaymentV2", backref="order", cascade="all, delete-orphan")


# 🔹 ITEMS (FEEDS INSIDE ORDER)
class FeedsOrderItemV2(db.Model):
    __tablename__ = "feeds_order_item_v2"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('feeds_order_v2.id'))

    feed_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Numeric(10,2))  # total kg
    price_per_unit = db.Column(db.Numeric(10,2))
    total_cost = db.Column(db.Numeric(10,2))


class FeedsDeliveryV2(db.Model):
    __tablename__ = "feeds_delivery_v2"

    id = db.Column(db.Integer, primary_key=True)

    order_id = db.Column(db.Integer, db.ForeignKey('feeds_order_v2.id'))
    item_id = db.Column(db.Integer, db.ForeignKey('feeds_order_item_v2.id'))

    date_delivered = db.Column(db.Date, nullable=False)

    pieces = db.Column(db.Integer)
    unit_weight = db.Column(db.Numeric(10,2))
    quantity_delivered = db.Column(db.Numeric(10,2))

    # 🔥 ADD THIS
    item = db.relationship("FeedsOrderItemV2")


# 🔹 PAYMENT (ORDER LEVEL)
class PaymentV2(db.Model):
    __tablename__ = "payment_v2"

    id = db.Column(db.Integer, primary_key=True)

    order_id = db.Column(db.Integer, db.ForeignKey('feeds_order_v2.id'))
    date_paid = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Numeric(10,2))

    account = db.Column(db.String(100))
    purpose = db.Column(db.String(200))


# =========================================================
# EDIT-MODE OTP SETTINGS (per farm + admin global)
# farm_id NULL = Admin/global. Otherwise Murang'a / Meru etc.
# emails = comma-separated list, can be more than one.
# =========================================================
class OTPSetting(db.Model):
    __tablename__ = "otp_setting"

    id = db.Column(db.Integer, primary_key=True)
    farm_id = db.Column(db.Integer, db.ForeignKey('farm.id'), nullable=True, unique=True)
    emails = db.Column(db.Text, nullable=False, default="")

    updated_by = db.Column(db.String(100), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    farm = db.relationship("Farm", backref="otp_setting")

    def email_list(self):
        out = []
        for part in (self.emails or "").replace(";", ",").split(","):
            e = part.strip()
            if e and "@" in e and e not in out:
                out.append(e)
        return out


# =========================================================
# EDIT-MODE OTP CODES
# =========================================================
class EditOTP(db.Model):
    __tablename__ = "edit_otp"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('admin.id'), nullable=True)
    username = db.Column(db.String(100), nullable=True)
    farm_id = db.Column(db.Integer, db.ForeignKey('farm.id'), nullable=True)
    otp_code = db.Column(db.String(6), nullable=False)
    purpose = db.Column(db.String(50), default="edit_mode")
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def is_valid(self):
        return (not self.used) and datetime.utcnow() < self.expires_at


# =========================================================
# AUDIT LOG — track operations by various users (admin view)
# =========================================================
class AuditLog(db.Model):
    __tablename__ = "audit_log"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, nullable=True)
    username = db.Column(db.String(100), nullable=True)
    role = db.Column(db.String(50), nullable=True)
    farm_id = db.Column(db.Integer, db.ForeignKey('farm.id'), nullable=True)
    farm_name = db.Column(db.String(100), nullable=True)
    action = db.Column(db.String(50), nullable=False)  # CREATE/UPDATE/DELETE/OTP_REQUEST/OTP_VERIFY/LOGIN/EDIT_MODE
    entity = db.Column(db.String(100), nullable=True)
    entity_id = db.Column(db.String(50), nullable=True)
    details = db.Column(db.Text, nullable=True)



