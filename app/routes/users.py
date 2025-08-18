from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.routes import bp
from app.models import User, Product, Ingredient
from app.auth.decorators import admin_required
from app.auth.forms import RegistrationForm
from app import db
from datetime import datetime

@bp.route('/users')
@admin_required
def users():
    """List all users (admin only)"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    role_filter = request.args.get('role', '', type=str)
    per_page = 20
    
    query = User.query
    
    if search:
        query = query.filter(User.username.ilike(f'%{search}%'))
    
    if role_filter:
        query = query.filter_by(role=role_filter)
    
    users = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Get user statistics
    user_stats = {}
    for user in users.items:
        products_count = Product.query.filter_by(created_by=user.id, is_active=True).count()
        ingredients_count = Ingredient.query.filter_by(created_by=user.id, is_active=True).count()
        
        user_stats[user.id] = {
            'products': products_count,
            'ingredients': ingredients_count
        }
    
    return render_template('users/list.html', 
                         users=users, 
                         search=search, 
                         role_filter=role_filter,
                         user_stats=user_stats)

@bp.route('/users/<int:id>')
@admin_required
def user_detail(id):
    """View user details (admin only)"""
    user = User.query.get_or_404(id)
    
    # Get user's products and ingredients
    products = Product.query.filter_by(created_by=user.id, is_active=True).limit(10).all()
    ingredients = Ingredient.query.filter_by(created_by=user.id, is_active=True).limit(10).all()
    
    # Calculate user statistics
    total_products = Product.query.filter_by(created_by=user.id, is_active=True).count()
    total_ingredients = Ingredient.query.filter_by(created_by=user.id, is_active=True).count()
    
    # Calculate total profit from user's products
    total_profit = db.session.query(db.func.sum(Product.gross_profit)).filter(
        Product.created_by == user.id,
        Product.gross_profit.isnot(None),
        Product.is_active == True
    ).scalar() or 0
    
    user_data = {
        'user': user,
        'products': products,
        'ingredients': ingredients,
        'stats': {
            'total_products': total_products,
            'total_ingredients': total_ingredients,
            'total_profit': round(total_profit, 2)
        }
    }
    
    return render_template('users/detail.html', **user_data)

@bp.route('/users/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_user(id):
    """Edit user details (admin only)"""
    user = User.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            user.username = request.form['username']
            user.email = request.form.get('email')
            user.role = request.form['role']
            user.is_active = 'is_active' in request.form
            
            # Check if username is unique (excluding current user)
            existing_user = User.query.filter(
                User.username == user.username,
                User.id != user.id
            ).first()
            
            if existing_user:
                flash('Username già in uso da un altro utente.', 'error')
                return render_template('users/edit.html', user=user)
            
            db.session.commit()
            flash(f'Utente {user.username} aggiornato con successo!', 'success')
            return redirect(url_for('main.user_detail', id=user.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Errore durante l\'aggiornamento: {str(e)}', 'error')
    
    return render_template('users/edit.html', user=user)

@bp.route('/users/<int:id>/toggle-status', methods=['POST'])
@admin_required
def toggle_user_status(id):
    """Toggle user active status (admin only)"""
    user = User.query.get_or_404(id)
    
    # Prevent admin from deactivating themselves
    if user.id == current_user.id:
        flash('Non puoi disattivare il tuo stesso account.', 'error')
        return redirect(url_for('main.users'))
    
    try:
        user.is_active = not user.is_active
        db.session.commit()
        
        status = 'attivato' if user.is_active else 'disattivato'
        flash(f'Utente {user.username} {status} con successo!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Errore durante il cambio di stato: {str(e)}', 'error')
    
    return redirect(url_for('main.users'))

@bp.route('/users/<int:id>/reset-password', methods=['POST'])
@admin_required
def reset_user_password(id):
    """Reset user password (admin only)"""
    user = User.query.get_or_404(id)
    
    try:
        # Set a temporary password
        new_password = f"temp_{user.username}_123"
        user.set_password(new_password)
        db.session.commit()
        
        flash(f'Password resetata per {user.username}. Nuova password: {new_password}', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Errore durante il reset della password: {str(e)}', 'error')
    
    return redirect(url_for('main.user_detail', id=user.id))

@bp.route('/users/stats')
@admin_required
def users_stats():
    """Get user statistics for API"""
    
    # Users by role
    role_stats = db.session.query(
        User.role,
        db.func.count(User.id).label('count')
    ).filter_by(is_active=True).group_by(User.role).all()
    
    # Users registration over time (last 6 months)
    six_months_ago = datetime.utcnow().replace(day=1) - timedelta(days=180)
    
    monthly_registrations = db.session.query(
        db.func.date_trunc('month', User.created_at).label('month'),
        db.func.count(User.id).label('count')
    ).filter(
        User.created_at >= six_months_ago
    ).group_by(
        db.func.date_trunc('month', User.created_at)
    ).order_by('month').all()
    
    # Most active users (by products created)
    active_users = db.session.query(
        User.username,
        db.func.count(Product.id).label('products_count')
    ).join(Product).filter(
        User.is_active == True,
        Product.is_active == True
    ).group_by(User.id, User.username).order_by(
        db.func.count(Product.id).desc()
    ).limit(5).all()
    
    return jsonify({
        'role_distribution': [{'role': stat.role, 'count': stat.count} for stat in role_stats],
        'monthly_registrations': [
            {'month': stat.month.strftime('%Y-%m'), 'count': stat.count} 
            for stat in monthly_registrations
        ],
        'active_users': [
            {'username': stat.username, 'products': stat.products_count} 
            for stat in active_users
        ]
    })