import os
import logging
import threading
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters
from openai import OpenAI
from duckduckgo_search import DDGS

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
        self.wfile.write("Bot de Soporte Técnico Orinoco Dev (Ultra-Rápido) activo!".encode('utf-8'))

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

# --- 2. BÚSQUEDA WEB RÁPIDA ---
def ejecutar_busqueda_rapida(query):
    try:
        query_tecnica = f"solucion error {query}"
        with DDGS() as ddgs:
            resultados = list(ddgs.text(query_tecnica, max_results=2))
            if not resultados:
                return None
            texto_resultados = ""
            for r in resultados:
                texto_resultados += f"- {r['title']}: {r['body']}\n"
            return texto_resultados
    except Exception as e:
        logging.error(f"Búsqueda web omitida/error: {e}")
        return None

def requiere_busqueda_tecnica(texto):
    palabras_clave_criticas = [
        "codigo de error", "pantalla azul", "bsod", "driver", "bug", "0x"
    ]
    texto_lower = texto.lower()
    return any(p in texto_lower for p in palabras_clave_criticas)

def es_saludo(texto):
    saludos = ["hola", "buenas", "buenos dias", "buenas tardes", "buenas noches", "quien eres", "presentate", "que haces", "ayuda"]
    texto_clean = texto.lower().strip()
    return any(s in texto_clean for s in saludos) or len(texto_clean) <= 4

# --- 3. CONFIGURACIÓN CLIENTE NVIDIA NIM ---
client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=NVIDIA_API_KEY
)

# Función sincrónica ejecutada de forma asíncrona dedicada
def obtener_respuesta_nvidia(prompt_sistema, texto_usuario):
    # Modelo ultra-rápido de baja latencia en NVIDIA NIM
    completion = client.chat.completions.create(
        model="meta/llama-3.1-8b-instruct",
        messages=[
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": texto_usuario}
        ],
        temperature=0.1,  # Minimiza la duda para responder mucho más rápido
        max_tokens=350,   # Respuestas sintéticas y al grano
        stream=False
    )
    return completion.choices[0].message.content

# --- 4. COMANDO /start Y PRESENTACIÓN ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    presentacion = (
        "🛠️ **Asistente de Soporte Técnico - Orinoco Dev**\n\n"
        "¡Hola! Soy tu bot de asistencia técnica informática. Estoy diseñado para apoyar en:\n"
        "• Diagnóstico y solución de fallas de **hardware y equipos**.\n"
        "• Mantenimiento y problemas de **software / sistemas operativos**.\n"
        "• Uso y configuración de herramientas de ofimática (**Word, Excel, etc.**).\n"
        "• Configuración de redes y aplicaciones corporativas.\n\n"
        "¿En qué consulta o problema técnico te puedo ayudar hoy?"
    )
    await update.message.reply_text(presentacion, parse_mode="Markdown")

# --- 5. RESPUESTA Y LÓGICA PRINCIPAL ---
async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    texto_usuario = update.message.text

    # 1. Saludos instantáneos (Responde en < 0.2 segundos)
    if es_saludo(texto_usuario):
        presentacion_corta = (
            "🛠️ **Soporte Técnico Orinoco Dev**\n"
            "¡Hola! Estoy listo para ayudarte con problemas de computadoras, programas, herramientas de oficina o soporte informático. "
            "Escribe tu duda o describe la falla que presentas."
        )
        await update.message.reply_text(presentacion_corta, parse_mode="Markdown")
        return

    informacion_web = None
    # 2. Búsqueda web solo si detecta palabras críticas
    if requiere_busqueda_tecnica(texto_usuario):
        try:
            informacion_web = await asyncio.wait_for(
                asyncio.to_thread(ejecutar_busqueda_rapida, texto_usuario), 
                timeout=1.5
            )
        except asyncio.TimeoutError:
            logging.info("Búsqueda web cancelada por tiempo límite.")
            informacion_web = None

    prompt_sistema = (
        "Eres un Asistente Experto en Soporte Técnico Informático para la empresa Orinoco Dev, C.A.\n\n"
        "INSTRUCCIÓN DE VELOCIDAD:\n"
        "Sé ultra conciso y directo. Da la respuesta en pasos cortos numerados.\n\n"
        "REGLAS:\n"
        "1. Solo responde temas informáticos (hardware, software, ofimática).\n"
        "2. Si es ajeno al tema, di amablemente que solo atiendes soporte técnico."
    )

    if informacion_web:
        prompt_sistema += f"\n\nDATOS WEB:\n{informacion_web}"

    try:
        # 3. Ejecución no bloqueante en hilo secundario (Responde en 1 a 3 segundos)
        respuesta_ia = await asyncio.to_thread(
            obtener_respuesta_nvidia, prompt_sistema, texto_usuario
        )

    except Exception as e:
        logging.error(f"Error al conectar con la API de NVIDIA: {e}")
        respuesta_ia = "⚠️ Ocurrió una incidencia técnica temporal. Por favor, reintenta tu consulta."

    await update.message.reply_text(respuesta_ia)

# --- 6. INICIALIZACIÓN DEL BOT ---
if __name__ == "__main__":
    threading.Thread(target=run_dummy_server, daemon=True).start()

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))
    
    print("Bot de Soporte Técnico Orinoco Dev (Ultra-Rápido) activo...")
    app.run_polling(drop_pending_updates=True)
