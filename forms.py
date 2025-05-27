from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, SelectField, TextAreaField, DateTimeField, IntegerField, BooleanField, FieldList, FormField, HiddenField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, Optional, NumberRange
from models import User

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already taken. Please choose a different one.')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered. Please use a different one.')

class ScheduleForm(FlaskForm):
    ewaste_type = SelectField('E-waste Type', choices=[
        ('Air-Conditioner', 'Air Conditioner'),
        ('Bar-Phone', 'Bar Phone'),
        ('Battery', 'Battery'),
        ('Blood-Pressure-Monitor', 'Blood Pressure Monitor'),
        ('Boiler', 'Boiler'),
        ('CRT-Monitor', 'CRT Monitor'),
        ('CRT-TV', 'CRT TV'),
        ('Calculator', 'Calculator'),
        ('Camera', 'Camera'),
        ('Ceiling-Fan', 'Ceiling Fan'),
        ('Christmas-Lights', 'Christmas Lights'),
        ('Clothes-Iron', 'Clothes Iron'),
        ('Coffee-Machine', 'Coffee Machine'),
        ('Compact-Fluorescent-Lamps', 'Compact Fluorescent Lamps'),
        ('Computer-Keyboard', 'Computer Keyboard'),
        ('Computer-Mouse', 'Computer Mouse'),
        ('Cooled-Dispenser', 'Cooled Dispenser'),
        ('Cooling-Display', 'Cooling Display'),
        ('Dehumidifier', 'Dehumidifier'),
        ('Desktop-PC', 'Desktop Computer'),
        ('Digital-Oscilloscope', 'Digital Oscilloscope'),
        ('Dishwasher', 'Dishwasher'),
        ('Drone', 'Drone'),
        ('Electric-Bicycle', 'Electric Bicycle'),
        ('Electric-Guitar', 'Electric Guitar'),
        ('Electrocardiograph-Machine', 'Electrocardiograph Machine'),
        ('Electronic-Keyboard', 'Electronic Keyboard'),
        ('Exhaust-Fan', 'Exhaust Fan'),
        ('Flashlight', 'Flashlight'),
        ('Flat-Panel-Monitor', 'Flat Panel Monitor'),
        ('Flat-Panel-TV', 'Flat Panel TV'),
        ('Floor-Fan', 'Floor Fan'),
        ('Freezer', 'Freezer'),
        ('Glucose-Meter', 'Glucose Meter'),
        ('HDD', 'Hard Disk Drive'),
        ('Hair-Dryer', 'Hair Dryer'),
        ('Headphone', 'Headphone'),
        ('LED-Bulb', 'LED Bulb'),
        ('Laptop', 'Laptop'),
        ('Microwave', 'Microwave'),
        ('Music-Player', 'Music Player'),
        ('Neon-Sign', 'Neon Sign'),
        ('Network-Switch', 'Network Switch'),
        ('Non-Cooled-Dispenser', 'Non-Cooled Dispenser'),
        ('Oven', 'Oven'),
        ('PCB', 'Printed Circuit Board'),
        ('Patient-Monitoring-System', 'Patient Monitoring System'),
        ('Photovoltaic-Panel', 'Photovoltaic Panel'),
        ('PlayStation-5', 'PlayStation 5'),
        ('Power-Adapter', 'Power Adapter'),
        ('Printer', 'Printer'),
        ('Projector', 'Projector'),
        ('Pulse-Oximeter', 'Pulse Oximeter'),
        ('Range-Hood', 'Range Hood'),
        ('Refrigerator', 'Refrigerator'),
        ('Rotary-Mower', 'Rotary Mower'),
        ('Router', 'Router'),
        ('SSD', 'Solid State Drive'),
        ('Server', 'Server'),
        ('Smart-Watch', 'Smart Watch'),
        ('Smartphone', 'Smartphone'),
        ('Smoke-Detector', 'Smoke Detector'),
        ('Soldering-Iron', 'Soldering Iron'),
        ('Speaker', 'Speaker'),
        ('Stove', 'Stove'),
        ('Straight-Tube-Fluorescent-Lamp', 'Straight Tube Fluorescent Lamp'),
        ('Street-Lamp', 'Street Lamp'),
        ('TV-Remote-Control', 'TV Remote Control'),
        ('Table-Lamp', 'Table Lamp'),
        ('Tablet', 'Tablet'),
        ('Telephone-Set', 'Telephone Set'),
        ('Toaster', 'Toaster'),
        ('Tumble-Dryer', 'Tumble Dryer'),
        ('USB-Flash-Drive', 'USB Flash Drive'),
        ('Vacuum-Cleaner', 'Vacuum Cleaner'),
        ('Washing-Machine', 'Washing Machine'),
        ('Xbox-Series-X', 'Xbox Series X'),
        ('Other', 'Other E-waste')
    ], validators=[DataRequired()])
    
    model = StringField('Model/Brand (if known)')
    ram = SelectField('RAM (for computers)', choices=[
        ('', 'Not Applicable'),
        ('2GB', '2GB'),
        ('4GB', '4GB'),
        ('8GB', '8GB'),
        ('16GB', '16GB'),
        ('32GB', '32GB'),
        ('64GB+', '64GB or more')
    ])
    
    condition = SelectField('Condition', choices=[
        ('Excellent', 'Excellent - Like New'),
        ('Good', 'Good - Minor Wear'),
        ('Fair', 'Fair - Working but Visible Wear'),
        ('Poor', 'Poor - Heavy Wear or Damaged')
    ], validators=[DataRequired()])
    
    pickup_date = DateTimeField('Pickup Date and Time', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    pickup_address = TextAreaField('Pickup Address', validators=[DataRequired()])
    submit = SubmitField('Schedule Pickup')

class AdminLoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RewardForm(FlaskForm):
    name = StringField('Reward Name', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description', validators=[DataRequired()])
    points_required = IntegerField('Points Required', validators=[DataRequired()])
    reward_type = SelectField('Reward Type', choices=[
        ('Product', 'Product'),
        ('Coupon', 'Coupon'),
        ('Discount', 'Discount')
    ], validators=[DataRequired()])
    stock = IntegerField('Stock', validators=[DataRequired()])
    submit = SubmitField('Add Reward')
    
class BulkEwasteItemForm(FlaskForm):
    ewaste_type = SelectField('E-waste Type', choices=[
        ('Air-Conditioner', 'Air Conditioner'),
        ('Bar-Phone', 'Bar Phone'),
        ('Battery', 'Battery'),
        ('Blood-Pressure-Monitor', 'Blood Pressure Monitor'),
        ('Boiler', 'Boiler'),
        ('CRT-Monitor', 'CRT Monitor'),
        ('CRT-TV', 'CRT TV'),
        ('Calculator', 'Calculator'),
        ('Camera', 'Camera'),
        ('Ceiling-Fan', 'Ceiling Fan'),
        ('Christmas-Lights', 'Christmas Lights'),
        ('Clothes-Iron', 'Clothes Iron'),
        ('Coffee-Machine', 'Coffee Machine'),
        ('Compact-Fluorescent-Lamps', 'Compact Fluorescent Lamps'),
        ('Computer-Keyboard', 'Computer Keyboard'),
        ('Computer-Mouse', 'Computer Mouse'),
        ('Cooled-Dispenser', 'Cooled Dispenser'),
        ('Cooling-Display', 'Cooling Display'),
        ('Dehumidifier', 'Dehumidifier'),
        ('Desktop-PC', 'Desktop Computer'),
        ('Digital-Oscilloscope', 'Digital Oscilloscope'),
        ('Dishwasher', 'Dishwasher'),
        ('Drone', 'Drone'),
        ('Electric-Bicycle', 'Electric Bicycle'),
        ('Electric-Guitar', 'Electric Guitar'),
        ('Electrocardiograph-Machine', 'Electrocardiograph Machine'),
        ('Electronic-Keyboard', 'Electronic Keyboard'),
        ('Exhaust-Fan', 'Exhaust Fan'),
        ('Flashlight', 'Flashlight'),
        ('Flat-Panel-Monitor', 'Flat Panel Monitor'),
        ('Flat-Panel-TV', 'Flat Panel TV'),
        ('Floor-Fan', 'Floor Fan'),
        ('Freezer', 'Freezer'),
        ('Glucose-Meter', 'Glucose Meter'),
        ('HDD', 'Hard Disk Drive'),
        ('Hair-Dryer', 'Hair Dryer'),
        ('Headphone', 'Headphone'),
        ('LED-Bulb', 'LED Bulb'),
        ('Laptop', 'Laptop'),
        ('Microwave', 'Microwave'),
        ('Music-Player', 'Music Player'),
        ('Neon-Sign', 'Neon Sign'),
        ('Network-Switch', 'Network Switch'),
        ('Non-Cooled-Dispenser', 'Non-Cooled Dispenser'),
        ('Oven', 'Oven'),
        ('PCB', 'Printed Circuit Board'),
        ('Patient-Monitoring-System', 'Patient Monitoring System'),
        ('Photovoltaic-Panel', 'Photovoltaic Panel'),
        ('PlayStation-5', 'PlayStation 5'),
        ('Power-Adapter', 'Power Adapter'),
        ('Printer', 'Printer'),
        ('Projector', 'Projector'),
        ('Pulse-Oximeter', 'Pulse Oximeter'),
        ('Range-Hood', 'Range Hood'),
        ('Refrigerator', 'Refrigerator'),
        ('Rotary-Mower', 'Rotary Mower'),
        ('Router', 'Router'),
        ('SSD', 'Solid State Drive'),
        ('Server', 'Server'),
        ('Smart-Watch', 'Smart Watch'),
        ('Smartphone', 'Smartphone'),
        ('Smoke-Detector', 'Smoke Detector'),
        ('Soldering-Iron', 'Soldering Iron'),
        ('Speaker', 'Speaker'),
        ('Stove', 'Stove'),
        ('Straight-Tube-Fluorescent-Lamp', 'Straight Tube Fluorescent Lamp'),
        ('Street-Lamp', 'Street Lamp'),
        ('TV-Remote-Control', 'TV Remote Control'),
        ('Table-Lamp', 'Table Lamp'),
        ('Tablet', 'Tablet'),
        ('Telephone-Set', 'Telephone Set'),
        ('Toaster', 'Toaster'),
        ('Tumble-Dryer', 'Tumble Dryer'),
        ('USB-Flash-Drive', 'USB Flash Drive'),
        ('Vacuum-Cleaner', 'Vacuum Cleaner'),
        ('Washing-Machine', 'Washing Machine'),
        ('Xbox-Series-X', 'Xbox Series X'),
        ('Other', 'Other E-waste')
    ], validators=[DataRequired()])
    brand_model = StringField('Brand/Model', validators=[Optional()])
    quantity = IntegerField('Quantity', validators=[DataRequired(), NumberRange(min=1, max=1000)], default=1)
    condition = SelectField('Condition', choices=[
        ('WORKING', 'Working - Functional'),
        ('DAMAGED', 'Damaged - Partially Working'),
        ('SCRAP', 'Scrap - Not Working')
    ], validators=[DataRequired()])
    image = FileField('Upload Image (Optional)', validators=[Optional(), FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')])
    notes = TextAreaField('Additional Notes', validators=[Optional(), Length(max=500)])
    item_id = HiddenField()

class BulkPickupForm(FlaskForm):
    # Organization Details
    organization_name = StringField('Organization Name', validators=[DataRequired(), Length(max=100)])
    organization_type = SelectField('Organization Type', choices=[
        ('OFFICE', 'Office'),
        ('SCHOOL', 'School'),
        ('COLLEGE', 'College'),
        ('GOVERNMENT', 'Government'),
        ('NON_PROFIT', 'Non-Profit Organization'),
        ('HEALTHCARE', 'Healthcare Facility'),
        ('OTHER', 'Other')
    ], validators=[DataRequired()])
    contact_person = StringField('Contact Person Name', validators=[DataRequired(), Length(max=100)])
    contact_email = StringField('Contact Email', validators=[DataRequired(), Email()])
    contact_phone = StringField('Contact Phone', validators=[DataRequired(), Length(min=10, max=20)])
    gstin = StringField('GSTIN/ID (Optional)', validators=[Optional(), Length(max=20)])
    pickup_address = TextAreaField('Pickup Address', validators=[DataRequired()])
    
    # Pickup Preferences
    preferred_pickup_date = DateTimeField('Preferred Pickup Date & Time', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    special_instructions = TextAreaField('Special Instructions', validators=[Optional(), Length(max=500)])
    
    # File Upload for Bulk Items
    bulk_file = FileField('Upload Inventory File (CSV/Excel)', validators=[Optional(), FileAllowed(['csv', 'xlsx'], 'CSV or Excel files only!')])
    
    # Agreement Checkboxes
    confirm_eligible = BooleanField('I confirm all items are eligible e-waste', validators=[DataRequired()])
    agree_policy = BooleanField('I agree to Ecycle\'s pickup and recycling policy', validators=[DataRequired()])
    acknowledge_points = BooleanField('I acknowledge eco-points will be awarded after verification', validators=[DataRequired()])
    
    # Certificate Requests
    request_certificate = BooleanField('Request Disposal Certificate', default=True)
    request_tax_receipt = BooleanField('Request Tax-deductible Donation Receipt')
    
    submit = SubmitField('Submit Bulk Pickup Request')
    
class MessageForm(FlaskForm):
    """Form for posting messages to the E-Talk community board"""
    content = TextAreaField('Message', validators=[
        DataRequired(), 
        Length(min=1, max=500, message="Message must be between 1 and 500 characters.")
    ])
    submit = SubmitField('Post')
