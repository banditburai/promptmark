import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter, ImageEnhance, ImageChops
import io
import zipfile
import base64
import textwrap
import re
from functools import partial

default_overlay_settings = {
    'font_path': "Lato-Regular.ttf", 
    'font_size': 24,
    'text_color': '#000000',
    'wrap_width_percentage': 80,
    'line_spacing_percentage': 100,
    'stroke_width': 0,
    'stroke_color': '#FFFFFF',
    'tint': False,
    'include_overlay': True,
    'overlay_position': "Bottom",
    'brightness': 0,
    'uniform_padding_checkbox': False,
    'uniform_padding': 3.0,
    'vertical_padding': 3.0,
    'horizontal_padding': 3.0,
    'overlay_margin': 10,
    'tint_color': '#FFFFFF',
    'tint_opacity': 0.5
}


FONT_FILES = {
    "Lato-Regular.ttf",
    "Merriweather-Regular.ttf",
    "Orbitron-SemiBold.ttf",
    "Pacifico-Regular.ttf",
    "PlayfairDisplaySC-Bold.ttf",
    "Poppins-Bold.ttf"           
}


st.session_state['current_text'] = st.session_state.get('current_text', 'Select an image')

if 'overlay_settings' not in st.session_state:
    st.session_state.overlay_settings = default_overlay_settings.copy()

if 'selected_image_info' not in st.session_state:
    st.session_state.selected_image_info = {'image': None, 'text': None, 'filename': None}

if 'update_needed' not in st.session_state:
    st.session_state.update_needed = False    

def create_layout():
    foo = st.container()
    with foo:
        file_upload_container = st.container()
        image_display_container = st.container()
        image_download_container =st.container()
        image_selection_container = st.container()
        html_generation_container = st.container()
        text_area_container = st.sidebar.container()

    return {
        "file_upload": file_upload_container,
        "image_display": image_display_container,
        "image_download": image_download_container,
        "image_selection": image_selection_container,
        "html_generation": html_generation_container,
        "text_area": text_area_container
    }

def update_settings(key, value):
    # Update the specific setting
    st.session_state.overlay_settings[key] = value    
    st.session_state.update_needed = True

def update_watermark():
    setattr(st.session_state, 'update_needed', True)

def update_font_path():
    update_settings('font_path', st.session_state.font_path)

def update_font_size():
    update_settings('font_size', st.session_state.font_size)

def update_text_color():
    update_settings('text_color', st.session_state.text_color)

def update_stroke_color():
    update_settings('stroke_color', st.session_state.stroke_color)

def update_stroke_width():
    update_settings('stroke_width', st.session_state.stroke_width)

def update_wrap_width_percentage():
    update_settings('wrap_width_percentage', st.session_state.wrap_width_percentage)

def update_brightness():
    update_settings('brightness', st.session_state.brightness)

def update_tint():
    update_settings('tint', st.session_state.tint)

def update_tint_color():
    update_settings('tint_color', st.session_state.tint_color)

def update_tint_opacity():
    update_settings('tint_opacity', st.session_state.tint_opacity)

def update_overlay_position():
    update_settings('overlay_position', st.session_state.overlay_position)

def update_overlay_margin():
    update_settings('overlay_margin', st.session_state.overlay_margin)

def update_include_overlay():
    update_settings('include_overlay', st.session_state.include_overlay)


def handle_padding_update():
    # Use default values as fallbacks
    default_vertical_padding = default_overlay_settings['vertical_padding']
    default_horizontal_padding = default_overlay_settings['horizontal_padding']
    default_uniform_padding = default_overlay_settings['uniform_padding']

    if st.session_state.uniform_padding_checkbox:
        # Update to non-uniform padding values
        vertical_padding = st.session_state.get('vertical_padding', default_vertical_padding)
        horizontal_padding = st.session_state.get('horizontal_padding', default_horizontal_padding)
        st.session_state.overlay_settings['vertical_padding'] = vertical_padding
        st.session_state.overlay_settings['horizontal_padding'] = horizontal_padding
    else:
        # Update to uniform padding value
        uniform_padding = st.session_state.get('uniform_padding', default_uniform_padding)
        st.session_state.overlay_settings['vertical_padding'] = uniform_padding
        st.session_state.overlay_settings['horizontal_padding'] = uniform_padding

    st.session_state.update_needed = True

