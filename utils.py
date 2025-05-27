import os
import uuid
import feedparser
import requests
from io import BytesIO
from datetime import datetime
from flask import current_app, url_for
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.pdfgen import canvas

def get_ewaste_news(limit=5):
    """
    Fetch the latest e-waste news from Google News RSS feed
    
    Args:
        limit (int): Maximum number of news items to return
        
    Returns:
        list: List of news items with titles and links
    """
    try:
        url = "https://news.google.com/rss/search?q=e+waste+latest+news"
        feed = feedparser.parse(url)
        
        news_list = []
        for entry in feed.entries[:limit]:
            news_list.append({
                "title": entry.title,
                "link": entry.link,
                "published": entry.published if hasattr(entry, 'published') else None,
                "summary": entry.summary if hasattr(entry, 'summary') else None
            })
        
        return news_list
    except Exception as e:
        current_app.logger.error(f"Error fetching e-waste news: {str(e)}")
        return []

def calculate_carbon_footprint(ewaste_type, quantity=1):
    """
    Calculate the carbon footprint saved by recycling e-waste
    
    Args:
        ewaste_type (str): Type of e-waste
        quantity (int): Number of devices
        
    Returns:
        float: Estimated carbon footprint in kg CO2
    """
    # Comprehensive carbon savings estimates in kg CO2 equivalent per device
    carbon_savings = {
        # Computing Devices
        'Laptop': 140.0,
        'Desktop-PC': 200.0,
        'Server': 250.0,
        'Tablet': 80.0,
        'Calculator': 8.0,
        'Digital-Oscilloscope': 90.0,
        
        # Computer Peripherals
        'Computer-Keyboard': 8.0,
        'Computer-Mouse': 5.0,
        'HDD': 15.0,
        'SSD': 12.0,
        'PCB': 20.0,
        'Network-Switch': 25.0,
        'Router': 30.0,
        'USB-Flash-Drive': 6.0,
        
        # Phones & Communication
        'Smartphone': 60.0,
        'Bar-Phone': 30.0,
        'Telephone-Set': 25.0,
        'Smart-Watch': 20.0,
        'TV-Remote-Control': 5.0,
        
        # Displays & Visual Equipment
        'Flat-Panel-Monitor': 90.0,
        'CRT-Monitor': 150.0,
        'Flat-Panel-TV': 120.0,
        'CRT-TV': 180.0,
        'Projector': 70.0,
        
        # Major Appliances
        'Air-Conditioner': 300.0,
        'Washing-Machine': 240.0,
        'Refrigerator': 350.0,
        'Freezer': 300.0,
        'Microwave': 100.0,
        'Dishwasher': 150.0,
        'Oven': 120.0,
        'Stove': 100.0,
        'Range-Hood': 70.0,
        'Tumble-Dryer': 180.0,
        'Boiler': 200.0,
        
        # Small Appliances & Kitchen Equipment
        'Coffee-Machine': 50.0,
        'Vacuum-Cleaner': 80.0,
        'Toaster': 30.0,
        'Cooled-Dispenser': 90.0,
        'Non-Cooled-Dispenser': 40.0,
        'Hair-Dryer': 20.0,
        'Clothes-Iron': 25.0,
        
        # Audio & Visual Equipment
        'Speaker': 25.0,
        'Headphone': 15.0,
        'Camera': 40.0,
        'Music-Player': 30.0,
        'Electronic-Keyboard': 60.0,
        'Electric-Guitar': 45.0,
        'PlayStation-5': 80.0,
        'Xbox-Series-X': 80.0,
        
        # Medical Devices
        'Blood-Pressure-Monitor': 30.0,
        'Glucose-Meter': 25.0,
        'Pulse-Oximeter': 20.0,
        'Electrocardiograph-Machine': 100.0,
        'Patient-Monitoring-System': 120.0,
        
        # Lighting & Electrical
        'Battery': 10.0,
        'LED-Bulb': 5.0,
        'Compact-Fluorescent-Lamps': 8.0,
        'Straight-Tube-Fluorescent-Lamp': 10.0,
        'Table-Lamp': 15.0,
        'Street-Lamp': 60.0,
        'Ceiling-Fan': 40.0,
        'Floor-Fan': 35.0,
        'Exhaust-Fan': 30.0,
        'Neon-Sign': 25.0,
        'Christmas-Lights': 15.0,
        'Flashlight': 8.0,
        'Power-Adapter': 7.0,
        'Smoke-Detector': 12.0,
        
        # Specialty Electronics
        'Drone': 50.0,
        'Electric-Bicycle': 120.0,
        'Soldering-Iron': 15.0,
        'Photovoltaic-Panel': 100.0,
        'Cooling-Display': 130.0,
        'Rotary-Mower': 70.0,
        
        # Legacy compatibility and fallbacks
        'Mobile': 60.0,
        'Desktop': 200.0,
        'Monitor': 90.0,
        'Other': 40.0
    }
    
    # Return carbon savings or default to 40kg if type not in dictionary
    return carbon_savings.get(ewaste_type, 40.0) * quantity

