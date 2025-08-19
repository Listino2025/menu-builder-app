from app import db
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import check_password_hash, generate_password_hash
import secrets

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
    price_per_unit = db.Column(db.Numeric(15, 7), nullable=False)
    unit_type = db.Column(db.String(20), nullable=False)
    
    # Valid unit types constraint
    __table_args__ = (
        db.CheckConstraint(unit_type.in_(['kg', 'g', 'hg', 'dag', 'dg', 'l', 'dl', 'cl', 'ml', 'pieces', 'slices', 'portions']), name='ingredients_unit_type_check'),
    )
    temperature_zone = db.Column(db.String(50), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Ingredient categories for UI grouping
    CATEGORIES = {
        'BASE': 'Base (Buns)',
        'PROTEIN': 'Proteins',
        'CHEESE': 'Cheeses', 
        'VEGETABLE': 'Vegetables',
        'SAUCE': 'Sauces',
        'OTHER': 'Other'
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
    product_type = db.Column(db.String(20), default='sandwich', nullable=False)  # sandwich, menu
    selling_price = db.Column(db.Numeric(15, 7), nullable=True)  # Can be null for sandwiches used in menus
    total_cost = db.Column(db.Numeric(15, 7), nullable=False, default=0)
    gross_profit = db.Column(db.Numeric(15, 7), nullable=True)
    gross_profit_percent = db.Column(db.Numeric(8, 4), nullable=True)
    
    # New required fields for menu creation
    restaurant_id = db.Column(db.String(50), nullable=True)  # ID ristorante per prezzi specifici
    delivery_price_id = db.Column(db.String(50), nullable=True)  # ID Prezzo prodotto Delivery
    food_paper_cost_total = db.Column(db.Numeric(15, 7), nullable=True)  # Food + Paper Cost Totale
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Menu specific fields
    sandwich_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=True)  # For menus
    fries_size = db.Column(db.String(10), nullable=True)  # small, medium, large
    drink_size = db.Column(db.String(10), nullable=True)  # small, medium, large
    
    # Relationships
    ingredients = db.relationship('ProductIngredient', backref='product', lazy='dynamic', cascade='all, delete-orphan')
    sandwich = db.relationship('Product', remote_side=[id], backref='menus')
    
    def calculate_costs(self):
        """Calculate total cost from ingredients"""
        from decimal import Decimal
        total = Decimal('0')
        for pi in self.ingredients:
            # Convert quantity to Decimal if it's not already
            quantity = Decimal(str(pi.quantity)) if pi.quantity else Decimal('0')
            price = Decimal(str(pi.ingredient.price_per_unit)) if pi.ingredient.price_per_unit else Decimal('0')
            total += quantity * price
            
        self.total_cost = total
        
        if self.selling_price:
            selling_price = Decimal(str(self.selling_price))
            self.gross_profit = selling_price - total
            self.gross_profit_percent = (self.gross_profit / selling_price * 100) if selling_price > 0 else Decimal('0')
        
        return total
    
    def get_ingredients_list(self):
        """Get formatted list of ingredients with quantities"""
        return [f"{pi.ingredient.name} ({pi.quantity}{pi.ingredient.unit_type})" 
                for pi in self.ingredients.order_by(ProductIngredient.id)]
    
    def __repr__(self):
        return f'<Product {self.name}>'

class ProductIngredient(db.Model):
    __tablename__ = 'product_ingredients'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    ingredient_id = db.Column(db.Integer, db.ForeignKey('ingredients.id'), nullable=False)
    quantity = db.Column(db.Numeric(15, 7), nullable=False, default=1)
    
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