def process_image(image, text, settings):    
    expected_keys = ['font_path', 'font_size', 'text_color', 'wrap_width_percentage', 'stroke_width', 'stroke_color', 'overlay_position', 'brightness', 'vertical_padding', 'horizontal_padding', 'overlay_margin', 'tint_color', 'tint_opacity', 'line_spacing_percentage']
    filtered_settings = {key: settings[key] for key in expected_keys if key in settings}
    image_copy = image.copy()
    if not settings['include_overlay']:
        return add_watermark(image, user_name, settings['font_path'], 24, settings['text_color'], settings['overlay_position'])
    
    updated_image = overlay_text_on_image(image_copy, text, **filtered_settings)
    if user_name:
        updated_image = add_watermark(updated_image, user_name, filtered_settings['font_path'], 24, settings['text_color'], filtered_settings['overlay_position'])    
    return updated_image


def update_selected_image():
    if st.session_state.update_needed and st.session_state.selected_image_info['image']:                
        processed_image = process_image(
            st.session_state.selected_image_info['image'],
            st.session_state.selected_image_info['text'],            
            st.session_state.overlay_settings
        )        
        # layout['image_display'].image(processed_image, caption="Current", use_column_width=True)
        
        st.session_state.processed_image = processed_image
        st.session_state.update_needed = False

def update_text(data):
   st.session_state['current_text'] = data['description']
   st.session_state['selected_image_info'] = {
       'image': data['image'].convert("RGB"),
       'text': data['description'],
       'filename': data['filename']
   }
   st.session_state['update_needed'] = True
   update_selected_image()

def prepare_download():
    if 'processed_image' in st.session_state and st.session_state.processed_image is not None:
        buffer = io.BytesIO()
        st.session_state.processed_image.save(buffer, format='PNG')
        buffer.seek(0)
        filename = st.session_state.selected_image_info.get('filename', 'downloaded_image.png')
        return buffer, f"overlay_{filename}"
    else:
        return None, None


def select_and_display_image(data):
    pass
       

def update_temp_description():
    st.session_state.selected_image_info['text'] = st.session_state.current_text
    st.session_state.update_needed = True
    update_selected_image() 


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

