# EBITA Bot Financiero 🤖

Chatbot de WhatsApp para registrar gastos personales con IA.

## Variables de entorno (Railway)

Estas variables las agregas en Railway → Variables:

```
SUPABASE_URL=https://zpaqjbdsyronafntqkmz.supabase.co
SUPABASE_KEY=tu_supabase_key
ANTHROPIC_API_KEY=tu_anthropic_key
```

## Setup base de datos

1. Ve a Supabase → SQL Editor
2. Copia y ejecuta el contenido de `setup_database.sql`

## Uso del bot

Manda mensajes naturales a WhatsApp:
- "Gasté 10 soles en taxi"
- "50 soles en McDonald's"
- "Pagué 200 soles de luz"

Comandos especiales:
- `resumen` — ver gastos del mes actual
- `ayuda` — ver instrucciones
