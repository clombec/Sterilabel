import os
import sys
import tempfile
from PIL import Image, ImageDraw, ImageFont, ImageWin
import barcode
from barcode.writer import ImageWriter

try:
    import win32print
    import win32ui
except Exception:
    win32print = None
    win32ui = None


# -----------------------------
# Helper: Path fix for PyInstaller
# -----------------------------
def resource_path(relative_path):
    """Get absolute path to resource (handles PyInstaller)"""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)

    # Running normally (VSCode, Python)
    return os.path.join(os.path.dirname(__file__), relative_path)

# Optional bundled fonts (add these in your project folder)
FALLBACK_FONT_1 = "arial.ttf"

# -----------------------------
# Barcode generation
# -----------------------------
def generate_barcode(image_path, value):
    code = barcode.get("code128", value, writer=ImageWriter())

    # Force the writer to use a proper font path
    writer = code.writer

    # Try to find DejaVuSans (default used by python-barcode)
    font_path = resource_path(FALLBACK_FONT_1)
    if os.path.exists(font_path):
        writer.font_path = font_path

    options = {
        "module_width": 0.3,
        "module_height": 12.0,
        "font_size": 10,
        "text_distance": 5,
    }

    with open(image_path, "wb") as f:
        code.write(f, options=options)

    return image_path


# -----------------------------
# Label generation
# -----------------------------
def generate_label(output_path, lines, barcode_value):
    """Génère une étiquette avec texte centré + code barre en dessous"""
    W, H = 600, 240
    margin = 20

    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)

    # Utility for text sizing
    def get_text_size(text, font):
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]

    # -----------------------------
    # Load fonts safely
    # -----------------------------
    def load_font(name, size):
        font_path = resource_path(name)
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, size)
            except:
                pass
        # Fallback
        return ImageFont.load_default()

    font_big = load_font(FALLBACK_FONT_1, 32)
    font_small = load_font(FALLBACK_FONT_1, 26)

    # Generate barcode
    tmp_barcode_path = os.path.join(tempfile.gettempdir(), "barcode_tmp.png")
    generate_barcode(tmp_barcode_path, barcode_value)
    barcode_img = Image.open(tmp_barcode_path)

    # Write text
    y = margin
    for i, text in enumerate(lines):
        font = font_big if i == 0 else font_small
        w, h = get_text_size(text, font)
        draw.text(((W - w) / 2, y), text, font=font, fill="black")
        y += h + 10

    # Place barcode
    max_bar_w = W - 40
    ratio = min(max_bar_w / barcode_img.width, 1.0)
    bar_w = int(barcode_img.width * ratio)
    bar_h = max(1, int((barcode_img.height * ratio) / 3))

    barcode_resized = barcode_img.resize((bar_w, bar_h))
    img.paste(barcode_resized, ((W - bar_w) // 2, y + 10))

    img.save(output_path)
    return output_path


# -----------------------------
# Printing
# -----------------------------
def print_image(image_path):
    """Impression via Windows (pywin32)"""
    if win32print is None or win32ui is None:
        raise RuntimeError("pywin32 non disponible")

    printer_name = win32print.GetDefaultPrinter()
    hDC = win32ui.CreateDC()
    hDC.CreatePrinterDC(printer_name)

    bmp = Image.open(image_path)
    rotated = bmp.rotate(90, expand=True)
    bmp = rotated

    HORZRES = 8
    VERTRES = 10

    printable_w = hDC.GetDeviceCaps(HORZRES)
    printable_h = hDC.GetDeviceCaps(VERTRES)

    img_w, img_h = bmp.size
    scale = min(printable_w / img_w, printable_h / img_h)
    draw_w = int(img_w * scale)
    draw_h = int(img_h * scale)

    x = (printable_w - draw_w) // 2
    y = (printable_h - draw_h) // 2

    hDC.StartDoc("Label print job")
    hDC.StartPage()

    dib = ImageWin.Dib(bmp)
    dib.draw(hDC.GetHandleOutput(), (x, y, x + draw_w, y + draw_h))

    hDC.EndPage()
    hDC.EndDoc()
    hDC.DeleteDC()


def PrintContentLabel(lines, barcode_value):
    """Génère une étiquette avec texte centré + code barre en dessous"""
    tmp_output = os.path.join(tempfile.gettempdir(), "etiquette_label.png")
    generate_label(tmp_output, lines, barcode_value)

    print(f"Étiquette générée : {tmp_output}")

    try:
        print_image(tmp_output)
        print("Impression envoyée à l'imprimante par défaut.")
    except Exception as e:
        print("Erreur impression :", e)


if __name__ == "__main__":
    lines = [
        "MELAG 40 B+  201740-B0112",
        "05.04.2018 / 04.10.2018",
        "Charge 03/00019",
        "ID: 1001"
    ]
    barcode_value = "3J41580ZX"

    PrintContentLabel(lines, barcode_value)
