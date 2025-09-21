from PIL import Image
import numpy as np
import requests
from io import BytesIO
from collections import Counter

def rgb_to_hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(*rgb)

def brightness(rgb):
    r, g, b = rgb
    return (0.2126*r + 0.7152*g + 0.0722*b) / 255

def lighten_color(rgb, factor=0.4):
    """Make a color lighter by mixing it with white."""
    r, g, b = rgb
    r = int(r + (255 - r) * factor)
    g = int(g + (255 - g) * factor)
    b = int(b + (255 - b) * factor)
    return (r, g, b)

def get_suggested_gradient(image_url, min_brightness=0.25):
    # Load album art
    response = requests.get(image_url)
    img = Image.open(BytesIO(response.content)).convert("RGB")
    small_img = img.resize((100, 100))  # downsample for speed
    pixels = np.array(small_img).reshape(-1, 3)
    
    # Count most common colors
    counter = Counter([tuple(p) for p in pixels])
    common = [c for c, _ in counter.most_common(50)]  # top 50
    
    # Filter only bright ones
    bright_colors = [c for c in common if brightness(c) >= min_brightness]
    
    if len(bright_colors) >= 2:
        # Take the top 2 bright dominant colors
        return rgb_to_hex(bright_colors[0]), rgb_to_hex(bright_colors[1])
    elif len(bright_colors) == 1:
        # Only one bright color → generate lighter companion
        return rgb_to_hex(bright_colors[0]), rgb_to_hex(lighten_color(bright_colors[0]))
    else:
        # Fallback → white gradient
        return "#ffffff", "#e0e0e0"
