import time
from playwright.sync_api import sync_playwright
from utils import configurar_contexto, extraer_perfil_y_videos, guardar_json

def main():
    usuarios = input("Usernames separados por coma: ").strip().split(",")
    usuarios = [u.strip().lstrip("@") for u in usuarios if u.strip()]

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = configurar_contexto(browser)
        page = context.new_page()

        # Cookies anónimas (ttwid, msToken)
        print(" Obteniendo cookies anónimas...")
        page.goto("https://www.tiktok.com", timeout=60000)
        time.sleep(5)

        resultados = []
        for user in usuarios:
            try:
                datos = extraer_perfil_y_videos(page, user)
                datos["lista_seguidores"] = " Requiere login (usar scraper_autenticado.py)"
                datos["lista_seguidos"] = " Requiere login (usar scraper_autenticado.py)"
                resultados.append(datos)
                time.sleep(10)
            except Exception as e:
                print(f" Error con {user}: {e}")
                resultados.append({"username": user, "error": str(e)})

        guardar_json(resultados, "resultados_anonimo.json")
        browser.close()

if __name__ == "__main__":
    main()