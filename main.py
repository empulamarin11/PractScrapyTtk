import sys
from Scrapytiktokanonimo import ejecutar_anonimo
from Scrapytiktoklogin import ejecutar_autenticado

def menu():
    print("\n" + "=" * 45)
    print("      SCRAPER DE TIKTOK — MENÚ PRINCIPAL")
    print("=" * 45)
    print("1. Modo anónimo   (sin login, sin seguidores)")
    print("2. Modo autenticado (con login, todo completo)")
    print("3. Salir")
    print("=" * 45)
    return input("Elige una opción (1/2/3): ").strip()

def main():
    while True:
        opcion = menu()
        if opcion == "1":
            ejecutar_anonimo()
        elif opcion == "2":
            ejecutar_autenticado()
        elif opcion == "3":
            print(" Saliendo...")
            sys.exit(0)
        else:
            print(" Opción inválida. Intenta de nuevo.")

if __name__ == "__main__":
    main()