def generate_disposal_certificate(user, ewaste, schedule):
    """
    Generate a PDF disposal certificate for a completed e-waste pickup
    
    Args:
        user (User): User who scheduled the pickup
        ewaste (Ewaste): The e-waste item collected
        schedule (Schedule): The schedule/pickup record
        
    Returns:
        BytesIO: PDF document as a byte stream
    """
    # Create a PDF buffer to store the PDF
    buffer = BytesIO()
    
    # Set up the PDF document with smaller margins to fit more content
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=50,
        bottomMargin=50
    )
    
    # Define green colors for the eco-themed certificate
    eco_dark_green = colors.Color(0.1, 0.5, 0.1)
    eco_medium_green = colors.Color(0.2, 0.6, 0.2)
    eco_light_green = colors.Color(0.8, 0.9, 0.8)
    
    # Styles for the document with enhanced typography
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='CertificateTitle',
        fontName='Helvetica-Bold',
        fontSize=18,
        alignment=1,
        spaceAfter=6,
        textColor=eco_dark_green
    ))
    styles.add(ParagraphStyle(
        name='CertificateSubTitle',
        fontName='Helvetica-Bold',
        fontSize=14,
        alignment=1,
        spaceAfter=6,
        textColor=eco_medium_green
    ))
    styles.add(ParagraphStyle(
        name='Normal-Center',
        parent=styles['Normal'],
        alignment=1,
        fontName='Helvetica',
        fontSize=10
    ))
    styles.add(ParagraphStyle(
        name='Bold-Center',
        parent=styles['BodyText'],
        fontName='Helvetica-Bold',
        alignment=1,
        fontSize=11,
        textColor=eco_dark_green
    ))
    styles.add(ParagraphStyle(
        name='TableHeader',
        fontName='Helvetica-Bold',
        fontSize=9,
        alignment=1,
        textColor=colors.white
    ))
    styles.add(ParagraphStyle(
        name='TableCell',
        fontName='Helvetica',
        fontSize=9,
        alignment=1
    ))
    styles.add(ParagraphStyle(
        name='Footer',
        fontName='Helvetica-Oblique',
        fontSize=9,
        alignment=1,
        textColor=eco_dark_green
    ))
    
    # Generate a unique certificate number
    certificate_number = f"ECO-{uuid.uuid4().hex[:8].upper()}-{schedule.id}"
    
    # Format dates
    pickup_date = schedule.pickup_date.strftime("%B %d, %Y")
    issued_date = datetime.now().strftime("%B %d, %Y")
    
    # Calculate environmental impact
    carbon_saved = calculate_carbon_footprint(ewaste.ewaste_type)
    
    # Build the document content
    elements = []
    
    # Create a header table with logo and title
    try:
        # Look for the logo at multiple possible locations
        logo_paths = [
            os.path.abspath(os.path.join('static', 'img', 'ecycle-logo.png')),
            os.path.abspath(os.path.join('static', 'img', 'logo.png')),
            os.path.abspath(os.path.join('static', 'images', 'ecycle-logo.png')),
            os.path.abspath(os.path.join('static', 'assets', 'ecycle-logo.png')),
            os.path.abspath(os.path.join('.', 'generated-icon.png'))
        ]
        
        logo_found = False
        for logo_path in logo_paths:
            current_app.logger.info(f"Looking for logo at: {logo_path}")
            if os.path.exists(logo_path):
                current_app.logger.info(f"Found logo at: {logo_path}")
                logo = Image(logo_path)
                logo.drawHeight = 1.2*inch
                logo.drawWidth = 1.2*inch
                
                # Create a header table with logo and title side by side
                header_data = [[logo, Paragraph('E-WASTE<br/>DISPOSAL CERTIFICATE', styles['CertificateTitle'])]]
                header_table = Table(header_data, colWidths=[1.2*inch, 4.8*inch])
                header_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                    ('ALIGN', (1, 0), (1, 0), 'CENTER'),
                    ('VALIGN', (0, 0), (1, 0), 'MIDDLE'),
                ]))
                elements.append(header_table)
                logo_found = True
                break
        
        if not logo_found:
            current_app.logger.warning("No logo found at any of the expected paths")
            elements.append(Paragraph('E-CYCLE', styles['CertificateTitle']))
            elements.append(Paragraph('E-WASTE DISPOSAL CERTIFICATE', styles['CertificateTitle']))
    except Exception as e:
        current_app.logger.error(f"Error adding logo to certificate: {str(e)}")
        elements.append(Paragraph('E-CYCLE', styles['CertificateTitle']))
        elements.append(Paragraph('E-WASTE DISPOSAL CERTIFICATE', styles['CertificateTitle']))
    
    elements.append(Spacer(1, 0.1*inch))
    
    # Certificate Number and Date in a colored box
    cert_box_data = [
        [Paragraph(f'Certificate Number: {certificate_number}', styles['Bold-Center'])],
        [Paragraph(f'Issued: {issued_date}', styles['Normal-Center'])]
    ]
    cert_box = Table(cert_box_data, colWidths=[6*inch])
    cert_box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 1), eco_light_green),
        ('BOX', (0, 0), (0, 1), 1, eco_dark_green),
        ('ALIGN', (0, 0), (0, 1), 'CENTER'),
        ('VALIGN', (0, 0), (0, 1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (0, 1), 4),
        ('BOTTOMPADDING', (0, 0), (0, 1), 4),
    ]))
    elements.append(cert_box)
    elements.append(Spacer(1, 0.15*inch))
    
    # Introduction Text
    intro_text = f'''
    This is to certify that <b>{user.username}</b> has responsibly disposed of electronic waste 
    through the Ecycle platform, contributing to environmental sustainability and proper e-waste management.
    '''
    elements.append(Paragraph(intro_text, styles['Normal-Center']))
    elements.append(Spacer(1, 0.15*inch))
    
    # Two-column layout for device info and environmental impact
    # Device Information
    device_data = [
        ['DEVICE INFORMATION', ''],
        ['E-Waste Type:', ewaste.ewaste_type.replace('-', ' ')],
        ['Model/Brand:', ewaste.model if ewaste.model else 'Not specified'],
        ['Condition:', ewaste.condition],
        ['Pickup Date:', pickup_date],
        ['Pickup Reference:', f'#{schedule.id}']
    ]
    
    # Environmental Impact Summary
    impact_data = [
        ['ENVIRONMENTAL IMPACT', ''],
        ['Carbon Footprint Saved:', f'{carbon_saved:.1f} kg CO₂e'],
        ['Eco Points Earned:', f'{ewaste.eco_points} points'],
        ['Recycling Method:', 'Responsible Recycling']
    ]
    
    # Create tables with matching styles
    device_table = Table(device_data, colWidths=[1.5*inch, 1.5*inch])
    device_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (1, 0), eco_dark_green),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.white),
        ('ALIGN', (0, 0), (1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (1, 0), 10),
        ('SPAN', (0, 0), (1, 0)),
        ('BOTTOMPADDING', (0, 0), (1, 0), 6),
        ('BACKGROUND', (0, 1), (1, len(device_data)-1), colors.white),
        ('GRID', (0, 0), (1, len(device_data)-1), 0.5, eco_medium_green),
        ('VALIGN', (0, 0), (1, len(device_data)-1), 'MIDDLE'),
        ('FONTSIZE', (0, 1), (1, len(device_data)-1), 8),
    ]))
    
    impact_table = Table(impact_data, colWidths=[1.5*inch, 1.5*inch])
    impact_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (1, 0), eco_medium_green),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.white),
        ('ALIGN', (0, 0), (1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (1, 0), 10),
        ('SPAN', (0, 0), (1, 0)),
        ('BOTTOMPADDING', (0, 0), (1, 0), 6),
        ('BACKGROUND', (0, 1), (1, len(impact_data)-1), colors.white),
        ('GRID', (0, 0), (1, len(impact_data)-1), 0.5, eco_medium_green),
        ('VALIGN', (0, 0), (1, len(impact_data)-1), 'MIDDLE'),
        ('FONTSIZE', (0, 1), (1, len(impact_data)-1), 8),
    ]))
    
    # Create a table to hold both tables side by side
    info_table_data = [[device_table, impact_table]]
    info_table = Table(info_table_data, colWidths=[3*inch, 3*inch])
    info_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (1, 0), 'TOP'),
    ]))
    
    elements.append(info_table)
    elements.append(Spacer(1, 0.15*inch))
    
    # Create a box for the certification statement
    certification_text = '''
    <b>CERTIFICATION STATEMENT</b><br/>
    This is to certify that the above-mentioned electronic waste item was collected and 
    processed in accordance with responsible e-waste management practices and applicable 
    environmental regulations. All data storage devices have been securely wiped or physically 
    destroyed as appropriate.
    '''
    cert_statement = Paragraph(certification_text, styles['Normal-Center'])
    cert_frame = Table([[cert_statement]], colWidths=[6*inch])
    cert_frame.setStyle(TableStyle([
        ('BOX', (0, 0), (0, 0), 1, eco_dark_green),
        ('BACKGROUND', (0, 0), (0, 0), eco_light_green),
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (0, 0), 10),
        ('BOTTOMPADDING', (0, 0), (0, 0), 10),
        ('LEFTPADDING', (0, 0), (0, 0), 10),
        ('RIGHTPADDING', (0, 0), (0, 0), 10),
    ]))
    elements.append(cert_frame)
    elements.append(Spacer(1, 0.15*inch))
    
    # Signature
    signature_data = [
        ['_______________________', '_______________________'],
        ['Authorized Signature', 'Date'],
        ['Ecycle Recycling Officer', '']
    ]
    
    signature_table = Table(signature_data, colWidths=[3*inch, 3*inch])
    signature_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (1, 2), 'CENTER'),
        ('VALIGN', (0, 0), (1, 2), 'MIDDLE'),
        ('FONTSIZE', (0, 1), (1, 2), 9),
        ('TEXTCOLOR', (0, 1), (1, 2), eco_dark_green),
    ]))
    elements.append(signature_table)
    elements.append(Spacer(1, 0.15*inch))
    
    # Footer with eco message
    footer_text = '''
    <i>Thank you for contributing to a sustainable future by responsibly recycling your electronic waste.</i>
    '''
    elements.append(Paragraph(footer_text, styles['Footer']))
    
    # Build the PDF with a green-themed border
    # Create a custom canvas to add the border
    class BorderedPage(canvas.Canvas):
        def __init__(self, *args, **kwargs):
            canvas.Canvas.__init__(self, *args, **kwargs)
            
        def showPage(self):
            self.saveState()
            # Draw a green border around the page
            self.setStrokeColor(eco_dark_green)
            self.setLineWidth(2)
            width, height = letter
            self.rect(20, 20, width - 40, height - 40)
            
            # Add a subtle eco leaf watermark
            self.setFillColor(eco_light_green)
            self.setFont("Helvetica", 8)
            self.drawRightString(width - 30, 30, "Ecycle - Sustainable E-Waste Management")
            
            self.restoreState()
            canvas.Canvas.showPage(self)
    
    # Build the PDF with our custom canvas
    buffer.seek(0)  # Reset buffer
    custom_canvas = BorderedPage(buffer)
    doc.build(elements, canvasmaker=lambda *args, **kwargs: BorderedPage(*args, **kwargs))
    
    # Reset buffer position to the beginning
    buffer.seek(0)
    
    return buffer

