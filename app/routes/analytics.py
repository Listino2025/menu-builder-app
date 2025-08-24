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
    
    # Average F&P cost calculation
    if current_user.is_manager():
        avg_fp_cost = db.session.query(func.avg(Product.food_paper_cost_total)).filter(
            Product.is_active == True,
            Product.food_paper_cost_total.isnot(None)
        ).scalar() or 0
    else:
        avg_fp_cost = db.session.query(func.avg(Product.food_paper_cost_total)).filter(
            Product.is_active == True,
            Product.created_by == current_user.id,
            Product.food_paper_cost_total.isnot(None)
        ).scalar() or 0
    
    # Most expensive products by F&P cost
    if current_user.is_manager():
        top_products = Product.query.filter(
            Product.is_active == True,
            Product.food_paper_cost_total.isnot(None)
        ).order_by(Product.food_paper_cost_total.desc()).limit(10).all()
    else:
        top_products = Product.query.filter(
            Product.is_active == True,
            Product.created_by == current_user.id,
            Product.food_paper_cost_total.isnot(None)
        ).order_by(Product.food_paper_cost_total.desc()).limit(10).all()
    
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
        'avg_fp_cost': round(avg_fp_cost, 2) if avg_fp_cost else 0,
        'top_products': top_products,
        'category_data': category_data,
        'recent_activity': recent_activity
    }
    
    return render_template('analytics/dashboard.html', data=analytics_data)

@bp.route('/analytics/fp-cost-trend')
@login_required
def fp_cost_trend_data():
    """API endpoint for F&P cost trend chart data"""
    days = request.args.get('days', 30, type=int)
    
    # Calculate weekly F&P cost trends
    labels = []
    data = []
    
    for i in range(days // 7):  # Weekly data
        week_start = datetime.utcnow() - timedelta(weeks=i+1)
        week_end = week_start + timedelta(weeks=1)
        labels.insert(0, week_start.strftime('%d/%m'))
        
        # Calculate average F&P cost for products created in this week
        if current_user.is_manager():
            week_avg_fp_cost = db.session.query(func.avg(Product.food_paper_cost_total)).filter(
                Product.created_at >= week_start,
                Product.created_at < week_end,
                Product.is_active == True,
                Product.food_paper_cost_total.isnot(None)
            ).scalar() or 0
        else:
            week_avg_fp_cost = db.session.query(func.avg(Product.food_paper_cost_total)).filter(
                Product.created_at >= week_start,
                Product.created_at < week_end,
                Product.is_active == True,
                Product.created_by == current_user.id,
                Product.food_paper_cost_total.isnot(None)
            ).scalar() or 0
        
        data.insert(0, round(week_avg_fp_cost, 2))
    
    return jsonify({
        'labels': labels,
        'data': data
    })

@bp.route('/analytics/category-costs')
@login_required
def category_costs_data():
    """API endpoint for category cost distribution"""
    
    # Calculate average F&P cost per category
    category_costs = db.session.query(
        Ingredient.category,
        func.avg(Ingredient.food_paper_cost).label('avg_fp_cost'),
        func.count(ProductIngredient.id).label('usage_count')
    ).join(ProductIngredient).join(Product)
    
    if not current_user.is_manager():
        category_costs = category_costs.filter(Product.created_by == current_user.id)
    
    category_costs = category_costs.filter(
        Product.is_active == True,
        Ingredient.is_active == True,
        Ingredient.food_paper_cost.isnot(None)
    ).group_by(Ingredient.category).all()
    
    return jsonify({
        'labels': [cat.category.replace('_', ' ').title() for cat in category_costs],
        'costs': [round(float(cat.avg_fp_cost), 3) if cat.avg_fp_cost else 0 for cat in category_costs],
        'usage': [cat.usage_count for cat in category_costs]
    })