from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Restaurant, ProductListing, Product
from sqlalchemy import text, func
from decimal import Decimal
import json
import csv
import io

bp = Blueprint('restaurant_mapping', __name__, url_prefix='/restaurant-mapping')

@bp.route('/')
@login_required
def index():
    """Restaurant mapping dashboard with map view and analytics"""
    restaurants = Restaurant.query.filter_by(is_active=True).all()
    
    # Get basic statistics
    stats = {
        'total_restaurants': len(restaurants),
        'total_products_listed': db.session.query(func.count(ProductListing.id)).scalar() or 0,
        'restaurants_with_coords': len([r for r in restaurants if r.get_coordinates()]),
        'avg_products_per_restaurant': 0
    }
    
    if stats['total_restaurants'] > 0:
        stats['avg_products_per_restaurant'] = round(stats['total_products_listed'] / stats['total_restaurants'], 1)
    
    # Use fixed Leaflet version with better error handling
    return render_template('restaurant_mapping/index_leaflet_fixed.html', 
                         restaurants=restaurants, 
                         stats=stats)

@bp.route('/restaurants')
@login_required 
def restaurants():
    """Manage restaurants list"""
    restaurants = Restaurant.query.order_by(Restaurant.name).all()
    return render_template('restaurant_mapping/restaurants.html', restaurants=restaurants)