def generate_bulk_disposal_certificate(user, bulk_pickup, items):
    """
    Generate a PDF disposal certificate for a completed bulk e-waste pickup
    
    Args:
        user (User): User who scheduled the pickup
        bulk_pickup (BulkPickup): The bulk pickup record
        items (list): List of BulkEwasteItem objects
        
    Returns:
        BytesIO: PDF document as a byte stream
    """
    # Create a PDF buffer to store the PDF
    buffer = BytesIO()
    
    # Set up the PDF document with smaller margins to fit more content
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=50,
        bottomMargin=50
    )
    
    # Define red colors for the bulk certificate theme
    eco_dark_green = colors.Color(0.6, 0.1, 0.1)  # Dark red
    eco_medium_green = colors.Color(0.8, 0.2, 0.2)  # Medium red
    eco_light_green = colors.Color(0.98, 0.9, 0.9)  # Light red
    
    # Styles for the document with enhanced typography
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='CertificateTitle',
        fontName='Helvetica-Bold',
        fontSize=18,
        alignment=1,
        spaceAfter=6,
        textColor=eco_dark_green
    ))
    styles.add(ParagraphStyle(
        name='CertificateSubTitle',
        fontName='Helvetica-Bold',
        fontSize=14,
        alignment=1,
        spaceAfter=6,
        textColor=eco_medium_green
    ))
    styles.add(ParagraphStyle(
        name='Normal-Center',
        parent=styles['Normal'],
        alignment=1,
        fontName='Helvetica',
        fontSize=10
    ))
    styles.add(ParagraphStyle(
        name='Bold-Center',
        parent=styles['BodyText'],
        fontName='Helvetica-Bold',
        alignment=1,
        fontSize=11,
        textColor=eco_dark_green
    ))
    styles.add(ParagraphStyle(
        name='TableHeader',
        fontName='Helvetica-Bold',
        fontSize=9,
        alignment=1,
        textColor=colors.white
    ))
    styles.add(ParagraphStyle(
        name='TableCell',
        fontName='Helvetica',
        fontSize=9,
        alignment=1
    ))
    styles.add(ParagraphStyle(
        name='Footer',
        fontName='Helvetica-Oblique',
        fontSize=9,
        alignment=1,
        textColor=eco_dark_green
    ))
    
    # Generate a unique certificate number
    certificate_number = f"ECO-BULK-{uuid.uuid4().hex[:8].upper()}-{bulk_pickup.id}"
    
    # Format dates
    pickup_date = bulk_pickup.preferred_pickup_date.strftime("%B %d, %Y")
    issued_date = datetime.now().strftime("%B %d, %Y")
    
    # Calculate environmental impact
    total_carbon_saved = sum(calculate_carbon_footprint(item.ewaste_type, item.quantity) for item in items)
    total_items = sum(item.quantity for item in items)
    total_eco_points = bulk_pickup.actual_eco_points or bulk_pickup.estimated_eco_points
    
    # Build the document content
    elements = []
    
    # Create a header table with logo and title
    try:
        # Look for the logo at multiple possible locations
        logo_paths = [
            os.path.abspath(os.path.join('static', 'img', 'ecycle-logo.png')),
            os.path.abspath(os.path.join('static', 'img', 'logo.png')),
            os.path.abspath(os.path.join('static', 'images', 'ecycle-logo.png')),
            os.path.abspath(os.path.join('static', 'assets', 'ecycle-logo.png')),
            os.path.abspath(os.path.join('.', 'generated-icon.png'))
        ]
        
        logo_found = False
        for logo_path in logo_paths:
            current_app.logger.info(f"Looking for logo at: {logo_path}")
            if os.path.exists(logo_path):
                current_app.logger.info(f"Found logo at: {logo_path}")
                logo = Image(logo_path)
                logo.drawHeight = 1.2*inch
                logo.drawWidth = 1.2*inch
                
                # Create a header table with logo and title side by side
                header_data = [[logo, Paragraph('BULK E-WASTE<br/>DISPOSAL CERTIFICATE', styles['CertificateTitle'])]]
                header_table = Table(header_data, colWidths=[1.2*inch, 4.8*inch])
                header_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                    ('ALIGN', (1, 0), (1, 0), 'CENTER'),
                    ('VALIGN', (0, 0), (1, 0), 'MIDDLE'),
                ]))
                elements.append(header_table)
                logo_found = True
                break
        
        if not logo_found:
            current_app.logger.warning("No logo found at any of the expected paths")
            elements.append(Paragraph('E-CYCLE', styles['CertificateTitle']))
            elements.append(Paragraph('BULK E-WASTE DISPOSAL CERTIFICATE', styles['CertificateTitle']))
    except Exception as e:
        current_app.logger.error(f"Error adding logo to certificate: {str(e)}")
        elements.append(Paragraph('E-CYCLE', styles['CertificateTitle']))
        elements.append(Paragraph('BULK E-WASTE DISPOSAL CERTIFICATE', styles['CertificateTitle']))
    
    elements.append(Spacer(1, 0.1*inch))
    
    # Certificate Number and Date in a colored box
    cert_box_data = [
        [Paragraph(f'Certificate Number: {certificate_number}', styles['Bold-Center'])],
        [Paragraph(f'Issued: {issued_date}', styles['Normal-Center'])]
    ]
    cert_box = Table(cert_box_data, colWidths=[6*inch])
    cert_box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 1), eco_light_green),
        ('BOX', (0, 0), (0, 1), 1, eco_dark_green),
        ('ALIGN', (0, 0), (0, 1), 'CENTER'),
        ('VALIGN', (0, 0), (0, 1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (0, 1), 4),
        ('BOTTOMPADDING', (0, 0), (0, 1), 4),
    ]))
    elements.append(cert_box)
    elements.append(Spacer(1, 0.15*inch))
    
    # Introduction Text
    org_name = bulk_pickup.organization_name
    intro_text = f'''
    This is to certify that <b>{org_name}</b> has responsibly disposed of electronic waste 
    through the Ecycle platform, contributing to environmental sustainability and proper e-waste management.
    '''
    elements.append(Paragraph(intro_text, styles['Normal-Center']))
    elements.append(Spacer(1, 0.15*inch))
    
    # Two-column layout for organization info and environmental impact
    # Organization Information
    org_data = [
        ['ORGANIZATION INFORMATION', ''],
        ['Organization Name:', org_name],
        ['Organization Type:', bulk_pickup.organization_type.value],
        ['Contact Person:', bulk_pickup.contact_person],
        ['Contact Email:', bulk_pickup.contact_email],
        ['Pickup Date:', pickup_date],
        ['Pickup Reference:', f'#{bulk_pickup.id}']
    ]
    
    if bulk_pickup.gstin:
        org_data.append(['GSTIN/ID:', bulk_pickup.gstin])
    
    # Environmental Impact Summary
    impact_data = [
        ['ENVIRONMENTAL IMPACT', ''],
        ['Total Items:', f'{total_items}'],
        ['Carbon Footprint Saved:', f'{total_carbon_saved:.1f} kg CO₂e'],
        ['Eco Points Earned:', f'{total_eco_points} points'],
        ['Recycling Method:', 'Responsible Recycling']
    ]
    
    # Create tables with matching styles
    org_table = Table(org_data, colWidths=[1.5*inch, 1.5*inch])
    org_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (1, 0), eco_dark_green),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.white),
        ('ALIGN', (0, 0), (1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (1, 0), 10),
        ('SPAN', (0, 0), (1, 0)),
        ('BOTTOMPADDING', (0, 0), (1, 0), 6),
        ('BACKGROUND', (0, 1), (1, len(org_data)-1), colors.white),
        ('GRID', (0, 0), (1, len(org_data)-1), 0.5, eco_medium_green),
        ('VALIGN', (0, 0), (1, len(org_data)-1), 'MIDDLE'),
        ('FONTSIZE', (0, 1), (1, len(org_data)-1), 8),
    ]))
    
    impact_table = Table(impact_data, colWidths=[1.5*inch, 1.5*inch])
    impact_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (1, 0), eco_medium_green),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.white),
        ('ALIGN', (0, 0), (1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (1, 0), 10),
        ('SPAN', (0, 0), (1, 0)),
        ('BOTTOMPADDING', (0, 0), (1, 0), 6),
        ('BACKGROUND', (0, 1), (1, len(impact_data)-1), colors.white),
        ('GRID', (0, 0), (1, len(impact_data)-1), 0.5, eco_medium_green),
        ('VALIGN', (0, 0), (1, len(impact_data)-1), 'MIDDLE'),
        ('FONTSIZE', (0, 1), (1, len(impact_data)-1), 8),
    ]))
    
    # Create a table to hold both tables side by side
    info_table_data = [[org_table, impact_table]]
    info_table = Table(info_table_data, colWidths=[3*inch, 3*inch])
    info_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (1, 0), 'TOP'),
    ]))
    
    elements.append(info_table)
    elements.append(Spacer(1, 0.15*inch))
    
    # Items Summary with more compact styling
    elements.append(Paragraph('E-WASTE ITEMS SUMMARY', styles['CertificateSubTitle']))
    elements.append(Spacer(1, 0.05*inch))
    
    # Items table header
    items_data = [
        ['Item Type', 'Qty', 'Condition', 'Carbon Saved']
    ]
    
    # Add up to 10 items to the certificate (to avoid making it too long)
    max_items = 10
    for item in items[:max_items]:
        carbon = calculate_carbon_footprint(item.ewaste_type, item.quantity)
        items_data.append([
            item.ewaste_type.replace('-', ' '),
            str(item.quantity),
            item.condition.value,
            f'{carbon:.1f} kg'
        ])
    
    # If there are more items than shown, add a summary row
    if len(items) > max_items:
        remaining_items = len(items) - max_items
        remaining_carbon = sum(calculate_carbon_footprint(i.ewaste_type, i.quantity) for i in items[max_items:])
        items_data.append([
            f'+ {remaining_items} more items',
            f'{sum(i.quantity for i in items[max_items:])}',
            '(Various)',
            f'{remaining_carbon:.1f} kg'
        ])
    
    # Create the items table with green headers
    items_table = Table(items_data, colWidths=[2.5*inch, 0.8*inch, 1.2*inch, 1.5*inch])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (3, 0), eco_dark_green),
        ('TEXTCOLOR', (0, 0), (3, 0), colors.white),
        ('ALIGN', (0, 0), (3, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (3, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (3, 0), 9),
        ('BOTTOMPADDING', (0, 0), (3, 0), 6),
        ('TOPPADDING', (0, 0), (3, 0), 6),
        ('BACKGROUND', (0, 1), (3, len(items_data)-1), colors.white),
        ('GRID', (0, 0), (3, len(items_data)-1), 0.5, eco_medium_green),
        ('VALIGN', (0, 0), (3, len(items_data)-1), 'MIDDLE'),
        ('ALIGN', (1, 1), (3, len(items_data)-1), 'CENTER'),
        ('FONTSIZE', (0, 1), (3, len(items_data)-1), 8),
        # Add alternating row colors for better readability
        ('ROWBACKGROUNDS', (0, 1), (3, len(items_data)-1), [colors.white, eco_light_green]),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 0.15*inch))
    
    # Create a box for the certification statement
    certification_text = '''
    <b>CERTIFICATION STATEMENT</b><br/>
    This is to certify that the above-mentioned electronic waste items were collected and 
    processed in accordance with responsible e-waste management practices and applicable 
    environmental regulations. All data storage devices have been securely wiped or physically 
    destroyed as appropriate.
    '''
    cert_statement = Paragraph(certification_text, styles['Normal-Center'])
    cert_frame = Table([[cert_statement]], colWidths=[6*inch])
    cert_frame.setStyle(TableStyle([
        ('BOX', (0, 0), (0, 0), 1, eco_dark_green),
        ('BACKGROUND', (0, 0), (0, 0), eco_light_green),
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (0, 0), 10),
        ('BOTTOMPADDING', (0, 0), (0, 0), 10),
        ('LEFTPADDING', (0, 0), (0, 0), 10),
        ('RIGHTPADDING', (0, 0), (0, 0), 10),
    ]))
    elements.append(cert_frame)
    elements.append(Spacer(1, 0.15*inch))
    
    # Signature
    signature_data = [
        ['_______________________', '_______________________'],
        ['Authorized Signature', 'Date'],
        ['Ecycle Recycling Officer', '']
    ]
    
    signature_table = Table(signature_data, colWidths=[3*inch, 3*inch])
    signature_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (1, 2), 'CENTER'),
        ('VALIGN', (0, 0), (1, 2), 'MIDDLE'),
        ('FONTSIZE', (0, 1), (1, 2), 9),
        ('TEXTCOLOR', (0, 1), (1, 2), eco_dark_green),
    ]))
    elements.append(signature_table)
    elements.append(Spacer(1, 0.15*inch))
    
    # Footer with eco message
    footer_text = '''
    <i>Thank you for contributing to a sustainable future by responsibly recycling your electronic waste.</i>
    '''
    elements.append(Paragraph(footer_text, styles['Footer']))
    
    # Build the PDF with a green-themed border
    # Create a custom canvas to add the border
    class BorderedPage(canvas.Canvas):
        def __init__(self, *args, **kwargs):
            canvas.Canvas.__init__(self, *args, **kwargs)
            
        def showPage(self):
            self.saveState()
            # Draw a green border around the page
            self.setStrokeColor(eco_dark_green)
            self.setLineWidth(2)
            width, height = letter
            self.rect(20, 20, width - 40, height - 40)
            
            # Add a subtle eco leaf watermark
            self.setFillColor(eco_light_green)
            self.setFont("Helvetica", 8)
            self.drawRightString(width - 30, 30, "Ecycle - Sustainable E-Waste Management")
            
            self.restoreState()
            canvas.Canvas.showPage(self)
    
    # Build the PDF with our custom canvas
    buffer.seek(0)  # Reset buffer
    custom_canvas = BorderedPage(buffer)
    doc.build(elements, canvasmaker=lambda *args, **kwargs: BorderedPage(*args, **kwargs))
    
    # Reset buffer position to the beginning
    buffer.seek(0)
    
    return buffer
