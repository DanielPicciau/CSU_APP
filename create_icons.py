#!/usr/bin/env python3
"""Generate PWA icons using Pillow."""

from PIL import Image, ImageDraw
import os

SIZES = [72, 96, 128, 144, 152, 192, 384, 512]
OUTPUT_DIR = 'static/icons'

def create_icon(size):
    """Create a simple purple circle icon."""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw a purple circle (the app's theme color)
    margin = int(size * 0.1)
    draw.ellipse([margin, margin, size - margin, size - margin], fill='#4F46E5')
    
    # Draw a white circle in the center
    center = size // 2
    r = int(size * 0.25)
    draw.ellipse([center - r, center - r, center + r, center + r], fill='white')
    
    return img

if __name__ == '__main__':
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Generate all sizes
    for size in SIZES:
        img = create_icon(size)
        path = f'{OUTPUT_DIR}/icon-{size}x{size}.png'
        img.save(path)
        print(f'Created: {path}')

    # Apple touch icon (180x180)
    img = create_icon(180)
    img.save(f'{OUTPUT_DIR}/apple-touch-icon.png')
    print('Created: apple-touch-icon.png')

    # Badge icon (72x72)
    img = create_icon(72)
    img.save(f'{OUTPUT_DIR}/badge-72x72.png')
    print('Created: badge-72x72.png')

    # Favicon (32x32)
    img = create_icon(32)
    img.save(f'{OUTPUT_DIR}/favicon.ico')
    print('Created: favicon.ico')

    print('\nAll icons generated!')
