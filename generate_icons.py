#!/usr/bin/env python3
"""
Generate PWA icons from the SVG source.

Requires: pip install cairosvg pillow
"""

import os
from pathlib import Path

try:
    import cairosvg
    from PIL import Image
    from io import BytesIO
except ImportError:
    print("This script requires cairosvg and pillow.")
    print("Install with: pip install cairosvg pillow")
    exit(1)

SIZES = [72, 96, 128, 144, 152, 192, 384, 512]
SVG_PATH = Path(__file__).parent / "static" / "icons" / "icon.svg"
OUTPUT_DIR = Path(__file__).parent / "static" / "icons"


def generate_icons():
    """Generate PNG icons from SVG."""
    if not SVG_PATH.exists():
        print(f"SVG not found: {SVG_PATH}")
        return

    svg_data = SVG_PATH.read_bytes()

    for size in SIZES:
        output_path = OUTPUT_DIR / f"icon-{size}x{size}.png"
        
        # Convert SVG to PNG
        png_data = cairosvg.svg2png(
            bytestring=svg_data,
            output_width=size,
            output_height=size,
        )
        
        # Save
        output_path.write_bytes(png_data)
        print(f"Generated: {output_path}")

    # Generate Apple Touch Icon (180x180)
    apple_icon_path = OUTPUT_DIR / "apple-touch-icon.png"
    png_data = cairosvg.svg2png(
        bytestring=svg_data,
        output_width=180,
        output_height=180,
    )
    apple_icon_path.write_bytes(png_data)
    print(f"Generated: {apple_icon_path}")

    # Generate badge icon (monochrome, 72x72)
    badge_path = OUTPUT_DIR / "badge-72x72.png"
    png_data = cairosvg.svg2png(
        bytestring=svg_data,
        output_width=72,
        output_height=72,
    )
    badge_path.write_bytes(png_data)
    print(f"Generated: {badge_path}")


if __name__ == "__main__":
    generate_icons()
    print("\nDone! Icons generated successfully.")
