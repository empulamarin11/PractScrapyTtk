#importamos las librerías

import json
import os

from dotenv import load_dotenv
from openai import OpenAI

# Carga las variables del .env al entorno (una sola vez al importar)
load_dotenv()

# Constantes del módulo (adaptadas a Groq)
_MODELO = "openai/gpt-oss-120b"  # Modelo gratuito con buen rendimiento [citation:3][citation:4]
_BASE_URL = "https://api.groq.com/openai/v1"  # Endpoint compatible con OpenAI [citation:2]


def _construir_prompt(datos: dict, clasificacion: dict) -> str:
    """Construye el prompt a partir de los datos del perfil, incluyendo emojis y enfoque de negocio."""
    bio = datos.get("bio", "") or "Sin biografía"
    descripciones = [
        v.get("descripcion", "")
        for v in datos.get("ultimos_10_videos", []) or []
        if v.get("descripcion")
    ]
    hashtags = [h[0] for h in clasificacion.get("top_hashtags", [])]
    engagement = clasificacion.get("engagement_promedio_pct", 0)
    seguidores = datos.get("seguidores", 0)

    # Extraer emojis del análisis ya hecho
    emojis_info = clasificacion.get("emojis", {})
    emojis_bio = emojis_info.get("emojis_bio", [])
    top_emojis = [e[0] for e in emojis_info.get("top_emojis", [])]
    total_emojis = emojis_info.get("total_emojis", 0)

    return f"""Eres el dueño de "TeddyCraft Studio", una tienda online de peluches personalizados y accesorios (pines, broches). 
Tu ÚNICA tarea es analizar este perfil de TikTok y recomendarle AL USUARIO EL ARTÍCULO FÍSICO EXACTO que debe comprar de tu tienda.

Responde ÚNICAMENTE con un objeto JSON válido con esta estructura:
{{
  "apertura": 0,
  "responsabilidad": 0,
  "extraversion": 0,
  "amabilidad": 0,
  "neuroticismo": 0,
  "justificacion": "2-3 frases explicando qué evidencia textual Y qué emojis sustentan cada rasgo",
  "evidencia_emojis": "1-2 frases explicando qué revelan los emojis",
  "rasgo_dominante": "nombre del rasgo más alto",
  "perfil_arquetipo": "etiqueta corta (ej: Creativo-Explorador)",
  "producto_recomendado": "El nombre de un producto físico inventado pero acorde a la tienda (Ej: 'Peluche de Dragón de Sombras', 'Pin de Espada Medieval', 'Peluche de Aguacate con lentes'). NO inventes negocios, NO inventes servicios, NO inventes plataformas. SOLO el nombre del producto.",
  "justificacion_venta": "3-4 frases explicando POR QUÉ este producto físico específico es perfecto para el cliente, basándote en sus rasgos Big Five y en sus emojis.",
  "conclusion": "párrafo interpretativo de 3-5 frases."
}}

INSTRUCCIONES CRÍTICAS (SI NO LAS CUMPLES, EL SISTEMA FALLARÁ):
1. Los valores de los 5 rasgos DEBEN sumar exactamente 100.
2. El campo "producto_recomendado" debe ser un objeto tangible (un peluche, un pin, un broche). Si el usuario tiene alta extraversión, NO le vendas un "servicio de streaming", véndele un "Peluche de Micrófono Cantante".
3. El campo "justificacion_venta" debe empezar con: "Te recomiendo este artículo porque..."

Datos del perfil:
- Biografía: {bio}
- Emojis en la biografía: {emojis_bio if emojis_bio else 'Ninguno'}
- Emojis frecuentes en videos: {top_emojis if top_emojis else 'Ninguno'}
- Seguidores: {seguidores}
- Engagement promedio: {engagement}%
- Descripciones de videos: {descripciones if descripciones else 'No disponibles'}
- Hashtags frecuentes: {hashtags if hashtags else 'No disponibles'}"""


def _limpiar_json(contenido: str) -> str:
    """Quita posibles bloques markdown (```json ... ```) que el modelo a veces añade."""
    contenido = contenido.strip()
    if contenido.startswith("```"):
        contenido = contenido.split("```")[1]
        if contenido.startswith("json"):
            contenido = contenido[4:]
    return contenido.strip()


def analizar_bigfive(datos: dict, clasificacion: dict) -> dict | None:
    """
    Estima rasgos Big Five con Groq.
    Devuelve un dict con los 5 rasgos + justificación, o None si falla.
    """
    api_key = os.getenv("GROQ_API_KEY") 
    if not api_key:
        print(" GROQ_API_KEY no configurada en .env. Saltando Big Five.")
        return None

    try:
        client = OpenAI(api_key=api_key, base_url=_BASE_URL) #inicializa el cliente
        #llamamos a la IA
        response = client.chat.completions.create(
            model=_MODELO,
            messages=[{"role": "user", "content": _construir_prompt(datos, clasificacion)}],
            temperature=0.3, #respuestas mas lógicas
        )
        contenido = _limpiar_json(response.choices[0].message.content)
        return json.loads(contenido) #extraemos de texto y convertir a diccionario py

    except Exception as e:
        print(f"⚠️ Error en Big Five para @{datos.get('username', '?')}: {e}")
        return None

