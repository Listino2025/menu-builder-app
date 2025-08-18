from flask import render_template, request, jsonify
from flask_login import login_required, current_user
from app.routes import bp
from app.models import Product, Ingredient, ProductIngredient, User
from app.auth.decorators import manager_required
from app import db
from sqlalchemy import func, and_
from datetime import datetime, timedelta

@bp.route('/analytics')
@login_required
def analytics():
    """Analytics dashboard with charts and KPIs"""
    
    # Basic KPIs
    if current_user.is_manager():
        total_products = Product.query.filter_by(is_active=True).count()
        total_users = User.query.filter_by(is_active=True).count()
    else:
        total_products = Product.query.filter_by(is_active=True, created_by=current_user.id).count()
        total_users = None
    
    total_ingredients = Ingredient.query.filter_by(is_active=True).count()
    
    # Average profit calculation
    if current_user.is_manager():
        avg_profit = db.session.query(func.avg(Product.gross_profit)).filter(
            Product.gross_profit.isnot(None),
            Product.is_active == True
        ).scalar() or 0
    else:
        avg_profit = db.session.query(func.avg(Product.gross_profit)).filter(
            Product.gross_profit.isnot(None),
            Product.is_active == True,
            Product.created_by == current_user.id
        ).scalar() or 0
    
    # Most profitable products
    if current_user.is_manager():
        top_products = Product.query.filter(
            Product.gross_profit.isnot(None),
            Product.is_active == True
        ).order_by(Product.gross_profit.desc()).limit(5).all()
    else:
        top_products = Product.query.filter(
            Product.gross_profit.isnot(None),
            Product.is_active == True,
            Product.created_by == current_user.id
        ).order_by(Product.gross_profit.desc()).limit(5).all()
    
    # Category distribution
    category_data = db.session.query(
        Ingredient.category,
        func.count(ProductIngredient.id).label('usage_count')
    ).join(ProductIngredient).join(Product)
    
    if not current_user.is_manager():
        category_data = category_data.filter(Product.created_by == current_user.id)
    
    category_data = category_data.filter(
        Product.is_active == True,
        Ingredient.is_active == True
    ).group_by(Ingredient.category).all()
    
    # Recent activity (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    if current_user.is_manager():
        recent_activity = Product.query.filter(
            Product.created_at >= thirty_days_ago,
            Product.is_active == True
        ).order_by(Product.created_at.desc()).limit(10).all()
    else:
        recent_activity = Product.query.filter(
            Product.created_at >= thirty_days_ago,
            Product.is_active == True,
            Product.created_by == current_user.id
        ).order_by(Product.created_at.desc()).limit(10).all()
    
    analytics_data = {
        'total_products': total_products,
        'total_ingredients': total_ingredients,
        'total_users': total_users,
        'avg_profit': round(avg_profit, 2) if avg_profit else 0,
        'top_products': top_products,
        'category_data': category_data,
        'recent_activity': recent_activity
    }
    
    return render_template('analytics/dashboard.html', data=analytics_data)

@bp.route('/analytics/profit-trend')
@login_required
def profit_trend_data():
    """API endpoint for profit trend chart data"""
    days = request.args.get('days', 30, type=int)
    
    # For now, return sample data
    # In a real implementation, you would calculate daily/weekly profit trends
    labels = []
    data = []
    
    for i in range(days // 7):  # Weekly data
        week_start = datetime.utcnow() - timedelta(weeks=i+1)
        labels.insert(0, week_start.strftime('%d/%m'))
        
        # Sample calculation - replace with real profit calculation
        if current_user.is_manager():
            week_profit = db.session.query(func.avg(Product.gross_profit)).filter(
                Product.created_at >= week_start,
                Product.created_at < week_start + timedelta(weeks=1),
                Product.gross_profit.isnot(None),
                Product.is_active == True
            ).scalar() or 0
        else:
            week_profit = db.session.query(func.avg(Product.gross_profit)).filter(
                Product.created_at >= week_start,
                Product.created_at < week_start + timedelta(weeks=1),
                Product.gross_profit.isnot(None),
                Product.is_active == True,
                Product.created_by == current_user.id
            ).scalar() or 0
        
        data.insert(0, round(week_profit, 2))
    
    return jsonify({
        'labels': labels,
        'data': data
    })

@bp.route('/analytics/category-costs')
@login_required
def category_costs_data():
    """API endpoint for category cost distribution"""
    
    # Calculate average cost per category
    category_costs = db.session.query(
        Ingredient.category,
        func.avg(Ingredient.price_per_unit).label('avg_cost'),
        func.count(ProductIngredient.id).label('usage_count')
    ).join(ProductIngredient).join(Product)
    
    if not current_user.is_manager():
        category_costs = category_costs.filter(Product.created_by == current_user.id)
    
    category_costs = category_costs.filter(
        Product.is_active == True,
        Ingredient.is_active == True
    ).group_by(Ingredient.category).all()
    
    return jsonify({
        'labels': [cat.category.replace('_', ' ').title() for cat in category_costs],
        'costs': [round(float(cat.avg_cost), 3) for cat in category_costs],
        'usage': [cat.usage_count for cat in category_costs]
    })