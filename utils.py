import json
import time

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

def configurar_contexto(browser, storage_state=None):
    """Crea un contexto de navegador con medidas anti-detección."""
    args = {
        "user_agent": USER_AGENT,
        "viewport": {"width": 1366, "height": 768},
        "locale": "es-ES",
    }
    if storage_state:
        args["storage_state"] = storage_state
    context = browser.new_context(**args)
    context.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
    )
    return context

def extraer_perfil_y_videos(page, username):
    """Extrae perfil + stats + últimos 12 videos con playCount."""
    url = f"https://www.tiktok.com/@{username}"
    print(f"\nExtrayendo @{username}...")
    page.goto(url, timeout=60000, wait_until="domcontentloaded")
    page.wait_for_selector('[data-e2e="user-title"]', timeout=30000)
    time.sleep(3)

    # Cerrar popup de login (por si aparece)
    try:
        page.locator('[data-e2e="modal-close-inner-button"]').click(timeout=3000)
    except:
        pass

    # JSON oculto
    raw_json = page.locator("#__UNIVERSAL_DATA_FOR_REHYDRATION__").inner_text()
    data = json.loads(raw_json)
    user_detail = data["__DEFAULT_SCOPE__"]["webapp.user-detail"]
    user_info = user_detail["userInfo"]
    user = user_info["user"]
    stats = user_info["stats"]

    perfil = {
        "username": user.get("uniqueId"),
        "name": user.get("nickname"),
        "bio": user.get("signature", ""),
        "seguidores": stats.get("followerCount"),
        "seguidos": stats.get("followingCount"),
        "likes_totales": stats.get("heart"),
        "videos_totales": stats.get("videoCount"),
    }

    # Capturar XHR para videos adicionales
    respuestas_api = []
    def capturar(response):
        if "/api/post/item_list" in response.url:
            try: respuestas_api.append(response.json())
            except: pass
    page.on("response", capturar)

    videos = user_detail.get("itemList", [])
    intentos = 0
    while len(videos) < 12 and intentos < 10:
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(2)
        intentos += 1

    for resp in respuestas_api:
        videos.extend(resp.get("itemList", []))

    lista_videos = []
    for v in videos[:12]:
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
    perfil["ultimos_12_videos"] = lista_videos
    return perfil

def guardar_json(resultados, nombre_archivo):
    with open(nombre_archivo, "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=4, ensure_ascii=False)
    print(f"\n Guardado en '{nombre_archivo}'.")
