import os
import logging
import threading
import asyncio
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters
from openai import OpenAI
from duckduckgo_search import DDGS

# Cargar variables de entorno desde .env
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- 1. SERVIDOR DUMMY PARA RENDER ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write("Bot Orinoco IA activo y funcionando!".encode('utf-8'))

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

# --- 2. BÚSQUEDA WEB EN TIEMPO REAL ---
def ejecutar_busqueda_ddg(query):
    try:
        with DDGS() as ddgs:
            resultados = list(ddgs.text(query, max_results=3))
            if not resultados:
                return None
            
            texto_resultados = ""
            for r in resultados:
                texto_resultados += f"- {r['title']}: {r['body']}\n"
            return texto_resultados
    except Exception as e:
        logging.error(f"Error en búsqueda web: {e}")
        return None

def requiere_busqueda(texto):
    palabras_clave = [
        "busca", "buscar", "noticias", "precio", "hoy", "quien es", 
        "actual", "clima", "donde", "reciente", "investiga", "resultado"
    ]
    texto_lower = texto.lower()
    return any(palabra in texto_lower for palabra in palabras_clave)

def es_saludo(texto):
    saludos = ["hola", "buenas", "buenos dias", "buenas tardes", "buenas noches", "quien eres", "presentate", "que haces"]
    texto_clean = texto.lower().strip()
    return any(s in texto_clean for s in saludos) or len(texto_clean) <= 4

# --- 3. CONFIGURACIÓN CLIENTE NVIDIA ---
client = OpenAI(
    api_key=NVIDIA_API_KEY,
    base_url="https://integrate.api.nvidia.com/v1"
)

# --- 4. PRESENTACIÓN Y COMANDO /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    presentacion = (
        "¡Hola! 👋 Soy **Orinoco IA**, el asistente virtual de **Orinoco Dev**.\n\n"
        "Estoy aquí para brindarte información sobre nuestra empresa, nuestros servicios tecnológicos y ayudarte a consultar cualquier información en la web.\n\n"
        "¿En qué te puedo ayudar hoy?"
    )
    await update.message.reply_text(presentacion, parse_mode="Markdown")

# --- 5. RESPUESTA PRINCIPAL DEL BOT ---
async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    texto_usuario = update.message.text
    fecha_actual = datetime.now().strftime("%d de %B de %Y")

    # Si es un saludo, responder rápido con la presentación corta
    if es_saludo(texto_usuario):
        presentacion_corta = (
            "¡Hola! 👋 Soy **Orinoco IA**, el asistente virtual de **Orinoco Dev**.\n"
            "¿En qué te puedo ayudar hoy?"
        )
        await update.message.reply_text(presentacion_corta, parse_mode="Markdown")
        return

    informacion_web = None
    if requiere_busqueda(texto_usuario):
        informacion_web = await asyncio.to_thread(ejecutar_busqueda_ddg, texto_usuario)

    # --- DATOS OPERATIVOS AUTORIZADOS DE ORINOCO DEV ---
    prompt_sistema = (
        f"Eres Orinoco IA, el asistente virtual corporativo de la empresa Orinoco Dev, C.A. "
        f"Eres un asistente profesional, amable, claro y muy preciso. "
        f"La fecha de hoy es {fecha_actual}. "
        f"\n\nDATOS PUBLICOS DE LA EMPRESA:\n"
        f"- Nombre: Orinoco Dev, C.A.\n"
        f"- ¿Quiénes somos?: Nos dedicamos a convertir ideas en negocios exitosos a fin de contribuir con el desarrollo económico, usando la tecnología para potenciar tus ideas.\n"
        f"- Fecha de fundación: 20 de febrero de 2020.\n"
        f"- Ubicación geográfica: Avenida intercomunal Tigre-Tigrito, C.C. Paseo Los Pinos, Local 1-0-17.\n"
        f"- Teléfono de contacto: 0283-2421795.\n"
        f"- Correo electrónico: orinocotalento@gmail.com.\n"
        f"- Objetivos principales: Formular estrategias de aceleración de negocios, realizar planes de desarrollo de productos y desarrollo tecnológico, y ejecutar planes de comercialización y operaciones.\n"
        f"\nREGLAS DE PRIVACIDAD Y SEGURIDAD:\n"
        f"1. NUNCA menciones RIF, misión, visión, estados financieros ni información administrativa o interna confidencial.\n"
        f"2. Si el usuario pregunta por RIF, Misión, Visión o contrataciones/cotizaciones específicas, indícale amablemente que debe comunicarse directamente a través del teléfono 0283-2421795 o al correo orinocotalento@gmail.com.\n"
        f"3. Responde siempre de forma educada y profesional en español."
    )

    if informacion_web:
        prompt_sistema += (
            f"\n\nINFORMACIÓN RECIENTE OBTENIDA DE INTERNET:\n"
            f"{informacion_web}\n"
            f"Utiliza esta información únicamente si es relevante para la consulta del usuario."
        )

    try:
        response = client.chat.completions.create(
            model="meta/llama-3.1-8b-instruct",
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": texto_usuario}
            ],
            temperature=0.5,
            max_tokens=1024
        )
        respuesta_ia = response.choices[0].message.content
    except Exception as e:
        logging.error(f"Error al conectar con NVIDIA: {e}")
        respuesta_ia = "Lo siento, ocurrió un problema técnico al procesar tu solicitud. Por favor, intenta de nuevo en unos momentos o contáctanos directamente al 0283-2421795."

    await update.message.reply_text(respuesta_ia)

# --- 6. INICIALIZACIÓN ---
if __name__ == "__main__":
    threading.Thread(target=run_dummy_server, daemon=True).start()

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))
    
    print("Bot Orinoco IA activo y operando de forma segura.")
    app.run_polling(drop_pending_updates=True)