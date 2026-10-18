import os
import time
from playwright.sync_api import sync_playwright
from utils import configurar_contexto, extraer_perfil_y_videos, guardar_json

STATE_FILE = "tiktok_state.json"

def iniciar_sesion(page):
    print("\n Inicia sesión manualmente en la ventana que se abrirá.")
    print("   Cuando estés dentro, vuelve aquí y pulsa ENTER.")
    page.goto("https://www.tiktok.com", timeout=60000)
    input("   ENTER cuando hayas iniciado sesión... ")
    page.context.storage_state(path=STATE_FILE)
    print(f"   Sesión guardada en '{STATE_FILE}'.")

def extraer_lista_modal(page, tipo):
    boton = f'[data-e2e="{tipo}-count"]'
    modal = f'[data-e2e="{tipo}-list"]'
    try:
        page.locator(boton).click(timeout=5000)
        time.sleep(3)
        page.wait_for_selector(modal, timeout=10000)

        usuarios = set()
        for _ in range(10):
            visibles = page.locator(f'{modal} [data-e2e="user-title"]').all_inner_texts()
            usuarios.update(visibles)
            page.locator(modal).evaluate("el => el.scrollTop = el.scrollHeight")
            time.sleep(2)

        # Cerrar el modal
        try:
            page.keyboard.press("Escape")
        except:
            pass

        return list(usuarios) if usuarios else " Lista vacía"
    except Exception as e:
        return f" No accesible: {str(e)[:80]}"

def ejecutar_autenticado():
    usuarios = input("\nUsernames separados por coma: ").strip().split(",")
    usuarios = [u.strip().lstrip("@") for u in usuarios if u.strip()]
    if not usuarios:
        print(" No ingresaste ningún username.")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        storage = STATE_FILE if os.path.exists(STATE_FILE) else None
        if storage:
            print(f" Cargando sesión desde '{storage}'...")
        context = configurar_contexto(browser, storage_state=storage)
        page = context.new_page()

        if not storage:
            iniciar_sesion(page)

        resultados = []
        for user in usuarios:
            try:
                datos = extraer_perfil_y_videos(page, user)
                datos["lista_seguidos"] = extraer_lista_modal(page, "following")
                datos["lista_seguidores"] = extraer_lista_modal(page, "followers")
                resultados.append(datos)
                time.sleep(12)
            except Exception as e:
                print(f" Error con {user}: {e}")
                resultados.append({"username": user, "error": str(e)})

        guardar_json(resultados, "resultados_autenticado.json")
        browser.close()