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
OPENCODE_API_KEY = os.getenv("OPENCODE_API_KEY")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- 1. SERVIDOR DUMMY PARA MANTENER ACTIVO RENDER ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write("Bot de Soporte Técnico Orinoco IA activo!".encode('utf-8'))

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

# --- 2. BÚSQUEDA WEB EN TIEMPO REAL (SOLO TÉCNICA) ---
def ejecutar_busqueda_ddg(query):
    try:
        # Forzar que la búsqueda sea sobre soporte o solución de errores técnicos
        query_tecnica = f"solucion error soporte tecnico {query}"
        with DDGS() as ddgs:
            resultados = list(ddgs.text(query_tecnica, max_results=3))
            if not resultados:
                return None
            
            texto_resultados = ""
            for r in resultados:
                texto_resultados += f"- {r['title']}: {r['body']}\n"
            return texto_resultados
    except Exception as e:
        logging.error(f"Error en búsqueda web técnica: {e}")
        return None

def requiere_busqueda_tecnica(texto):
    palabras_clave_tecnicas = [
        "error", "fallo", "codigo de error", "driver", "pantalla azul", 
        "actualizar", "instalar", "formatear", "como usar", "tutorial", 
        "solucionar", "no arranca", "lento", "bug"
    ]
    texto_lower = texto.lower()
    return any(palabra in texto_lower for palabra in palabras_clave_tecnicas)

def es_saludo(texto):
    saludos = ["hola", "buenas", "buenos dias", "buenas tardes", "buenas noches", "quien eres", "presentate", "que haces", "ayuda"]
    texto_clean = texto.lower().strip()
    return any(s in texto_clean for s in saludos) or len(texto_clean) <= 4

# --- 3. CONFIGURACIÓN CLIENTE OPENCODE / OPENROUTER ---
client = OpenAI(
    api_key=OPENCODE_API_KEY,
    base_url="https://openrouter.ai/api/v1"
)

# --- 4. COMANDO /start Y PRESENTACIÓN ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    presentacion = (
        "🛠️ **Asistente de Soporte Técnico - Orinoco Dev**\n\n"
        "¡Hola! Soy tu bot de asistencia técnica informática. Estoy diseñado para apoyar al personal en:\n"
        "• Diagnóstico y solución de fallas de **hardware y equipos**.\n"
        "• Mantenimiento y problemas de **software / sistemas operativos**.\n"
        "• Uso y configuración de herramientas de ofimática (**Word, Excel, etc.**).\n"
        "• Configuración de redes y aplicaciones corporativas.\n\n"
        "¿En qué falla, error o consulta técnica te puedo ayudar hoy?"
    )
    await update.message.reply_text(presentacion, parse_mode="Markdown")

# --- 5. RESPUESTA Y LÓGICA PRINCIPAL DE SOPORTE TÉCNICO ---
async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    texto_usuario = update.message.text

    # Saludo y presentación corta
    if es_saludo(texto_usuario):
        presentacion_corta = (
            "🛠️ **Soporte Técnico Orinoco Dev**\n"
            "¡Hola! Estoy listo para ayudarte con problemas de computadoras, programas, herramientas de oficina o soporte informático. "
            "Escribe tu duda o Describe la falla que presentas."
        )
        await update.message.reply_text(presentacion_corta, parse_mode="Markdown")
        return

    informacion_web = None
    if requiere_busqueda_tecnica(texto_usuario):
        informacion_web = await asyncio.to_thread(ejecutar_busqueda_ddg, texto_usuario)

    # --- PROMPT DE SISTEMA: RESTRICCIÓN ESTRICTA A SOPORTE TÉCNICO Y PRIVACIDAD ---
    prompt_sistema = (
        "Eres un Asistente Experto en Soporte Técnico Informático para el personal de la empresa Orinoco Dev, C.A.\n\n"
        "ROL Y OBJETIVO:\n"
        "Tu ÚNICA función es ofrecer asistencia técnica clara, estructurada, profesional y paso a paso sobre:\n"
        "- Hardware (Mantenimiento, componentes, fallas informáticas, diagnósticos).\n"
        "- Software y Sistemas Operativos (Windows, Linux, errores de instalación, drivers, optimización).\n"
        "- Herramientas de Oficina y Productividad (Uso de Microsoft Word, Excel, PowerPoint, correo, etc.).\n"
        "- Solución de errores y problemas comunes en computadoras y periféricos.\n\n"
        "REGLAS STRICTAS DE RESTRICCIÓN Y SEGURIDAD:\n"
        "1. NO respondas sobre datos de la empresa, finanzas, RIF, clientes, ventas, ubicación o soporte operativo.\n"
        "2. NO respondas preguntas generales fuera del ámbito informático o de soporte técnico (por ejemplo: cultura general, personajes ficticios, entretenimiento, deportes, cocina, etc.). Si te preguntan algo ajeno a la informática, responde cortésmente: 'Lo siento, mi función se limita estrictamente a brindar asistencia y soporte técnico informático para hardware, software y aplicaciones.'\n"
        "3. Mantén la confidencialidad absoluta: NUNCA solicites ni reveles contraseñas, credenciales internas o código fuente privado.\n"
        "4. Estructura siempre tus respuestas técnicas con viñetas, pasos numerados y un lenguaje claro y accesible."
    )

    if informacion_web:
        prompt_sistema += (
            f"\n\nDATOS TÉCNICOS ADICIONALES DE BÚSQUEDA WEB:\n"
            f"{informacion_web}\n"
            f"Utiliza esta información solo si ayuda a solucionar técnicamente el problema del usuario."
        )

    try:
        response = client.chat.completions.create(
            model="meta-llama/llama-3.1-8b-instruct:free",
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": texto_usuario}
            ],
            temperature=0.3,  # Baja temperatura para respuestas precisas y estructuradas
            max_tokens=1024
        )
        respuesta_ia = response.choices[0].message.content
    except Exception as e:
        logging.error(f"Error al conectar con la API de OpenCode: {e}")
        respuesta_ia = "⚠️ Ocurrió una incidencia técnica temporal al procesar tu consulta. Por favor, reintenta en unos instantes."

    await update.message.reply_text(respuesta_ia)

# --- 6. INICIALIZACIÓN DEL BOT ---
if __name__ == "__main__":
    # Iniciar servidor dummy para Render en un hilo secundario
    threading.Thread(target=run_dummy_server, daemon=True).start()

    # Construir y lanzar el bot de Telegram
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))
    
    print("Bot de Soporte Técnico Orinoco IA desplegado y escuchando...")
    app.run_polling(drop_pending_updates=True)
