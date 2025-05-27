from datetime import datetime, timedelta
import random
from app import app, db
from models import User, Ewaste, Schedule

# E-waste types for random selection
ewaste_types = [
    'Laptop', 'Smartphone', 'Tablet', 'Desktop-PC', 'Refrigerator', 
    'Washing-Machine', 'Microwave', 'Flat-Panel-TV', 'Air-Conditioner',
    'Vacuum-Cleaner', 'Coffee-Machine', 'Speaker', 'Printer'
]

# Condition options
conditions = ['Excellent', 'Good', 'Fair', 'Poor']

# Sample addresses
addresses = [
    "123 Tech Avenue, Innovation City",
    "456 Green Street, Eco Town",
    "789 Recycle Road, Sustainability Village",
    "101 Circuit Lane, E-waste City",
    "202 Component Street, Digital District"
]

def calculate_estimated_price(ewaste_type, condition):
    # Base prices for different e-waste types
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
        'Vacuum-Cleaner': 35,
        'Coffee-Machine': 40,
        'Speaker': 30,
        'Printer': 60,
        'Air-Conditioner': 80
    }
    
    # Multipliers based on condition
    condition_multiplier = {
        'Excellent': 1.5,
        'Good': 1.2,
        'Fair': 1.0,
        'Poor': 0.8
    }
    
    base_price = price_map.get(ewaste_type, 30)
    return int(base_price * condition_multiplier.get(condition, 1.0))

def create_sample_user(username, email, password, num_ewaste_items, carbon_saved=None):
    # Create user
    user = User(username=username, email=email)
    user.set_password(password)
    
    # Default carbon saved
    if carbon_saved is None:
        carbon_saved = random.uniform(20.0, 100.0)
    
    user.carbon_saved = carbon_saved
    db.session.add(user)
    db.session.flush()  # Get user ID without committing
    
    total_eco_points = 0
    
    # Create e-waste items and schedules
    for i in range(num_ewaste_items):
        # Random e-waste details
        ewaste_type = random.choice(ewaste_types)
        condition = random.choice(conditions)
        model = f"{ewaste_type} Model {random.randint(1000, 9999)}"
        ram = "" if ewaste_type not in ['Laptop', 'Desktop-PC'] else random.choice(['4GB', '8GB', '16GB', '32GB'])
        
        # Calculate price and eco points
        estimated_price = calculate_estimated_price(ewaste_type, condition)
        eco_points = estimated_price // 10
        total_eco_points += eco_points
        
        # Create e-waste record
        ewaste = Ewaste(
            user_id=user.id,
            ewaste_type=ewaste_type,
            model=model,
            ram=ram,
            condition=condition,
            estimated_price=estimated_price,
            eco_points=eco_points,
            created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30))
        )
        db.session.add(ewaste)
        db.session.flush()
        
        # Create schedule record (some completed, some pending)
        status = random.choice(['Collected', 'Pending'])
        pickup_date = datetime.utcnow() - timedelta(days=random.randint(1, 15)) if status == 'Collected' else datetime.utcnow() + timedelta(days=random.randint(1, 15))
        
        schedule = Schedule(
            user_id=user.id,
            ewaste_id=ewaste.id,
            pickup_date=pickup_date,
            pickup_address=random.choice(addresses),
            status=status,
            scheduled_at=datetime.utcnow() - timedelta(days=random.randint(20, 40)),
            updated_at=datetime.utcnow() - timedelta(days=random.randint(1, 10)) if status == 'Collected' else None
        )
        db.session.add(schedule)
    
    # Update user's eco points
    user.eco_points = total_eco_points
    return user

def main():
    with app.app_context():
        print("Creating sample users...")
        
        # Check if users already exist
        existing_users = User.query.filter(User.username.in_(['anand', 'yash', 'ankit'])).all()
        existing_usernames = [user.username for user in existing_users]
        
        users_to_create = []
        
        if 'anand' not in existing_usernames:
            users_to_create.append({
                'username': 'anand',
                'email': 'anand@example.com',
                'password': 'password123',
                'num_ewaste_items': random.randint(7, 12),
                'carbon_saved': random.uniform(70.0, 120.0)
            })
        
        if 'yash' not in existing_usernames:
            users_to_create.append({
                'username': 'yash',
                'email': 'yash@example.com',
                'password': 'password123',
                'num_ewaste_items': random.randint(5, 10),
                'carbon_saved': random.uniform(50.0, 90.0)
            })
        
        if 'ankit' not in existing_usernames:
            users_to_create.append({
                'username': 'ankit',
                'email': 'ankit@example.com',
                'password': 'password123',
                'num_ewaste_items': random.randint(8, 15),
                'carbon_saved': random.uniform(80.0, 150.0)
            })
        
        for user_data in users_to_create:
            user = create_sample_user(**user_data)
            print(f"Created user: {user.username} with {user.eco_points} eco points and {user_data['num_ewaste_items']} e-waste items")
        
        db.session.commit()
        print("Sample users created successfully!")

if __name__ == "__main__":
    main()