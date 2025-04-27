services:
  - type: web
    name: fujitec-barcode-bot
    env: python
    plan: free
    buildCommand: "pip install -r requirements.txt"
    startCommand: "python run.py"
    envVars:
      - key: API_TOKEN
        value: YOUR_TELEGRAM_API_TOKEN
    region: singapore
