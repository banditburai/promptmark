import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter
import io
import zipfile
import base64
import textwrap
import re



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

def add_watermark(image, watermark_text, font_path, font_size, stroke_color):
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
    y = max(height - text_height - stroke_width - 10, 0)  # 10 pixels from the bottom edge

    # Draw stroke-only text
    draw.text((x, y), watermark_text, font=watermark_font, fill=(0, 0, 0, 0), stroke_width=stroke_width, stroke_fill=stroke_color)

    # Paste the text image onto the original image with transparency
    image.paste(text_image, (0, 0), text_image)

    return image
def overlay_text_on_image(image, text, font_path, font_size, text_color, wrap_width_percentage, stroke_width, stroke_color):
    font = ImageFont.truetype(font_path, font_size)

    blur_padding_percentage= 0.03
    # Calculate the width of the area to wrap the text in pixels
    wrap_area_width_px = int(image.width * wrap_width_percentage)

    # Estimate character width to calculate wrap width in characters
    average_char_width = sum(font.getbbox(char)[2] for char in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ') / 52
    wrap_width_chars = max(1, int(wrap_area_width_px / average_char_width))  # at least one character

    # Wrap the text
    wrapped_text = textwrap.fill(text, width=wrap_width_chars)
    wrapped_lines = wrapped_text.split('\n')

    # Measure the width of the text block (longest line)
    max_line_width = max(font.getbbox(line)[2] for line in wrapped_lines)

    # Measure the height of the text block
    text_block_height = sum([font.getbbox(line)[3] + font.getbbox(line)[1] for line in wrapped_lines])

    # Calculate padding based on the image's width and blur padding percentage
    blur_padding = int(image.width * blur_padding_percentage)

    # Calculate the width and height of the blurred background
    bg_width = max_line_width + blur_padding * 2
    bg_height = text_block_height + blur_padding * 2

    # Calculate the position for the background
    bg_x = max((image.width - bg_width) // 2, 0)
    bg_y = max(image.height - bg_height - blur_padding, 0)

    # Crop and blur the background area
    cropped_area = image.crop((bg_x, bg_y, bg_x + bg_width, bg_y + bg_height))
    blurred_background = cropped_area.filter(ImageFilter.GaussianBlur(radius=blur_padding // 2)).convert("RGBA")

    # Create a mask for the blurred background to maintain rounded corners
    mask = Image.new("L", (bg_width, bg_height), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([(0, 0), (bg_width, bg_height)], radius=blur_padding, fill=255)

    # Paste the blurred background onto the original image
    image.paste(blurred_background, (bg_x, bg_y), mask)

    # Draw the wrapped text over the blurred background
    draw = ImageDraw.Draw(image)
    current_y = bg_y + blur_padding
    for line in wrapped_lines:
        text_width = font.getbbox(line)[2]
        text_x = (image.width - text_width) // 2

        if stroke_width > 0:
            # Outline text
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
FONT_FILES = {
    "PlayfairDisplaySC-Bold": "PlayfairDisplaySC-Bold.ttf",
    "Poppins-Bold": "Poppins-Bold.ttf",
    "Merriweather-Regular": "Merriweather-Regular.ttf",
    "Lato-Regular": "Lato-Regular.ttf",
    "Pacifico-Regular": "Pacifico-Regular.ttf",
    "Orbitron-SemiBold": "Orbitron-SemiBold.ttf"
}

# Use Streamlit's selectbox to let the user select a font
selected_font_display_name = st.sidebar.selectbox("Select a font:", list(FONT_FILES.keys()))

# Map the selected friendly font name to its .ttf file path
selected_font = FONT_FILES[selected_font_display_name]
wrap_width_percentage = st.sidebar.slider("Wrap width percentage", 0.1, 1.0, 0.8)
# Create columns for the text color and text size
col1, col2 = st.sidebar.columns([1, 4])
with col1:
    text_color = st.color_picker("Text", '#000000')
with col2:
    font_size = st.slider("Font size", 10, 100, 24)

# Create columns for the stroke color and stroke width
col3, col4 = st.sidebar.columns([1, 4])
with col3:
    stroke_color = st.color_picker("Stroke", '#FFFFFF')
with col4:
    stroke_width = st.slider("Stroke Width", 0, 20, 0)

user_name = st.sidebar.text_input("Corner text:")
overlay_description = st.sidebar.checkbox("Include Overlay", True)



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
                img = overlay_text_on_image(img, data['description'], selected_font, font_size, text_color, wrap_width_percentage, stroke_width, stroke_color)            
            if user_name:  # Only add watermark if user has entered a name
                img = add_watermark(
                    img, user_name, selected_font, 24, text_color
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