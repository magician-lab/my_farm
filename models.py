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

    confirmation_method = db.Column(db.String(50))

    confirmation_date = db.Column(db.Date)

    status = db.Column(db.String(20), default=None)

    calving_date = db.Column(db.Date)

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

    morning = db.Column(db.Numeric(10,2), nullable=False)
    noon = db.Column(db.Numeric(10,2), nullable=False)
    evening = db.Column(db.Numeric(10,2), nullable=False)
    total = db.Column(db.Numeric(10,2), nullable=False)

    cow = db.relationship('AnimalRegistry', backref='milk_records')

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

class MilkPrice(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    price = db.Column(db.Numeric(10,2), nullable=False)

    # 🔥 when this price becomes active
    effective_date = db.Column(db.Date, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CarRegistry(db.Model):
    __tablename__ = "car_registry"

    id = db.Column(db.Integer, primary_key=True)
    plate_number = db.Column(db.String(50), unique=True, nullable=False)
    model = db.Column(db.String(100))
    driver = db.Column(db.String(100))

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

class CowShed(db.Model):

    __tablename__ = "cow_shed"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), unique=True, nullable=False)

    category_allowed = db.Column(db.String(50))

    capacity = db.Column(db.Integer, default=0)

    color = db.Column(db.String(20), default="primary")

    description = db.Column(db.Text)

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
    date = db.Column(db.Date, unique=True, nullable=False)
    actual_remaining = db.Column(db.Numeric(10,2), default=0)

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


