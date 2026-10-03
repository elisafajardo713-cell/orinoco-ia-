import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from google import genai
from google.genai import types

# Cargar las variables del archivo .env
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configuración de logs para depuración
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# Inicializar el cliente oficial de Gemini
ai_client = genai.Client(api_key=GEMINI_API_KEY)

# Configuración del modelo y del sistema
# Si en tu código original tenías un System Prompt o instrucciones iniciales,
# las colocamos dentro de 'system_instruction'.
model_config = types.GenerateContentConfig(
    system_instruction="Responde de manera amable, útil y concisa.",
    temperature=0.7,
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manejador del comando /start (conserva exactamente tu texto original)."""
    # Aquí va exactamente tu mensaje de presentación tal y como lo tenías escrito
    mensaje_bienvenida = (
        "¡Hola! 👋 Soy tu asistente virtual impulsado por inteligencia artificial. "
        "Estoy aquí para ayudarte en lo que necesites. ¿En qué te puedo colaborar hoy?"
    )
    await update.message.reply_text(mensaje_bienvenida)

async def responder_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Recibe el mensaje del usuario y envía la consulta a Gemini API."""
    texto_usuario = update.message.text

    try:
        # Consulta a la API de Gemini usando el modelo gemini-2.5-flash
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=texto_usuario,
            config=model_config
        )

        respuesta_bot = response.text
        await update.message.reply_text(respuesta_bot)

    except Exception as e:
        logging.error(f"Error al consultar la API de Gemini: {e}")
        await update.message.reply_text(
            "Lo siento, ocurrió un error al procesar tu solicitud. Por favor intenta de nuevo en unos momentos."
        )

def main() -> None:
    """Función principal para iniciar el bot."""
    if not TELEGRAM_BOT_TOKEN or not GEMINI_API_KEY:
        print("Error: Asegúrate de configurar TELEGRAM_BOT_TOKEN y GEMINI_API_KEY en el archivo .env")
        return

    # Construcción de la aplicación del bot con python-telegram-bot
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Comandos y manejadores de mensajes
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder_mensaje))

    print("Bot en marcha y escuchando mensajes...")
    app.run_polling()

if __name__ == "__main__":
    main()
