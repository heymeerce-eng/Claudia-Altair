import os
import base64
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

# In production (Railway), decode Google credentials from env var
creds_file = Path(__file__).parent / "google_credentials.json"
if not creds_file.exists():
    encoded = os.environ.get("GOOGLE_CREDENTIALS_BASE64", "")
    if encoded:
        creds_file.write_bytes(base64.b64decode(encoded))

from claudia.bot import run_bot

if __name__ == "__main__":
    required = ["ANTHROPIC_API_KEY", "TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        print(f"Faltan variables de entorno: {', '.join(missing)}")
        print("Copia .env.example a .env y completa los valores.")
        exit(1)

    run_bot()
