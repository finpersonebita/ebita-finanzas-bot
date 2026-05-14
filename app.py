from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import anthropic
from supabase import create_client
from datetime import datetime
import os
import json

app = Flask(__name__)

# Clientes de cada servicio
supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
anthropic_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

CATEGORIAS = [
    "Transporte", "Comida", "Restaurantes", "Entretenimiento",
    "Salud", "Educación", "Ropa", "Hogar", "Servicios",
    "Supermercado", "Tecnología", "Otros"
]

def categorizar_gasto(mensaje):
    """Usa Claude para extraer monto, categoría y descripción del mensaje."""
    prompt = f"""Eres un asistente de finanzas personales. El usuario te mandará un mensaje describiendo un gasto.
Debes extraer la información y responder SOLO con un JSON válido, sin texto adicional, sin markdown, sin backticks.

Categorías disponibles: {', '.join(CATEGORIAS)}

Mensaje del usuario: "{mensaje}"

Responde SOLO con este JSON (sin nada más):
{{
  "es_gasto": true o false,
  "monto": número o null,
  "categoria": "categoría" o null,
  "descripcion": "descripción corta" o null,
  "moneda": "PEN" o "USD"
}}

Reglas:
- Si el mensaje no es un gasto, pon es_gasto: false y el resto null
- El monto debe ser solo el número (sin "soles" ni "S/.")
- Si dice "soles" o "S/." la moneda es PEN, si dice "$" o "dólares" es USD
- La descripción debe ser corta (máximo 5 palabras)"""

    response = anthropic_client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}]
    )

    resultado = json.loads(response.content[0].text.strip())
    return resultado

def guardar_gasto(telefono, monto, categoria, descripcion, moneda):
    """Guarda el gasto en Supabase."""
    data = {
        "telefono": telefono,
        "monto": monto,
        "categoria": categoria,
        "descripcion": descripcion,
        "moneda": moneda,
        "fecha": datetime.now().isoformat()
    }
    supabase.table("gastos").insert(data).execute()

def obtener_resumen_mes(telefono):
    """Obtiene el total gastado este mes por categoría."""
    hoy = datetime.now()
    primer_dia = hoy.replace(day=1, hour=0, minute=0, second=0).isoformat()

    response = supabase.table("gastos")\
        .select("categoria, monto")\
        .eq("telefono", telefono)\
        .gte("fecha", primer_dia)\
        .execute()

    if not response.data:
        return {}

    resumen = {}
    for gasto in response.data:
        cat = gasto["categoria"]
        resumen[cat] = resumen.get(cat, 0) + gasto["monto"]

    return resumen

def formatear_monto(monto, moneda):
    if moneda == "USD":
        return f"${monto:.2f}"
    return f"S/. {monto:.2f}"

@app.route("/webhook", methods=["POST"])
def webhook():
    mensaje = request.form.get("Body", "").strip()
    telefono = request.form.get("From", "").replace("whatsapp:", "")

    resp = MessagingResponse()
    msg = resp.message()

    # Comandos especiales
    if mensaje.lower() in ["/resumen", "resumen", "/mes", "mes"]:
        resumen = obtener_resumen_mes(telefono)
        if not resumen:
            msg.body("📊 No tienes gastos registrados este mes todavía.")
        else:
            total = sum(resumen.values())
            texto = "📊 *Resumen de este mes:*\n\n"
            for cat, monto in sorted(resumen.items(), key=lambda x: x[1], reverse=True):
                texto += f"• {cat}: S/. {monto:.2f}\n"
            texto += f"\n💰 *Total: S/. {total:.2f}*"
            msg.body(texto)
        return str(resp)

    if mensaje.lower() in ["/ayuda", "ayuda", "help", "/help"]:
        msg.body(
            "🤖 *EBITA Bot Financiero*\n\n"
            "Registra tus gastos escribiendo naturalmente:\n"
            "• _Gasté 10 soles en taxi_\n"
            "• _50 soles en McDonald's_\n"
            "• _Pagué 200 soles de luz_\n\n"
            "📋 *Comandos:*\n"
            "• *resumen* — ver gastos del mes\n"
            "• *ayuda* — ver este mensaje"
        )
        return str(resp)

    # Intentar categorizar como gasto
    try:
        resultado = categorizar_gasto(mensaje)

        if not resultado.get("es_gasto") or not resultado.get("monto"):
            msg.body(
                "🤔 No entendí ese gasto. Intenta algo como:\n"
                "_\"Gasté 15 soles en almuerzo\"_\n\n"
                "Escribe *ayuda* para ver más ejemplos."
            )
            return str(resp)

        monto = float(resultado["monto"])
        categoria = resultado["categoria"]
        descripcion = resultado["descripcion"]
        moneda = resultado.get("moneda", "PEN")

        guardar_gasto(telefono, monto, categoria, descripcion, moneda)

        # Resumen rápido del mes en esa categoría
        resumen = obtener_resumen_mes(telefono)
        total_categoria = resumen.get(categoria, 0)

        simbolo = "S/." if moneda == "PEN" else "$"
        respuesta = (
            f"✅ *Registrado:*\n"
            f"📝 {descripcion}\n"
            f"💸 {simbolo} {monto:.2f} — {categoria}\n"
            f"📅 {datetime.now().strftime('%d %b, %I:%M %p')}\n\n"
            f"📊 Este mes en {categoria}: S/. {total_categoria:.2f}"
        )

        msg.body(respuesta)

    except Exception as e:
        print(f"Error: {e}")
        msg.body("❌ Hubo un error procesando tu mensaje. Intenta de nuevo.")

    return str(resp)

@app.route("/", methods=["GET"])
def health():
    return "✅ EBITA Bot Financiero activo", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
