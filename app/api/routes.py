from flask import jsonify, request
from flask_login import login_required, current_user
from app.api import bp
from app.models import Ingredient, Product, ProductIngredient
from app.auth.decorators import manager_required
from app import db
import json

@bp.route('/ingredients')
@login_required
def get_ingredients():
    """Get all active ingredients for API consumption"""
    category = request.args.get('category')
    search = request.args.get('search', '')
    
    query = Ingredient.query.filter_by(is_active=True)
    
    if category:
        query = query.filter_by(category=category)
    
    if search:
        query = query.filter(Ingredient.name.ilike(f'%{search}%'))
    
    ingredients = query.order_by(Ingredient.name).all()
    
    return jsonify([{
        'id': ing.id,
        'name': ing.name,
        'category': ing.category,
        'food_paper_cost': float(ing.food_paper_cost) if ing.food_paper_cost else 0,
        'wrin_code': ing.wrin_code
    } for ing in ingredients])

@bp.route('/ingredients/categories')
@login_required
def get_ingredient_categories():
    """Get all ingredient categories"""
    categories = db.session.query(Ingredient.category).filter_by(is_active=True).distinct().all()
    return jsonify([cat[0] for cat in categories])

@bp.route('/products/<int:product_id>/cost')
@login_required
def calculate_product_cost(product_id):
    """Calculate and return cost for a specific product"""
    product = Product.query.get_or_404(product_id)
    
    # Ensure user owns this product or is manager/admin
    if product.created_by != current_user.id and not current_user.is_manager():
        return jsonify({'error': 'Unauthorized'}), 403
    
    return jsonify({
        'product_id': product.id,
        'food_paper_cost': float(product.food_paper_cost_total)
    })

@bp.route('/products', methods=['POST'])
@login_required
def create_product():
    """Create a new product via API"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    required_fields = ['name', 'ingredients']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    try:
        # Create product
        product = Product(
            name=data['name'],
            product_code=data.get('product_code', f"PROD_{current_user.id}_{db.session.query(Product).count() + 1}"),
            product_type=data.get('product_type', 'product'),
            food_paper_cost_total=data.get('food_paper_cost_total', 0),
            created_by=current_user.id
        )
        
        db.session.add(product)
        db.session.flush()  # Get the product ID
        
        # Add ingredients
        for ing_data in data['ingredients']:
            ingredient_id = ing_data.get('ingredient_id')
            quantity = ing_data.get('quantity', 1)
            
            ingredient = Ingredient.query.get(ingredient_id)
            if not ingredient:
                return jsonify({'error': f'Ingredient with ID {ingredient_id} not found'}), 400
            
            product_ingredient = ProductIngredient(
                product_id=product.id,
                ingredient_id=ingredient_id,
                quantity=quantity
            )
            db.session.add(product_ingredient)
        
        db.session.commit()
        
        return jsonify({
            'id': product.id,
            'name': product.name,
            'product_code': product.product_code,
            'food_paper_cost': float(product.food_paper_cost_total)
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/products/<int:product_id>', methods=['PUT'])
@login_required
def update_product(product_id):
    """Update an existing product via API"""
    product = Product.query.get_or_404(product_id)
    
    # Check permissions
    if product.created_by != current_user.id and not current_user.is_manager():
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    try:
        # Update basic fields
        if 'name' in data:
            product.name = data['name']
        
        # Update ingredients if provided
        if 'ingredients' in data:
            # Remove existing ingredients
            ProductIngredient.query.filter_by(product_id=product.id).delete()
            
            # Add new ingredients
            for ing_data in data['ingredients']:
                ingredient_id = ing_data.get('ingredient_id')
                quantity = ing_data.get('quantity', 1)
                
                ingredient = Ingredient.query.get(ingredient_id)
                if not ingredient:
                    return jsonify({'error': f'Ingredient with ID {ingredient_id} not found'}), 400
                
                product_ingredient = ProductIngredient(
                    product_id=product.id,
                    ingredient_id=ingredient_id,
                    quantity=quantity
                )
                db.session.add(product_ingredient)
        
        db.session.commit()
        
        return jsonify({
            'id': product.id,
            'name': product.name,
            'food_paper_cost': float(product.food_paper_cost_total)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/analytics/profit-trend')
@login_required
def profit_trend():
    """Get profit trend data for charts"""
    days = request.args.get('days', 30, type=int)
    
    # This would require more complex date aggregation
    # For now, return sample data structure
    return jsonify({
        'labels': ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
        'data': [150.5, 200.3, 175.8, 220.1]
    })

@bp.route('/analytics/category-distribution')
@login_required
def category_distribution():
    """Get ingredient category distribution for pie charts"""
    categories = db.session.query(
        Ingredient.category,
        db.func.count(ProductIngredient.id).label('usage_count')
    ).join(ProductIngredient).join(Product).filter(
        Product.is_active == True,
        Ingredient.is_active == True
    ).group_by(Ingredient.category).all()
    
    return jsonify({
        'labels': [cat.category for cat in categories],
        'data': [cat.usage_count for cat in categories]
    })

@bp.route('/validate-wrin-code', methods=['POST'])
@login_required
def validate_wrin_code():
    """Validate if WRIN code already exists"""
    data = request.get_json()
    
    if not data or 'wrin_code' not in data:
        return jsonify({'error': 'WRIN code is required'}), 400
    
    wrin_code = data['wrin_code'].strip()
    if not wrin_code:
        return jsonify({'exists': False})
    
    # Check if WRIN code already exists
    existing = Ingredient.query.filter_by(wrin_code=wrin_code).first()
    
    return jsonify({'exists': existing is not None})

@bp.route('/validate-product-code', methods=['POST'])
@login_required
def validate_product_code():
    """Validate if product code already exists"""
    data = request.get_json()
    
    if not data or 'product_code' not in data:
        return jsonify({'error': 'Product code is required'}), 400
    
    product_code = data['product_code'].strip()
    if not product_code:
        return jsonify({'exists': False})
    
    # Check if product code already exists
    existing = Product.query.filter_by(product_code=product_code).first()
    
    return jsonify({'exists': existing is not None})