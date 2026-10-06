import os
import logging
import threading
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters
from openai import OpenAI

# Cargar variables de entorno locales
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY") or os.getenv("OPENCODE_API_KEY")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

if not TELEGRAM_TOKEN or not NVIDIA_API_KEY:
    logging.error("❌ CRÍTICO: Configura TELEGRAM_TOKEN y NVIDIA_API_KEY en las Environment Variables.")

# --- 1. SERVIDOR DUMMY PARA MANTENER ACTIVO RENDER ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write("Bot de Soporte Técnico Orinoco Dev (NVIDIA API Ultra-Rápido) activo!".encode('utf-8'))

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

def es_saludo(texto):
    saludos = ["hola", "buenas", "buenos dias", "buenas tardes", "buenas noches", "quien eres", "presentate", "que haces", "ayuda"]
    texto_clean = texto.lower().strip()
    return any(s in texto_clean for s in saludos) or len(texto_clean) <= 4

# --- 2. CONFIGURACIÓN CLIENTE NVIDIA NIM ---
client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=NVIDIA_API_KEY,
    timeout=20.0
)

def llamar_nvidia_api(prompt_sistema, texto_usuario):
    # Modelo oficial y ultra veloz disponible en NVIDIA NIM
    return client.chat.completions.create(
        model="meta/llama-3.1-70b-instruct",
        messages=[
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": texto_usuario}
        ],
        temperature=0.3,
        max_tokens=700,
        stream=False
    )

# --- 3. COMANDO /start Y PRESENTACIÓN ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    presentacion = (
        "🛠️️ **Asistente de Soporte Técnico - Orinoco Dev**\n\n"
        "¡Hola! Soy tu bot de asistencia técnica informática. Estoy diseñado para apoyar en:\n"
        "• Diagnóstico y solución de fallas de **hardware y equipos**.\n"
        "• Mantenimiento y problemas de **software / sistemas operativos**.\n"
        "• Uso y configuración de herramientas de ofimática (**Word, Excel, etc.**).\n"
        "• Configuración de redes y aplicaciones corporativas.\n\n"
        "¿En qué consulta o problema técnico te puedo ayudar hoy?"
    )
    await update.message.reply_text(presentacion, parse_mode="Markdown")

# --- 4. RESPUESTA Y LÓGICA PRINCIPAL ---
async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    texto_usuario = update.message.text

    # Responder saludos de forma instantánea
    if es_saludo(texto_usuario):
        presentacion_corta = (
            "🛠️ **Soporte Técnico Orinoco Dev**\n"
            "¡Hola! Estoy listo para ayudarte con problemas de computadoras, programas, herramientas de oficina o soporte informático. "
            "Escribe tu duda o describe la falla que presentas."
        )
        await update.message.reply_text(presentacion_corta, parse_mode="Markdown")
        return

    prompt_sistema = (
        "Eres un Asistente Experto en Soporte Técnico Informático para la empresa Orinoco Dev, C.A.\n\n"
        "INSTRUCCIÓN DE VELOCIDAD Y CONCISIÓN:\n"
        "Sé breve, directo y conciso. Ve al grano inmediatamente con la solución paso a paso.\n\n"
        "ROL Y OBJETIVO:\n"
        "Brindar asistencia sobre Hardware, Software, Sistemas Operativos, Herramientas de Oficina y solución de errores informáticos.\n\n"
        "REGLAS DE SEGURIDAD Y RESTRICCIÓN:\n"
        "1. NO respondas sobre datos internos, finanzas, RIF, clientes o ventas de la empresa.\n"
        "2. NO respondas temas ajenos a la informática. Si te preguntan algo ajeno, indica brevemente que solo atiendes soporte técnico.\n"
        "3. Estructura con viñetas o pasos numerados de forma sintética."
    )

    try:
        # Indicar al usuario que el bot está procesando
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

        # Llamar a la API de NVIDIA de forma asíncrona sin congelar el servidor
        completion = await asyncio.to_thread(
            llamar_nvidia_api, prompt_sistema, texto_usuario
        )
        respuesta_ia = completion.choices[0].message.content

    except Exception as e:
        logging.error(f"Error al conectar con la API de NVIDIA: {e}")
        respuesta_ia = "⚠️ Ocurrió una incidencia técnica al conectar con el servidor de IA. Por favor, reintenta en un momento."

    await update.message.reply_text(respuesta_ia)

# --- 5. INICIALIZACIÓN DEL BOT ---
if __name__ == "__main__":
    threading.Thread(target=run_dummy_server, daemon=True).start()

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))
    
    print("Bot de Soporte Técnico Orinoco Dev (NVIDIA API Ultra-Rápido) activo...")
    app.run_polling(drop_pending_updates=True)
