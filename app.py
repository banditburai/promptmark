import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter, ImageEnhance, ImageChops
import io
import zipfile
import base64
import textwrap
import re

def adjust_brightness(input_img, brightness=0):
    enhancer = ImageEnhance.Brightness(input_img)
    # Brightness is a value between 0.0 (black image) and 2.0 or higher (increased brightness), with 1 being the original image
    adjusted_img = enhancer.enhance(1 + brightness / 255)
    return adjusted_img

def add_color_tint(image, tint_color, opacity=0.5):
    tint_layer = Image.new("RGBA", image.size, tint_color)
    return ImageChops.blend(image, tint_layer, opacity)

def create_html_table(image_data, custom_title):
    # Start the HTML content with CSS
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
    <style>
    body {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        margin: 0;
        padding: 0;
        color: #333;
        max-width: 1000px;
        margin: auto;
        box-sizing: border-box;
    }
    h1 {
        text-align: center;
        font-size: 24px;
        margin-top: 50px;
    }
    table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 20px;
        margin-bottom: 50px;
    }
    table, th, td {
        border: 1px solid #ddd;
    }
    th, td {
        text-align: left;
        padding: 8px;
    }
    tr:nth-child(even) {
        background-color: #f2f2f2;
    }
    img {
        width: 100px;
        height: auto;
        object-fit: contain;
    }
    .selectable {
        user-select: all; 
        cursor: pointer;
    }
    @media print {
        body {
            color: #000;
        }
        table {
            width: 100%;
            border: 1px solid #000;
        }
        th, td {
            border: 1px solid #000;
            padding: 10px;
        }
    }
    @media only screen and (max-width: 600px) {
        body {
            max-width: 100%;
            padding: 10px;
            font-size: 16px;
        }
        h1 {
            font-size: 20px;
            margin-top: 20px;
        }
        table {
            margin-top: 10px;
            margin-bottom: 20px;
        }
        img {
            width: 80px; /* smaller images on mobile */
        }
        th, td {
            padding: 5px; /* smaller padding on mobile */
        }
        .selectable {
            font-size: 14px; /* larger font size for readability on mobile */
        }
    }
    </style>
    <script>
    function copyToClipboard(text) {
        navigator.clipboard.writeText(text).then(function() {
             alert('Copied to clipboard: ' + text);
        }).catch(function(error) {
            console.log('Copy to clipboard failed: ' + error);
        });
    }
    </script>
    </head>
    <body>
    <h1>""" + custom_title + """</h1>
    <table>
    """

    # Add rows for each image
    for data in image_data:
        # Split description to get text before Job ID
        description_text = data['description']
        job_id = data['job_id']

        # Add row to HTML table
        html_content += f"""
        <tr>
            <td><img src='data:image/png;base64,{data['thumbnail']}' onclick="copyToClipboard('{job_id}')"/></td>
            <td onclick="copyToClipboard('{description_text}')" class="selectable">{description_text}</td>
        </tr>
        """

    # Close the table and HTML tags
    html_content += "</table></body></html>"

    return html_content

def add_watermark(image, watermark_text, font_path, font_size, stroke_color, overlay_position):
    width, height = image.size
    stroke_width=3
    watermark_font = ImageFont.truetype(font_path, font_size)
    # Create an image for the text to get the exact size of the text box needed
    text_image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(text_image)

    # Estimate size of watermark text
    text_bbox = draw.textbbox((0, 0), watermark_text, font=watermark_font, stroke_width=stroke_width)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]

    # Calculate position for watermark to avoid being cut off
    x = max(width - text_width - stroke_width - 10, 0)  # 10 pixels from the right edge
    if overlay_position == "Top":
        y = 10 
    else:
        y = max(height - text_height - stroke_width - 10, 0)  # Place watermark at the bottom edge


    # Draw stroke-only text
    draw.text((x, y), watermark_text, font=watermark_font, fill=(0, 0, 0, 0), stroke_width=stroke_width, stroke_fill=stroke_color)

    # Paste the text image onto the original image with transparency
    image.paste(text_image, (0, 0), text_image)

    return image

def overlay_text_on_image(image, text, font_path, font_size, text_color, wrap_width_percentage, stroke_width, stroke_color, overlay_position, brightness, vertical_padding, horizontal_padding, overlay_margin, tint_color, tint_opacity):
    font = ImageFont.truetype(font_path, font_size)

    # Convert padding percentages to pixel values
    vertical_padding_px = int(image.height * (vertical_padding / 100))
    horizontal_padding_px = int(image.width * (horizontal_padding / 100))

    # Calculate the width of the area to wrap the text in pixels
    adjusted_wrap_percentage = min(1.6, wrap_width_percentage * 1.2) 
    wrap_area_width_px = int(image.width * adjusted_wrap_percentage)    
    average_char_width = sum(font.getbbox(char)[2] for char in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ') / 52
    wrap_width_chars = max(1, int(wrap_area_width_px / average_char_width))    
    wrapped_text = textwrap.fill(text, width=wrap_width_chars)
    wrapped_lines = wrapped_text.split('\n')    
    max_line_width = max(font.getbbox(line)[2] for line in wrapped_lines)
    text_block_height = sum([font.getbbox(line)[3] + font.getbbox(line)[1] for line in wrapped_lines])

    # Calculate the width and height of the blurred background
    bg_width = max_line_width + horizontal_padding_px * 2
    bg_height = text_block_height + vertical_padding_px * 2

    # Convert margin percentage to pixel value and calculate the position
    max_margin = (image.height - bg_height) / 2
    overlay_margin_px = int(max_margin * (overlay_margin / 100))

    # Calculate the position for the background
    bg_x = (image.width - bg_width) // 2
    if overlay_position == "Top":
        bg_y = overlay_margin_px
    else:
        bg_y = image.height - bg_height - overlay_margin_px

    # Crop and blur the background area
    cropped_area = image.crop((bg_x, bg_y, bg_x + bg_width, bg_y + bg_height))
    blurred_background = cropped_area.filter(ImageFilter.GaussianBlur(radius=min(horizontal_padding_px, vertical_padding_px) // 2)).convert("RGBA")

    # Adjust the brightness if needed
    if brightness != 0:
        blurred_background = adjust_brightness(blurred_background, brightness)
        # blurred_background = blend_with_color(blurred_background, brightness)
    if tint:
        blurred_background = add_color_tint(blurred_background, tint_color, tint_opacity)
    
    # Create a mask for the blurred background to maintain rounded corners
    corner_radius = max(vertical_padding_px, horizontal_padding_px) // 2
    mask = Image.new("L", (bg_width, bg_height), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([(0, 0), (bg_width, bg_height)], radius=corner_radius, fill=255)

    # Paste the blurred background onto the original image
    image.paste(blurred_background, (bg_x, bg_y), mask)

    # Draw the wrapped text over the blurred background
    draw = ImageDraw.Draw(image)
    current_y = bg_y + vertical_padding_px
    for line in wrapped_lines:
        text_width = font.getbbox(line)[2]
        text_x = (image.width - text_width) // 2

        # Outline text if stroke width is greater than 0
        if stroke_width > 0:
            draw.text((text_x, current_y), line, font=font, fill=stroke_color, stroke_width=stroke_width)

        # Draw the main text
        draw.text((text_x, current_y), line, fill=text_color, font=font)
        current_y += font.getbbox(line)[3] + font.getbbox(line)[1]  # Increment y position for the next line

    return image



def extract_job_id(metadata):
    # Attempt to find a job ID in the image metadata description
    description = metadata.get('Description', '')
    job_id_match = re.search(r"Job ID: ([\w-]+)", description)
    return job_id_match.group(1) if job_id_match else "No Job ID Found"

def process_images(uploaded_files):
    image_data = []
    dates = set()
    total_images = 0

    for uploaded_file in uploaded_files:
        match = re.search(r"(\d{4}-\d{1,2}-\d{1,2})_\[(\d+)-(\d+)\]", uploaded_file.name)
        if match:
            dates.add(match.group(1))
            start_range, end_range = int(match.group(2)), int(match.group(3))
            total_images += (end_range - start_range + 1)

        if zipfile.is_zipfile(uploaded_file):
            with zipfile.ZipFile(uploaded_file, 'r') as z:
                for file_name in z.namelist():
                    if file_name.lower().endswith('.png'):
                        with z.open(file_name) as image_file:
                            img = Image.open(image_file)
                            img_copy = img.copy()  # Create a copy of the image
                            metadata = img.info
                            job_id = extract_job_id(metadata)
                            description = metadata.get('Description', 'No Description Found').split('Job ID:')[0].strip()
                            img_copy.thumbnail((100, 100))
                            thumb_buffer = io.BytesIO()
                            img_copy.save(thumb_buffer, format="PNG")
                            thumbnail = base64.b64encode(thumb_buffer.getvalue()).decode('utf-8')
                            image_data.append({
                                'image': img,  # Store the original image object
                                'filename': file_name,
                                'thumbnail': thumbnail,
                                'description': description,
                                'job_id': job_id,
                                'is_zip': True
                            })
        else:
            img = Image.open(uploaded_file)
            total_images += 1
            img_copy = img.copy()
            metadata = img.info
            job_id = extract_job_id(metadata)
            description = metadata.get('Description', 'No Description Found').split('Job ID:')[0].strip()
            img_copy.thumbnail((100, 100))
            thumb_buffer = io.BytesIO()
            img_copy.save(thumb_buffer, format="PNG")
            thumbnail = base64.b64encode(thumb_buffer.getvalue()).decode('utf-8')
            image_data.append({
                'image': img,
                'filename': uploaded_file.name,
                'thumbnail': thumbnail,
                'description': description,
                'job_id': job_id,
                'is_zip': False
            })

    if dates:
        dates_str = '_'.join(sorted(dates))
        html_file_name = f"{dates_str}-[{total_images}].html"
    else:
        html_file_name = "image_metadata.html"

    return image_data, html_file_name, total_images

st.title("PromptMark Studio")


st.sidebar.title("Overlay Settings")
user_name = st.sidebar.text_input("Corner text:")
FONT_FILES = {
    "Lato-Regular": "Lato-Regular.ttf",
    "Merriweather-Regular": "Merriweather-Regular.ttf",
    "Orbitron-SemiBold": "Orbitron-SemiBold.ttf",
    "Pacifico-Regular": "Pacifico-Regular.ttf",
    "PlayfairDisplaySC-Bold": "PlayfairDisplaySC-Bold.ttf",
    "Poppins-Bold": "Poppins-Bold.ttf",        
   
}

# Font settings inside an expander
with st.sidebar.expander("Text Styling options", True):
    selected_font_display_name = st.selectbox("Select a font:", list(FONT_FILES.keys()),
                                              help="Choose a font style for the text.")
    selected_font = FONT_FILES[selected_font_display_name]
    wrap_width_percentage = st.slider("Wrap width percentage", 0.1, 1.0, 0.8,
                                      help="Adjust the width of the text wrap. At 90%, the text spans almost the full width.")

    col1, col2 = st.columns([1, 4])
    with col1:
        text_color = st.color_picker("Text", '#000000')
    with col2:
        font_size = st.slider("Font size", 10, 100, 24)

    col3, col4 = st.columns([1, 4])
    with col3:
        stroke_color = st.color_picker("Stroke", '#FFFFFF')
    with col4:
        stroke_width = st.slider("Stroke Width", 0, 20, 0)

# Overlay positioning and styling settings inside another expander
with st.sidebar.expander("Overlay Positioning & Styling", False):
    overlay_description = st.checkbox("Include Overlay", True,
                                      help="Toggle this to add or remove the text overlay on the image.")
    brightness = st.slider("Brightness/Darkness", -255, 255, 0,
                           help="Adjust the brightness or darkness of the overlay background."
    )
    tint = st.checkbox("Apply Tint")
    tint_color = '#FFFFFF'  # Default tint color
    tint_opacity = 0.5
    if tint:        
        col1, col2 = st.columns([1,4])
        with col1:
            tint_color = st.color_picker("Tint Color", '#FFFFFF')
        with col2:
            tint_opacity = st.slider("Tint Opacity", 0.0, 1.0, 0.5, help="Adjust the opacity of the color tint.")

    overlay_position = st.selectbox("Overlay Position", ["Bottom", "Top"],
                                    help="Select where to position the overlay text: at the top or bottom of the image."
    )

    overlay_margin = st.slider(
        "Overlay Margin (%)", 0, 100, 10,
        help="Adjust the margin as a percentage of the total height divided by two. At 100%, the overlay centers in the middle."
    )

    split_padding = st.checkbox("Non-uniform Padding")
    if split_padding:
        vertical_padding = st.slider(
            "Vertical Padding (Top/Bottom)", 0.0, 5.0, 3.0, step=0.01, format="%.2f%%")
        horizontal_padding = st.slider(
            "Horizontal Padding (Left/Right)", 0.0, 5.0, 3.0, step=0.01, format="%.2f%%")
    else:
        uniform_padding = st.slider(
            "Uniform Padding (All Sides)", 0.0, 5.0, 3.0, step=0.01, format="%.2f%%")
        vertical_padding = horizontal_padding = uniform_padding

    

# st.image("path/to/hero_image.png", use_column_width=True)

# File uploader
uploaded_files = st.file_uploader("Upload ZIP files containing images", type=['png','zip'], accept_multiple_files=True)

# Process uploaded files and display UI for each image
if uploaded_files:
    all_image_data, html_file_name, total_images = process_images(uploaded_files)

    for idx, data in enumerate(all_image_data):
        cols = st.columns([1, 3, 1])
        cols[0].image(f"data:image/png;base64,{data['thumbnail']}", use_column_width=True, width=150)
        wrapped_description = textwrap.fill(data['description'], width=50)
        cols[1].write(wrapped_description)

        if cols[2].button(f"Overlay {idx}", key=f"btn_overlay_{idx}"):
            img = data['image'].convert("RGB")            
            if overlay_description:
                img = overlay_text_on_image(
            img, data['description'], selected_font, font_size, text_color,
            wrap_width_percentage, stroke_width, stroke_color, overlay_position,
            brightness, vertical_padding, horizontal_padding, overlay_margin, tint_color, tint_opacity
        )            
            if user_name:  # Only add watermark if user has entered a name
                img = add_watermark(
                    img, user_name, selected_font, 24, text_color, overlay_position
                )
            cols[1].image(img, use_column_width=True, caption=f"Overlayed {data['filename']}")
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            download_button = cols[2].download_button(
                label="Download Image",
                data=buffer.getvalue(),
                file_name=f"overlay_{data['filename']}",
                mime="image/png"
            )

    # Create HTML content and download button
    if all_image_data:
        custom_title = st.text_input("Enter a custom title for the HTML file:", "My Image Collection")
        # Only show the download button if a custom title has been entered
        if custom_title:
            # When the button is pressed, generate the HTML with the custom title
            if st.button('Generate HTML'):
                html_content = create_html_table(all_image_data, custom_title)
                
                st.download_button(
                    label="Download HTML",
                    data=html_content,
                    file_name=html_file_name,
                    mime="text/html"
                )
        else:
            st.warning("Please enter a custom title to enable HTML download.")