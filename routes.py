import os
import tempfile
import json
import uuid
import csv
import pandas as pd
from io import BytesIO, StringIO
from datetime import datetime, timedelta
from flask import render_template, request, redirect, url_for, flash, session, jsonify, make_response, send_file, abort, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_login import login_required, current_user
from app import app, db
from models import User, Admin, Ewaste, Schedule, Reward, Redemption, BulkPickup, BulkEwasteItem, OrganizationType, EwasteCondition, BulkPickupStatus, Message
from utils import get_ewaste_news, calculate_carbon_footprint, generate_disposal_certificate, generate_bulk_disposal_certificate
from api import classify_image
from forms import LoginForm, RegisterForm, ScheduleForm, AdminLoginForm, RewardForm, BulkPickupForm, BulkEwasteItemForm, MessageForm
from sqlalchemy import func, desc

@app.route('/')
def index():
    # Get latest news for the homepage
    news = get_ewaste_news()
    return render_template('index.html', news=news)

# Learning page with educational content about e-waste
@app.route('/learn')
def learn():
    return render_template('learn.html')

# User registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data
        
        # Check if user already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose a different one.', 'danger')
            return redirect(url_for('register'))
        
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash('Email already registered. Please use a different one.', 'danger')
            return redirect(url_for('register'))
        
        # Create new user
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', form=form)

# User login
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['eco_points'] = user.eco_points  # Store eco points in session
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
    
    return render_template('login.html', form=form)

# User logout
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('eco_points', None)  # Clear eco_points from session
    session.pop('admin_id', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))

