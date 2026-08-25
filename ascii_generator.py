"""
ASCII Art Generator for GitHub Profile SVGs
Converts any image (portrait, logo, avatar) into monospace ASCII art formatted
specifically for dark_mode.svg and light_mode.svg profiles (Andrew6rant style).
"""

import sys
import argparse
from pathlib import Path
from PIL import Image, ImageEnhance, ImageOps

# 25 lines of ASCII art from y=30 to y=510 with step 20
DEFAULT_WIDTH = 42
DEFAULT_HEIGHT = 25

# Character density ramps (from least dense / darkest to most dense / brightest)
RAMP_DARK = " .'`^,:;~-_+!*?lcj1I{}[]()trxnzuvopwqkdbkhao*#MW&8%B@$"
RAMP_LIGHT = "$@B%8&WM#*oahkbdkqwvunxzrt()[]{}I1jcl?*!+_-~;:,'^`. "

# Short ramps for distinct stylized rendering
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


def image_to_ascii(
    image_path: str,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    contrast: float = 1.4,
    brightness: float = 1.0,
    invert: bool = False,
    mode: str = "dark",
    custom_ramp: str = None,
) -> list[str]:
    """
    Converts an image file to a list of ASCII strings (one per line).
    """
    try:
        img = Image.open(image_path)
    except Exception as e:
        print(f"Error opening image '{image_path}': {e}", file=sys.stderr)
        return []

    # Convert to grayscale
    img = img.convert("L")

    # Invert if requested
    if invert:
        img = ImageOps.invert(img)

    # Adjust contrast
    if contrast != 1.0:
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(contrast)

    # Adjust brightness
    if brightness != 1.0:
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(brightness)

    # Resize with aspect ratio correction for monospace fonts
    # In Consolas / monospace fonts, character aspect ratio (width:height) is approx 1:2
    img = img.resize((width, height), Image.Resampling.LANCZOS)

    # Select character ramp
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
            # Map pixel value (0-255) to ramp index
            char_idx = int((pixel / 255) * (ramp_len - 1))
            raw_char = ramp[char_idx]
            line_chars.append(raw_char)
        # Right pad or strip as necessary
        line_str = "".join(line_chars).rstrip()
        lines.append(line_str)

    return lines


def format_for_svg(lines: list[str], x_pos: int = 15, start_y: int = 30, step_y: int = 20) -> str:
    """
    Formats a list of ASCII lines into SVG <tspan> elements.
    """
    tspans = []
    for i, line in enumerate(lines):
        y_pos = start_y + (i * step_y)
        # Escape for XML inside <tspan>
        escaped_line = "".join(escape_xml(c) for c in line)
        tspans.append(f'<tspan x="{x_pos}" y="{y_pos}">{escaped_line}</tspan>')
    return "\n".join(tspans)


def update_svg_file(svg_path: str, new_tspans: str):
    """
    Updates the ASCII text block in an existing SVG file.
    """
    path = Path(svg_path)
    if not path.exists():
        print(f"SVG file '{svg_path}' not found.", file=sys.stderr)
        return False

    content = path.read_text(encoding="utf-8")
    start_tag = '<text x="15" y="30" fill="#'
    alt_start_tag = '<text x="15" y="30"'

    if start_tag in content:
        # Find opening text tag end
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


