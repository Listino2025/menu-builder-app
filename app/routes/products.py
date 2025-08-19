from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.routes import bp
from app.models import Product, Ingredient, ProductIngredient
from app.auth.decorators import manager_required
from app import db
from sqlalchemy import or_

@bp.route('/products')
@login_required
def products():
    """List all products with search and filter capabilities"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    product_type = request.args.get('type', '', type=str)
    sort_by = request.args.get('sort', 'created_at', type=str)
    order = request.args.get('order', 'desc', type=str)
    per_page = 20
    
    query = Product.query.filter_by(is_active=True)
    
    # Filter by creator for non-managers
    if not current_user.is_manager():
        query = query.filter_by(created_by=current_user.id)
    
    if search:
        query = query.filter(or_(
            Product.name.ilike(f'%{search}%'),
            Product.product_code.ilike(f'%{search}%')
        ))
    
    if product_type:
        query = query.filter_by(product_type=product_type)
    
    # Sorting
    if sort_by == 'name':
        query = query.order_by(Product.name.desc() if order == 'desc' else Product.name.asc())
    elif sort_by == 'cost':
        query = query.order_by(Product.total_cost.desc() if order == 'desc' else Product.total_cost.asc())
    elif sort_by == 'profit':
        query = query.order_by(Product.gross_profit.desc() if order == 'desc' else Product.gross_profit.asc())
    else:  # created_at
        query = query.order_by(Product.created_at.desc() if order == 'desc' else Product.created_at.asc())
    
    products = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('products/list.html', 
                         products=products, 
                         search=search, 
                         product_type=product_type,
                         sort_by=sort_by,
                         order=order)

@bp.route('/products/<int:id>')
@login_required
def product_detail(id):
    """View product details"""
    product = Product.query.get_or_404(id)
    
    # Check permissions
    if not current_user.is_manager() and product.created_by != current_user.id:
        flash('You do not have permission to view this product.', 'error')
        return redirect(url_for('main.products'))
    
    return render_template('products/detail.html', product=product)

@bp.route('/products/sandwich/new', methods=['GET', 'POST'])
@login_required
def create_sandwich():
    """Create a new sandwich"""
    if request.method == 'POST':
        try:
            # Generate product code
            product_count = Product.query.filter_by(created_by=current_user.id).count()
            product_code = f"SW_{current_user.id}_{product_count + 1}"
            
            # Validate required fields
            required_fields = ['name', 'product_code_id', 'restaurant_id', 'delivery_price_id', 'selling_price', 'food_paper_cost_total']
            for field in required_fields:
                if not request.form.get(field) or request.form.get(field).strip() == '':
                    flash(f'Il campo "{field.replace("_", " ").title()}" è obbligatorio.', 'error')
                    return redirect(request.url)
            
            # Create product with new mandatory fields
            product = Product(
                name=request.form['name'],
                product_code=request.form.get('product_code_id', product_code),  # Use provided ID or generated one
                product_type='sandwich',
                selling_price=float(request.form['selling_price']),
                restaurant_id=request.form['restaurant_id'],
                delivery_price_id=request.form['delivery_price_id'],
                food_paper_cost_total=float(request.form['food_paper_cost_total']),
                created_by=current_user.id
            )
            
            db.session.add(product)
            db.session.flush()  # Get the product ID
            
            # Add ingredients from form
            ingredient_ids = request.form.getlist('ingredient_ids[]')
            quantities = request.form.getlist('quantities[]')
            
            if not ingredient_ids:
                flash('Please select at least one ingredient.', 'error')
                return redirect(request.url)
            
            for i, ingredient_id in enumerate(ingredient_ids):
                if ingredient_id:  # Skip empty values
                    from decimal import Decimal
                    quantity_str = quantities[i] if i < len(quantities) and quantities[i] else '1.0'
                    quantity = Decimal(str(quantity_str))
                    
                    product_ingredient = ProductIngredient(
                        product_id=product.id,
                        ingredient_id=int(ingredient_id),
                        quantity=quantity
                    )
                    db.session.add(product_ingredient)
            
            # Calculate costs
            product.calculate_costs()
            db.session.commit()
            
            flash(f'Sandwich "{product.name}" created successfully!', 'success')
            return redirect(url_for('main.product_detail', id=product.id))
            
        except ValueError as e:
            flash('Invalid number format. Please check your inputs.', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating sandwich: {str(e)}', 'error')
    
    # Get ingredients for the composer
    ingredients = Ingredient.query.filter_by(is_active=True).order_by(Ingredient.category, Ingredient.name).all()
    
    # Group ingredients by category
    ingredients_by_category = {}
    for ingredient in ingredients:
        if ingredient.category not in ingredients_by_category:
            ingredients_by_category[ingredient.category] = []
        ingredients_by_category[ingredient.category].append(ingredient)
    
    return render_template('products/create_sandwich.html', 
                         ingredients_by_category=ingredients_by_category)

@bp.route('/products/menu/new', methods=['GET', 'POST'])
@login_required
def create_menu():
    """Create a new menu"""
    if request.method == 'POST':
        try:
            # Generate product code
            product_count = Product.query.filter_by(created_by=current_user.id).count()
            product_code = f"MN_{current_user.id}_{product_count + 1}"
            
            # Validate required fields for menu
            menu_required_fields = ['name', 'product_code_id', 'restaurant_id', 'delivery_price_id', 'selling_price', 'food_paper_cost_total']
            for field in menu_required_fields:
                if not request.form.get(field) or request.form.get(field).strip() == '':
                    flash(f'Il campo "{field.replace("_", " ").title()}" è obbligatorio.', 'error')
                    return redirect(request.url)
            
            # Create menu product with new mandatory fields
            from decimal import Decimal
            selling_price = request.form.get('selling_price')
            selling_price_decimal = Decimal(str(selling_price)) if selling_price and selling_price.strip() else None
            
            menu = Product(
                name=request.form['name'],
                product_code=request.form.get('product_code_id', product_code),
                product_type='menu',
                selling_price=selling_price_decimal,
                sandwich_id=int(request.form['sandwich_id']) if request.form.get('sandwich_id') else None,
                fries_size=request.form.get('fries_size'),
                drink_size=request.form.get('drink_size'),
                restaurant_id=request.form['restaurant_id'],
                delivery_price_id=request.form['delivery_price_id'],
                food_paper_cost_total=Decimal(str(request.form['food_paper_cost_total'])),
                created_by=current_user.id
            )
            
            db.session.add(menu)
            db.session.flush()
            
            # Calculate total cost (sandwich + fries + drink)
            total_cost = Decimal('0')
            
            # Add sandwich cost
            if menu.sandwich_id:
                sandwich = Product.query.get(menu.sandwich_id)
                if sandwich and sandwich.total_cost:
                    total_cost += sandwich.total_cost
            
            # Add fries cost (predefined prices)
            fries_prices = {'small': Decimal('2.50'), 'medium': Decimal('3.00'), 'large': Decimal('3.50')}
            if menu.fries_size and menu.fries_size in fries_prices:
                total_cost += fries_prices[menu.fries_size]
            
            # Add drink cost (predefined prices)
            drink_prices = {'small': Decimal('1.50'), 'medium': Decimal('2.00'), 'large': Decimal('2.50')}
            if menu.drink_size and menu.drink_size in drink_prices:
                total_cost += drink_prices[menu.drink_size]
            
            menu.total_cost = total_cost
            
            # Calculate profit for menu (don't use calculate_costs as it would override total_cost)
            if menu.selling_price:
                menu.gross_profit = menu.selling_price - total_cost
                menu.gross_profit_percent = (menu.gross_profit / menu.selling_price * 100) if menu.selling_price > 0 else Decimal('0')
            
            db.session.commit()
            
            flash(f'Menu "{menu.name}" created successfully!', 'success')
            return redirect(url_for('main.product_detail', id=menu.id))
            
        except ValueError as e:
            flash('Invalid number format. Please check your inputs.', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating menu: {str(e)}', 'error')
    
    # Get available sandwiches for the menu
    sandwiches = Product.query.filter_by(
        product_type='sandwich', 
        is_active=True,
        created_by=current_user.id
    ).order_by(Product.name).all()
    
    return render_template('products/create_menu.html', sandwiches=sandwiches)

@bp.route('/products/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_product(id):
    """Edit an existing product"""
    product = Product.query.get_or_404(id)
    
    # Check permissions
    if not current_user.is_manager() and product.created_by != current_user.id:
        flash('You do not have permission to edit this product.', 'error')
        return redirect(url_for('main.products'))
    
    if request.method == 'POST':
        try:
            product.name = request.form['name']
            
            if request.form.get('selling_price'):
                product.selling_price = float(request.form['selling_price'])
            
            # Handle sandwich-specific updates
            if product.product_type == 'sandwich':
                # Update ingredients
                ProductIngredient.query.filter_by(product_id=product.id).delete()
                
                ingredient_ids = request.form.getlist('ingredient_ids[]')
                quantities = request.form.getlist('quantities[]')
                
                for i, ingredient_id in enumerate(ingredient_ids):
                    if ingredient_id:
                        quantity = float(quantities[i]) if i < len(quantities) and quantities[i] else 1.0
                        
                        product_ingredient = ProductIngredient(
                            product_id=product.id,
                            ingredient_id=int(ingredient_id),
                            quantity=quantity
                        )
                        db.session.add(product_ingredient)
            
            # Handle menu-specific updates
            elif product.product_type == 'menu':
                if request.form.get('sandwich_id'):
                    product.sandwich_id = int(request.form['sandwich_id'])
                product.fries_size = request.form.get('fries_size')
                product.drink_size = request.form.get('drink_size')
            
            # Recalculate costs
            product.calculate_costs()
            db.session.commit()
            
            flash(f'{product.product_type.title()} "{product.name}" updated successfully!', 'success')
            return redirect(url_for('main.product_detail', id=product.id))
            
        except ValueError as e:
            flash('Invalid number format. Please check your inputs.', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating product: {str(e)}', 'error')
    
    # Prepare data for edit form
    context = {'product': product}
    
    if product.product_type == 'sandwich':
        ingredients = Ingredient.query.filter_by(is_active=True).order_by(Ingredient.category, Ingredient.name).all()
        ingredients_by_category = {}
        for ingredient in ingredients:
            if ingredient.category not in ingredients_by_category:
                ingredients_by_category[ingredient.category] = []
            ingredients_by_category[ingredient.category].append(ingredient)
        context['ingredients_by_category'] = ingredients_by_category
        
        # Get current ingredients with quantities
        current_ingredients = {}
        for pi in product.ingredients:
            current_ingredients[pi.ingredient_id] = float(pi.quantity)
        context['current_ingredients'] = current_ingredients
        
    elif product.product_type == 'menu':
        sandwiches = Product.query.filter_by(
            product_type='sandwich', 
            is_active=True,
            created_by=current_user.id
        ).order_by(Product.name).all()
        context['sandwiches'] = sandwiches
    
    return render_template(f'products/edit_{product.product_type}.html', **context)

@bp.route('/products/<int:id>/delete', methods=['POST'])
@bp.route('/products/<int:id>', methods=['DELETE'])
@login_required
def delete_product(id):
    """Soft delete a product"""
    product = Product.query.get_or_404(id)
    
    # Check permissions
    if not current_user.is_manager() and product.created_by != current_user.id:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Non hai i permessi per eliminare questo prodotto.'}), 403
        flash('Non hai i permessi per eliminare questo prodotto.', 'error')
        return redirect(url_for('main.products'))
    
    try:
        # Check if this sandwich is used in any menus
        if product.product_type == 'sandwich':
            menus_using_sandwich = Product.query.filter_by(sandwich_id=product.id, is_active=True).count()
            if menus_using_sandwich > 0:
                error_msg = f'Impossibile eliminare "{product.name}" - è utilizzato in {menus_using_sandwich} menu.'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': error_msg}), 400
                flash(error_msg, 'error')
                return redirect(url_for('main.products'))
        
        # Soft delete the product
        product.is_active = False
        db.session.commit()
        
        success_msg = f'{product.product_type.title()} "{product.name}" eliminato con successo!'
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True, 
                'message': success_msg,
                'product_type': product.product_type,
                'redirect_url': url_for('main.products')
            })
        
        flash(success_msg, 'success')
        return redirect(url_for('main.products'))
        
    except Exception as e:
        db.session.rollback()
        error_msg = f'Errore durante l\'eliminazione del prodotto: {str(e)}'
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': error_msg}), 500
        
        flash(error_msg, 'error')
        return redirect(url_for('main.products'))

@bp.route('/products/<int:id>/duplicate', methods=['POST'])
@login_required
def duplicate_product(id):
    """Duplicate an existing product"""
    original = Product.query.get_or_404(id)
    
    # Check permissions
    if not current_user.is_manager() and original.created_by != current_user.id:
        flash('You do not have permission to duplicate this product.', 'error')
        return redirect(url_for('main.products'))
    
    try:
        # Generate unique product code for duplicate
        product_count = Product.query.filter_by(created_by=current_user.id).count()
        prefix = "SW" if original.product_type == 'sandwich' else "MN"
        attempts = 0
        max_attempts = 10
        product_code = None
        
        while attempts < max_attempts:
            product_code = f"{prefix}_{current_user.id}_{product_count + 1 + attempts}"
            existing_product = Product.query.filter_by(product_code=product_code).first()
            if not existing_product:
                break
            attempts += 1
        
        if attempts >= max_attempts:
            flash('Unable to generate unique product code for duplicate. Please try again.', 'error')
            return redirect(url_for('main.products'))
        
        # Create duplicate
        duplicate = Product(
            name=f"{original.name} (Copy)",
            product_code=product_code,
            product_type=original.product_type,
            selling_price=original.selling_price,
            sandwich_id=original.sandwich_id,
            fries_size=original.fries_size,
            drink_size=original.drink_size,
            created_by=current_user.id
        )
        
        db.session.add(duplicate)
        db.session.flush()
        
        # Copy ingredients for sandwiches
        if original.product_type == 'sandwich':
            for pi in original.ingredients:
                duplicate_ingredient = ProductIngredient(
                    product_id=duplicate.id,
                    ingredient_id=pi.ingredient_id,
                    quantity=pi.quantity
                )
                db.session.add(duplicate_ingredient)
        
        # Calculate costs
        duplicate.calculate_costs()
        db.session.commit()
        
        flash(f'{original.product_type.title()} duplicated successfully as "{duplicate.name}"!', 'success')
        return redirect(url_for('main.product_detail', id=duplicate.id))
        
    except Exception as e:
        db.session.rollback()
        if 'product_code' in str(e).lower() and 'unique' in str(e).lower():
            flash('Product code already exists. Please try again.', 'error')
        else:
            flash(f'Error duplicating product: {str(e)}', 'error')
        return redirect(url_for('main.products'))

@bp.route('/products/bulk-delete', methods=['POST'])
@login_required
def bulk_delete_products():
    """Bulk delete multiple products"""
    data = request.get_json()
    
    if not data or 'product_ids' not in data:
        return jsonify({'success': False, 'message': 'No product IDs provided'}), 400
    
    product_ids = data['product_ids']
    if not isinstance(product_ids, list) or not product_ids:
        return jsonify({'success': False, 'message': 'Invalid product IDs'}), 400
    
    try:
        deleted_count = 0
        skipped_count = 0
        error_messages = []
        
        for product_id in product_ids:
            try:
                product = Product.query.get(int(product_id))
                if not product:
                    error_messages.append(f'Product ID {product_id} not found')
                    continue
                
                # Check permissions
                if not current_user.is_manager() and product.created_by != current_user.id:
                    error_messages.append(f'No permission to delete "{product.name}"')
                    continue
                
                # Check if sandwich is used in menus
                if product.product_type == 'sandwich':
                    menus_using_sandwich = Product.query.filter_by(sandwich_id=product.id, is_active=True).count()
                    if menus_using_sandwich > 0:
                        error_messages.append(f'Cannot delete "{product.name}" - used in {menus_using_sandwich} menus')
                        skipped_count += 1
                        continue
                
                # Soft delete
                product.is_active = False
                deleted_count += 1
                
            except ValueError:
                error_messages.append(f'Invalid product ID: {product_id}')
            except Exception as e:
                error_messages.append(f'Error deleting product {product_id}: {str(e)}')
        
        db.session.commit()
        
        result = {
            'success': True,
            'deleted_count': deleted_count,
            'skipped_count': skipped_count,
            'total_requested': len(product_ids)
        }
        
        if error_messages:
            result['errors'] = error_messages
            result['message'] = f'Deleted {deleted_count} products. {len(error_messages)} errors occurred.'
        else:
            result['message'] = f'Successfully deleted {deleted_count} products.'
        
        return jsonify(result)
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False, 
            'message': f'Database error during bulk deletion: {str(e)}'
        }), 500

@bp.route('/products/restore/<int:id>', methods=['POST'])
@login_required
def restore_product(id):
    """Restore a soft-deleted product"""
    product = Product.query.get_or_404(id)
    
    # Check permissions
    if not current_user.is_manager() and product.created_by != current_user.id:
        return jsonify({'success': False, 'message': 'Non hai i permessi per ripristinare questo prodotto.'}), 403
    
    try:
        product.is_active = True
        db.session.commit()
        
        success_msg = f'{product.product_type.title()} "{product.name}" ripristinato con successo!'
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': success_msg})
        
        flash(success_msg, 'success')
        return redirect(url_for('main.products'))
        
    except Exception as e:
        db.session.rollback()
        error_msg = f'Errore durante il ripristino del prodotto: {str(e)}'
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': error_msg}), 500
        
        flash(error_msg, 'error')
        return redirect(url_for('main.products'))