# Bulk pickup form
@app.route('/bulk-pickup', methods=['GET', 'POST'])
def bulk_pickup():
    if 'user_id' not in session:
        flash('Please login to schedule a bulk pickup.', 'warning')
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    # If user doesn't exist for some reason (maybe was deleted), redirect to login
    if not user:
        flash('User account not found. Please login again.', 'danger')
        session.pop('user_id', None)
        session.pop('username', None)
        session.pop('eco_points', None)
        return redirect(url_for('login'))
    
    # Store eco points in session for display in navbar
    session['eco_points'] = user.eco_points
    
    form = BulkPickupForm()
    
    if form.validate_on_submit():
        try:
            # Create new bulk pickup entry
            bulk_pickup = BulkPickup(
                user_id=user_id,
                organization_name=form.organization_name.data,
                organization_type=OrganizationType[form.organization_type.data],
                contact_person=form.contact_person.data,
                contact_email=form.contact_email.data,
                contact_phone=form.contact_phone.data,
                pickup_address=form.pickup_address.data,
                gstin=form.gstin.data,
                preferred_pickup_date=form.preferred_pickup_date.data,
                special_instructions=form.special_instructions.data,
                request_certificate=form.request_certificate.data,
                request_tax_receipt=form.request_tax_receipt.data,
                status=BulkPickupStatus.PENDING
            )
            
            db.session.add(bulk_pickup)
            db.session.flush()  # Get the bulk_pickup.id without committing
            
            # Process item data from the form
            ewaste_types = request.form.getlist('ewaste_type[]')
            brand_models = request.form.getlist('brand_model[]')
            quantities = request.form.getlist('quantity[]')
            conditions = request.form.getlist('condition[]')
            notes_list = request.form.getlist('notes[]')
            
            total_items = 0
            total_eco_points = 0
            
            # Process each item
            for i in range(len(ewaste_types)):
                if i < len(ewaste_types) and ewaste_types[i]:
                    ewaste_type = ewaste_types[i]
                    brand_model = brand_models[i] if i < len(brand_models) else ""
                    quantity = int(quantities[i]) if i < len(quantities) and quantities[i].isdigit() else 1
                    condition_value = conditions[i] if i < len(conditions) else "WORKING"
                    notes = notes_list[i] if i < len(notes_list) else ""
                    
                    # Calculate estimated price and eco points
                    price_map = {
                        'Desktop-PC': 150,
                        'Laptop': 120,
                        'Server': 200,
                        'Smartphone': 70,
                        'Tablet': 80,
                        'Flat-Panel-TV': 90,
                        'Refrigerator': 70,
                        'Washing-Machine': 70,
                        'Microwave': 50,
                        'Other': 30
                    }
                    
                    condition_multiplier = {
                        'WORKING': 1.2,
                        'DAMAGED': 0.8,
                        'SCRAP': 0.5
                    }
                    
                    base_price = price_map.get(ewaste_type, 30)
                    estimated_price = int(base_price * condition_multiplier.get(condition_value, 1.0))
                    eco_points = estimated_price // 10  # 1 eco point for every $10 of estimated value
                    
                    # Create new bulk e-waste item
                    item = BulkEwasteItem(
                        bulk_pickup_id=bulk_pickup.id,
                        ewaste_type=ewaste_type,
                        brand_model=brand_model,
                        quantity=quantity,
                        condition=EwasteCondition[condition_value],
                        additional_notes=notes,
                        estimated_price_per_unit=estimated_price,
                        eco_points_per_unit=eco_points
                    )
                    
                    db.session.add(item)
                    
                    # Update totals
                    total_items += quantity
                    total_eco_points += (eco_points * quantity)
            
            # If a bulk file was uploaded, process it
            if form.bulk_file.data:
                file = form.bulk_file.data
                if file.filename.endswith('.csv'):
                    # Process CSV file with robust error handling
                    try:
                        file_content = file.read()
                        
                        # Try multiple encodings if UTF-8 fails
                        try:
                            stream = StringIO(file_content.decode('utf-8-sig'))
                        except UnicodeDecodeError:
                            try:
                                # Try Latin-1 (more forgiving encoding)
                                stream = StringIO(file_content.decode('latin-1'))
                            except UnicodeDecodeError:
                                # Last resort: ignore problematic characters
                                stream = StringIO(file_content.decode('utf-8', errors='ignore'))
                        
                        csv_reader = csv.DictReader(stream)
                        
                        for row in csv_reader:
                            try:
                                ewaste_type = str(row.get('Device Type', 'Other')).strip()
                                brand_model = str(row.get('Model', '')).strip()
                                
                                # Sanitize inputs
                                brand_model = ''.join(c for c in brand_model if c.isprintable())
                                
                                # Handle quantity properly
                                try:
                                    quantity = int(row.get('Quantity', 1))
                                except (ValueError, TypeError):
                                    quantity = 1
                                
                                condition_str = str(row.get('Condition', 'WORKING')).strip().upper()
                                notes = str(row.get('Notes', '')).strip()
                                
                                # Sanitize notes
                                notes = ''.join(c for c in notes if c.isprintable())
                                
                                # Map the condition string to enum value
                                if 'WORK' in condition_str:
                                    condition = EwasteCondition.WORKING
                                elif 'DAMAGE' in condition_str:
                                    condition = EwasteCondition.DAMAGED
                                else:
                                    condition = EwasteCondition.SCRAP
                                
                                # Calculate price and points
                                base_price = price_map.get(ewaste_type, 30)
                                estimated_price = int(base_price * condition_multiplier.get(condition.name, 1.0))
                                eco_points = estimated_price // 10
                                
                                # Create new bulk e-waste item
                                item = BulkEwasteItem(
                                    bulk_pickup_id=bulk_pickup.id,
                                    ewaste_type=ewaste_type,
                                    brand_model=brand_model,
                                    quantity=quantity,
                                    condition=condition,
                                    additional_notes=notes,
                                    estimated_price_per_unit=estimated_price,
                                    eco_points_per_unit=eco_points
                                )
                                
                                db.session.add(item)
                                
                                # Update totals
                                total_items += quantity
                                total_eco_points += (eco_points * quantity)
                            except Exception as e:
                                current_app.logger.error(f"Error processing CSV row: {str(e)}")
                    except Exception as e:
                        current_app.logger.error(f"Error processing CSV file: {str(e)}")
                
                elif file.filename.endswith(('.xlsx', '.xls')):
                    # Process Excel file with improved error handling
                    try:
                        # Save to temporary file to handle potential streaming issues
                        import tempfile
                        
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp:
                            temp_path = temp.name
                            file.save(temp_path)
                        
                        # Try multiple engines and handle errors
                        try:
                            # First try with openpyxl (modern Excel files)
                            df = pd.read_excel(temp_path, engine='openpyxl')
                        except Exception as e:
                            current_app.logger.warning(f"Error with openpyxl: {str(e)}. Trying xlrd engine.")
                            try:
                                # Try with xlrd (older Excel files)
                                df = pd.read_excel(temp_path, engine='xlrd')
                            except Exception as e:
                                current_app.logger.error(f"Error with xlrd: {str(e)}")
                                raise
                        
                        for index, row in df.iterrows():
                            try:
                                # Handle NaN and convert to proper types
                                ewaste_type = str(row.get('Device Type', '') or 'Other').strip()
                                
                                # Fix common empty values in pandas
                                if ewaste_type == 'nan' or not ewaste_type:
                                    ewaste_type = 'Other'
                                
                                brand_model = str(row.get('Model', '') or '').strip()
                                
                                # Sanitize strings
                                brand_model = ''.join(c for c in brand_model if c.isprintable())
                                
                                # Handle quantity with error checking
                                try:
                                    quantity_value = row.get('Quantity', 1)
                                    if pd.isna(quantity_value):
                                        quantity = 1
                                    else:
                                        quantity = int(quantity_value)
                                except (ValueError, TypeError):
                                    quantity = 1
                                
                                # Ensure quantity is positive
                                quantity = max(1, quantity)
                                
                                # Handle condition
                                condition_str = str(row.get('Condition', '') or 'WORKING').strip().upper()
                                
                                # Handle notes with sanitization
                                notes = str(row.get('Notes', '') or '').strip()
                                notes = ''.join(c for c in notes if c.isprintable())
                                
                                # Map the condition string to enum value
                                if 'WORK' in condition_str:
                                    condition = EwasteCondition.WORKING
                                elif 'DAMAGE' in condition_str:
                                    condition = EwasteCondition.DAMAGED
                                else:
                                    condition = EwasteCondition.SCRAP
                                
                                # Calculate price and points
                                base_price = price_map.get(ewaste_type, 30)
                                estimated_price = int(base_price * condition_multiplier.get(condition.name, 1.0))
                                eco_points = estimated_price // 10
                                
                                # Create new bulk e-waste item
                                item = BulkEwasteItem(
                                    bulk_pickup_id=bulk_pickup.id,
                                    ewaste_type=ewaste_type,
                                    brand_model=brand_model,
                                    quantity=quantity,
                                    condition=condition,
                                    additional_notes=notes,
                                    estimated_price_per_unit=estimated_price,
                                    eco_points_per_unit=eco_points
                                )
                                
                                db.session.add(item)
                                
                                # Update totals
                                total_items += quantity
                                total_eco_points += (eco_points * quantity)
                            except Exception as e:
                                current_app.logger.error(f"Error processing Excel row: {str(e)}")
                        
                        # Clean up temporary file
                        import os
                        if os.path.exists(temp_path):
                            os.unlink(temp_path)
                            
                    except Exception as e:
                        current_app.logger.error(f"Error processing Excel file: {str(e)}")
            
            # Update bulk pickup with item totals
            bulk_pickup.total_items = total_items
            bulk_pickup.estimated_eco_points = total_eco_points
            
            # Add eco points to user's account
            user.eco_points += total_eco_points
            session['eco_points'] = user.eco_points
            
            # Calculate carbon savings
            carbon_saved = sum(calculate_carbon_footprint(item.ewaste_type, item.quantity) for item in bulk_pickup.ewaste_items)
            user.carbon_saved += carbon_saved
            
            db.session.commit()
            
            flash(f'Bulk pickup request submitted successfully! You earned {total_eco_points} eco points and saved {carbon_saved:.1f} kg of CO2!', 'success')
            return redirect(url_for('history'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error submitting bulk pickup: {str(e)}")
            flash(f'An error occurred while submitting your request: {str(e)}', 'danger')
    
    return render_template('bulk_pickup.html', form=form)

# Admin bulk pickups management
@app.route('/admin/bulk-pickups')
def admin_bulk_pickups():
    if 'admin_id' not in session:
        flash('Please login as admin to access this page.', 'warning')
        return redirect(url_for('admin_login'))
    
    # Get all bulk pickups with related data
    bulk_pickups = BulkPickup.query.order_by(BulkPickup.created_at.desc()).all()
    
    # Calculate statistics
    stats = {
        'pending': BulkPickup.query.filter_by(status=BulkPickupStatus.PENDING).count(),
        'scheduled': BulkPickup.query.filter_by(status=BulkPickupStatus.SCHEDULED).count(),
        'collected': BulkPickup.query.filter_by(status=BulkPickupStatus.COLLECTED).count(),
        'verified': BulkPickup.query.filter_by(status=BulkPickupStatus.VERIFIED).count(),
        'total_items': db.session.query(func.sum(BulkPickup.total_items)).scalar() or 0,
        'total_eco_points': db.session.query(func.sum(BulkPickup.actual_eco_points)).scalar() or 0
    }
    
    # Get recent activity (status changes)
    recent_activity = []
    for pickup in bulk_pickups[:5]:
        recent_activity.append({
            'organization_name': pickup.organization_name,
            'status': pickup.status.value,
            'time': pickup.updated_at.strftime('%Y-%m-%d %H:%M') if pickup.updated_at else pickup.created_at.strftime('%Y-%m-%d %H:%M')
        })
    
    return render_template('admin/bulk_pickups.html', bulk_pickups=bulk_pickups, stats=stats, recent_activity=recent_activity)

# Admin bulk pickup details
@app.route('/admin/bulk-pickups/<int:pickup_id>')
def admin_bulk_pickup_details(pickup_id):
    if 'admin_id' not in session:
        flash('Please login as admin to access this page.', 'warning')
        return redirect(url_for('admin_login'))
    
    # Get the bulk pickup with all related items
    bulk_pickup = BulkPickup.query.get_or_404(pickup_id)
    items = BulkEwasteItem.query.filter_by(bulk_pickup_id=pickup_id).all()
    user = User.query.get(bulk_pickup.user_id)
    
    return render_template('admin/bulk_pickup_details.html', 
                          bulk_pickup=bulk_pickup, 
                          items=items,
                          user=user)

# Admin update bulk pickup status
@app.route('/admin/bulk-pickups/<int:pickup_id>/update', methods=['POST'])
def admin_update_bulk_pickup(pickup_id):
    if 'admin_id' not in session:
        flash('Please login as admin to access this page.', 'warning')
        return redirect(url_for('admin_login'))
    
    bulk_pickup = BulkPickup.query.get_or_404(pickup_id)
    old_status = bulk_pickup.status
    
    # Update the pickup status and assigned team
    new_status = request.form.get('status')
    if new_status and hasattr(BulkPickupStatus, new_status):
        bulk_pickup.status = BulkPickupStatus[new_status]
    
    bulk_pickup.assigned_team = request.form.get('assigned_team', bulk_pickup.assigned_team)
    
    # Update actual eco points if provided
    if request.form.get('actual_eco_points'):
        try:
            bulk_pickup.actual_eco_points = int(request.form.get('actual_eco_points'))
        except:
            pass
    
    # If status changed from non-collected to collected, generate certificate
    if old_status != BulkPickupStatus.COLLECTED and bulk_pickup.status == BulkPickupStatus.COLLECTED:
        if bulk_pickup.request_certificate:
            try:
                # Get the user and items
                user = User.query.get(bulk_pickup.user_id)
                items = BulkEwasteItem.query.filter_by(bulk_pickup_id=pickup_id).all()
                
                # Generate certificate PDF
                certificate_buffer = generate_bulk_disposal_certificate(user, bulk_pickup, items)
                
                # Save the certificate to a file
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                certificate_filename = f"bulk_certificate_{pickup_id}_{timestamp}.pdf"
                certificate_path = os.path.join('static', 'certificates', certificate_filename)
                
                # Ensure the certificates directory exists
                os.makedirs(os.path.join('static', 'certificates'), exist_ok=True)
                
                # Write the PDF to file
                with open(certificate_path, 'wb') as f:
                    f.write(certificate_buffer.read())
                
                # Update the bulk pickup with the certificate path
                bulk_pickup.certificate_path = certificate_path
                
            except Exception as e:
                current_app.logger.error(f"Error generating bulk certificate: {str(e)}")
    
    db.session.commit()
    flash('Bulk pickup updated successfully!', 'success')
    return redirect(url_for('admin_bulk_pickups'))

# Admin generate/download bulk certificate
@app.route('/admin/bulk-pickups/<int:pickup_id>/certificate')
def admin_bulk_certificate(pickup_id):
    if 'admin_id' not in session:
        flash('Please login as admin to access this page.', 'warning')
        return redirect(url_for('admin_login'))
    
    bulk_pickup = BulkPickup.query.get_or_404(pickup_id)
    
    # Check if a certificate already exists
    if bulk_pickup.certificate_path and os.path.exists(bulk_pickup.certificate_path):
        return send_file(bulk_pickup.certificate_path, as_attachment=True, download_name=f"bulk_certificate_{pickup_id}.pdf")
    
    # Otherwise generate a new certificate
    user = User.query.get(bulk_pickup.user_id)
    items = BulkEwasteItem.query.filter_by(bulk_pickup_id=pickup_id).all()
    
    try:
        certificate_buffer = generate_bulk_disposal_certificate(user, bulk_pickup, items)
        return send_file(
            certificate_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f"bulk_certificate_{pickup_id}.pdf"
        )
    except Exception as e:
        current_app.logger.error(f"Error generating bulk certificate: {str(e)}")
        flash('An error occurred while generating the certificate.', 'danger')
        return redirect(url_for('admin_bulk_pickups'))

# User dashboard
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please login to access your dashboard.', 'warning')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    # If user doesn't exist for some reason (maybe was deleted), redirect to login
    if not user:
        flash('User account not found. Please login again.', 'danger')
        session.pop('user_id', None)  # Clear the session
        session.pop('username', None)
        session.pop('eco_points', None)
        return redirect(url_for('login'))
    
    # Store eco points in session for display in navbar
    session['eco_points'] = user.eco_points
    
    # Get user's scheduled pickups
    pickups = Schedule.query.filter_by(user_id=user_id).all()
    
    # Get the latest news
    news = get_ewaste_news()
    
    # Get user's e-waste items and calculate statistics
    ewaste_items = Ewaste.query.filter_by(user_id=user_id).all()
    total_items = len(ewaste_items)
    total_carbon_saved = user.carbon_saved
    
    # Get completed pickups
    completed_pickups = Schedule.query.filter_by(user_id=user_id, status='Collected').count()
    
    # Get recent rewards
    recent_redemptions = Redemption.query.filter_by(user_id=user_id).order_by(Redemption.redeemed_at.desc()).limit(3).all()
    
    # Get top users by eco points for leaderboard
    eco_leaders = db.session.query(
        User.id, 
        User.username, 
        User.eco_points
    ).order_by(
        User.eco_points.desc()
    ).limit(5).all()
    
    # Get top users by e-waste recycled
    ewaste_leaders = db.session.query(
        User.id,
        User.username,
        db.func.count(Ewaste.id).label('items_count')
    ).join(
        Ewaste, User.id == Ewaste.user_id
    ).group_by(
        User.id, User.username
    ).order_by(
        db.func.count(Ewaste.id).desc()
    ).limit(5).all()
    
    # Calculate user's rank in leaderboard
    user_rank_query = db.session.query(
        db.func.count(User.id) + 1
    ).filter(
        User.eco_points > user.eco_points
    ).scalar()
    
    user_rank = user_rank_query if user_rank_query else 1
    
    return render_template('dashboard.html', 
                          user=user, 
                          pickups=pickups, 
                          news=news, 
                          total_items=total_items,
                          total_carbon_saved=total_carbon_saved,
                          completed_pickups=completed_pickups,
                          recent_redemptions=recent_redemptions,
                          eco_leaders=eco_leaders,
                          ewaste_leaders=ewaste_leaders,
                          user_rank=user_rank)

# Schedule new pickup (form)
@app.route('/schedule', methods=['GET', 'POST'])
def schedule():
    if 'user_id' not in session:
        flash('Please login to schedule a pickup.', 'warning')
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    # If user doesn't exist for some reason (maybe was deleted), redirect to login
    if not user:
        flash('User account not found. Please login again.', 'danger')
        session.pop('user_id', None)  # Clear the session
        session.pop('username', None)
        session.pop('eco_points', None)
        return redirect(url_for('login'))
    
    # Store eco points in session for display in navbar
    session['eco_points'] = user.eco_points
    
    form = ScheduleForm()
    if form.validate_on_submit():
        ewaste_type = form.ewaste_type.data
        model = form.model.data
        ram = form.ram.data
        condition = form.condition.data
        pickup_date = form.pickup_date.data
        pickup_address = form.pickup_address.data
        
        # Calculate estimated price and eco points based on ewaste details
        # Comprehensive price map for all e-waste types
        price_map = {
            # High value items
            'Desktop-PC': 150,
            'Laptop': 120,
            'Server': 200,
            'PlayStation-5': 100,
            'Xbox-Series-X': 100,
            
            # Medium-high value items
            'Smartphone': 70,
            'Tablet': 80,
            'Flat-Panel-TV': 90,
            'Flat-Panel-Monitor': 70,
            'Digital-Oscilloscope': 150,
            'Printer': 60,
            'Air-Conditioner': 80,
            'Refrigerator': 70,
            'Washing-Machine': 70,
            'Dishwasher': 70,
            
            # Medium value items
            'CRT-Monitor': 50,
            'CRT-TV': 40,
            'Microwave': 50,
            'Coffee-Machine': 40,
            'Projector': 60,
            'Router': 40,
            'Network-Switch': 45,
            'Oven': 50,
            'Boiler': 40,
            'PCB': 30,
            'Electric-Guitar': 50,
            'Electronic-Keyboard': 55,
            'Drone': 60,
            'Electric-Bicycle': 90,
            'Cooled-Dispenser': 45,
            
            # Lower value items
            'Battery': 20,
            'Headphone': 25,
            'Computer-Keyboard': 20,
            'Computer-Mouse': 15,
            'Smart-Watch': 35,
            'Camera': 40,
            'Soldering-Iron': 25,
            'Bar-Phone': 20,
            'Hair-Dryer': 20,
            'Calculator': 15,
            'LED-Bulb': 10,
            'Flashlight': 15,
            'USB-Flash-Drive': 15,
            'HDD': 25,
            'SSD': 30,
            'Vacuum-Cleaner': 35,
            'Speaker': 30,
            'Toaster': 25,
            
            # Default for any other items
            'Other': 30
        }
        
        condition_multiplier = {
            'Excellent': 1.5,
            'Good': 1.2,
            'Fair': 1.0,
            'Poor': 0.8
        }
        
        base_price = price_map.get(ewaste_type, 30)
        estimated_price = int(base_price * condition_multiplier.get(condition, 1.0))
        eco_points = estimated_price // 10  # 1 eco point for every $10 of estimated value
        
        # Create new e-waste entry
        new_ewaste = Ewaste(
            user_id=user_id,
            ewaste_type=ewaste_type,
            model=model,
            ram=ram,
            condition=condition,
            estimated_price=estimated_price,
            eco_points=eco_points
        )
        
        db.session.add(new_ewaste)
        db.session.flush()  # Get the new_ewaste.id without committing
        
        # Create new schedule entry
        new_schedule = Schedule(
            user_id=user_id,
            ewaste_id=new_ewaste.id,
            pickup_date=pickup_date,
            pickup_address=pickup_address,
            status='Pending'
        )
        
        db.session.add(new_schedule)
        
        # Update user's eco points
        user = User.query.get(user_id)
        user.eco_points += eco_points
        # Update eco_points in session too
        session['eco_points'] = user.eco_points
        
        # Calculate carbon savings
        carbon_saved = calculate_carbon_footprint(ewaste_type)
        user.carbon_saved += carbon_saved
        
        db.session.commit()
        
        flash(f'Pickup scheduled successfully! You earned {eco_points} eco points and saved {carbon_saved} kg of CO2!', 'success')
        return redirect(url_for('history'))
    
    return render_template('schedule.html', form=form)

# Upload image for classification
@app.route('/classify', methods=['GET', 'POST'])
def classify():
    # For GET requests, show the classify page
    if request.method == 'GET':
        if 'user_id' not in session:
            flash('Please log in to use the classification feature', 'warning')
            return redirect(url_for('login'))
        return render_template('classify.html')
    
    # For POST requests, handle image classification
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    # Save the uploaded file to a temporary location with the original filename
    original_filename = secure_filename(file.filename)
    _, temp_path = tempfile.mkstemp(suffix=f'_{original_filename}')
    
    try:
        # Save the image and print debug info
        file.save(temp_path)
        print(f"Processing image: {original_filename}, saved at: {temp_path}")
        
        # Classify the image using Roboflow API or mock function
        result = classify_image(temp_path)
        
        # Process the classification result
        detected_items = result.get('predictions', [])
        
        if not detected_items:
            if os.path.exists(temp_path):
                os.unlink(temp_path)  # Clean up on error
            return jsonify({'error': 'No e-waste detected in the image'}), 400
        
        # Get the item with highest confidence
        best_match = max(detected_items, key=lambda x: x.get('confidence', 0))
        
        # Debug the prediction result
        print(f"Classification result: {best_match.get('class', 'Unknown')} with confidence {best_match.get('confidence', 0):.2f}")
        
        # Create a comprehensive mapping from lowercase to proper case format
        class_to_type = {
            'air-conditioner': 'Air-Conditioner',
            'bar-phone': 'Bar-Phone',
            'battery': 'Battery',
            'blood-pressure-monitor': 'Blood-Pressure-Monitor',
            'boiler': 'Boiler',
            'crt-monitor': 'CRT-Monitor',
            'crt-tv': 'CRT-TV',
            'calculator': 'Calculator',
            'camera': 'Camera',
            'ceiling-fan': 'Ceiling-Fan',
            'christmas-lights': 'Christmas-Lights',
            'clothes-iron': 'Clothes-Iron',
            'coffee-machine': 'Coffee-Machine',
            'compact-fluorescent-lamps': 'Compact-Fluorescent-Lamps',
            'computer-keyboard': 'Computer-Keyboard',
            'computer-mouse': 'Computer-Mouse',
            'cooled-dispenser': 'Cooled-Dispenser',
            'cooling-display': 'Cooling-Display',
            'dehumidifier': 'Dehumidifier',
            'desktop-pc': 'Desktop-PC',
            'desktop': 'Desktop-PC',
            'digital-oscilloscope': 'Digital-Oscilloscope',
            'dishwasher': 'Dishwasher',
            'drone': 'Drone',
            'electric-bicycle': 'Electric-Bicycle',
            'electric-guitar': 'Electric-Guitar',
            'electrocardiograph-machine': 'Electrocardiograph-Machine',
            'electronic-keyboard': 'Electronic-Keyboard',
            'exhaust-fan': 'Exhaust-Fan',
            'flashlight': 'Flashlight',
            'flat-panel-monitor': 'Flat-Panel-Monitor',
            'flat-panel-tv': 'Flat-Panel-TV',
            'monitor': 'Flat-Panel-Monitor',
            'tv': 'Flat-Panel-TV',
            'floor-fan': 'Floor-Fan',
            'freezer': 'Freezer',
            'glucose-meter': 'Glucose-Meter',
            'hdd': 'HDD',
            'hard disk': 'HDD',
            'hair-dryer': 'Hair-Dryer',
            'headphone': 'Headphone',
            'led-bulb': 'LED-Bulb',
            'laptop': 'Laptop',
            'microwave': 'Microwave',
            'music-player': 'Music-Player',
            'neon-sign': 'Neon-Sign',
            'network-switch': 'Network-Switch',
            'non-cooled-dispenser': 'Non-Cooled-Dispenser',
            'oven': 'Oven',
            'pcb': 'PCB',
            'patient-monitoring-system': 'Patient-Monitoring-System',
            'photovoltaic-panel': 'Photovoltaic-Panel',
            'playstation-5': 'PlayStation-5',
            'ps5': 'PlayStation-5',
            'power-adapter': 'Power-Adapter',
            'printer': 'Printer',
            'projector': 'Projector',
            'pulse-oximeter': 'Pulse-Oximeter',
            'range-hood': 'Range-Hood',
            'refrigerator': 'Refrigerator',
            'rotary-mower': 'Rotary-Mower',
            'router': 'Router',
            'ssd': 'SSD',
            'server': 'Server',
            'smart-watch': 'Smart-Watch',
            'smartphone': 'Smartphone',
            'mobile': 'Smartphone',
            'phone': 'Smartphone',
            'cell phone': 'Smartphone',
            'smoke-detector': 'Smoke-Detector',
            'soldering-iron': 'Soldering-Iron',
            'speaker': 'Speaker',
            'stove': 'Stove',
            'straight-tube-fluorescent-lamp': 'Straight-Tube-Fluorescent-Lamp',
            'street-lamp': 'Street-Lamp',
            'tv-remote-control': 'TV-Remote-Control',
            'remote': 'TV-Remote-Control',
            'table-lamp': 'Table-Lamp',
            'tablet': 'Tablet',
            'telephone-set': 'Telephone-Set',
            'toaster': 'Toaster',
            'tumble-dryer': 'Tumble-Dryer',
            'dryer': 'Tumble-Dryer',
            'usb-flash-drive': 'USB-Flash-Drive',
            'usb': 'USB-Flash-Drive',
            'vacuum-cleaner': 'Vacuum-Cleaner',
            'washing-machine': 'Washing-Machine',
            'washer': 'Washing-Machine',
            'xbox-series-x': 'Xbox-Series-X',
            'xbox': 'Xbox-Series-X'
        }
        
        # Extract the class name and standardize it
        detected_class = best_match.get('class', '')
        # Convert to lowercase for case-insensitive matching
        detected_class_lower = detected_class.lower()
        # Use the mapping if available, otherwise use the original class with proper capitalization
        ewaste_type = class_to_type.get(detected_class_lower, detected_class)
        confidence = best_match.get('confidence', 0) * 100
        
        # Recycling information for each e-waste type
        recycling_info = {
            'Battery': "Batteries contain hazardous materials like lead, cadmium, and mercury that can contaminate soil and water. They should be recycled at designated collection points. The metals can be extracted and reused in new batteries, reducing the need for mining raw materials.",
            
            'Smartphone': "Smartphones contain valuable materials like gold, silver, copper, and rare earth elements. These can be recovered during recycling. The circuit boards and components are processed to extract metals, while plastics are recycled separately. Always remove personal data before recycling.",
            
            'Laptop': "Laptops contain precious metals in their circuit boards, recyclable aluminum in their cases, and lithium in their batteries. Professional recyclers disassemble them to separate valuable components. The battery should be removed and recycled separately due to its hazardous materials.",
            
            'Desktop-PC': "Desktop computers contain recoverable materials like aluminum, copper, gold, and silver. Their large size means more materials can be reclaimed. The hard drives should be properly wiped or physically destroyed to protect personal data before recycling.",
            
            'Flat-Panel-Monitor': "Flat panel monitors contain mercury in their backlights and valuable metals in their circuit boards. They should be recycled at e-waste facilities equipped to handle them. The glass, plastic, and metal components are separated and processed individually.",
            
            'CRT-Monitor': "CRT monitors contain lead and phosphors that require special handling. They should never be thrown in regular trash as they can release toxic substances. Specialized recyclers safely break down these monitors and contain the harmful materials.",
        }
        
        # Get default recycling info if specific type not found
        default_info = "This e-waste item contains various materials that can be recovered through proper recycling. Always ensure it is disposed of through certified e-waste recycling facilities to prevent environmental contamination and recover valuable resources."
        info = recycling_info.get(ewaste_type, default_info)
        
        os.unlink(temp_path)  # Delete the temporary file
        
        return jsonify({
            'success': True,
            'ewaste_type': ewaste_type,
            'confidence': confidence,
            'recycling_info': info
        })
        
    except Exception as e:
        if os.path.exists(temp_path):
            os.unlink(temp_path)  # Clean up on error
        return jsonify({'error': str(e)}), 500

# View pickup history
@app.route('/history')
def history():
    if 'user_id' not in session:
        flash('Please login to view your history.', 'warning')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    # Get all pickups for the user, order by most recent first
    pickups = Schedule.query.filter_by(user_id=user_id).order_by(Schedule.pickup_date.desc()).all()
    
    return render_template('history.html', user=user, pickups=pickups)

# View and redeem rewards
@app.route('/rewards')
def rewards():
    if 'user_id' not in session:
        flash('Please login to view rewards.', 'warning')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    # Get all rewards to check what's in the database
    all_rewards = Reward.query.all()
    app.logger.debug(f"All rewards: {[{r.id: r.name, 'active': r.active} for r in all_rewards]}")
    
    # Get all active rewards
    available_rewards = Reward.query.filter_by(active=True).order_by(Reward.points_required).all()
    app.logger.debug(f"Active rewards: {[{r.id: r.name, 'active': r.active} for r in available_rewards]}")
    
    # Get user's redemptions
    redemptions = Redemption.query.filter_by(user_id=user_id).order_by(Redemption.redeemed_at.desc()).all()
    
    return render_template('rewards.html', user=user, rewards=available_rewards, redemptions=redemptions)

# Redeem a reward
@app.route('/redeem/<int:reward_id>', methods=['POST'])
def redeem_reward(reward_id):
    if 'user_id' not in session:
        flash('Please login to redeem rewards.', 'warning')
        return redirect(url_for('login'))
    
    # Make sure this is a POST request
    if request.method != 'POST':
        flash('Invalid redemption method.', 'danger')
        return redirect(url_for('rewards'))
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    reward = Reward.query.get_or_404(reward_id)
    
    # Log the redemption attempt
    app.logger.debug(f"Redemption attempt: User ID {user_id}, Reward ID {reward_id}, User Points {user.eco_points}, Reward Points {reward.points_required}, Stock {reward.stock}")
    
    # Check if reward is active and in stock
    if not reward.active:
        flash('This reward is no longer available.', 'danger')
        return redirect(url_for('rewards'))
    
    if reward.stock <= 0:
        flash('This reward is out of stock.', 'danger')
        return redirect(url_for('rewards'))
    
    # Check if user has enough points
    if user.eco_points < reward.points_required:
        flash(f'You need {reward.points_required - user.eco_points} more eco points for this reward.', 'danger')
        return redirect(url_for('rewards'))
    
    try:
        # Process redemption
        redemption = Redemption(
            user_id=user_id,
            reward_id=reward_id,
            points_spent=reward.points_required,
            status='Pending'
        )
        
        # Deduct points and update stock
        user.eco_points -= reward.points_required
        reward.stock -= 1
        
        # Add to session and commit transaction
        db.session.add(redemption)
        db.session.commit()
        
        # Update session eco points
        session['eco_points'] = user.eco_points
        
        app.logger.info(f"Redemption successful: User {user.username} redeemed {reward.name} for {reward.points_required} points")
        flash(f'You have successfully redeemed the {reward.name}!', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Redemption error: {str(e)}")
        flash('An error occurred while processing your redemption. Please try again.', 'danger')
    
    return redirect(url_for('rewards'))

# Admin login
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    form = AdminLoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        
        admin = Admin.query.filter_by(username=username).first()
        if admin and admin.check_password(password):
            session['admin_id'] = admin.id
            session['admin_username'] = admin.username
            flash('Admin login successful!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid admin credentials.', 'danger')
    
    return render_template('admin/login.html', form=form)

# Admin dashboard
@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin_id' not in session:
        flash('Please login as admin to access the dashboard.', 'warning')
        return redirect(url_for('admin_login'))
    
    # Get total users, e-waste items, pending pickups
    total_users = User.query.count()
    total_ewaste = Ewaste.query.count()
    pending_pickups = Schedule.query.filter_by(status='Pending').count()
    completed_pickups = Schedule.query.filter_by(status='Collected').count()
    
    # Get recent user registrations
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    
    # Get upcoming pickups
    upcoming_pickups = Schedule.query.filter_by(status='Pending').order_by(Schedule.pickup_date).limit(5).all()
    
    # Get recent redemptions
    recent_redemptions = Redemption.query.order_by(Redemption.redeemed_at.desc()).limit(5).all()
    
    # Import necessary SQLAlchemy functions
    from sqlalchemy import func, extract, text
    import json
    from datetime import datetime, timedelta
    
    # Get e-waste statistics for pie chart
    ewaste_stats_query = db.session.query(
        Ewaste.ewaste_type.label('type'),
        func.count(Ewaste.id).label('count')
    ).group_by(Ewaste.ewaste_type).order_by(func.count(Ewaste.id).desc()).limit(5).all()
    
    ewaste_stats = [{'type': item.type, 'count': item.count} for item in ewaste_stats_query] if ewaste_stats_query else []
    
    # Calculate total eco points
    total_eco_points = db.session.query(func.sum(User.eco_points)).scalar() or 0
    
    # Get monthly pickup data for the past 6 months
    six_months_ago = datetime.now() - timedelta(days=180)
    monthly_pickups = db.session.query(
        extract('month', Schedule.pickup_date).label('month'),
        extract('year', Schedule.pickup_date).label('year'),
        func.count(Schedule.id).label('count')
    ).filter(Schedule.pickup_date >= six_months_ago).group_by(
        extract('month', Schedule.pickup_date),
        extract('year', Schedule.pickup_date)
    ).order_by(
        extract('year', Schedule.pickup_date),
        extract('month', Schedule.pickup_date)
    ).all()
    
    # Format monthly data for Chart.js
    months = []
    pickups_data = []
    
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    # Initialize with last 6 months
    for i in range(6):
        month_idx = (current_month - i - 1) % 12 + 1
        year = current_year if month_idx <= current_month else current_year - 1
        month_name = datetime(year, month_idx, 1).strftime('%b %Y')
        months.insert(0, month_name)
        pickups_data.insert(0, 0)  # Default to 0
    
    # Fill in actual data
    for mp in monthly_pickups:
        month_idx = int(mp.month)
        year = int(mp.year)
        month_name = datetime(year, month_idx, 1).strftime('%b %Y')
        if month_name in months:
            idx = months.index(month_name)
            pickups_data[idx] = mp.count
    
    # Get user registration growth
    monthly_registrations = db.session.query(
        extract('month', User.created_at).label('month'),
        extract('year', User.created_at).label('year'),
        func.count(User.id).label('count')
    ).filter(User.created_at >= six_months_ago).group_by(
        extract('month', User.created_at),
        extract('year', User.created_at)
    ).order_by(
        extract('year', User.created_at),
        extract('month', User.created_at)
    ).all()
    
    # Format user registration data
    user_reg_data = []
    for i in range(6):
        user_reg_data.insert(0, 0)  # Default to 0
    
    for ur in monthly_registrations:
        month_idx = int(ur.month)
        year = int(ur.year)
        month_name = datetime(year, month_idx, 1).strftime('%b %Y')
        if month_name in months:
            idx = months.index(month_name)
            user_reg_data[idx] = ur.count
    
    # Get collection status distribution for donut chart
    status_distribution = db.session.query(
        Schedule.status.label('status'),
        func.count(Schedule.id).label('count')
    ).group_by(Schedule.status).all()
    
    status_labels = []
    status_data = []
    status_colors = []
    
    color_map = {
        'Pending': '#ffc107',  # warning
        'Scheduled': '#0d6efd',  # primary
        'Collected': '#198754',  # success
        'Cancelled': '#dc3545'   # danger
    }
    
    for status in status_distribution:
        status_labels.append(status.status)
        status_data.append(status.count)
        status_colors.append(color_map.get(status.status, '#6c757d'))  # default to secondary
    
    # Get eco points by e-waste type
    eco_by_type = db.session.query(
        Ewaste.ewaste_type.label('type'),
        func.sum(Ewaste.eco_points).label('points')
    ).group_by(Ewaste.ewaste_type).order_by(func.sum(Ewaste.eco_points).desc()).limit(5).all()
    
    eco_types = []
    eco_points = []
    
    for item in eco_by_type:
        if item.points:  # Only add if points isn't None
            eco_types.append(item.type)
            eco_points.append(int(item.points))
    
    # Get top 5 users by eco points
    top_users_query = User.query.order_by(User.eco_points.desc()).limit(5).all()
    top_user_names = [user.username for user in top_users_query]
    top_user_points = [user.eco_points for user in top_users_query]
    
    return render_template('admin/dashboard.html', 
                          total_users=total_users,
                          total_ewaste=total_ewaste,
                          pending_pickups=pending_pickups,
                          completed_pickups=completed_pickups,
                          recent_users=recent_users,
                          upcoming_pickups=upcoming_pickups,
                          recent_redemptions=recent_redemptions,
                          ewaste_stats=ewaste_stats,
                          total_eco_points=total_eco_points,
                          months_json=json.dumps(months),
                          pickups_data_json=json.dumps(pickups_data),
                          user_reg_data_json=json.dumps(user_reg_data),
                          status_labels_json=json.dumps(status_labels),
                          status_data_json=json.dumps(status_data),
                          status_colors_json=json.dumps(status_colors),
                          eco_types_json=json.dumps(eco_types),
                          eco_points_json=json.dumps(eco_points),
                          top_user_names_json=json.dumps(top_user_names),
                          top_user_points_json=json.dumps(top_user_points))

# Admin user management
@app.route('/admin/users')
def admin_users():
    if 'admin_id' not in session:
        flash('Please login as admin to access user management.', 'warning')
        return redirect(url_for('admin_login'))
    
    # Get filter parameters
    search = request.args.get('search', '')
    sort_by = request.args.get('sort', 'username')
    order = request.args.get('order', 'asc')
    
    # Base query
    query = User.query
    
    # Apply search filter
    if search:
        query = query.filter(db.or_(
            User.username.ilike(f'%{search}%'),
            User.email.ilike(f'%{search}%')
        ))
    
    # Apply sorting
    if sort_by == 'username':
        query = query.order_by(User.username.asc() if order == 'asc' else User.username.desc())
    elif sort_by == 'date':
        query = query.order_by(User.created_at.asc() if order == 'asc' else User.created_at.desc())
    elif sort_by == 'points':
        query = query.order_by(User.eco_points.asc() if order == 'asc' else User.eco_points.desc())
    
    # Execute query
    users = query.all()
    
    # Calculate statistics
    thirty_days_ago = datetime.now() - timedelta(days=30)
    new_users_count = User.query.filter(User.created_at >= thirty_days_ago).count()
    
    if users:
        avg_eco_points = sum(user.eco_points for user in users) / len(users)
        total_carbon_saved = sum(user.carbon_saved for user in users)
    else:
        avg_eco_points = 0
        total_carbon_saved = 0
    
    return render_template('admin/users.html', 
                          users=users,
                          new_users_count=new_users_count,
                          avg_eco_points=avg_eco_points,
                          total_carbon_saved=total_carbon_saved)

# Admin view user details
@app.route('/admin/users/<int:user_id>')
def admin_user_details(user_id):
    if 'admin_id' not in session:
        flash('Please login as admin to access user details.', 'warning')
        return redirect(url_for('admin_login'))
    
    user = User.query.get_or_404(user_id)
    ewaste_items = Ewaste.query.filter_by(user_id=user_id).all()
    pickups = Schedule.query.filter_by(user_id=user_id).all()
    redemptions = Redemption.query.filter_by(user_id=user_id).all()
    
    return render_template('admin/user_details.html', 
                          user=user, 
                          ewaste_items=ewaste_items, 
                          pickups=pickups,
                          redemptions=redemptions)

# Admin update user (eco points, reset password, delete account)
@app.route('/admin/users/<int:user_id>/update', methods=['POST'])
def admin_update_user(user_id):
    if 'admin_id' not in session:
        flash('Please login as admin to update user details.', 'warning')
        return redirect(url_for('admin_login'))
    
    user = User.query.get_or_404(user_id)
    action = request.form.get('action')
    
    if action == 'update_points':
        try:
            new_points = int(request.form.get('eco_points', 0))
            update_reason = request.form.get('update_reason', 'Admin adjustment')
            
            # Record the change
            change = new_points - user.eco_points
            if change != 0:
                adjustment_type = "increase" if change > 0 else "decrease"
                user.eco_points = new_points
                db.session.commit()
                flash(f'User eco points {adjustment_type}d by {abs(change)} points. Reason: {update_reason}', 'success')
            else:
                flash('No change in eco points.', 'info')
        except ValueError:
            flash('Invalid eco points value.', 'danger')
            
    elif action == 'reset_password':
        # Generate a random temporary password
        import random
        import string
        temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        
        user.set_password(temp_password)
        db.session.commit()
        flash(f'Password reset successful. Temporary password: {temp_password}', 'success')
        
    elif action == 'delete_user':
        # First delete all associated records
        Redemption.query.filter_by(user_id=user_id).delete()
        Schedule.query.filter_by(user_id=user_id).delete()
        Ewaste.query.filter_by(user_id=user_id).delete()
        
        # Then delete the user
        db.session.delete(user)
        db.session.commit()
        flash('User account and all associated data deleted permanently.', 'success')
        return redirect(url_for('admin_users'))
    
    return redirect(url_for('admin_user_details', user_id=user.id))

# Admin pickup management
@app.route('/admin/pickups')
def admin_pickups():
    if 'admin_id' not in session:
        flash('Please login as admin to access pickup management.', 'warning')
        return redirect(url_for('admin_login'))
    
    # Get filter parameters
    status_filter = request.args.get('status', '')
    date_range = request.args.get('date_range', 'all')
    search = request.args.get('search', '')
    
    # Base query
    query = Schedule.query
    
    # Apply filters
    if status_filter:
        query = query.filter(Schedule.status == status_filter)
        
    if date_range:
        today = datetime.now().date()
        if date_range == 'today':
            query = query.filter(db.func.date(Schedule.pickup_date) == today)
        elif date_range == 'week':
            week_start = today - timedelta(days=today.weekday())
            week_end = week_start + timedelta(days=6)
            query = query.filter(db.func.date(Schedule.pickup_date).between(week_start, week_end))
        elif date_range == 'month':
            query = query.filter(db.extract('year', Schedule.pickup_date) == today.year,
                               db.extract('month', Schedule.pickup_date) == today.month)
    
    if search:
        query = query.join(User).join(Ewaste).filter(
            db.or_(
                User.username.ilike(f'%{search}%'),
                Ewaste.ewaste_type.ilike(f'%{search}%')
            )
        )
    
    # Execute query with ordered results
    pickups = query.order_by(Schedule.pickup_date).all()
    
    # Get counts for stats
    pending_count = Schedule.query.filter_by(status='Pending').count()
    collected_count = Schedule.query.filter_by(status='Collected').count()
    today_count = Schedule.query.filter(db.func.date(Schedule.pickup_date) == datetime.now().date()).count()
    
    # Calculate carbon footprint and eco points totals
    total_eco_points = db.session.query(db.func.sum(Ewaste.eco_points)).join(Schedule).scalar() or 0
    total_carbon = 0
    for pickup in pickups:
        total_carbon += calculate_carbon_footprint(pickup.ewaste.ewaste_type)
    
    # Get upcoming pickups
    upcoming_pickups = Schedule.query.filter(
        Schedule.status == 'Pending',
        Schedule.pickup_date > datetime.now()
    ).order_by(Schedule.pickup_date).limit(5).all()
    
    # Prepare stats for template
    stats = {
        'pending_count': pending_count,
        'collected_count': collected_count,
        'today_count': today_count,
        'total_eco_points': total_eco_points,
        'total_carbon': total_carbon
    }
    
    # Add pagination variables
    page = 1  # Default to page 1
    total_pages = 1  # Default to 1 page
    
    return render_template('admin/pickups.html', 
                          pickups=pickups,
                          stats=stats,
                          page=page,
                          total_pages=total_pages,
                          upcoming_pickups=upcoming_pickups,
                          today=datetime.now().date())

# Admin update pickup status
@app.route('/admin/pickups/<int:pickup_id>/update', methods=['POST'])
def admin_update_pickup(pickup_id):
    if 'admin_id' not in session:
        flash('Please login as admin to update pickup status.', 'warning')
        return redirect(url_for('admin_login'))
    
    pickup = Schedule.query.get_or_404(pickup_id)
    new_status = request.form.get('status')
    
    if new_status in ['Pending', 'Collected']:
        # See if status was changed from Pending to Collected
        was_status_changed_to_collected = (pickup.status != 'Collected' and new_status == 'Collected')
        
        pickup.status = new_status
        pickup.updated_at = datetime.utcnow()
        db.session.commit()
        
        flash(f'Pickup status updated to {new_status}.', 'success')
        
        # If pickup is marked as collected, update the user's carbon footprint
        if was_status_changed_to_collected:
            # Get user and ewaste details
            user = User.query.get(pickup.user_id)
            ewaste = Ewaste.query.get(pickup.ewaste_id)
            
            # Update user's carbon footprint based on the ewaste type
            carbon_saved = calculate_carbon_footprint(ewaste.ewaste_type)
            user.carbon_saved += carbon_saved
            db.session.commit()
            
            # Log the certificate generation
            print(f"Generating certificate for pickup #{pickup_id}, user: {user.username}, ewaste: {ewaste.ewaste_type}")
    else:
        flash('Invalid status.', 'danger')
    
    return redirect(url_for('admin_pickups'))

# Admin e-waste inventory
@app.route('/admin/inventory')
def admin_inventory():
    if 'admin_id' not in session:
        flash('Please login as admin to access inventory.', 'warning')
        return redirect(url_for('admin_login'))
    
    # Get filter parameters
    ewaste_type_filter = request.args.get('ewaste_type', '')
    condition_filter = request.args.get('condition', '')
    search = request.args.get('search', '')
    
    # Base query
    query = Ewaste.query.join(User)
    
    # Apply filters
    if ewaste_type_filter:
        query = query.filter(Ewaste.ewaste_type == ewaste_type_filter)
        
    if condition_filter:
        query = query.filter(Ewaste.condition == condition_filter)
    
    if search:
        query = query.filter(
            db.or_(
                User.username.ilike(f'%{search}%'),
                Ewaste.model.ilike(f'%{search}%')
            )
        )
    
    # Execute query
    ewaste_items = query.all()
    
    # Calculate totals for stats
    total_value = sum(item.estimated_price or 0 for item in ewaste_items)
    total_eco_points = sum(item.eco_points or 0 for item in ewaste_items)
    
    # Calculate carbon saved (using utility function)
    carbon_saved = 0
    for item in ewaste_items:
        carbon_saved += calculate_carbon_footprint(item.ewaste_type)
    
    # Get unique e-waste types for filter dropdown
    ewaste_types = db.session.query(Ewaste.ewaste_type).distinct().order_by(Ewaste.ewaste_type).all()
    ewaste_types = [t[0] for t in ewaste_types]
    
    # Prepare data for charts
    type_data = {}
    for item in ewaste_items:
        if item.ewaste_type in type_data:
            type_data[item.ewaste_type] += 1
        else:
            type_data[item.ewaste_type] = 1
    
    # If we have too many types, group the less common ones as "Other"
    if len(type_data) > 6:
        sorted_types = sorted(type_data.items(), key=lambda x: x[1], reverse=True)
        top_types = dict(sorted_types[:5])
        other_count = sum(count for _, count in sorted_types[5:])
        top_types['Other'] = other_count
        type_data = top_types
    
    type_labels = list(type_data.keys())
    type_counts = list(type_data.values())
    
    # Condition breakdown
    condition_counts = [0, 0, 0, 0]  # Excellent, Good, Fair, Poor
    for item in ewaste_items:
        if item.condition == 'Excellent':
            condition_counts[0] += 1
        elif item.condition == 'Good':
            condition_counts[1] += 1
        elif item.condition == 'Fair':
            condition_counts[2] += 1
        elif item.condition == 'Poor':
            condition_counts[3] += 1
    
    return render_template('admin/inventory.html', 
                          ewaste_items=ewaste_items,
                          total_value=total_value,
                          total_eco_points=total_eco_points,
                          carbon_saved=carbon_saved,
                          ewaste_types=ewaste_types,
                          type_labels=type_labels,
                          type_counts=type_counts,
                          condition_counts=condition_counts)

# Admin rewards management
@app.route('/admin/rewards', methods=['GET', 'POST'])
def admin_rewards():
    if 'admin_id' not in session:
        flash('Please login as admin to access rewards management.', 'warning')
        return redirect(url_for('admin_login'))
    
    form = RewardForm()
    if form.validate_on_submit():
        reward = Reward(
            name=form.name.data,
            description=form.description.data,
            points_required=form.points_required.data,
            reward_type=form.reward_type.data,
            stock=form.stock.data,
            active=True
        )
        
        db.session.add(reward)
        db.session.commit()
        flash('New reward added successfully!', 'success')
        return redirect(url_for('admin_rewards'))
    
    rewards = Reward.query.all()
    return render_template('admin/rewards.html', rewards=rewards, form=form)

# Admin update reward
@app.route('/admin/rewards/<int:reward_id>/update', methods=['GET', 'POST'])
def admin_update_reward(reward_id):
    if 'admin_id' not in session:
        flash('Please login as admin to update rewards.', 'warning')
        return redirect(url_for('admin_login'))
    
    reward = Reward.query.get_or_404(reward_id)
    
    # Check if this is a toggle request from the URL
    if request.args.get('toggle'):
        reward.active = not reward.active
        db.session.commit()
        status = 'activated' if reward.active else 'deactivated'
        flash(f'Reward {status} successfully.', 'success')
        return redirect(url_for('admin_rewards'))
    
    # Otherwise, check for form action
    action = request.form.get('action')
    
    if action == 'toggle_active':
        reward.active = not reward.active
        db.session.commit()
        status = 'activated' if reward.active else 'deactivated'
        flash(f'Reward {status} successfully.', 'success')
    elif action == 'update_stock':
        new_stock = request.form.get('stock')
        try:
            reward.stock = int(new_stock)
            db.session.commit()
            flash('Stock updated successfully.', 'success')
        except ValueError:
            flash('Invalid stock value.', 'danger')
    
    return redirect(url_for('admin_rewards'))

# Admin redemption management
@app.route('/admin/redemptions')
def admin_redemptions():
    if 'admin_id' not in session:
        flash('Please login as admin to access redemption management.', 'warning')
        return redirect(url_for('admin_login'))
    
    redemptions = Redemption.query.join(User).join(Reward).order_by(Redemption.redeemed_at.desc()).all()
    return render_template('admin/redemptions.html', redemptions=redemptions)

# Admin update redemption status
@app.route('/admin/redemptions/<int:redemption_id>/update', methods=['GET', 'POST'])
def admin_update_redemption(redemption_id):
    if 'admin_id' not in session:
        flash('Please login as admin to update redemption status.', 'warning')
        return redirect(url_for('admin_login'))
    
    redemption = Redemption.query.get_or_404(redemption_id)
    
    # Check for status in URL parameters (GET request)
    if request.method == 'GET' and request.args.get('status'):
        new_status = request.args.get('status')
    else:
        # Get status from form (POST request)
        new_status = request.form.get('status')
    
    if new_status in ['Pending', 'Processed', 'Delivered']:
        redemption.status = new_status
        db.session.commit()
        flash(f'Redemption status updated to {new_status}.', 'success')
    else:
        flash('Invalid status.', 'danger')
    
    # Return to rewards page if this was called from there
    if request.referrer and 'admin/rewards' in request.referrer:
        return redirect(url_for('admin_rewards'))
    
    return redirect(url_for('admin_redemptions'))

# Create admin user (called at startup)
def create_admin():
    # Check if admin exists
    admin = Admin.query.filter_by(username='admin').first()
    if not admin:
        admin = Admin(username='admin')
        admin.set_password('admin123')  # Default password
        db.session.add(admin)
        db.session.commit()
        app.logger.info('Admin user created')
        
# View all certificates page
@app.route('/certificates')
def certificates():
    """
    Display all certificates for the logged-in user (both regular and bulk pickups)
    """
    if 'user_id' not in session:
        flash('Please login to view your certificates.', 'warning')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    # Get all completed regular pickups for the user
    regular_certificates = Schedule.query.filter_by(
        user_id=user_id, 
        status='Collected'
    ).order_by(Schedule.updated_at.desc()).all()
    
    # Get all completed bulk pickups for the user
    bulk_certificates = BulkPickup.query.filter_by(
        user_id=user_id,
        status=BulkPickupStatus.COLLECTED
    ).order_by(BulkPickup.updated_at.desc()).all()
    
    # Calculate carbon footprint for each regular pickup
    carbon_footprints = {}
    for cert in regular_certificates:
        ewaste = Ewaste.query.get(cert.ewaste_id)
        carbon_footprints[cert.id] = calculate_carbon_footprint(ewaste.ewaste_type)
    
    # Calculate carbon footprint for each bulk pickup
    bulk_carbon_footprints = {}
    bulk_item_counts = {}
    for bulk_cert in bulk_certificates:
        # Get all items for this bulk pickup
        items = BulkEwasteItem.query.filter_by(bulk_pickup_id=bulk_cert.id).all()
        # Calculate total carbon saved
        total_carbon = sum(calculate_carbon_footprint(item.ewaste_type, item.quantity) for item in items)
        bulk_carbon_footprints[bulk_cert.id] = total_carbon
        # Count total items
        bulk_item_counts[bulk_cert.id] = sum(item.quantity for item in items)
    
    return render_template('certificates.html', 
                           certificates=regular_certificates,
                           carbon_footprints=carbon_footprints,
                           bulk_certificates=bulk_certificates,
                           bulk_carbon_footprints=bulk_carbon_footprints,
                           bulk_item_counts=bulk_item_counts)

# Route to download regular disposal certificate
@app.route('/certificate/<int:pickup_id>')
def download_certificate(pickup_id):
    """
    Generate and download a disposal certificate PDF for a completed e-waste pickup
    """
    if 'user_id' not in session:
        flash('Please login to access your certificates.', 'warning')
        return redirect(url_for('login'))
    
    # Get the pickup/schedule
    pickup = Schedule.query.get_or_404(pickup_id)
    
    # Check if the user has permission (either the admin or the user who owns the pickup)
    if session.get('user_id') != pickup.user_id and 'admin_id' not in session:
        flash('You do not have permission to access this certificate.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Check if the pickup status is "Collected"
    if pickup.status != 'Collected':
        flash('Certificate is only available for completed pickups.', 'warning')
        return redirect(url_for('history'))
    
    # Get the user and ewaste details
    user = User.query.get(pickup.user_id)
    ewaste = Ewaste.query.get(pickup.ewaste_id)
    
    # Generate the certificate PDF
    try:
        pdf_buffer = generate_disposal_certificate(user, ewaste, pickup)
        
        # Prepare the response with the PDF
        response = make_response(pdf_buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=ecycle_certificate_{pickup_id}.pdf'
        
        return response
    
    except Exception as e:
        app.logger.error(f"Error generating certificate: {str(e)}")
        flash('An error occurred while generating the certificate. Please try again later.', 'danger')
        return redirect(url_for('history'))

# Route to download bulk disposal certificate
@app.route('/bulk-certificate/<int:bulk_pickup_id>')
def download_bulk_certificate(bulk_pickup_id):
    """
    Generate and download a disposal certificate PDF for a completed bulk e-waste pickup
    """
    if 'user_id' not in session:
        flash('Please login to access your certificates.', 'warning')
        return redirect(url_for('login'))
    
    # Get the bulk pickup
    bulk_pickup = BulkPickup.query.get_or_404(bulk_pickup_id)
    
    # Check if the user has permission (either the admin or the user who owns the pickup)
    if session.get('user_id') != bulk_pickup.user_id and 'admin_id' not in session:
        flash('You do not have permission to access this certificate.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Check if the pickup status is "Collected"
    if bulk_pickup.status != BulkPickupStatus.COLLECTED:
        flash('Certificate is only available for completed pickups.', 'warning')
        return redirect(url_for('bulk_history'))
    
    # Get the user and e-waste item details
    user = User.query.get(bulk_pickup.user_id)
    items = BulkEwasteItem.query.filter_by(bulk_pickup_id=bulk_pickup.id).all()
    
    # Generate the certificate PDF
    try:
        pdf_buffer = generate_bulk_disposal_certificate(user, bulk_pickup, items)
        
        # Prepare the response with the PDF
        response = make_response(pdf_buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=ecycle_bulk_certificate_{bulk_pickup_id}.pdf'
        
        return response
    
    except Exception as e:
        app.logger.error(f"Error generating bulk certificate: {str(e)}")
        flash('An error occurred while generating the certificate. Please try again later.', 'danger')
        return redirect(url_for('bulk_history'))

# API endpoint for image classification from the frontend
@app.route('/api/classify', methods=['POST'])
def api_classify():
    """
    API endpoint for e-waste image classification
    Accepts a multipart form with an 'image' file
    Returns classification result as JSON
    """
    if 'image' not in request.files:
        return jsonify({'success': False, 'message': 'No image uploaded'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No selected file'}), 400
    
    # Save the uploaded file to a temporary location with the original filename
    original_filename = secure_filename(file.filename)
    _, temp_path = tempfile.mkstemp(suffix=f'_{original_filename}')
    
    try:
        # Save the image and print debug info
        file.save(temp_path)
        print(f"API Processing image: {original_filename}, saved at: {temp_path}")
        
        # Classify the image using Roboflow API
        result = classify_image(temp_path)
        
        # Process the classification result
        detected_items = result.get('predictions', [])
        
        if not detected_items:
            if os.path.exists(temp_path):
                os.unlink(temp_path)  # Clean up on error
            return jsonify({'success': False, 'message': 'No e-waste detected in the image'}), 400
        
        # Get the item with highest confidence
        best_match = max(detected_items, key=lambda x: x.get('confidence', 0))
        
        # Debug the prediction result
        print(f"API Classification result: {best_match.get('class', 'Unknown')} with confidence {best_match.get('confidence', 0):.2f}")
        
        # Create a comprehensive mapping from lowercase to proper case format
        class_to_type = {
            'air-conditioner': 'Air-Conditioner',
            'bar-phone': 'Bar-Phone',
            'battery': 'Battery',
            'blood-pressure-monitor': 'Blood-Pressure-Monitor',
            'boiler': 'Boiler',
            'crt-monitor': 'CRT-Monitor',
            'crt-tv': 'CRT-TV',
            'calculator': 'Calculator',
            'camera': 'Camera',
            'ceiling-fan': 'Ceiling-Fan',
            'christmas-lights': 'Christmas-Lights',
            'clothes-iron': 'Clothes-Iron',
            'coffee-machine': 'Coffee-Machine',
            'compact-fluorescent-lamps': 'Compact-Fluorescent-Lamps',
            'computer-keyboard': 'Computer-Keyboard',
            'computer-mouse': 'Computer-Mouse',
            'cooled-dispenser': 'Cooled-Dispenser',
            'cooling-display': 'Cooling-Display',
            'dehumidifier': 'Dehumidifier',
            'desktop-pc': 'Desktop-PC',
            'desktop': 'Desktop-PC',
            'digital-oscilloscope': 'Digital-Oscilloscope',
            'dishwasher': 'Dishwasher',
            'drone': 'Drone',
            'electric-bicycle': 'Electric-Bicycle',
            'electric-guitar': 'Electric-Guitar',
            'electrocardiograph-machine': 'Electrocardiograph-Machine',
            'electronic-keyboard': 'Electronic-Keyboard',
            'exhaust-fan': 'Exhaust-Fan',
            'flashlight': 'Flashlight',
            'flat-panel-monitor': 'Flat-Panel-Monitor',
            'flat-panel-tv': 'Flat-Panel-TV',
            'monitor': 'Flat-Panel-Monitor',
            'tv': 'Flat-Panel-TV',
            'floor-fan': 'Floor-Fan',
            'freezer': 'Freezer',
            'glucose-meter': 'Glucose-Meter',
            'hdd': 'HDD',
            'hard disk': 'HDD',
            'hair-dryer': 'Hair-Dryer',
            'headphone': 'Headphone',
            'led-bulb': 'LED-Bulb',
            'laptop': 'Laptop',
            'microwave': 'Microwave',
            'music-player': 'Music-Player',
            'neon-sign': 'Neon-Sign',
            'network-switch': 'Network-Switch',
            'non-cooled-dispenser': 'Non-Cooled-Dispenser',
            'oven': 'Oven',
            'pcb': 'PCB',
            'patient-monitoring-system': 'Patient-Monitoring-System',
            'photovoltaic-panel': 'Photovoltaic-Panel',
            'playstation-5': 'PlayStation-5',
            'playstation': 'PlayStation-5',
            'ps5': 'PlayStation-5',
            'power-adapter': 'Power-Adapter',
            'adapter': 'Power-Adapter',
            'printer': 'Printer',
            'projector': 'Projector',
            'pulse-oximeter': 'Pulse-Oximeter',
            'range-hood': 'Range-Hood',
            'refrigerator': 'Refrigerator',
            'fridge': 'Refrigerator',
            'rotary-mower': 'Rotary-Mower',
            'router': 'Router',
            'ssd': 'SSD',
            'solid state drive': 'SSD',
            'server': 'Server',
            'smart-watch': 'Smart-Watch',
            'smartwatch': 'Smart-Watch',
            'smartphone': 'Smartphone',
            'phone': 'Smartphone',
            'smoke-detector': 'Smoke-Detector',
            'soldering-iron': 'Soldering-Iron',
            'speaker': 'Speaker',
            'stove': 'Stove',
            'straight-tube-fluorescent-lamp': 'Straight-Tube-Fluorescent-Lamp',
            'street-lamp': 'Street-Lamp',
            'tv-remote-control': 'TV-Remote-Control',
            'remote': 'TV-Remote-Control',
            'table-lamp': 'Table-Lamp',
            'tablet': 'Tablet',
            'telephone-set': 'Telephone-Set',
            'toaster': 'Toaster',
            'tumble-dryer': 'Tumble-Dryer',
            'dryer': 'Tumble-Dryer',
            'usb-flash-drive': 'USB-Flash-Drive',
            'usb': 'USB-Flash-Drive',
            'vacuum-cleaner': 'Vacuum-Cleaner',
            'washing-machine': 'Washing-Machine',
            'washer': 'Washing-Machine',
            'xbox-series-x': 'Xbox-Series-X',
            'xbox': 'Xbox-Series-X'
        }
        
        # Extract the class name and standardize it
        detected_class = best_match.get('class', '')
        # Convert to lowercase for case-insensitive matching
        detected_class_lower = detected_class.lower()
        # Use the mapping if available, otherwise use the original class with proper capitalization
        ewaste_type = class_to_type.get(detected_class_lower, detected_class)
        confidence = best_match.get('confidence', 0)
        
        # Recycling information for each e-waste type
        recycling_info = {
            'Battery': "Batteries contain hazardous materials like lead, cadmium, and mercury that can contaminate soil and water. They should be recycled at designated collection points. The metals can be extracted and reused in new batteries, reducing the need for mining raw materials.",
            
            'Smartphone': "Smartphones contain valuable materials like gold, silver, copper, and rare earth elements. These can be recovered during recycling. The circuit boards and components are processed to extract metals, while plastics are recycled separately. Always remove personal data before recycling.",
            
            'Laptop': "Laptops contain precious metals in their circuit boards, recyclable aluminum in their cases, and lithium in their batteries. Professional recyclers disassemble them to separate valuable components. The battery should be removed and recycled separately due to its hazardous materials.",
            
            'Desktop-PC': "Desktop computers contain recoverable materials like aluminum, copper, gold, and silver. Their large size means more materials can be reclaimed. The hard drives should be properly wiped or physically destroyed to protect personal data before recycling.",
            
            'Flat-Panel-Monitor': "Flat panel monitors contain mercury in their backlights and valuable metals in their circuit boards. They should be recycled at e-waste facilities equipped to handle them. The glass, plastic, and metal components are separated and processed individually.",
            
            'CRT-Monitor': "CRT monitors contain lead and phosphors that require special handling. They should never be thrown in regular trash as they can release toxic substances. Specialized recyclers safely break down these monitors and contain the harmful materials.",
        }
        
        # Get default recycling info if specific type not found
        default_info = "This e-waste item contains various materials that can be recovered through proper recycling. Always ensure it is disposed of through certified e-waste recycling facilities to prevent environmental contamination and recover valuable resources."
        info = recycling_info.get(ewaste_type, default_info)
        
        os.unlink(temp_path)  # Delete the temporary file
        
        return jsonify({
            'success': True,
            'result': {
                'ewaste_type': ewaste_type,
                'confidence': confidence,
                'recycling_info': info
            }
        })
        
    except Exception as e:
        if os.path.exists(temp_path):
            os.unlink(temp_path)  # Clean up on error
        print(f"API Classification error: {str(e)}")
        return jsonify({'success': False, 'message': f'Error during classification: {str(e)}'}), 500

# E-Talk Community Board Routes

@app.route('/etalk')
def etalk():
    """Render the E-Talk community message board page"""
    if 'user_id' not in session:
        flash('Please login to access the E-Talk community board.', 'warning')
        return redirect(url_for('login'))
    
    form = MessageForm()
    
    # Get all messages ordered by newest first
    messages = Message.query.order_by(Message.created_at.desc()).all()
    
    return render_template('etalk.html', form=form, messages=messages)

@app.route('/etalk/post', methods=['POST'])
def post_message():
    """Handle posting a new message to the E-Talk community board"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Login required'}), 401
    
    form = MessageForm()
    if form.validate_on_submit():
        user_id = session['user_id']
        content = form.content.data
        
        # Create and save the new message
        message = Message(user_id=user_id, content=content)
        db.session.add(message)
        db.session.commit()
        
        # Return JSON response for AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True,
                'message': message.to_dict()
            })
        
        flash('Your message has been posted!', 'success')
        return redirect(url_for('etalk'))
    
    # If form validation failed
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': False,
            'errors': form.errors
        }), 400
    
    flash('Error posting message. Please try again.', 'danger')
    return redirect(url_for('etalk'))

@app.route('/etalk/messages')
def get_messages():
    """API endpoint to get latest messages for real-time updates"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Login required'}), 401
    
    # Get timestamp parameter for messages newer than a specific time
    since = request.args.get('since', 0, type=int)
    
    # Get messages newer than the provided timestamp
    if since > 0:
        timestamp = datetime.fromtimestamp(since)
        messages = Message.query.filter(Message.created_at > timestamp).order_by(Message.created_at.desc()).all()
    else:
        messages = Message.query.order_by(Message.created_at.desc()).limit(50).all()
    
    return jsonify({
        'success': True,
        'messages': [message.to_dict() for message in messages]
    })

@app.route('/etalk/message/<int:message_id>/delete', methods=['POST'])
def delete_message(message_id):
    """Delete a message (admin only or message owner)"""
    if 'user_id' not in session and 'admin_id' not in session:
        return jsonify({'success': False, 'error': 'Login required'}), 401
    
    message = Message.query.get_or_404(message_id)
    
    # Check if user is admin or the message owner
    is_admin = 'admin_id' in session
    is_owner = 'user_id' in session and session['user_id'] == message.user_id
    
    if not (is_admin or is_owner):
        return jsonify({'success': False, 'error': 'Permission denied'}), 403
    
    # Delete the message
    db.session.delete(message)
    db.session.commit()
    
    # Return JSON response for AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True})
    
    flash('Message deleted successfully.', 'success')
    return redirect(url_for('etalk'))

@app.route('/admin/etalk', methods=['GET'])
def admin_etalk():
    """Admin interface for E-Talk community board"""
    if 'admin_id' not in session:
        flash('Please login as admin to access this page.', 'warning')
        return redirect(url_for('admin_login'))
        
    form = MessageForm()
    
    # Get all messages ordered by newest first
    messages = Message.query.order_by(Message.created_at.desc()).all()
    
    return render_template('admin/etalk.html', form=form, messages=messages)

@app.route('/admin/etalk/post', methods=['POST'])
def admin_post_message():
    """Handle posting a new admin message to the E-Talk community board"""
    if 'admin_id' not in session:
        return jsonify({'success': False, 'error': 'Admin login required'}), 401
    
    form = MessageForm()
    if form.validate_on_submit():
        # Get a default user for admin posts (first user)
        admin_user = User.query.first()
        if not admin_user:
            return jsonify({'success': False, 'error': 'No user found for admin post'}), 500
            
        content = form.content.data
        
        # Create and save the new message with admin flag
        message = Message(user_id=admin_user.id, content=content, is_admin=True)
        db.session.add(message)
        db.session.commit()
        
        # Return JSON response for AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True,
                'message': message.to_dict()
            })
        
        flash('Your admin message has been posted!', 'success')
        return redirect(url_for('admin_etalk'))
    
    # If form validation fails, return errors
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': False,
            'errors': form.errors
        })
    
    flash('Error posting message. Please try again.', 'danger')
    return redirect(url_for('admin_etalk'))
