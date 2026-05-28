#!/bin/bash
set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Instalando Claudia — Agente Personal"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Dependencias del sistema para WeasyPrint (PDF)
echo ""
echo "→ Instalando dependencias del sistema (necesitas Homebrew)..."
brew install pango libffi

# Entorno virtual Python
echo ""
echo "→ Creando entorno virtual Python..."
python3 -m venv .venv
source .venv/bin/activate

# Dependencias Python
echo ""
echo "→ Instalando dependencias Python..."
pip install --upgrade pip
pip install -r requirements.txt

# Archivo .env
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo ""
    echo "⚠️  Archivo .env creado. Completa estas credenciales en .env:"
    echo ""
    echo "   1. ANTHROPIC_API_KEY"
    echo "      → console.anthropic.com"
    echo ""
    echo "   2. TWILIO_ACCOUNT_SID + TWILIO_AUTH_TOKEN"
    echo "      → twilio.com/console"
    echo ""
    echo "   3. TWILIO_WHATSAPP_NUMBER"
    echo "      → En sandbox: whatsapp:+14155238886"
    echo "      → Ve a twilio.com/console > Messaging > Try it out > Send a WhatsApp message"
    echo "      → Envía el código de activación desde tu WhatsApp al número sandbox"
    echo ""
    echo "   4. ALLOWED_WHATSAPP_NUMBER"
    echo "      → Tu número con prefijo: whatsapp:+34600000000"
    echo ""
    echo "   5. ICLOUD_EMAIL + ICLOUD_APP_PASSWORD"
    echo "      → appleid.apple.com > Inicio de sesión y seguridad > Contraseñas específicas"
    echo ""
else
    echo "→ .env ya existe, no se sobreescribe."
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✓ Instalación completada"
echo ""
echo "  Para arrancar Claudia:"
echo "  source .venv/bin/activate && python run.py"
echo ""
echo "  Al arrancar, ngrok generará automáticamente una URL pública."
echo "  Copia esa URL + /webhook y pégala en Twilio como Webhook URL."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
