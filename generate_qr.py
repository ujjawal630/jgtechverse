import qrcode
from qrcode.constants import ERROR_CORRECT_H
from PIL import Image

print("=" * 40)
print("       TECHVERSE 2026 QR GENERATOR")
print("=" * 40)

website_url = input("Enter your live website URL: ").strip()

if not website_url.startswith(("https://", "http://")):
    print("Error: Please enter a valid website URL.")
    raise SystemExit

qr = qrcode.QRCode(
    version=None,
    error_correction=ERROR_CORRECT_H,
    box_size=12,
    border=5
)

qr.add_data(website_url)
qr.make(fit=True)

qr_image = qr.make_image(
    fill_color="#B5121B",
    back_color="#FFFFFF"
).convert("RGB")

border = 24

canvas = Image.new(
    "RGB",
    (qr_image.width + border * 2, qr_image.height + border * 2),
    "#D4AF37"
)

canvas.paste(qr_image, (border, border))
canvas.save("TechVerse_2026_QR.png")

print("\nQR CODE GENERATED SUCCESSFULLY!")
print("File: TechVerse_2026_QR.png")
print("Theme: Red + White + Golden")