import time
from playwright.sync_api import sync_playwright
from utils import configurar_contexto, extraer_perfil_y_videos, guardar_json


def ejecutar_anonimo():
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
                "--no-proxy-server"   #  comentarlo Forzar que no se use ningún proxy
            ]
        )
        context = configurar_contexto(browser)
        page = context.new_page()

        print(" Obteniendo cookies anónimas...")
        page.goto("https://www.tiktok.com", timeout=60000)
        page.wait_for_timeout(8000)  # CAMBIO: wait_for_timeout en lugar de time.sleep

        for user in usuarios:
            try:
                datos = extraer_perfil_y_videos(page, user)
                datos["lista_seguidores"] = " Requiere login "
                datos["lista_seguidos"] = " Requiere login "

                #  Guardar UN archivo por usuario
                nombre_archivo = f"resultado_{user}.json"
                guardar_json([datos], nombre_archivo)

                page.wait_for_timeout(10000)  # CAMBIO: wait_for_timeout
            except Exception as e:
                print(f" Error con {user}: {e}")
                #  También guardar el error en su propio archivo
                guardar_json(
                    [{"username": user, "error": str(e)}],
                    f"resultado_{user}.json"
                )

        browser.close()


#  Esto permite ejecutarlo directo con: python scraper_anonimo.py
if __name__ == "__main__":
    print("=== MODO ANÓNIMO ===")
    ejecutar_anonimo()