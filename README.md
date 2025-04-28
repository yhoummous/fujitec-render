# Fujitec Barcode Bot 📦🤖

A Telegram bot for generating professional barcode labels and QR codes for spare parts, automatically creating ready-to-print PDF files.

---

## 🚀 Features

- Create barcode and QR code labels from manual text input.
- Automatically generate and send back printable PDF files.
- Webhook-based for fast performance (uses Flask + Render).
- Logo, part name, rack location printed on stickers.
- Border, margins, and auto-wrapping text for clean label design.

---

## 🛠️ Tech Stack

- Python 3.12+
- Flask
- pyTelegramBotAPI (Telebot)
- python-barcode
- reportlab
- qrcode

---

## ⚙️ Environment Variables

| Variable Name | Description |
|:--------------|:------------|
| `API_TOKEN`    | Your Telegram Bot API token from @BotFather |

Make sure you set this in Render under **Environment Variables**.

---

## 📦 Installation

```bash
# Clone the repo
git clone https://github.com/yourusername/fujitec-barcode-bot.git

# Go into the project
cd fujitec-barcode-bot

# Install dependencies
pip install -r requirements.txt