def overlay_text_on_image(image, text, font_path, font_size, text_color, wrap_width_percentage, stroke_width, stroke_color, overlay_position, brightness, vertical_padding, horizontal_padding, overlay_margin, tint_color, tint_opacity, line_spacing_percentage):
    font = ImageFont.truetype(font_path, font_size)

    # Convert padding percentages to pixel values
    vertical_padding_px = int(image.height * (vertical_padding / 100))
    horizontal_padding_px = int(image.width * (horizontal_padding / 100))

    line_height = font.getbbox('Ay')[3]
    line_spacing = int(line_height * (line_spacing_percentage / 100.0))

    # Calculate the width of the area to wrap the text in pixels
    adjusted_wrap_percentage = min(1.6, (wrap_width_percentage/ 100) * 1.2) 
    wrap_area_width_px = int(image.width * adjusted_wrap_percentage)    
    average_char_width = sum(font.getbbox(char)[2] for char in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ') / 52
    wrap_width_chars = max(1, int(wrap_area_width_px / average_char_width))    
    wrapped_text = textwrap.fill(text, width=wrap_width_chars)
    wrapped_lines = wrapped_text.split('\n')    
    max_line_width = max(font.getbbox(line)[2] for line in wrapped_lines)
    text_block_height = sum([font.getbbox(line)[3] + font.getbbox(line)[1] for line in wrapped_lines]) + (len(wrapped_lines) - 1) * (line_spacing - line_height)

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
    if st.session_state.overlay_settings.get('tint', False):
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
        current_y += line_spacing  # Increment y position for the next line

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
user_name = st.sidebar.text_input("Corner text:", on_change= update_watermark )

# Font settings inside an expander
with st.sidebar.expander("Text Styling options", True):
    font_path = st.selectbox("Select a font:", options=FONT_FILES, key="font_path", format_func=lambda name: name.split('-')[0], on_change=update_font_path)
    

    wrap_width_percentage = st.slider("Wrap width percentage", 10, 100, 80, key="wrap_width_percentage",format="%.0f%%", on_change=update_wrap_width_percentage,                                     
                                      help="Adjust the width of the text wrap. At 90%, the text spans almost the full width.")
    line_spacing = st.slider("Line Spacing Percentage", 50, 150, 100, key="line_spacing_percentage", format="%.0f%%", on_change=lambda: update_settings('line_spacing_percentage', st.session_state.line_spacing_percentage))
    
    col1, col2 = st.columns([1, 4])
    with col1:
        text_color = st.color_picker("Text", '#000000', key="text_color", on_change=update_text_color)
    with col2:
        font_size = st.slider("Font size", 10, 100, 24, key="font_size", on_change=update_font_size)

    col3, col4 = st.columns([1, 4])
    with col3:
        stroke_color = st.color_picker("Stroke", '#FFFFFF', key="stroke_color", on_change= update_stroke_color)
    with col4:
        stroke_width = st.slider("Stroke Width", 0, 20, 0, key="stroke_width", on_change= update_stroke_width)

# Overlay positioning and styling settings inside another expander
with st.sidebar.expander("Overlay Positioning & Styling", False):
    overlay_description = st.checkbox("Include Overlay", True, key="include_overlay", on_change= update_include_overlay,                                   
                                      help="Toggle this to add or remove the text overlay on the image.")    
    brightness = st.slider("Brightness/Darkness", -255, 255, 0,
                           key="brightness", on_change= update_brightness,
                           help="Adjust the brightness or darkness of the overlay background."
    )
    tint = st.checkbox("Apply Tint", key="tint", on_change= update_tint)
    tint_color = '#FFFFFF'  # Default tint color
    tint_opacity = 0.5
    if tint:        
        col1, col2 = st.columns([1,4])
        with col1:
            tint_color = st.color_picker("Tint Color", '#FFFFFF', key="tint_color", on_change= update_tint_color)
        with col2:
            tint_opacity = st.slider("Tint Opacity", 0.0, 1.0, 0.5, help="Adjust the opacity of the color tint.", key="tint_opacity", on_change= update_tint_opacity,                                     
                                     )

    overlay_position = st.selectbox("Overlay Position", ["Bottom", "Top"],
                                    key="overlay_position", on_change= update_overlay_position,                            
                                    help="Select where to position the overlay text: at the top or bottom of the image."
    )

    overlay_margin = st.slider(
        "Overlay Margin (%)", 0, 100, 10, key="overlay_margin", on_change= update_overlay_margin,    
        help="Adjust the margin as a percentage of the total height divided by two. At 100%, the overlay centers in the middle."
    )

    split_padding = st.checkbox("Non-uniform Padding", key="uniform_padding_checkbox", on_change= handle_padding_update)
    if split_padding:
        vertical_padding = st.slider(
            "Vertical Padding (Top/Bottom)", 0.0, 5.0, 3.0, step=0.01, format="%.2f%%", key="vertical_padding", on_change= handle_padding_update,
            )
        horizontal_padding = st.slider(
            "Horizontal Padding (Left/Right)", 0.0, 5.0, 3.0, step=0.01, format="%.2f%%", key ="horizontal_padding", on_change= handle_padding_update,
            )
    else:
        uniform_padding = st.slider(
            "Uniform Padding (All Sides)", 0.0, 5.0, 3.0, step=0.01, format="%.2f%%", key = "uniform_padding", on_change= handle_padding_update,
            )
        vertical_padding = horizontal_padding = uniform_padding


layout = create_layout()

with layout["text_area"]:
    # Create text area without directly assigning to session state variable
    edited_text = st.text_area("Edit Description:", value=st.session_state.current_text, key="current_text", on_change=update_temp_description)
    # Update the session state variable if text area content is changed
    if edited_text != st.session_state.current_text:
        st.session_state.current_text = edited_text

with layout["file_upload"]:
    uploaded_files = st.file_uploader("Upload ZIP files containing images", type=['png', 'zip'], accept_multiple_files=True)

all_image_data=[]

with layout["image_display"]:    
    if st.session_state.update_needed:
        update_selected_image()                
    # Always display the processed image if it exists
    if 'processed_image' in st.session_state and st.session_state.processed_image is not None:
        st.image(st.session_state.processed_image, caption="Current", use_column_width=True)


with layout["image_download"]:
    buffer, filename = prepare_download()
    if buffer and filename:
        st.download_button(
            label="Download Image",
            data=buffer,
            file_name=filename,
            mime="image/png"
        )

with layout["image_selection"]:
    if uploaded_files:
        all_image_data, html_file_name, total_images = process_images(uploaded_files)
        
        # Display each uploaded image with an option to select for overlay
        for idx, data in enumerate(all_image_data):
            cols = st.columns([1, 3, 1])
            cols[0].image(f"data:image/png;base64,{data['thumbnail']}", use_column_width=True, width=150)        
            cols[1].write( textwrap.fill(data['description'], width=50))

            # Button to select the image for overlay
            select_button = partial(update_text, data)
            if cols[2].button(f"Select Img {idx}", key=f"btn_select_{idx}",  on_click=select_button):                                                
                select_and_display_image(data)
                

with layout["html_generation"]:    
    if all_image_data:
        custom_title = st.text_input("Enter a custom title for the HTML file:", "My Image Collection")
        if custom_title and st.button('Generate HTML'):
            html_content = create_html_table(all_image_data, custom_title)
            st.download_button(
                label="Download HTML",
                data=html_content,
                file_name=html_file_name,
                mime="text/html"
            )
        elif not custom_title:
            st.warning("Please enter a custom title to enable HTML download.")