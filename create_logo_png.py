from PIL import Image, ImageDraw, ImageFont
import os

# Create a directory for the logo if it doesn't exist
os.makedirs('static/img', exist_ok=True)

# Create a blank image with a green background
width, height = 300, 300
image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
draw = ImageDraw.Draw(image)

# Draw a green circle
center_x, center_y = width // 2, height // 2
radius = 130
circle_color = (30, 142, 62, 255)  # Green color
draw.ellipse((center_x - radius, center_y - radius, center_x + radius, center_y + radius), fill=circle_color)

# Try to add "ECYCLE" text
try:
    # Try to use a font if available
    font_size = 48
    try:
        font = ImageFont.truetype('Arial', font_size)
    except:
        # Fall back to default font
        font = ImageFont.load_default()
    
    # Add "ECYCLE" text
    text = "ECYCLE"
    text_width = draw.textlength(text, font=font)
    text_x = (width - text_width) // 2
    text_y = center_y + 40
    draw.text((text_x, text_y), text, fill=(255, 255, 255), font=font)
    
except Exception as e:
    print(f"Error adding text: {str(e)}")

# Draw a simple recycling symbol
recycle_color = (255, 255, 255, 255)  # White

# Draw three arrows in a triangle pattern
arrow_width = 15
arrow_length = 40
arrow_head_size = 15

# First arrow
start_x1, start_y1 = center_x - 40, center_y + 20
end_x1, end_y1 = center_x, center_y - 40
draw.line((start_x1, start_y1, end_x1, end_y1), fill=recycle_color, width=arrow_width)
draw.polygon([(end_x1, end_y1), (end_x1 - arrow_head_size, end_y1 + arrow_head_size), 
              (end_x1 + arrow_head_size, end_y1 + arrow_head_size)], fill=recycle_color)

# Second arrow
start_x2, start_y2 = center_x, center_y - 40
end_x2, end_y2 = center_x + 40, center_y + 20
draw.line((start_x2, start_y2, end_x2, end_y2), fill=recycle_color, width=arrow_width)
draw.polygon([(end_x2, end_y2), (end_x2 - arrow_head_size, end_y2 - arrow_head_size), 
              (end_x2 - arrow_head_size, end_y2 + arrow_head_size)], fill=recycle_color)

# Third arrow
start_x3, start_y3 = center_x + 40, center_y + 20
end_x3, end_y3 = center_x - 40, center_y + 20
draw.line((start_x3, start_y3, end_x3, end_y3), fill=recycle_color, width=arrow_width)
draw.polygon([(end_x3, end_y3), (end_x3 + arrow_head_size, end_y3 - arrow_head_size), 
              (end_x3 + arrow_head_size, end_y3 + arrow_head_size)], fill=recycle_color)

# Save the image as PNG
image.save('static/img/ecycle-logo.png')
print("Logo created at static/img/ecycle-logo.png")