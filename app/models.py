from app import db
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import check_password_hash, generate_password_hash
import secrets
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import JSON

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(100), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='user', nullable=False)  # admin, manager, user
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    created_ingredients = db.relationship('Ingredient', backref='creator', lazy='dynamic')
    created_products = db.relationship('Product', backref='creator', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        return self.role == 'admin'
    
    def is_manager(self):
        return self.role in ['admin', 'manager']
    
    def __repr__(self):
        return f'<User {self.username}>'

class Ingredient(db.Model):
    __tablename__ = 'ingredients'
    
    id = db.Column(db.Integer, primary_key=True)
    wrin_code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False, index=True)  # FOOD_FROZEN, FOOD_CHILLED, etc.
    food_paper_cost = db.Column(db.Numeric(15, 2), nullable=False, default=0)  # Manual F&P cost in EUR
    temperature_zone = db.Column(db.String(50), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Ingredient categories for UI grouping
    CATEGORIES = {
        'BASE': 'Base',
        'PROTEIN': 'Proteine',
        'CHEESE': 'Formaggi', 
        'VEGETABLE': 'Verdure',
        'SAUCE': 'Salse',
        'OTHER': 'Altro'
    }
    
    # Temperature zones
    TEMP_ZONES = {
        'FROZEN': 'Frozen (-18°C)',
        'CHILLED': 'Chilled (0-4°C)',
        'AMBIENT': 'Ambient (room temp)',
        'HOT': 'Hot (>65°C)'
    }
    
    def __repr__(self):
        return f'<Ingredient {self.name}>'

class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    product_code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    product_type = db.Column(db.String(20), default='product', nullable=False)  # product, menu
    food_paper_cost_total = db.Column(db.Numeric(15, 2), nullable=False, default=0)  # Total F&P Cost in EUR
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Menu specific fields
    base_product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=True)  # For menus
    fries_size = db.Column(db.String(10), nullable=True)  # small, medium, large
    drink_size = db.Column(db.String(10), nullable=True)  # small, medium, large  
    fries_fp_cost = db.Column(db.Numeric(15, 2), default=0)  # Manual F&P cost for fries
    drink_fp_cost = db.Column(db.Numeric(15, 2), default=0)  # Manual F&P cost for drink
    
    # Relationships
    ingredients = db.relationship('ProductIngredient', backref='product', lazy='dynamic', cascade='all, delete-orphan')
    base_product = db.relationship('Product', remote_side=[id], backref='menus', foreign_keys=[base_product_id])
    
    # Table constraints
    __table_args__ = (
        db.CheckConstraint(product_type.in_(['product', 'menu']), name='products_type_check'),
    )
    
    def calculate_fp_cost(self):
        """Calculate total F&P cost including base product + menu extras"""
        from decimal import Decimal
        
        # Start with base F&P cost
        total = Decimal(str(self.food_paper_cost_total)) if self.food_paper_cost_total else Decimal('0')
        
        # For menu items, add extras costs
        if self.product_type == 'menu':
            if self.fries_size and self.fries_fp_cost:
                total += Decimal(str(self.fries_fp_cost))
            if self.drink_size and self.drink_fp_cost:
                total += Decimal(str(self.drink_fp_cost))
                
        return total
    
    def get_ingredients_list(self):
        """Get formatted list of ingredients"""
        return [pi.ingredient.name for pi in self.ingredients.order_by(ProductIngredient.id)]
    
    def __repr__(self):
        return f'<Product {self.name}>'

class ProductIngredient(db.Model):
    __tablename__ = 'product_ingredients'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    ingredient_id = db.Column(db.Integer, db.ForeignKey('ingredients.id'), nullable=False)
    
    # Relationships
    ingredient = db.relationship('Ingredient', backref='product_uses')
    
    # Ensure unique ingredient per product
    __table_args__ = (db.UniqueConstraint('product_id', 'ingredient_id', name='unique_product_ingredient'),)
    
    def __repr__(self):
        return f'<ProductIngredient {self.product_id}-{self.ingredient_id}>'

