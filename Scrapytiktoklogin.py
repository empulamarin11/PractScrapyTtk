#Importar librerías
import os
from playwright.sync_api import sync_playwright #Versión síncrona
from utils import configurar_contexto, extraer_perfil_y_videos, guardar_json, clasificar_perfil
from grok_client import analizar_bigfive

STATE_FILE = "tiktok_state.json" #sesión iniciada guardada


def iniciar_sesion(page):
    print("\n Inicia sesión manualmente en la ventana que se abrirá.")
    print("   Cuando estés dentro, vuelve aquí y pulsa ENTER.")
    page.goto("https://www.tiktok.com", timeout=60000)
    input("   ENTER cuando hayas iniciado sesión... ")
    page.context.storage_state(path=STATE_FILE)
    print(f"  Sesión guardada en '{STATE_FILE}'.")


def extraer_lista_modal(page, tipo):
    boton = f'[data-e2e="{tipo}-count"]'
    modal = f'[data-e2e="{tipo}-list"]'
    try:
        page.locator(boton).click(timeout=5000)
        page.wait_for_selector(modal, timeout=10000)
        #esperar explícitamente a que aparezca el primer usuario en el modal
        page.wait_for_selector(f'{modal} [data-e2e="user-title"]', timeout=10000)

        usuarios = set()
        for _ in range(10):
            visibles = page.locator(f'{modal} [data-e2e="user-title"]').all_inner_texts()
            usuarios.update(visibles)
            page.locator(modal).evaluate("el => el.scrollTop = el.scrollHeight")
            page.wait_for_timeout(2000)  

        try:
            page.keyboard.press("Escape")#tecla scape
        except:
            pass

        return list(usuarios) if usuarios else " Lista vacía"
    except Exception as e:
        return f" No accesible: {str(e)[:80]}"


def ejecutar_autenticado():
    usuarios = input("\nUsername: ").strip().split(",")
    usuarios = [u.strip().lstrip("@") for u in usuarios if u.strip()]
    if not usuarios:
        print(" No ingresaste ningún username.")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-proxy-server"   # comentar si falla Forzar que no se use ningún proxy
            ]
        )
        storage = STATE_FILE if os.path.exists(STATE_FILE) else None #comprobar la sesión
        if storage:
            print(f" Cargando sesión desde '{storage}'...")
        context = configurar_contexto(browser, storage_state=storage)
        page = context.new_page()

        if not storage:
            iniciar_sesion(page)

        for user in usuarios:
            try:
                datos = extraer_perfil_y_videos(page, user)
                datos["clasificacion"] = clasificar_perfil(datos)   # ← LÍNEA NUEVa
                datos["bigfive"] = analizar_bigfive(datos, datos["clasificacion"])   # ← NUEVA
                datos["lista_seguidos"] = extraer_lista_modal(page, "following")
                datos["lista_seguidores"] = extraer_lista_modal(page, "followers")

                # Guardar UN archivo por usuario
                nombre_archivo = f"resultado_auth_{user}.json"
                guardar_json([datos], nombre_archivo)

                page.wait_for_timeout(12000)  # CAMBIO: wait_for_timeout
            except Exception as e:
                print(f" Error con {user}: {e}")
                #  También guardar el error en su propio archivo
                guardar_json(
                    [{"username": user, "error": str(e)}],
                    f"resultado_auth_{user}.json"
                )

        browser.close()



if __name__ == "__main__":
    print("=== MODO AUTENTICADO ===")
    ejecutar_autenticado()