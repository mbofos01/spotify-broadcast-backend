from PIL import Image
import numpy as np
from collections import Counter
import requests
from io import BytesIO

def rgb_to_hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(*rgb)

def get_suggested_gradient(source, num_colors=5):
    # Check if input is a URL
    if source.startswith("http://") or source.startswith("https://"):
        response = requests.get(source)
        img = Image.open(BytesIO(response.content)).convert("RGB")
    else:
        img = Image.open(source).convert("RGB")
    
    # Resize for speed
    small_img = img.resize((100, 100))
    pixels = np.array(small_img).reshape(-1, 3)
    
    # Count most common colors
    counter = Counter([tuple(p) for p in pixels])
    most_common = counter.most_common(num_colors)
    
    # Take first and last colors as gradient suggestion
    start_color = rgb_to_hex(most_common[0][0])
    end_color = rgb_to_hex(most_common[-1][0])
    
    return start_color, end_color
