from flask import render_template, redirect, url_for
from flask_login import login_required, current_user
from app.routes import bp
from app.models import User, Ingredient, Product
from app import db
from sqlalchemy import func
from datetime import datetime, timedelta

@bp.route('/')
def index():
    """Landing page - redirect to login if not authenticated, dashboard if authenticated"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))

@bp.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard with KPIs and overview"""
    
    # Calculate KPIs
    sandwich_count = Product.query.filter_by(is_active=True, product_type='sandwich').count()
    menu_count = Product.query.filter_by(is_active=True, product_type='menu').count()
    total_ingredients = Ingredient.query.filter_by(is_active=True).count()
    total_users = User.query.filter_by(is_active=True).count()
    
    # Average cost calculation
    avg_cost = db.session.query(func.avg(Product.total_cost)).filter(
        Product.total_cost.isnot(None),
        Product.is_active == True
    ).scalar() or 0
    
    # Recent products (last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_products = Product.query.filter(
        Product.created_at >= week_ago,
        Product.is_active == True
    ).order_by(Product.created_at.desc()).limit(5).all()
    
    
    kpis = {
        'sandwich_count': sandwich_count,
        'menu_count': menu_count,
        'total_ingredients': total_ingredients,
        'total_users': total_users,
        'avg_cost': round(avg_cost, 2) if avg_cost else 0
    }
    
    return render_template('dashboard.html', 
                         kpis=kpis, 
                         recent_products=recent_products)

@bp.route('/about')
def about():
    """About page with app information"""
    return render_template('about.html')