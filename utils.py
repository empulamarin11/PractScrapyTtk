#Librerías a usar
import json
import re
from collections import Counter
import re as _re_emojis
import emoji

#Simulador del navegador Chrome real enviar http al tiktok
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def configurar_contexto(browser, storage_state=None): #contexto de navegador una pestaña
    """Creaun perfil de navegador con medidas anti-detección."""
    args = {
        "user_agent": USER_AGENT,
        "viewport": {"width": 1366, "height": 768}, #tamaño de la pantalla virtual
        "locale": "es-ES",
    }
    if storage_state:  #Pasamos el archivo de cookies guardadas
        args["storage_state"] = storage_state
    context = browser.new_context(**args) #creamos el contexto args
    context.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
    ) #Ejecución antes de cualquier página y ocultamos la propiedad navigator
    return context


def extraer_perfil_y_videos(page, username):
    """Recibe la página, username y extrae perfil + stats + últimos 10 videos con playCount."""
    url = f"https://www.tiktok.com/@{username}"
    print(f"\n Extrayendo @{username}...")

    try:
        #Navegamos a la URL
        respuesta = page.goto(url, timeout=60000, wait_until="domcontentloaded")#Esperar al HTML esté contruido (Parseado)
        if respuesta:
            print(f"Estado HTTP: {respuesta.status}") #ok, bloqueado
            print(f"URL final: {page.url}") #redirección
        else:
            print("La navegación no devolvió una respuesta HTTP.")
    except Exception as e: #si llega a fallar mostramos el error
        print(f"Error de navegación: {e}")
        print(f"URL actual: {page.url}")
        raise #cada modo maneje su error

    page.wait_for_selector('[data-e2e="user-title"]', timeout=30000) #Espera que la página carge el atributo html de tiktok
    page.wait_for_timeout(3000)  # pausa para carga de JSon que nos da el perfil

    # Cerrar pestaña de login
    try:
        page.locator('[data-e2e="modal-close-inner-button"]').click(timeout=3000)
    except:
        pass

    # extraer JSON oculto
    #busca el script que contiene los datos del perfil 
    raw_json = page.locator("#__UNIVERSAL_DATA_FOR_REHYDRATION__").inner_text()
    data = json.loads(raw_json) #Pasamos el string JSon al diccionario de python
    user_detail = data["__DEFAULT_SCOPE__"]["webapp.user-detail"] #Navegamos al diccionario
    user_info = user_detail["userInfo"]
    user = user_info["user"]
    stats = user_info["stats"]

    perfil = {
        "username": user.get("uniqueId"),
        "name": user.get("nickname"),
        "bio": user.get("signature", ""),
        "seguidores": stats.get("followerCount"),
        "seguidos": stats.get("followingCount"),
        "likes_totales": stats.get("heartCount") or stats.get("heart"),  
        "videos_totales": stats.get("videoCount"),
    }

    # Capturar XHR para videos adicionales en una lista
    respuestas_api = []

    # Función "callback" que se ejecuta CADA VEZ que llega una respuesta HTTP
    def capturar(response):
        if "/api/post/item_list" in response.url: # Si la URL contiene "/api/post/item_list" → es la API de videos
            try:
                respuestas_api.append(response.json())
            except:
                pass

    page.on("response", capturar)#cada respuesta captura información

    videos = user_detail.get("itemList", [])
    intentos_sin_nuevos = 0
    while intentos_sin_nuevos < 3: # Si 3 scrolls seguidos no traen nada, paramos
        videos_antes = len(videos)
        # Esto dispara el "lazy loading" → TikTok pide más videos vía XHR
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(2500) # Esperar a que cargue
        # (Aquí se capturan las respuestas XHR y se añaden a 'videos')
        if len(videos) == videos_antes:
            intentos_sin_nuevos += 1
        else:
            intentos_sin_nuevos = 0
        for resp in respuestas_api: # Añadimos a 'videos' todos los itemList de las respuestas capturadas
            videos.extend(resp.get("itemList", []))

    #  función varias veces (varios usuarios), los callbacks se acumularían
    # cada respuesta se capturaría N veces y se acumularia
    page.remove_listener("response", capturar)

    # deduplicar videos por id antes de construir la lista final
    vistos = set()
    videos_unicos = [] #videos filtrados
    for v in videos:
        vid = v.get("id")
        if vid and vid not in vistos:
            vistos.add(vid)
            videos_unicos.append(v)

    lista_videos = []
    for v in videos_unicos[:10]:
        vid = v.get("id")
        v_stats = v.get("stats", {})
        lista_videos.append({
            "url": f"https://www.tiktok.com/@{username}/video/{vid}",
            "descripcion": v.get("desc", "")[:100],
            "vistas": v_stats.get("playCount", 0),
            "likes": v_stats.get("diggCount", 0),
            "comentarios": v_stats.get("commentCount", 0),
            "compartidos": v_stats.get("shareCount", 0),
        })
    perfil["ultimos_10_videos"] = lista_videos
    return perfil


