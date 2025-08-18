from flask import render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, current_user
from app.auth import bp
from app.auth.forms import LoginForm, RegistrationForm, ChangePasswordForm, ProfileForm
from app.auth.decorators import admin_required, login_required
from app.models import User
from app import db
from datetime import datetime
import logging

# Set up logging for authentication events
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    # Redirect if already logged in
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        # Find user by username
        user = User.query.filter_by(username=form.username.data).first()
        
        # Check if user exists and password is correct
        if user and user.check_password(form.password.data):
            # Check if user is active
            if not user.is_active:
                flash('Il tuo account è stato disattivato. Contatta un amministratore.', 'error')
                logger.warning(f'Login attempt for deactivated user: {form.username.data}')
                return render_template('auth/login.html', form=form)
            
            # Log the user in
            login_user(user, remember=form.remember_me.data)
            
            # Update last login time
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            # Log successful login
            logger.info(f'Successful login for user: {user.username}')
            
            # Redirect to next page or dashboard
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('main.dashboard')
            
            flash(f'Bentornato, {user.username}!', 'success')
            return redirect(next_page)
        else:
            # Log failed login attempt
            logger.warning(f'Failed login attempt for username: {form.username.data}')
            flash('Username o password non validi', 'error')
    
    return render_template('auth/login.html', form=form)

@bp.route('/logout')
@login_required
def logout():
    username = current_user.username
    logout_user()
    session.clear()
    logger.info(f'User logged out: {username}')
    flash('Logout eseguito con successo.', 'info')
    return redirect(url_for('auth.login'))

@bp.route('/register', methods=['GET', 'POST'])
@admin_required
def register():
    form = RegistrationForm()
    
    if form.validate_on_submit():
        # Create new user
        user = User(
            username=form.username.data,
            email=form.email.data,
            role=form.role.data,
            is_active=True
        )
        user.set_password(form.password.data)
        
        try:
            db.session.add(user)
            db.session.commit()
            
            logger.info(f'New user registered: {user.username} with role: {user.role}')
            flash(f'User {user.username} has been registered successfully!', 'success')
            return redirect(url_for('main.users'))
        except Exception as e:
            db.session.rollback()
            logger.error(f'Error registering user: {str(e)}')
            flash('An error occurred while registering the user. Please try again.', 'error')
    
    return render_template('auth/register.html', form=form)

@bp.route('/profile')
@login_required
def profile():
    return render_template('auth/profile.html')

@bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = ProfileForm(current_user.username, current_user.email)
    
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.email = form.email.data
        
        try:
            db.session.commit()
            logger.info(f'Profile updated for user: {current_user.username}')
            flash('Your profile has been updated successfully!', 'success')
            return redirect(url_for('auth.profile'))
        except Exception as e:
            db.session.rollback()
            logger.error(f'Error updating profile: {str(e)}')
            flash('An error occurred while updating your profile. Please try again.', 'error')
    
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    
    return render_template('auth/edit_profile.html', form=form)

@bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    
    if form.validate_on_submit():
        # Verify current password
        if not current_user.check_password(form.current_password.data):
            flash('Current password is incorrect.', 'error')
            return render_template('auth/change_password.html', form=form)
        
        # Update password
        current_user.set_password(form.new_password.data)
        
        try:
            db.session.commit()
            logger.info(f'Password changed for user: {current_user.username}')
            flash('Your password has been changed successfully!', 'success')
            return redirect(url_for('auth.profile'))
        except Exception as e:
            db.session.rollback()
            logger.error(f'Error changing password: {str(e)}')
            flash('An error occurred while changing your password. Please try again.', 'error')
    
    return render_template('auth/change_password.html', form=form)