def get_default_developer_art(mode: str = "dark") -> list[str]:
    """
    Returns a clean default 25-line cyberpunk / developer ASCII avatar.
    """
    if mode == "dark":
        return [
            "           .g@@@@@@@@Nw.                  ",
            "        .d@@@@@@@@@@@@@@@b.               ",
            "       w@@@@@@@@@@@@@@@@@@@w              ",
            "      d@@@@@@@@@@@@@@@@@@@@@b             ",
            "     .@@@@@M\"\"\"\"\"\"\"\"\"\"M@@@@@.            ",
            "     :@@@@'  .g@@@@g.  '@@@@:             ",
            "     :@@@'  d@@@@@@@@b  '@@@:             ",
            "     .@@@   @@@@@@@@@@   @@@.             ",
            "      'M@.  'M@@@@@@M'  .@M'              ",
            "        'N.   '\"\"\"\"'   .N'                ",
            "         'Mb.        .dM'                 ",
            "       .d@@@@NNmmmmNN@@@@b.               ",
            "     .d@@@@@@@@@@@@@@@@@@@@b.             ",
            "    .@@@@@@@@@@@@@@@@@@@@@@@@.            ",
            "   .@@@@@@@'  '@@@@'  '@@@@@@@.           ",
            "   d@@@@@@@    @@@@    @@@@@@@b           ",
            "   @@@@@@@@.  .@@@@.  .@@@@@@@@           ",
            "   @@@@@@@@@@@@@@@@@@@@@@@@@@@@           ",
            "   '@@@@@@@@@@@@@@@@@@@@@@@@@@'           ",
            "    '@@@@@@@@@@@@@@@@@@@@@@@@'            ",
            "     '@@@@@@@@@@@@@@@@@@@@@@'             ",
            "      '@@@@@@@@@@@@@@@@@@@@'              ",
            "       '@@@@@@@@@@@@@@@@@@'               ",
            "        '@@@@@@@@@@@@@@@@'                ",
            "         '@@@@@@@@@@@@@@'                 ",
        ]
    else:
        return [
            "           ,w$$$$$$$$gp,                  ",
            "        .g$$$$$$$$$$$$$$$g.               ",
            "       p$$$$$$$$$$$$$$$$$$$p              ",
            "      g$$$$$$$$$$$$$$$$$$$$$g             ",
            "     ,$$$$$W''''''''''W$$$$$,            ",
            "     ;$$$$'  ,g$$$$g,  '$$$$;             ",
            "     ;$$$'  g$$$$$$$$g  '$$$;             ",
            "     ,$$$   $$$$$$$$$$   $$$,             ",
            "      'W$,  'W$$$$$$W'  ,$W'              ",
            "        'p,   '\"\"\"\"'   ,p'                ",
            "         'Wg,        ,gW'                 ",
            "       ,g$$$$ppwwwwpp$$$$g,               ",
            "     ,g$$$$$$$$$$$$$$$$$$$$g,             ",
            "    ,$$$$$$$$$$$$$$$$$$$$$$$$,            ",
            "   ,$$$$$$$'  '$$$$'  '$$$$$$$,           ",
            "   g$$$$$$$    $$$$    $$$$$$$g           ",
            "   $$$$$$$$,  ,$$$$,  ,$$$$$$$$           ",
            "   $$$$$$$$$$$$$$$$$$$$$$$$$$$$           ",
            "   '$$$$$$$$$$$$$$$$$$$$$$$$$$'           ",
            "    '$$$$$$$$$$$$$$$$$$$$$$$$'            ",
            "     '$$$$$$$$$$$$$$$$$$$$$$'             ",
            "      '$$$$$$$$$$$$$$$$$$$$'              ",
            "       '$$$$$$$$$$$$$$$$$$'               ",
            "        '$$$$$$$$$$$$$$$$'                ",
            "         '$$$$$$$$$$$$$$'                 ",
        ]


def main():
    parser = argparse.ArgumentParser(description="Convert an image to ASCII art for GitHub Profile SVGs.")
    parser.add_argument("--image", "-i", type=str, help="Path to input image file (PNG, JPG, WEBP).")
    parser.add_argument("--width", "-w", type=int, default=DEFAULT_WIDTH, help=f"ASCII width (default: {DEFAULT_WIDTH})")
    parser.add_argument("--height", "-t", type=int, default=DEFAULT_HEIGHT, help=f"ASCII height (default: {DEFAULT_HEIGHT})")
    parser.add_argument("--contrast", "-c", type=float, default=1.4, help="Contrast adjustment factor (default: 1.4)")
    parser.add_argument("--brightness", "-b", type=float, default=1.0, help="Brightness adjustment factor (default: 1.0)")
    parser.add_argument("--invert", action="store_true", help="Invert image colors before processing.")
    parser.add_argument("--update-svgs", action="store_true", help="Directly update dark_mode.svg and light_mode.svg in current directory.")

    args = parser.parse_args()

    if args.image:
        print(f"Processing image: {args.image}")
        dark_lines = image_to_ascii(args.image, width=args.width, height=args.height, contrast=args.contrast, brightness=args.brightness, invert=args.invert, mode="dark")
        light_lines = image_to_ascii(args.image, width=args.width, height=args.height, contrast=args.contrast, brightness=args.brightness, invert=not args.invert, mode="light")
    else:
        print("No image provided. Using default high-tech developer avatar.")
        dark_lines = get_default_developer_art(mode="dark")
        light_lines = get_default_developer_art(mode="light")

    dark_tspans = format_for_svg(dark_lines)
    light_tspans = format_for_svg(light_lines)

    if args.update_svgs:
        update_svg_file("dark_mode.svg", dark_tspans)
        update_svg_file("light_mode.svg", light_tspans)
    else:
        print("\n=== DARK MODE ASCII (Raw) ===")
        for line in dark_lines:
            print(line)
        print("\n=== SVG TSPAN SNIPPET (First 5 lines) ===")
        print("\n".join(dark_tspans.split("\n")[:5]))
        print("...\n(Use --update-svgs to write directly to dark_mode.svg and light_mode.svg)")


if __name__ == "__main__":
    main()