@bp.route('/restaurants/create', methods=['GET', 'POST'])
@login_required
def create_restaurant():
    """Create new restaurant"""
    if not current_user.is_manager():
        flash('Accesso negato. Solo i manager possono creare ristoranti.', 'error')
        return redirect(url_for('restaurant_mapping.restaurants'))
    
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form['name'].strip()
            address = request.form['address'].strip()
            city = request.form['city'].strip()
            postal_code = request.form.get('postal_code', '').strip() or None
            phone = request.form.get('phone', '').strip() or None
            email = request.form.get('email', '').strip() or None
            restaurant_code = request.form['restaurant_code'].strip()
            
            # Get coordinates
            latitude = request.form.get('latitude', '').strip()
            longitude = request.form.get('longitude', '').strip()
            
            latitude = Decimal(latitude) if latitude else None
            longitude = Decimal(longitude) if longitude else None
            
            # Parse opening hours JSON if provided
            opening_hours_json = request.form.get('opening_hours', '').strip()
            opening_hours = None
            if opening_hours_json:
                try:
                    opening_hours = json.loads(opening_hours_json)
                except json.JSONDecodeError:
                    flash('Formato orari di apertura non valido. Usare formato JSON.', 'error')
                    return render_template('restaurant_mapping/create_restaurant.html')
            
            # Validate required fields
            if not all([name, address, city, restaurant_code]):
                flash('Nome, indirizzo, città e codice ristorante sono obbligatori.', 'error')
                return render_template('restaurant_mapping/create_restaurant.html')
            
            # Check for duplicate restaurant code
            existing = Restaurant.query.filter_by(restaurant_code=restaurant_code).first()
            if existing:
                flash(f'Codice ristorante "{restaurant_code}" già esistente.', 'error')
                return render_template('restaurant_mapping/create_restaurant.html')
            
            # Create restaurant
            restaurant = Restaurant(
                name=name,
                address=address,
                city=city,
                postal_code=postal_code,
                latitude=latitude,
                longitude=longitude,
                phone=phone,
                email=email,
                opening_hours=opening_hours,
                restaurant_code=restaurant_code
            )
            
            db.session.add(restaurant)
            db.session.commit()
            
            flash(f'Ristorante "{name}" creato con successo!', 'success')
            return redirect(url_for('restaurant_mapping.restaurants'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Errore durante la creazione: {str(e)}', 'error')
            return render_template('restaurant_mapping/create_restaurant.html')
    
    return render_template('restaurant_mapping/create_restaurant.html')

@bp.route('/restaurants/<int:restaurant_id>')
@login_required
def restaurant_detail(restaurant_id):
    """View restaurant details and product listings"""
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    
    # Get ALL active products
    all_products = (Product.query
                   .filter(Product.is_active == True)
                   .order_by(Product.name)
                   .all())
    
    # Get existing listings for this restaurant (for pricing info)
    existing_listings = {l.product_id: l for l in 
                        ProductListing.query.filter_by(restaurant_id=restaurant_id).all()}
    
    # Create combined product list with pricing info
    products_with_pricing = []
    for product in all_products:
        listing = existing_listings.get(product.id)
        products_with_pricing.append({
            'product': product,
            'listing': listing,  # None if no pricing set yet
            'has_pricing': listing is not None,
            'local_price': listing.local_price if listing else None,
            'delivery_price': listing.delivery_price if listing else None,
            'is_available': listing.is_available if listing else True
        })
    
    return render_template('restaurant_mapping/restaurant_detail.html',
                         restaurant=restaurant,
                         products_with_pricing=products_with_pricing)

@bp.route('/listings/save', methods=['POST'])
@login_required
def save_listing():
    """Create or update product listing for restaurant"""
    if not current_user.is_manager():
        return jsonify({'error': 'Accesso negato'}), 403
    
    try:
        data = request.get_json()
        restaurant_id = data['restaurant_id']
        product_id = data['product_id']
        local_price = Decimal(str(data['local_price']))
        delivery_price = Decimal(str(data['delivery_price']))
        is_available = data.get('is_available', True)
        
        # Validate restaurant and product exist
        restaurant = Restaurant.query.get_or_404(restaurant_id)
        product = Product.query.get_or_404(product_id)
        
        # Check if listing already exists
        existing = ProductListing.query.filter_by(
            restaurant_id=restaurant_id, 
            product_id=product_id
        ).first()
        
        if existing:
            # Update existing listing
            existing.local_price = local_price
            existing.delivery_price = delivery_price
            existing.is_available = is_available
            listing = existing
            action = 'updated'
        else:
            # Create new listing
            listing = ProductListing(
                restaurant_id=restaurant_id,
                product_id=product_id,
                local_price=local_price,
                delivery_price=delivery_price,
                is_available=is_available
            )
            db.session.add(listing)
            action = 'created'
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Listino {action} per {product.name}',
            'listing_id': listing.id,
            'action': action
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/comparison')
@login_required
def price_comparison():
    """Product price comparison across restaurants"""
    # Get all products with listings and their F&P costs
    products_query = text("""
        SELECT DISTINCT p.id, p.name, p.product_type, p.food_paper_cost_total,
               p.fries_fp_cost, p.drink_fp_cost
        FROM products p
        JOIN product_listings pl ON p.id = pl.product_id
        WHERE p.is_active = true
        ORDER BY p.name
    """)
    
    products = db.session.execute(products_query).fetchall()
    
    # Get comparison data
    comparison_data = []
    for product in products:
        # Calculate total F&P cost for this product
        total_fp_cost = float(product.food_paper_cost_total or 0)
        if product.product_type == 'menu':
            total_fp_cost += float(product.fries_fp_cost or 0) + float(product.drink_fp_cost or 0)
        
        listings_query = text("""
            SELECT r.id as restaurant_id, r.name as restaurant_name, r.city, 
                   pl.local_price, pl.delivery_price, pl.is_available
            FROM product_listings pl
            JOIN restaurants r ON pl.restaurant_id = r.id
            WHERE pl.product_id = :product_id AND r.is_active = true
            ORDER BY pl.local_price ASC
        """)
        
        raw_listings = db.session.execute(listings_query, {'product_id': product.id}).fetchall()
        
        # Add F&P cost to each listing
        listings = []
        for listing in raw_listings:
            listings.append({
                'restaurant_id': listing.restaurant_id,
                'restaurant_name': listing.restaurant_name,
                'city': listing.city,
                'local_price': float(listing.local_price),
                'delivery_price': float(listing.delivery_price),
                'is_available': listing.is_available,
                'total_fp_cost': total_fp_cost
            })
        
        if listings:
            prices = [l['local_price'] for l in listings if l['is_available']]
            comparison_data.append({
                'product': product,
                'listings': listings,
                'min_price': min(prices) if prices else 0,
                'max_price': max(prices) if prices else 0,
                'price_range': max(prices) - min(prices) if len(prices) > 1 else 0
            })
    
    # Get all restaurants for the filter dropdown
    restaurants = Restaurant.query.filter_by(is_active=True).order_by(Restaurant.name).all()
    
    return render_template('restaurant_mapping/price_comparison.html',
                         comparison_data=comparison_data,
                         restaurants=restaurants)

@bp.route('/api/restaurants-geojson')
@login_required
def restaurants_geojson():
    """Get restaurants data as GeoJSON for map display"""
    restaurants = Restaurant.query.filter_by(is_active=True).all()
    
    features = []
    for restaurant in restaurants:
        coords = restaurant.get_coordinates()
        if coords:
            feature = {
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [float(coords[1]), float(coords[0])]  # [lng, lat]
                },
                'properties': {
                    'id': restaurant.id,
                    'name': restaurant.name,
                    'address': restaurant.address,
                    'city': restaurant.city,
                    'phone': restaurant.phone,
                    'restaurant_code': restaurant.restaurant_code,
                    'is_open': restaurant.is_open_now(),
                    'listings_count': restaurant.product_listings.filter_by(is_available=True).count()
                }
            }
            features.append(feature)
    
    geojson = {
        'type': 'FeatureCollection',
        'features': features
    }
    
    return jsonify(geojson)

@bp.route('/api/restaurant-stats/<int:restaurant_id>')
@login_required
def restaurant_stats(restaurant_id):
    """Get statistics for specific restaurant"""
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    
    # Get listings statistics
    stats_query = text("""
        SELECT 
            COUNT(*) as total_products,
            COUNT(CASE WHEN is_available = true THEN 1 END) as available_products,
            AVG(local_price) as avg_local_price,
            AVG(delivery_price) as avg_delivery_price,
            AVG(delivery_price - local_price) as avg_markup
        FROM product_listings pl
        WHERE pl.restaurant_id = :restaurant_id
    """)
    
    stats = db.session.execute(stats_query, {'restaurant_id': restaurant_id}).fetchone()
    
    return jsonify({
        'restaurant_name': restaurant.name,
        'total_products': stats.total_products or 0,
        'available_products': stats.available_products or 0,
        'avg_local_price': float(stats.avg_local_price or 0),
        'avg_delivery_price': float(stats.avg_delivery_price or 0),
        'avg_markup': float(stats.avg_markup or 0)
    })

@bp.route('/import')
@login_required
def import_page():
    """Import restaurants and product listings from CSV"""
    if not current_user.is_manager():
        flash('Accesso negato. Solo i manager possono importare dati.', 'error')
        return redirect(url_for('restaurant_mapping.index'))
    
    return render_template('restaurant_mapping/import.html')

@bp.route('/import/restaurants', methods=['POST'])
@login_required
def import_restaurants():
    """Import restaurants from CSV file"""
    if not current_user.is_manager():
        return jsonify({'error': 'Accesso negato'}), 403
    
    if 'csv_file' not in request.files:
        return jsonify({'error': 'Nessun file selezionato'}), 400
    
    file = request.files['csv_file']
    if file.filename == '':
        return jsonify({'error': 'Nessun file selezionato'}), 400
    
    if not file.filename.lower().endswith('.csv'):
        return jsonify({'error': 'File deve essere in formato CSV'}), 400
    
    try:
        # Read CSV content
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_reader = csv.DictReader(stream)
        
        imported_count = 0
        errors = []
        
        # Expected columns for restaurants CSV
        required_columns = ['name', 'address', 'city', 'restaurant_code']
        optional_columns = ['postal_code', 'latitude', 'longitude', 'phone', 'email', 'opening_hours']
        
        # Validate CSV headers
        if not all(col in csv_reader.fieldnames for col in required_columns):
            missing_cols = [col for col in required_columns if col not in csv_reader.fieldnames]
            return jsonify({
                'error': f'Colonne obbligatorie mancanti: {", ".join(missing_cols)}',
                'required_columns': required_columns,
                'optional_columns': optional_columns
            }), 400
        
        for row_num, row in enumerate(csv_reader, start=2):  # Start from 2 (header = 1)
            try:
                # Validate required fields
                for col in required_columns:
                    if not row.get(col, '').strip():
                        errors.append(f'Riga {row_num}: Campo obbligatorio vuoto: {col}')
                        continue
                
                # Check if restaurant_code already exists
                existing = Restaurant.query.filter_by(restaurant_code=row['restaurant_code'].strip()).first()
                if existing:
                    errors.append(f'Riga {row_num}: Codice ristorante già esistente: {row["restaurant_code"]}')
                    continue
                
                # Parse coordinates if provided
                latitude = None
                longitude = None
                if row.get('latitude', '').strip() and row.get('longitude', '').strip():
                    try:
                        latitude = Decimal(str(row['latitude'].strip()))
                        longitude = Decimal(str(row['longitude'].strip()))
                    except (ValueError, TypeError):
                        errors.append(f'Riga {row_num}: Coordinate GPS non valide')
                        continue
                
                # Parse opening hours if provided
                opening_hours = None
                if row.get('opening_hours', '').strip():
                    try:
                        opening_hours = json.loads(row['opening_hours'].strip())
                    except json.JSONDecodeError:
                        errors.append(f'Riga {row_num}: Formato orari apertura non valido (deve essere JSON)')
                        continue
                
                # Create restaurant
                restaurant = Restaurant(
                    name=row['name'].strip(),
                    address=row['address'].strip(),
                    city=row['city'].strip(),
                    postal_code=row.get('postal_code', '').strip() or None,
                    latitude=latitude,
                    longitude=longitude,
                    phone=row.get('phone', '').strip() or None,
                    email=row.get('email', '').strip() or None,
                    opening_hours=opening_hours,
                    restaurant_code=row['restaurant_code'].strip()
                )
                
                db.session.add(restaurant)
                imported_count += 1
                
            except Exception as e:
                errors.append(f'Riga {row_num}: Errore durante l\'importazione: {str(e)}')
        
        if imported_count > 0:
            db.session.commit()
            
        return jsonify({
            'success': True,
            'imported_count': imported_count,
            'errors': errors,
            'message': f'Importati {imported_count} ristoranti con successo'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Errore durante l\'importazione: {str(e)}'}), 500

@bp.route('/import/product-listings', methods=['POST'])
@login_required
def import_product_listings():
    """Import product listings from CSV file"""
    if not current_user.is_manager():
        return jsonify({'error': 'Accesso negato'}), 403
    
    if 'csv_file' not in request.files:
        return jsonify({'error': 'Nessun file selezionato'}), 400
    
    file = request.files['csv_file']
    if file.filename == '':
        return jsonify({'error': 'Nessun file selezionato'}), 400
    
    if not file.filename.lower().endswith('.csv'):
        return jsonify({'error': 'File deve essere in formato CSV'}), 400
    
    try:
        # Read CSV content
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_reader = csv.DictReader(stream)
        
        imported_count = 0
        errors = []
        
        # Expected columns for product listings CSV
        required_columns = ['restaurant_code', 'product_name', 'local_price', 'delivery_price']
        optional_columns = ['is_available']
        
        # Validate CSV headers
        if not all(col in csv_reader.fieldnames for col in required_columns):
            missing_cols = [col for col in required_columns if col not in csv_reader.fieldnames]
            return jsonify({
                'error': f'Colonne obbligatorie mancanti: {", ".join(missing_cols)}',
                'required_columns': required_columns,
                'optional_columns': optional_columns
            }), 400
        
        for row_num, row in enumerate(csv_reader, start=2):  # Start from 2 (header = 1)
            try:
                # Validate required fields
                for col in required_columns:
                    if not row.get(col, '').strip():
                        errors.append(f'Riga {row_num}: Campo obbligatorio vuoto: {col}')
                        continue
                
                # Find restaurant by code
                restaurant = Restaurant.query.filter_by(restaurant_code=row['restaurant_code'].strip()).first()
                if not restaurant:
                    errors.append(f'Riga {row_num}: Ristorante non trovato con codice: {row["restaurant_code"]}')
                    continue
                
                # Find product by name
                product = Product.query.filter_by(name=row['product_name'].strip()).first()
                if not product:
                    errors.append(f'Riga {row_num}: Prodotto non trovato: {row["product_name"]}')
                    continue
                
                # Check if listing already exists
                existing = ProductListing.query.filter_by(
                    restaurant_id=restaurant.id,
                    product_id=product.id
                ).first()
                
                if existing:
                    errors.append(f'Riga {row_num}: Listino già esistente per {product.name} in {restaurant.name}')
                    continue
                
                # Parse prices
                try:
                    local_price = Decimal(str(row['local_price'].strip()))
                    delivery_price = Decimal(str(row['delivery_price'].strip()))
                except (ValueError, TypeError):
                    errors.append(f'Riga {row_num}: Prezzi non validi')
                    continue
                
                # Parse availability
                is_available = True
                if row.get('is_available', '').strip().lower() in ['false', 'no', '0', 'non disponibile']:
                    is_available = False
                
                # Create product listing
                listing = ProductListing(
                    restaurant_id=restaurant.id,
                    product_id=product.id,
                    local_price=local_price,
                    delivery_price=delivery_price,
                    is_available=is_available
                )
                
                db.session.add(listing)
                imported_count += 1
                
            except Exception as e:
                errors.append(f'Riga {row_num}: Errore durante l\'importazione: {str(e)}')
        
        if imported_count > 0:
            db.session.commit()
            
        return jsonify({
            'success': True,
            'imported_count': imported_count,
            'errors': errors,
            'message': f'Importati {imported_count} listini prezzi con successo'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Errore durante l\'importazione: {str(e)}'}), 500