class UserSession(db.Model):
    __tablename__ = 'user_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    session_token = db.Column(db.String(255), unique=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='sessions')
    
    @staticmethod
    def generate_token():
        return secrets.token_urlsafe(32)
    
    def is_expired(self):
        return datetime.utcnow() > self.expires_at
    
    def __repr__(self):
        return f'<UserSession {self.user_id}-{self.session_token[:8]}>'

class Restaurant(db.Model):
    __tablename__ = 'restaurants'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    address = db.Column(db.Text, nullable=False)
    city = db.Column(db.String(100), nullable=False)
    postal_code = db.Column(db.String(20))
    latitude = db.Column(db.Numeric(10, 8))  # GPS coordinates precision
    longitude = db.Column(db.Numeric(11, 8))  # GPS coordinates precision
    phone = db.Column(db.String(20))
    email = db.Column(db.String(255))
    opening_hours = db.Column(JSONB)  # Store as JSON for flexibility
    restaurant_code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    product_listings = db.relationship('ProductListing', backref='restaurant', lazy='dynamic', cascade='all, delete-orphan')
    
    def get_coordinates(self):
        """Get coordinates as tuple for mapping"""
        if self.latitude and self.longitude:
            return (float(self.latitude), float(self.longitude))
        return None
    
    def is_open_now(self):
        """Check if restaurant is currently open (basic implementation)"""
        if not self.opening_hours:
            return True  # Assume open if no hours specified
        
        from datetime import datetime
        now = datetime.now()
        weekday = now.strftime('%A').lower()
        
        if weekday in self.opening_hours:
            day_hours = self.opening_hours[weekday]
            if isinstance(day_hours, dict) and 'open' in day_hours and 'close' in day_hours:
                current_time = now.strftime('%H:%M')
                return day_hours['open'] <= current_time <= day_hours['close']
        
        return False
    
    def __repr__(self):
        return f'<Restaurant {self.name}>'

class ProductListing(db.Model):
    __tablename__ = 'product_listings'
    
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    local_price = db.Column(db.Numeric(15, 7), nullable=False)  # Same precision as products
    delivery_price = db.Column(db.Numeric(15, 7), nullable=False)
    is_available = db.Column(db.Boolean, default=True, nullable=False)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    product = db.relationship('Product', backref='listings')
    
    # Constraints
    __table_args__ = (
        db.UniqueConstraint('restaurant_id', 'product_id', name='unique_restaurant_product'),
        db.Index('idx_product_listings_restaurant', 'restaurant_id'),
        db.Index('idx_product_listings_product', 'product_id'),
        db.Index('idx_product_listings_available', 'is_available')
    )
    
    def get_delivery_markup(self):
        """Calculate delivery markup amount"""
        return float(self.delivery_price - self.local_price)
    
    def get_delivery_markup_percent(self):
        """Calculate delivery markup percentage"""
        if self.local_price > 0:
            return (self.get_delivery_markup() / float(self.local_price)) * 100
        return 0
    
    def get_total_food_paper_cost(self):
        """Calculate total F&P cost using product's method"""
        return self.product.calculate_fp_cost()
    
    def get_gross_profit_local(self):
        """Calculate gross profit for local price"""
        return float(self.local_price - self.get_total_food_paper_cost())
    
    def get_gross_profit_delivery(self):
        """Calculate gross profit for delivery price"""
        return float(self.delivery_price - self.get_total_food_paper_cost())
    
    def get_gross_profit_margin_local(self):
        """Calculate gross profit margin percentage for local price"""
        if self.local_price > 0:
            return (self.get_gross_profit_local() / float(self.local_price)) * 100
        return 0
    
    def get_gross_profit_margin_delivery(self):
        """Calculate gross profit margin percentage for delivery price"""
        if self.delivery_price > 0:
            return (self.get_gross_profit_delivery() / float(self.delivery_price)) * 100
        return 0
    
    def __repr__(self):
        return f'<ProductListing {self.restaurant.name}-{self.product.name}>'