def guardar_json(resultados, nombre_archivo):
    with open(nombre_archivo, "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=4, ensure_ascii=False)
    print(f"\n Guardado en '{nombre_archivo}'.")


# ---------------------------------------------------------------------------
# Clasificación y métricas derivadas (para gráficas en el dashboard)
# ---------------------------------------------------------------------------
def clasificar_perfil(datos: dict) -> dict:
    """
    Analiza un perfil recién extraído y devuelve un dict con:
    - clasificacion_tamano: nano/micro/medio/macro/mega
    - engagement_promedio_pct: % medio de likes/vistas
    - top_hashtags: los 5 hashtags más frecuentes en las descripciones
    - top_palabras_bio: las 5 palabras más frecuentes en la bio
    """
    seguidores = datos.get("seguidores", 0) or 0

    # 1. Clasificación por tamaño (según seguidores)
    if seguidores < 1_000:
        tamaño = "nano"
    elif seguidores < 10_000:
        tamaño = "micro"
    elif seguidores < 100_000:
        tamaño = "medio"
    elif seguidores < 1_000_000:
        tamaño = "macro"
    else:
        tamaño = "mega"

    videos = datos.get("ultimos_10_videos", []) or []

    # 2. Engagement promedio: (likes / vistas) * 100 por cada video
    ratios = []
    for v in videos:
        vistas = v.get("vistas", 0) or 0
        likes = v.get("likes", 0) or 0
        if vistas > 0:
            ratios.append(likes / vistas * 100)
    engagement = round(sum(ratios) / len(ratios), 2) if ratios else 0

    # 3. Hashtags frecuentes en las descripciones
    hashtags = Counter()
    for v in videos:
        desc = v.get("descripcion", "") or ""
        hashtags.update(re.findall(r"#(\w+)", desc))

    # 4. Palabras frecuentes en la bio (más de 3 letras, en minúsculas)
    bio = datos.get("bio", "") or ""
    palabras = [p for p in re.findall(r"\w+", bio.lower()) if len(p) > 3]
    palabras_bio = Counter(palabras)

    return {
        "clasificacion_tamano": tamaño,
        "engagement_promedio_pct": engagement,
        "top_hashtags": hashtags.most_common(5),
        "top_palabras_bio": palabras_bio.most_common(5),
        "emojis": analizar_emojis(datos),   # ← LÍNEA NUEVA
    }

def extraer_emojis(texto: str) -> list[str]:
    """Devuelve una lista con todos los emojis encontrados en un texto usando la librería 'emoji'."""
    if not texto:
        return []
    # emoji_list() encuentra todos los emojis de forma infalible
    return [e['emoji'] for e in emoji.emoji_list(texto)]


def analizar_emojis(datos: dict) -> dict:
    """
    Extrae y cuenta los emojis de la bio y de las descripciones de videos.
    """
    bio = datos.get("bio", "") or ""
    emojis_bio = extraer_emojis(bio)

    videos = datos.get("ultimos_10_videos", []) or []
    emojis_videos = {}
    todos_los_emojis = list(emojis_bio)

    for i, v in enumerate(videos):
        desc = v.get("descripcion", "") or ""
        emojis_desc = extraer_emojis(desc)
        if emojis_desc:
            emojis_videos[i] = emojis_desc
            todos_los_emojis.extend(emojis_desc)

    contador = Counter(todos_los_emojis)

    return {
        "emojis_bio": emojis_bio,
        "emojis_videos": emojis_videos,
        "top_emojis": contador.most_common(10),
        "total_emojis": len(todos_los_emojis),
    }