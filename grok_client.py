"""
Módulo dedicado a la integración con Groq (API compatible con OpenAI).
Encapsula la lógica de Big Five para separarla del scraping.

Uso:
    from grok_client import analizar_bigfive
    resultado = analizar_bigfive(datos, clasificacion)
"""

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
    """Construye el prompt a partir de los datos del perfil, incluyendo emojis."""
    bio = datos.get("bio", "") or "Sin biografía"
    descripciones = [
        v.get("descripcion", "")
        for v in datos.get("ultimos_10_videos", []) or []
        if v.get("descripcion")
    ]
    hashtags = [h[0] for h in clasificacion.get("top_hashtags", [])]
    engagement = clasificacion.get("engagement_promedio_pct", 0)
    seguidores = datos.get("seguidores", 0)

    # ⭐ NUEVO: extraer emojis del análisis ya hecho
    emojis_info = clasificacion.get("emojis", {})
    emojis_bio = emojis_info.get("emojis_bio", [])
    top_emojis = [e[0] for e in emojis_info.get("top_emojis", [])]
    total_emojis = emojis_info.get("total_emojis", 0)

    return f"""Eres un analista de personalidad digital experto en comunicación en redes sociales. Analiza los textos públicos y los emojis de un perfil de TikTok para estimar los rasgos Big Five (OCEAN) en escala 0-100.

Los EMOJIS son señales emocionales clave: un perfil que usa 🎨🌍🎵 proyecta creatividad y apertura; uno que usa 💪🔥😤 proyecta energía y competitividad; uno que usa 🥺💔😢 proyecta vulnerabilidad emocional. Úsalos como evidencia junto al texto.

Responde ÚNICAMENTE con un objeto JSON válido, sin texto adicional, con esta estructura exacta:
{{
  "apertura": 0,
  "responsabilidad": 0,
  "extraversion": 0,
  "amabilidad": 0,
  "neuroticismo": 0,
  "justificacion": "2-3 frases explicando qué evidencia textual Y qué emojis sustentan cada rasgo",
  "evidencia_emojis": "1-2 frases explicando qué revelan los emojis sobre la personalidad",
  "rasgo_dominante": "nombre del rasgo con puntuación más alta",
  "rasgo_debil": "nombre del rasgo con puntuación más baja",
  "perfil_arquetipo": "etiqueta corta de 2-3 palabras que resuma la personalidad (ej: Creativo-Explorador, Líder-Comunicador, Artista-Introspectivo)",
  "conclusion": "párrafo interpretativo de 3-5 frases que sintetice cómo esta persona se proyecta en redes, qué valores comunica, qué tipo de comunidad atrae y una recomendación práctica para potenciar su marca personal. Debe leerse como un análisis con valor, no como una lista de rasgos."
}}

Datos del perfil:
- Biografía: {bio}
- Emojis en la biografía: {emojis_bio if emojis_bio else 'Ninguno'}
- Emojis más frecuentes en videos: {top_emojis if top_emojis else 'Ninguno'}
- Total de emojis detectados: {total_emojis}
- Seguidores: {seguidores}
- Engagement promedio: {engagement}%
- Descripciones de videos: {descripciones if descripciones else 'No disponibles'}
- Hashtags frecuentes: {hashtags if hashtags else 'No disponibles'}

Instrucciones adicionales:
- Los valores de los 5 rasgos deben estar entre 0 y 100.
- `rasgo_dominante` y `rasgo_debil` deben ser exactamente uno de: "apertura", "responsabilidad", "extraversion", "amabilidad", "neuroticismo".
- La `conclusion` debe estar redactada en español, en tono profesional pero cercano.
- El campo `evidencia_emojis` es OBLIGATORIO y debe mencionar emojis concretos del perfil.
- Responde SOLO el JSON, sin markdown ni texto extra."""


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
        print("⚠️ GROQ_API_KEY no configurada en .env. Saltando Big Five.")
        return None

    try:
        client = OpenAI(api_key=api_key, base_url=_BASE_URL)
        response = client.chat.completions.create(
            model=_MODELO,
            messages=[{"role": "user", "content": _construir_prompt(datos, clasificacion)}],
            temperature=0.3,
        )
        contenido = _limpiar_json(response.choices[0].message.content)
        return json.loads(contenido)

    except Exception as e:
        print(f"⚠️ Error en Big Five para @{datos.get('username', '?')}: {e}")
        return None