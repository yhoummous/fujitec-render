
# run.py
import os
import io
import logging

from flask import Flask, request, abort
import telebot
from telebot.types import InputFile

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import portrait
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader

import qrcode
from barcode import Code128
from barcode.writer import ImageWriter
from PIL import Image

# -----------------------
# Logging (stdout for Render)
# -----------------------
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger("fujitec-bot")

# -----------------------
# Environment & Bot Setup
# -----------------------
API_TOKEN = os.getenv("API_TOKEN")
if not API_TOKEN:
    raise RuntimeError("Missing API_TOKEN environment variable")

# Optional secret for webhook verification
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")  # set this when calling setWebhook

# Optional: logo path
LOGO_PATH = os.getenv("LOGO_PATH", "logo.png")

# Create bot (HTML parse mode by default)
bot = telebot.TeleBot(API_TOKEN, parse_mode="HTML")

# Flask app
app = Flask(__name__)


@app.get("/")
def home():
    return "🚀 Fujitec Barcode Bot is alive!", 200


@app.post("/webhook")
def telegram_webhook():
    # Verify Telegram secret header if configured
    if WEBHOOK_SECRET:
        header_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if header_secret != WEBHOOK_SECRET:
            logger.warning("Invalid webhook secret token")
            return abort(401)

    try:
        update = telebot.types.Update.de_json(request.get_data(as_text=True))
        bot.process_new_updates([update])
    except Exception as exc:
        logger.exception("Failed to process update: %s", exc)
        return "ERROR", 500

    return "OK", 200


# -----------------------
# Bot Handlers
# -----------------------
@bot.message_handler(commands=["start"])
def send_welcome(message):
    welcome_text = (
        "👋 <b>Welcome to Fujitec Barcode Bot!</b>\n\n"
        "🔹 Create professional barcode/QR stickers for your spare parts.\n\n"
        "<b>📄 Manual Entry:</b>\n"
        "Send text like:\n"
        "<code>123456789012, Motor Gear, R12</code>\n"
        "<code>987654321098, Brake Unit, R34</code>\n\n"
        "✅ I’ll generate and send back a ready‑to‑print PDF.\n\n"
        "For support: @BDM_IT"
    )

    # Try sending logo + caption; fallback to text
    try:
        if os.path.exists(LOGO_PATH):
            with open(LOGO_PATH, "rb") as logo:
                bot.send_photo(message.chat.id, logo, caption=welcome_text, parse_mode="HTML")
        else:
            bot.send_message(message.chat.id, welcome_text)
    except Exception as exc:
        logger.exception("Error sending welcome message: %s", exc)
        bot.reply_to(message, "❌ Error: Could not send the welcome message.")


@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_text(message):
    """
    Expected simple CSV: <barcode>, <part name>, <rack>
    Example: 123456789012, Motor Gear, R12
    """
    try:
        text = (message.text or "").strip()
        if not text:
            return bot.reply_to(message, "Please send: <code>BARCODE, Part Name, Rack</code>", parse_mode="HTML")

        parts = [p.strip() for p in text.split(",")]
        if len(parts) < 3:
            return bot.reply_to(
                message,
                "Format invalid. Use: <code>BARCODE, Part Name, Rack</code>",
                parse_mode="HTML",
            )

        barcode_number, part_name, rack = parts[0], parts[1], parts[2]
        labels_data = [(barcode_number, part_name, rack)]

        # Generate PDF in-memory
        pdf_bytes, filename = generate_pdf(labels_data)

        # Send as document
        input_file = InputFile(pdf_bytes, filename)
        bot.send_document(message.chat.id, input_file, caption=f"✅ Generated: <code>{filename}</code>", parse_mode="HTML")

    except Exception as exc:
        logger.exception("Failed to handle text message: %s", exc)
        bot.reply_to(message, "❌ Error: could not generate your label PDF.")


# -----------------------
# PDF Generation (in-memory)
# -----------------------
def generate_pdf(labels_data):
    """
    labels_data: list of tuples (barcode_number, part_name, rack)
    Returns: (BytesIO, filename)
    """
    barcode_numbers = [item[0] for item in labels_data]
    filename = ",".join(barcode_numbers) + "_labels.pdf"

    # Page size ~ 10cm x 15cm (portrait)
    width, height = 10 * cm, 15 * cm

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=portrait((width, height)))

    for barcode_number, part_name, rack in labels_data:
        # Draw border
        c.setLineWidth(1)
        c.rect(5, 5, width - 10, height - 10)

        y = height - 1.0 * cm
        space = 0.7 * cm

        # Logo (optional)
        if os.path.exists(LOGO_PATH):
            try:
                logo_img = Image.open(LOGO_PATH)
                c.drawImage(ImageReader(logo_img), cm, y - 2 * cm, width - 2 * cm, 2 * cm, preserveAspectRatio=True)
                y -= 2 * cm + space
            except Exception:
                # Non-fatal if logo can't be drawn
                logger.warning("Logo found but could not be drawn; continuing.")

        # Barcode (PIL in-memory)
        barcode_img = Code128(barcode_number, writer=ImageWriter()).render()
        c.drawImage(ImageReader(barcode_img), cm, y - 2.5 * cm, width - 2 * cm, 2.5 * cm)
        y -= 2.5 * cm + space

        # QR code (PIL in-memory)
        qr_text = f"{barcode_number} | {part_name} | {rack}"
        qr_img = qrcode.make(qr_text)
        # Place QR at left; you can adjust position/size
        c.drawImage(ImageReader(qr_img), cm + 2 * cm, y - 3 * cm, 3 * cm, 3 * cm)
        y -= 3 * cm + space

        # Text
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(width / 2, y, f"Part: {part_name}")
        y -= 1.2 * cm
        c.drawCentredString(width / 2, y, f"Rack: {rack}")

        # Footer
        c.setFont("Helvetica-Oblique", 8)
        c.drawCentredString(width / 2, 1 * cm, "FUJITEC SA - JEDDAH WAREHOUSE")

        c.showPage()

    c.save()
    buffer.seek(0)
    return buffer, filename


# -------------
# Entry Point
# -------------
if __name__ == "__main__":
    # On local dev you can `python run.py` to run Flask directly.
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
