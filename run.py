
#!/usr/bin/env python3
import os
import time
import logging
from threading import Thread
from flask import Flask, request
import telebot
import qrcode
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import portrait
from reportlab.lib.units import cm
from barcode import Code128
from barcode.writer import ImageWriter

# === Logging ===
logging.basicConfig(filename='bot.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# === Config ===
API_TOKEN = os.getenv("API_TOKEN")            # Telegram Bot API Token
WEBHOOK_URL = os.getenv("WEBHOOK_URL")        # e.g., https://your-service.onrender.com/webhook
PORT = int(os.getenv("PORT", "10000"))        # Render injects PORT automatically
MODE = os.getenv("MODE", "webhook")           # "webhook" or "polling"

if not API_TOKEN:
    raise RuntimeError("API_TOKEN is missing in environment.")

bot = telebot.TeleBot(API_TOKEN, parse_mode="HTML")
app = Flask(__name__)

# === Health Check ===
@app.route("/")
def home():
    return "🚀 Fujitec Barcode Bot is alive!", 200

# === Webhook Endpoint ===
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        json_str = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return "OK", 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return "ERROR", 400

# === /start Command ===
@bot.message_handler(commands=["start"])
def send_welcome(message):
    caption = (
        "👋 <b>Welcome to Fujitec Barcode Bot!</b>\n\n"
        "🔹 Easily create professional barcode stickers for your spare parts.\n\n"
        "<b>📄 Manual Entry:</b>\n"
        "Send text like:\n"
        "<code>123456789012, Motor Gear, R12</code>\n"
        "<code>987654321098, Brake Unit, R34</code>\n\n"
        "✅ After sending, the bot will generate and send you a ready-to-print PDF.\n\n"
        "⚡ Let's get started!\n\n"
        "For Support: @Fujitecsa_bot"
    )
    try:
        if os.path.exists("logo.png"):
            with open("logo.png", "rb") as logo:
                bot.send_photo(message.chat.id, logo, caption=caption)
        else:
            bot.send_message(message.chat.id, caption)
    except Exception as e:
        logger.error(f"Error sending welcome: {e}")
        bot.reply_to(message, "❌ Error sending welcome.")

# === Handle Manual Entry ===
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    try:
        lines = [ln.strip() for ln in message.text.strip().split("\n") if ln.strip()]
        data = []
        for line in lines:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) != 3:
                bot.reply_to(message, "❌ Use format: Barcode, Part Name, Rack")
                return
            data.append(parts)

        generating_msg = bot.reply_to(message, "⏳ Generating your PDF...")
        pdf_path = generate_pdf(data)

        with open(pdf_path, "rb") as pdf_file:
            bot.send_document(message.chat.id, pdf_file)

        try:
            os.remove(pdf_path)
        except Exception:
            pass

        try:
            bot.delete_message(message.chat.id, generating_msg.message_id)
        except Exception:
            pass

    except Exception as e:
        logger.error(f"Manual entry error: {e}")
        bot.reply_to(message, f"❌ Error: {e}")

# === Generate PDF with Barcode, QR, and Part Name ===
def generate_pdf(labels_data):
    # Name output PDF by the barcode numbers
    barcode_numbers = [item[0] for item in labels_data]
    pdf_file_name = ",".join(barcode_numbers) + "_labels.pdf"

    # Set PDF dimensions
    width, height = 10 * cm, 15 * cm
    c = canvas.Canvas(pdf_file_name, pagesize=portrait((width, height)))

    for barcode_number, part_name, rack in labels_data:
        # Barcode Image
        barcode_png_base = f"{barcode_number}_barcode"
        Code128(barcode_number, writer=ImageWriter()).save(barcode_png_base)
        barcode_filename = barcode_png_base + ".png"

        # QR Code Image
        qr_path = f"{barcode_number}_qr.png"
        qrcode.make(f"{barcode_number} | {part_name} | {rack}").save(qr_path)

        # Border
        c.setLineWidth(1)
        c.rect(5, 5, width - 10, height - 10)

        y = height - 1 * cm
        space = 0.7 * cm

        # Logo (optional)
        if os.path.exists("logo.png"):
            c.drawImage("logo.png", cm, y - 2*cm, width - 2*cm, 2*cm, preserveAspectRatio=True)
        y -= 2*cm + space

        # Barcode
        c.drawImage(barcode_filename, cm, y - 2.5*cm, width - 2*cm, 2.5*cm)
        y -= 2.5*cm + space

        # QR Code
        c.drawImage(qr_path, cm + 2*cm, y - 3*cm, 3*cm, 3*cm)
        y -= 3*cm + space

        # Part Name (centered)
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(width/2, y, f"Part: {part_name}")
        y -= 1.2 * cm
        c.drawCentredString(width/2, y, f"Rack: {rack}")

        # Footer (centered)
        c.setFont("Helvetica-Oblique", 8)
        c.drawCentredString(width / 2, 1 * cm, "FUJITEC SA - JEDDAH WAREHOUSE")

        c.showPage()

        # Clean up image files
        for temp in (barcode_filename, qr_path):
            try:
                os.remove(temp)
            except Exception:
                pass

    c.save()
    return pdf_file_name

# === Startup (Webhook) ===
def start_webhook():
    # Validate token
    me = bot.get_me()
    logger.info(f"Bot authenticated: @{me.username} (id={me.id})")

    # Start Flask server
    Thread(target=lambda: app.run(host="0.0.0.0", port=PORT, debug=False, threaded=True)).start()
    time.sleep(2)

    # Configure webhook
    if not WEBHOOK_URL:
        raise RuntimeError("WEBHOOK_URL is missing in environment.")
    bot.remove_webhook()
    time.sleep(1)
    ok = bot.set_webhook(url=WEBHOOK_URL)
    logger.info(f"Webhook set to {WEBHOOK_URL}: {ok}")

# === Alternative: Polling (for local testing) ===
def start_polling():
    bot.remove_webhook()
    logger.info("Starting bot with polling...")
    bot.infinity_polling(timeout=20, long_polling_timeout=20)

if __name__ == "__main__":
       if MODE == "polling":
        start_polling()
    else:
