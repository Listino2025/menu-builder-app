from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.routes import bp
from app.models import Ingredient
from app.auth.decorators import manager_required
from app import db
import pandas as pd
import os
from werkzeug.utils import secure_filename

@bp.route('/ingredients')
@login_required
def ingredients():
    """List all ingredients with search and filter capabilities"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    category = request.args.get('category', '', type=str)
    per_page = 20
    
    query = Ingredient.query.filter_by(is_active=True)
    
    if search:
        query = query.filter(Ingredient.name.ilike(f'%{search}%'))
    
    if category:
        query = query.filter_by(category=category)
    
    ingredients = query.order_by(Ingredient.name).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Get all categories for filter dropdown
    categories = db.session.query(Ingredient.category).filter_by(is_active=True).distinct().all()
    categories = [cat[0] for cat in categories]
    
    return render_template('ingredients/list.html', 
                         ingredients=ingredients, 
                         search=search, 
                         category=category,
                         categories=categories)

@bp.route('/ingredients/new', methods=['GET', 'POST'])
@manager_required
def create_ingredient():
    """Create a new ingredient"""
    if request.method == 'POST':
        try:
            ingredient = Ingredient(
                wrin_code=request.form.get('wrin_code') or None,
                name=request.form['name'],
                category=request.form['category'],
                price_per_unit=float(request.form['price_per_unit']),
                unit_type=request.form['unit_type'],
                temperature_zone=request.form.get('temperature_zone'),
                created_by=current_user.id
            )
            
            db.session.add(ingredient)
            db.session.commit()
            
            flash(f'Ingredient "{ingredient.name}" created successfully!', 'success')
            return redirect(url_for('main.ingredients'))
            
        except ValueError as e:
            flash('Invalid price format. Please enter a valid number.', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating ingredient: {str(e)}', 'error')
    
    return render_template('ingredients/create.html', 
                         categories=Ingredient.CATEGORIES,
                         temp_zones=Ingredient.TEMP_ZONES)

@bp.route('/ingredients/<int:id>/edit', methods=['GET', 'POST'])
@manager_required
def edit_ingredient(id):
    """Edit an existing ingredient"""
    ingredient = Ingredient.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            ingredient.wrin_code = request.form.get('wrin_code') or None
            ingredient.name = request.form['name']
            ingredient.category = request.form['category']
            ingredient.price_per_unit = float(request.form['price_per_unit'])
            ingredient.unit_type = request.form['unit_type']
            ingredient.temperature_zone = request.form.get('temperature_zone')
            
            db.session.commit()
            
            flash(f'Ingredient "{ingredient.name}" updated successfully!', 'success')
            return redirect(url_for('main.ingredients'))
            
        except ValueError as e:
            flash('Invalid price format. Please enter a valid number.', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating ingredient: {str(e)}', 'error')
    
    return render_template('ingredients/edit.html', 
                         ingredient=ingredient,
                         categories=Ingredient.CATEGORIES,
                         temp_zones=Ingredient.TEMP_ZONES)

@bp.route('/ingredients/<int:id>/delete', methods=['POST'])
@manager_required
def delete_ingredient(id):
    """Soft delete an ingredient"""
    ingredient = Ingredient.query.get_or_404(id)
    
    try:
        # Check if ingredient is used in any products
        if ingredient.product_uses:
            flash(f'Cannot delete "{ingredient.name}" - it is used in existing products.', 'error')
        else:
            ingredient.is_active = False
            db.session.commit()
            flash(f'Ingredient "{ingredient.name}" deleted successfully!', 'success')
            
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting ingredient: {str(e)}', 'error')
    
    return redirect(url_for('main.ingredients'))

@bp.route('/ingredients/import', methods=['GET', 'POST'])
@manager_required
def import_ingredients():
    """Import ingredients from CSV file"""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        import_mode = request.form.get('import_mode', 'add')  # Default to 'add' mode
        
        if file.filename == '':
            flash('Nessun file selezionato', 'error')
            return redirect(request.url)
        
        if file and file.filename.endswith('.csv'):
            try:
                # Try to detect encoding and CSV format
                file.seek(0)
                raw_data = file.read()
                file.seek(0)
                
                # Try different encodings - start with most common formats
                encodings = ['windows-1252', 'iso-8859-1', 'cp1252', 'latin1', 'utf-8']
                sample = None
                detected_encoding = 'windows-1252'
                
                for encoding in encodings:
                    try:
                        # Test decoding the entire file, not just a sample
                        test_decode = raw_data.decode(encoding)
                        sample = test_decode[:1024]
                        detected_encoding = encoding
                        flash(f'Rilevato encoding: {encoding}', 'info')
                        break
                    except UnicodeDecodeError:
                        continue
                
                if sample is None:
                    # Ultimate fallback - use errors='ignore' to skip problematic characters
                    try:
                        sample = raw_data[:1024].decode('windows-1252', errors='ignore')
                        detected_encoding = 'windows-1252'
                        flash('Usato fallback encoding windows-1252 con caratteri ignorati', 'warning')
                    except:
                        flash('Impossibile leggere il file. Verifica che sia un file CSV valido.', 'error')
                        return redirect(request.url)
                
                # Detect separator
                separator = ','
                if ';' in sample and sample.count(';') > sample.count(','):
                    separator = ';'
                
                # Read CSV file with detected encoding and separator
                file.seek(0)
                try:
                    df = pd.read_csv(file, sep=separator, encoding=detected_encoding)
                except UnicodeDecodeError:
                    # Final fallback with error handling
                    file.seek(0)
                    df = pd.read_csv(file, sep=separator, encoding=detected_encoding, encoding_errors='ignore')
                    flash('Alcuni caratteri potrebbero essere stati ignorati durante la lettura', 'warning')
                
                # Skip empty rows at the beginning (common in CSV files)
                df = df.dropna(how='all').reset_index(drop=True)
                
                # Find the header row (look for recognizable column names)
                header_row = 0
                for i, row in df.iterrows():
                    row_values = [str(val).strip() for val in row if pd.notna(val)]
                    if any(col in row_values for col in ['Material group', 'WRIN code', 'Article description', 'name', 'category']):
                        header_row = i
                        break
                
                # Re-organize dataframe to use correct header
                if header_row > 0:
                    # Header is not at row 0, use the found header row
                    df = df.iloc[header_row:].reset_index(drop=True)
                    df.columns = df.iloc[0]  # Set first row as header
                    df = df.iloc[1:].reset_index(drop=True)  # Remove header row from data
                
                # Detect and normalize column format
                df.columns = df.columns.str.strip()
                
                # Check if it's standard restaurant format
                is_standard_format = False
                standard_columns = ['Material group', 'WRIN code', 'Article description', 'Case unit', 'Temperature zone', 'Price']
                
                # Clean column names and check for standard format
                df.columns = [str(col).strip() for col in df.columns]
                
                if all(col in df.columns for col in standard_columns):
                    is_standard_format = True
                    flash('Rilevato formato standard ristorante - Conversione automatica in corso...', 'info')
                    
                    # Map standard columns to our format
                    df = df.rename(columns={
                        'Article description': 'name',
                        'Material group': 'material_group_raw',
                        'WRIN code': 'wrin_code',
                        'Case unit': 'unit_type_raw',
                        'Temperature zone': 'temperature_zone_raw',
                        'Price': 'price_raw'
                    })
                    
                    # Convert categories with intelligent mapping based on product names
                    def map_category(material_group, product_name):
                        product_name_lower = str(product_name).lower()
                        
                        # Base/Bread products
                        if any(word in product_name_lower for word in ['buns', 'muffin', 'pane', 'panino']):
                            return 'BASE'
                        
                        # Protein products  
                        elif any(word in product_name_lower for word in ['hamburger', 'filetto', 'pesce', 'pollo', 'chicken', 'carne']):
                            return 'PROTEIN'
                        
                        # Cheese products
                        elif any(word in product_name_lower for word in ['formaggio', 'cheese', 'form.', 'cheddar']):
                            return 'CHEESE'
                        
                        # Vegetables
                        elif any(word in product_name_lower for word in ['lattuga', 'cipolle', 'cetrioli', 'pomodori', 'insalata']):
                            return 'VEGETABLE'
                        
                        # Sauces
                        elif any(word in product_name_lower for word in ['salsa', 'sauce', 'senape', 'ketchup', 'mayo']):
                            return 'SAUCE'
                        
                        # Default mapping by material group
                        else:
                            material_mapping = {
                                'FOOD FROZEN': 'PROTEIN',
                                'FOOD CHILLED': 'CHEESE', 
                                'FOOD DRY': 'SAUCE',
                                'PAPER': 'OTHER',
                                'OPERATING': 'OTHER',
                                'PROMOTION': 'OTHER'
                            }
                            return material_mapping.get(material_group, 'OTHER')
                    
                    df['category'] = df.apply(lambda row: map_category(row['material_group_raw'], row['name']), axis=1)
                    
                    # Convert unit types
                    unit_mapping = {
                        'CES': 'pieces',
                        'CAR': 'kg',
                        'LT': 'l',
                        'KG': 'kg'
                    }
                    df['unit_type'] = df['unit_type_raw'].map(unit_mapping).fillna('pieces')
                    
                    # Convert temperature zones
                    temp_mapping = {
                        'SURGELATO/CONGELATO': 'FROZEN',
                        'REFRIGERATO': 'CHILLED', 
                        'SECCO GENERALE': 'AMBIENT'
                    }
                    df['temperature_zone'] = df['temperature_zone_raw'].map(temp_mapping).fillna('AMBIENT')
                    
                    # Convert prices (remove EUR and convert decimal separator)
                    def convert_price(price_str):
                        try:
                            # Handle different price formats
                            price_clean = str(price_str).replace(' EUR', '').replace('EUR', '').strip()
                            # Convert decimal separator from European to US format
                            if ',' in price_clean and '.' in price_clean:
                                # Format like "1.234,56" -> "1234.56"
                                price_clean = price_clean.replace('.', '').replace(',', '.')
                            elif ',' in price_clean:
                                # Format like "1234,56" -> "1234.56"  
                                price_clean = price_clean.replace(',', '.')
                            
                            return float(price_clean)
                        except:
                            return 0.0
                    
                    df['price_per_unit'] = df['price_raw'].apply(convert_price)
                    
                else:
                    # Standard format check
                    required_columns = ['name', 'category', 'price_per_unit', 'unit_type']
                    df.columns = df.columns.str.lower().str.strip()
                    
                    missing_columns = [col for col in required_columns if col not in df.columns]
                    if missing_columns:
                        flash(f'Colonne mancanti: {", ".join(missing_columns)}', 'error')
                        return redirect(request.url)
                
                # Handle replace mode - delete all existing ingredients and related products
                deleted_ingredients_count = 0
                deleted_products_count = 0
                if import_mode == 'replace':
                    try:
                        from app.models import Product, ProductIngredient
                        
                        # Get all user's ingredients
                        existing_ingredients = Ingredient.query.filter_by(created_by=current_user.id).all()
                        deleted_ingredients_count = len(existing_ingredients)
                        
                        if deleted_ingredients_count > 0:
                            # Get all user's ingredients
                            ingredient_ids = [ing.id for ing in existing_ingredients]
                            
                            # In replace mode, delete ALL user's products since we're replacing the entire ingredient list
                            products_to_delete = db.session.query(Product).filter(
                                Product.created_by == current_user.id,
                                Product.is_active == True
                            ).all()
                            
                            deleted_products_count = len(products_to_delete)
                            
                            # Delete all user's products completely (this will cascade delete ProductIngredient relationships)
                            for product in products_to_delete:
                                db.session.delete(product)
                            
                            # Now delete all user's ingredients (safe since products are deleted)
                            for ingredient in existing_ingredients:
                                db.session.delete(ingredient)
                            
                            # Commit the deletion to release UNIQUE constraints
                            db.session.commit()
                            
                            # Inform user about what was deleted
                            if deleted_products_count > 0:
                                flash(f'Modalità sostituzione: {deleted_products_count} prodotti disattivati e {deleted_ingredients_count} ingredienti eliminati', 'info')
                            else:
                                flash(f'Modalità sostituzione: {deleted_ingredients_count} ingredienti eliminati', 'info')
                        
                    except Exception as e:
                        db.session.rollback()
                        flash(f'Errore durante l\'eliminazione degli ingredienti e prodotti esistenti: {str(e)}', 'error')
                        return redirect(request.url)
                
                # Import ingredients
                imported_count = 0
                updated_count = 0
                error_count = 0
                errors = []
                
                for index, row in df.iterrows():
                    try:
                        # Skip rows with missing required data
                        if pd.isna(row['name']) or row['name'] == '' or str(row['name']).strip() == '':
                            continue
                        if pd.isna(row['price_per_unit']) or row['price_per_unit'] == '':
                            continue
                        
                        # Check if ingredient already exists (only in add mode)
                        existing = None
                        if import_mode == 'add':
                            if 'wrin_code' in df.columns and pd.notna(row['wrin_code']):
                                existing = Ingredient.query.filter_by(wrin_code=row['wrin_code']).first()
                            
                            if not existing:
                                existing = Ingredient.query.filter_by(name=row['name']).first()
                        
                        if existing and import_mode == 'add':
                            # Update existing ingredient
                            existing.name = row['name']
                            existing.category = row['category']
                            existing.price_per_unit = float(row['price_per_unit'])
                            existing.unit_type = row['unit_type']
                            if 'wrin_code' in df.columns:
                                existing.wrin_code = row['wrin_code'] if pd.notna(row['wrin_code']) else None
                            if 'temperature_zone' in df.columns:
                                existing.temperature_zone = row['temperature_zone'] if pd.notna(row['temperature_zone']) else None
                            existing.is_active = True
                            updated_count += 1
                        else:
                            # Create new ingredient
                            ingredient = Ingredient(
                                wrin_code=row['wrin_code'] if 'wrin_code' in df.columns and pd.notna(row['wrin_code']) else None,
                                name=row['name'],
                                category=row['category'],
                                price_per_unit=float(row['price_per_unit']),
                                unit_type=row['unit_type'],
                                temperature_zone=row['temperature_zone'] if 'temperature_zone' in df.columns and pd.notna(row['temperature_zone']) else None,
                                created_by=current_user.id
                            )
                            db.session.add(ingredient)
                            imported_count += 1
                        
                    except Exception as e:
                        error_count += 1
                        errors.append(f"Row {index + 2}: {str(e)}")
                
                db.session.commit()
                
                # Create detailed success message
                if import_mode == 'replace':
                    if error_count == 0:
                        if deleted_products_count > 0:
                            flash(f'Importazione completata: {imported_count} nuovi ingredienti importati. {deleted_products_count} prodotti e {deleted_ingredients_count} ingredienti precedenti sostituiti.', 'success')
                        else:
                            flash(f'Importazione completata: {imported_count} nuovi ingredienti importati. {deleted_ingredients_count} ingredienti precedenti sostituiti.', 'success')
                    else:
                        if deleted_products_count > 0:
                            flash(f'Importazione completata con errori: {imported_count} importati, {error_count} errori. {deleted_products_count} prodotti e {deleted_ingredients_count} ingredienti precedenti sostituiti.', 'warning')
                        else:
                            flash(f'Importazione completata con errori: {imported_count} importati, {error_count} errori. {deleted_ingredients_count} ingredienti precedenti sostituiti.', 'warning')
                else:
                    if error_count == 0:
                        flash(f'Importazione completata: {imported_count} nuovi ingredienti, {updated_count} aggiornati.', 'success')
                    else:
                        flash(f'Importazione completata con errori: {imported_count} nuovi, {updated_count} aggiornati, {error_count} errori.', 'warning')
                if errors and len(errors) <= 10:  # Show first 10 errors
                    for error in errors[:10]:
                        flash(error, 'warning')
                
                return redirect(url_for('main.ingredients'))
                
            except UnicodeDecodeError as e:
                flash(f'Errore di encoding del file: {str(e)}. Prova a salvare il file come UTF-8 o Windows-1252.', 'error')
            except pd.errors.EmptyDataError:
                flash('Il file CSV è vuoto o non contiene dati validi.', 'error')
            except pd.errors.ParserError as e:
                flash(f'Errore nel parsing del CSV: {str(e)}. Verifica il formato del file.', 'error')
            except Exception as e:
                db.session.rollback()
                flash(f'Errore durante l\'elaborazione del file CSV: {str(e)}', 'error')
        else:
            flash('Please upload a CSV file', 'error')
    
    # Show sample CSV format
    sample_data = {
        'Sample CSV Format': [
            'wrin_code,name,category,price_per_unit,unit_type,temperature_zone',
            'BUN001,Regular Bun,BASE,0.25,pieces,AMBIENT',
            'BEEF001,Beef Patty,PROTEIN,2.50,pieces,FROZEN',
            'CHED001,Cheddar Cheese,CHEESE,0.30,slices,CHILLED'
        ]
    }
    
    return render_template('ingredients/import.html', sample_data=sample_data)

@bp.route('/ingredients/export')
@manager_required
def export_ingredients():
    """Export ingredients to CSV"""
    try:
        ingredients = Ingredient.query.filter_by(is_active=True).order_by(Ingredient.category, Ingredient.name).all()
        
        # Create CSV data
        csv_data = []
        csv_data.append(['WRIN Code', 'Name', 'Category', 'Price per Unit', 'Unit Type', 'Temperature Zone', 'Created By'])
        
        for ing in ingredients:
            csv_data.append([
                ing.wrin_code or '',
                ing.name,
                ing.category,
                float(ing.price_per_unit),
                ing.unit_type,
                ing.temperature_zone or '',
                ing.creator.username if ing.creator else ''
            ])
        
        # Convert to DataFrame and return as CSV
        df = pd.DataFrame(csv_data[1:], columns=csv_data[0])
        
        from flask import Response
        import io
        
        output = io.StringIO()
        df.to_csv(output, index=False)
        output.seek(0)
        
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=ingredients_export.csv'}
        )
        
    except Exception as e:
        flash(f'Error exporting ingredients: {str(e)}', 'error')
        return redirect(url_for('main.ingredients'))