from datetime import datetime
import enum
import json
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from flask_login import UserMixin

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    eco_points = db.Column(db.Integer, default=0)
    carbon_saved = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    pickups = db.relationship('Schedule', backref='user', lazy=True)
    ewaste_items = db.relationship('Ewaste', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Admin(UserMixin, db.Model):
    __tablename__ = 'admins'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Ewaste(db.Model):
    __tablename__ = 'ewaste'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    ewaste_type = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(100))
    ram = db.Column(db.String(50))
    condition = db.Column(db.String(50))
    estimated_price = db.Column(db.Integer)
    eco_points = db.Column(db.Integer, default=0)
    classification_result = db.Column(db.Text)
    image_path = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    schedules = db.relationship('Schedule', backref='ewaste', lazy=True)

class Schedule(db.Model):
    __tablename__ = 'schedule'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    ewaste_id = db.Column(db.Integer, db.ForeignKey('ewaste.id'), nullable=False)
    pickup_date = db.Column(db.DateTime, nullable=False)
    pickup_address = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='Pending')  # Pending, Collected
    scheduled_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'ewaste_id': self.ewaste_id,
            'pickup_date': self.pickup_date.strftime('%Y-%m-%d %H:%M'),
            'pickup_address': self.pickup_address,
            'status': self.status,
            'scheduled_at': self.scheduled_at.strftime('%Y-%m-%d %H:%M'),
            'ewaste_type': self.ewaste.ewaste_type,
            'model': self.ewaste.model,
            'estimated_price': self.ewaste.estimated_price
        }

class Reward(db.Model):
    __tablename__ = 'rewards'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    image_path = db.Column(db.String(255))
    points_required = db.Column(db.Integer, nullable=False)
    reward_type = db.Column(db.String(50), nullable=False)  # Product, Coupon, Discount
    stock = db.Column(db.Integer, default=10)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with redemptions
    redemptions = db.relationship('Redemption', backref='reward', lazy=True)
    
class Redemption(db.Model):
    __tablename__ = 'redemptions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reward_id = db.Column(db.Integer, db.ForeignKey('rewards.id'), nullable=False)
    points_spent = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(50), default='Pending')  # Pending, Processed, Delivered
    redeemed_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='redemptions', lazy=True)

class OrganizationType(enum.Enum):
    OFFICE = "Office"
    SCHOOL = "School"
    COLLEGE = "College"
    GOVERNMENT = "Government"
    NON_PROFIT = "Non-Profit"
    HEALTHCARE = "Healthcare"
    OTHER = "Other"

class EwasteCondition(enum.Enum):
    WORKING = "Working"
    DAMAGED = "Damaged"
    SCRAP = "Scrap"

class BulkPickupStatus(enum.Enum):
    PENDING = "Pending"
    SCHEDULED = "Scheduled"
    COLLECTED = "Collected"
    VERIFIED = "Verified"
    CANCELLED = "Cancelled"

class BulkPickup(db.Model):
    __tablename__ = 'bulk_pickups'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    organization_name = db.Column(db.String(100), nullable=False)
    organization_type = db.Column(db.Enum(OrganizationType), nullable=False)
    contact_person = db.Column(db.String(100), nullable=False)
    contact_email = db.Column(db.String(120), nullable=False)
    contact_phone = db.Column(db.String(20), nullable=False)
    pickup_address = db.Column(db.Text, nullable=False)
    gstin = db.Column(db.String(20))
    preferred_pickup_date = db.Column(db.DateTime, nullable=False)
    special_instructions = db.Column(db.Text)
    total_items = db.Column(db.Integer, default=0)
    estimated_eco_points = db.Column(db.Integer, default=0)
    actual_eco_points = db.Column(db.Integer, default=0)
    request_certificate = db.Column(db.Boolean, default=True)
    request_tax_receipt = db.Column(db.Boolean, default=False)
    status = db.Column(db.Enum(BulkPickupStatus), default=BulkPickupStatus.PENDING)
    certificate_path = db.Column(db.String(255))
    assigned_team = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='bulk_pickups', lazy=True)
    ewaste_items = db.relationship('BulkEwasteItem', backref='bulk_pickup', lazy=True, cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'organization_name': self.organization_name,
            'organization_type': self.organization_type.value,
            'contact_person': self.contact_person,
            'contact_email': self.contact_email,
            'contact_phone': self.contact_phone,
            'pickup_address': self.pickup_address,
            'gstin': self.gstin,
            'preferred_pickup_date': self.preferred_pickup_date.strftime('%Y-%m-%d %H:%M'),
            'special_instructions': self.special_instructions,
            'total_items': self.total_items,
            'estimated_eco_points': self.estimated_eco_points,
            'actual_eco_points': self.actual_eco_points,
            'request_certificate': self.request_certificate,
            'request_tax_receipt': self.request_tax_receipt,
            'status': self.status.value,
            'certificate_path': self.certificate_path,
            'assigned_team': self.assigned_team,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M'),
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M') if self.updated_at else None
        }

class BulkEwasteItem(db.Model):
    __tablename__ = 'bulk_ewaste_items'
    
    id = db.Column(db.Integer, primary_key=True)
    bulk_pickup_id = db.Column(db.Integer, db.ForeignKey('bulk_pickups.id'), nullable=False)
    ewaste_type = db.Column(db.String(50), nullable=False)
    brand_model = db.Column(db.String(100))
    quantity = db.Column(db.Integer, default=1)
    condition = db.Column(db.Enum(EwasteCondition), nullable=False)
    image_path = db.Column(db.String(255))
    additional_notes = db.Column(db.Text)
    estimated_price_per_unit = db.Column(db.Integer, default=0)
    eco_points_per_unit = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'bulk_pickup_id': self.bulk_pickup_id,
            'ewaste_type': self.ewaste_type,
            'brand_model': self.brand_model,
            'quantity': self.quantity,
            'condition': self.condition.value,
            'image_path': self.image_path,
            'additional_notes': self.additional_notes,
            'estimated_price_per_unit': self.estimated_price_per_unit,
            'eco_points_per_unit': self.eco_points_per_unit,
            'total_eco_points': self.eco_points_per_unit * self.quantity,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M')
        }

class Message(db.Model):
    """Model for E-Talk community messages"""
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)
    
    # Relationship with user
    user = db.relationship('User', backref='messages', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.user.username,
            'content': self.content,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M'),
            'timestamp': int(self.created_at.timestamp()),
            'is_admin': self.is_admin
        }
