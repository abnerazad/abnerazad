"""
ASCII Art Generator for GitHub Profile SVGs
Converts any image (portrait, logo, avatar) into monospace ASCII art formatted
specifically for dark_mode.svg and light_mode.svg profiles (Andrew6rant style).
"""

import sys
import argparse
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter, ImageOps, ImageDraw

DEFAULT_WIDTH = 42
DEFAULT_HEIGHT = 25

# Character density ramps
RAMP_DARK_HIGH_CONTRAST = " .':;~+!*jrkmgpwHB%NM@$"
RAMP_LIGHT_HIGH_CONTRAST = "$@MN%BHwpgmkjr!*+~;:'. "


def escape_xml(char: str) -> str:
    """Escapes XML special characters for SVG text safety."""
    replacements = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&apos;",
    }
    return replacements.get(char, char)


def create_radial_mask(width, height, center_x, center_y, radius_x, radius_y, inner_ratio=0.70):
    """Creates a smooth radial alpha mask using Pillow."""
    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    steps = 40
    for i in range(steps, 0, -1):
        ratio = inner_ratio + (1.0 - inner_ratio) * (i / steps)
        rx = radius_x * ratio
        ry = radius_y * ratio
        val = int(255 * (1.0 - (i / steps)))
        bbox = [center_x - rx, center_y - ry, center_x + rx, center_y + ry]
        draw.ellipse(bbox, fill=val)
    inner_bbox = [
        center_x - radius_x * inner_ratio,
        center_y - radius_y * inner_ratio,
        center_x + radius_x * inner_ratio,
        center_y + radius_y * inner_ratio,
    ]
    draw.ellipse(inner_bbox, fill=255)
    return mask.filter(ImageFilter.GaussianBlur(radius=8))


def preprocess_portrait(img: Image.Image, mode: str = "dark") -> Image.Image:
    """Isolates central subject and enhances features for ASCII rendering."""
    w, h = img.size
    crop_box = (int(w * 0.06), int(h * 0.02), int(w * 0.94), int(h * 0.98))
    img_cropped = img.crop(crop_box).convert("RGBA")
    cw, ch = img_cropped.size

    mask = create_radial_mask(cw, ch, cw * 0.50, ch * 0.48, cw * 0.46, ch * 0.52, inner_ratio=0.72)

    bg_color = (0, 0, 0, 255) if mode == "dark" else (255, 255, 255, 255)
    bg = Image.new("RGBA", (cw, ch), bg_color)
    composite = Image.composite(img_cropped, bg, mask).convert("L")

    # Boost contrast and sharpen
    enhancer = ImageEnhance.Contrast(composite)
    enhanced = enhancer.enhance(1.55)
    sharpener = ImageEnhance.Sharpness(enhanced)
    sharp = sharpener.enhance(2.0).filter(ImageFilter.UnsharpMask(radius=2, percent=175, threshold=2))
    return sharp


def image_to_ascii(
    image_path: str,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    contrast: float = 1.3,
    brightness: float = 1.0,
    invert: bool = False,
    mode: str = "dark",
    custom_ramp: str = None,
    isolate_bg: bool = True,
) -> list[str]:
    """Converts an image file to a list of ASCII strings."""
    try:
        img = Image.open(image_path)
    except Exception as e:
        print(f"Error opening image '{image_path}': {e}", file=sys.stderr)
        return []

    if isolate_bg:
        img = preprocess_portrait(img, mode=mode)
    else:
        img = img.convert("L")

    if invert:
        img = ImageOps.invert(img)

    if contrast != 1.0:
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(contrast)

    if brightness != 1.0:
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(brightness)

    # Monospace aspect ratio correction
    img = img.resize((width, height), Image.Resampling.LANCZOS)

    if custom_ramp:
        ramp = custom_ramp
    elif mode == "dark":
        ramp = RAMP_DARK_HIGH_CONTRAST
    else:
        ramp = RAMP_LIGHT_HIGH_CONTRAST

    ramp_len = len(ramp)
    lines = []
    for y in range(height):
        line_chars = []
        for x in range(width):
            pixel = img.getpixel((x, y))
            char_idx = int((pixel / 255) * (ramp_len - 1))
            line_chars.append(ramp[char_idx])
        lines.append("".join(line_chars).rstrip())

    return lines


def format_for_svg(lines: list[str], x_pos: int = 15, start_y: int = 30, step_y: int = 20) -> str:
    """Formats ASCII lines into SVG <tspan> elements."""
    tspans = []
    for i, line in enumerate(lines):
        y_pos = start_y + (i * step_y)
        escaped_line = "".join(escape_xml(c) for c in line)
        tspans.append(f'<tspan x="{x_pos}" y="{y_pos}">{escaped_line}</tspan>')
    return "\n".join(tspans)


def update_svg_file(svg_path: str, new_tspans: str):
    """Updates the ASCII text block in an existing SVG file."""
    path = Path(svg_path)
    if not path.exists():
        print(f"SVG file '{svg_path}' not found.", file=sys.stderr)
        return False

    content = path.read_text(encoding="utf-8")
    start_tag = '<text x="15" y="30"'

    if start_tag in content:
        start_idx = content.find(start_tag)
        tag_close_idx = content.find(">", start_idx) + 1
        end_text_idx = content.find("</text>", tag_close_idx)
        if tag_close_idx > 0 and end_text_idx > 0:
            updated_content = content[:tag_close_idx] + "\n" + new_tspans + "\n" + content[end_text_idx:]
            path.write_text(updated_content, encoding="utf-8")
            print(f"Successfully updated ASCII art in '{svg_path}'!")
            return True

    print(f"Could not locate ASCII <text> block in '{svg_path}'.", file=sys.stderr)
    return False


def main():
    parser = argparse.ArgumentParser(description="Convert an image to ASCII art for GitHub Profile SVGs.")
    parser.add_argument("--image", "-i", type=str, default="avatar.jpg", help="Path to input image file.")
    parser.add_argument("--width", "-w", type=int, default=DEFAULT_WIDTH, help=f"ASCII width (default: {DEFAULT_WIDTH})")
    parser.add_argument("--height", "-t", type=int, default=DEFAULT_HEIGHT, help=f"ASCII height (default: {DEFAULT_HEIGHT})")
    parser.add_argument("--contrast", "-c", type=float, default=1.3, help="Contrast factor (default: 1.3)")
    parser.add_argument("--brightness", "-b", type=float, default=1.0, help="Brightness factor (default: 1.0)")
    parser.add_argument("--no-mask", action="store_true", help="Disable background isolation mask.")
    parser.add_argument("--update-svgs", action="store_true", help="Write directly to dark_mode.svg and light_mode.svg.")

    args = parser.parse_args()

    image_path = args.image
    if not Path(image_path).exists():
        print(f"Image '{image_path}' not found.", file=sys.stderr)
        return

    print(f"Processing image: {image_path}")
    dark_lines = image_to_ascii(image_path, width=args.width, height=args.height, contrast=args.contrast, brightness=args.brightness, mode="dark", isolate_bg=not args.no_mask)
    light_lines = image_to_ascii(image_path, width=args.width, height=args.height, contrast=args.contrast, brightness=args.brightness, mode="light", isolate_bg=not args.no_mask)

    dark_tspans = format_for_svg(dark_lines)
    light_tspans = format_for_svg(light_lines)

    if args.update_svgs:
        update_svg_file("dark_mode.svg", dark_tspans)
        update_svg_file("light_mode.svg", light_tspans)
    else:
        print("\n=== DARK MODE ASCII (Raw) ===")
        for line in dark_lines:
            print(line)


if __name__ == "__main__":
    main()
