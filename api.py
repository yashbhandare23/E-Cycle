import os
import json
import random
from PIL import Image
from datetime import datetime

# Check if Roboflow API key is available
api_key = os.environ.get('ROBOFLOW_API_KEY')
HAS_API_KEY = bool(api_key)

# Only import and initialize the client if API key is available
if HAS_API_KEY:
    try:
        from inference_sdk import InferenceHTTPClient
        CLIENT = InferenceHTTPClient(
            api_url="https://detect.roboflow.com",
            api_key=api_key
        )
    except ImportError:
        HAS_API_KEY = False

# Complete list of e-waste types from Roboflow
EWASTE_TYPES = [
    "Air-Conditioner", "Bar-Phone", "Battery", "Blood-Pressure-Monitor", "Boiler", 
    "CRT-Monitor", "CRT-TV", "Calculator", "Camera", "Ceiling-Fan", "Christmas-Lights", 
    "Clothes-Iron", "Coffee-Machine", "Compact-Fluorescent-Lamps", "Computer-Keyboard", 
    "Computer-Mouse", "Cooled-Dispenser", "Cooling-Display", "Dehumidifier", "Desktop-PC", 
    "Digital-Oscilloscope", "Dishwasher", "Drone", "Electric-Bicycle", "Electric-Guitar", 
    "Electrocardiograph-Machine", "Electronic-Keyboard", "Exhaust-Fan", "Flashlight", 
    "Flat-Panel-Monitor", "Flat-Panel-TV", "Floor-Fan", "Freezer", "Glucose-Meter", 
    "HDD", "Hair-Dryer", "Headphone", "LED-Bulb", "Laptop", "Microwave", "Music-Player", 
    "Neon-Sign", "Network-Switch", "Non-Cooled-Dispenser", "Oven", "PCB", 
    "Patient-Monitoring-System", "Photovoltaic-Panel", "PlayStation-5", "Power-Adapter", 
    "Printer", "Projector", "Pulse-Oximeter", "Range-Hood", "Refrigerator", "Rotary-Mower",
    "Router", "SSD", "Server", "Smart-Watch", "Smartphone", "Smoke-Detector", 
    "Soldering-Iron", "Speaker", "Stove", "Straight-Tube-Fluorescent-Lamp", "Street-Lamp", 
    "TV-Remote-Control", "Table-Lamp", "Tablet", "Telephone-Set", "Toaster", "Tumble-Dryer", 
    "USB-Flash-Drive", "Vacuum-Cleaner", "Washing-Machine", "Xbox-Series-X"
]

def generate_mock_results(image_path):
    """
    Generate smart mock classification results when API is not available
    Uses simple image analysis to make a more educated guess
    
    Args:
        image_path (str): Path to the image file
        
    Returns:
        dict: Mock classification results
    """
    # Get image info
    try:
        img = Image.open(image_path)
        width, height = img.size
        
        # Common e-waste types for demonstration
        common_types = [
            "Laptop", "Smartphone", "Desktop-PC", "Tablet", "Flat-Panel-Monitor",
            "Printer", "Camera", "Refrigerator", "Battery"
        ]
        
        # Default to a common type with high confidence
        ewaste_type = "Laptop"
        confidence = 0.92
        
        # Do some very basic image analysis to make a slightly more educated guess
        # This is not real classification, just a simple heuristic based on image dimensions and color
        aspect_ratio = width / height if height > 0 else 1
        
        # Convert to RGB if the image has an alpha channel
        if img.mode == 'RGBA':
            img = img.convert('RGB')
        
        # Get the average color (very simplistic approach)
        pixel_data = list(img.resize((1, 1)).getdata()[0])
        avg_color = sum(pixel_data) / len(pixel_data) if pixel_data else 128
        
        # Simple heuristics based on aspect ratio and color
        if 0.9 < aspect_ratio < 1.1:  # Square-ish
            if avg_color < 100:  # Dark
                ewaste_type = "Computer-Mouse"
                confidence = 0.85
            else:
                ewaste_type = "Battery"
                confidence = 0.88
        elif aspect_ratio > 1.5:  # Wide
            ewaste_type = "Laptop"
            confidence = 0.94
        elif aspect_ratio < 0.7:  # Tall
            ewaste_type = "Smartphone"
            confidence = 0.91
        elif width > 1000 and height > 800:  # Large image
            ewaste_type = "Flat-Panel-Monitor"
            confidence = 0.89
        
        # Override type if the user explicitly mentioned "laptop" in the path
        if "laptop" in image_path.lower():
            ewaste_type = "Laptop"
            confidence = 0.97
        elif "phone" in image_path.lower() or "smartphone" in image_path.lower():
            ewaste_type = "Smartphone"
            confidence = 0.96
        elif "monitor" in image_path.lower() or "display" in image_path.lower():
            ewaste_type = "Flat-Panel-Monitor"
            confidence = 0.95
                
    except Exception as e:
        print(f"Error analyzing image: {str(e)}, defaulting to simple mock")
        width, height = 640, 480
        ewaste_type = "Laptop"  # Default to laptop if analysis fails
        confidence = 0.85
    
    # Create mock bounding box
    box_width = int(width * 0.7)
    box_height = int(height * 0.7)
    x = int((width - box_width) * 0.15)
    y = int((height - box_height) * 0.15)
    
    # Generate mock result in the format similar to Roboflow API
    mock_result = {
        "time": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f"),
        "image": {
            "width": width,
            "height": height
        },
        "predictions": [
            {
                "x": x + box_width/2,
                "y": y + box_height/2,
                "width": box_width,
                "height": box_height,
                "class": ewaste_type,
                "confidence": confidence
            }
        ]
    }
    
    print(f"Mock classification: {ewaste_type} with confidence {confidence:.2f}")
    return mock_result

def classify_image(image_path):
    """
    Classify an e-waste image using Roboflow API or mock results
    
    Args:
        image_path (str): Path to the image file
        
    Returns:
        dict: Classification results
    """
    if HAS_API_KEY:
        try:
            result = CLIENT.infer(image_path, model_id="e-waste-dataset-r0ojc/43")
            print("Used Roboflow API for classification")
            return result
        except Exception as e:
            print(f"Error using Roboflow API: {str(e)}, using mock data instead")
            return generate_mock_results(image_path)
    else:
        print("Roboflow API key not available, using mock data for classification")
        return generate_mock_results(image_path)
