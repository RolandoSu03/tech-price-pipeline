import subprocess
import sys
import os
import time
from datetime import datetime


def print_header(message):
    """
    Imprime el message por la teerminal
    """
    print("\n" + "=" * 60)
    print(f"  {message}")
    print("=" * 60 + "\n")


def run_script(script_path, description, extra_args=None):
    """
    Ejecuta un script Python con argumentos extra
    """
    
    print_header(f"Ejecutando: {description}")

    cmd = [sys.executable, script_path]
    if extra_args:
        cmd.extend(extra_args)

    try:
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=False, text=True, check=False)
        elapsed_time = time.time() - start_time
        if result.returncode == 0:
            print(f"\n[OK] {description} completado en {elapsed_time:.2f} segundos")
            return True
        else:
            print(f"\n[ERROR] {description} falló con código {result.returncode}")
            return False
    except Exception as e:
        print(f"\n[ERROR] Ejecutando {description}: {e}")
        return False


def run_amazon(search_term, pages):
    script_path = os.path.join('scrapers', 'amazon_monitor.py')
    if os.path.exists(script_path):
        return run_script(script_path, "Scraper Amazon", [search_term, str(pages)])
    else:
        print(f"[ERROR] No se encuentra {script_path}")
        return False


def run_ebay(search_term, pages):
    script_path = os.path.join('scrapers', 'ebay_monitor.py')
    if os.path.exists(script_path):
        return run_script(script_path, "Scraper eBay", [search_term, str(pages)])
    else:
        print(f"[ERROR] No se encuentra {script_path}")
        return False


def run_newegg(search_term, pages):
    script_path = os.path.join('scrapers', 'newegg_monitor.py')
    if os.path.exists(script_path):
        return run_script(script_path, "Scraper Newegg", [search_term, str(pages)])
    else:
        print(f"[ERROR] No se encuentra {script_path}")
        return False


def run_etl():
    script_path = os.path.join('processing', 'data_cleaning.py')
    if os.path.exists(script_path):
        return run_script(script_path, "Procesamiento ETL")
    else:
        print(f"[ERROR] No se encuentra {script_path}")
        return False


def run_dashboard():
    script_path = os.path.join('visualization', 'dashboard.py')
    if os.path.exists(script_path):
        print_header("INICIANDO DASHBOARD")
        subprocess.run([sys.executable, '-m', 'streamlit', 'run', script_path])
        return True
    else:
        print(f"[ERROR] No se encuentra {script_path}")
        return False


def run_pipeline_completo(search_term, pages):
    print_header("PIPELINE COMPLETO")
    results = []
    results.append(("Amazon", run_amazon(search_term, pages)))
    results.append(("eBay", run_ebay(search_term, pages)))
    results.append(("Newegg", run_newegg(search_term, pages)))
    if any([r[1] for r in results]):
        results.append(("ETL", run_etl()))
    else:
        print("[AVISO] No se ejecutó ETL porque no hay datos nuevos")
    run_dashboard()
    print_header("RESUMEN DE EJECUCIÓN")
    for name, success in results:
        status = "[OK]" if success else "[FALLIDO]"
        print(f"  {name}: {status}")


def mostrar_menu():
    print("\nOpciones disponibles:")
    print("  1. Ejecutar pipeline completo (Amazon + eBay + Newegg + ETL + Dashboard)")
    print("  2. Ejecutar solo Amazon + ETL + Dashboard")
    print("  3. Ejecutar solo eBay + ETL + Dashboard")
    print("  4. Ejecutar solo Newegg + ETL + Dashboard")
    print("  5. Ejecutar solo ETL")
    print("  6. Ejecutar solo Dashboard")
    print("  7. Ejecutar solo Amazon")
    print("  8. Ejecutar solo eBay")
    print("  9. Ejecutar solo Newegg")
    print("  10. Cambiar término de búsqueda/páginas")
    print("  11. Salir")
    print("")


def configurar_busqueda(search_term, pages):
    """Devuelve una tupla (nuevo_search_term, nuevas_pages)"""
    print_header("CONFIGURACIÓN DE BÚSQUEDA")
    nuevo_term = input(f"Término de búsqueda actual: {search_term}\nNuevo término (Enter para mantener): ").strip()
    if nuevo_term:
        search_term = nuevo_term
    try:
        nuevas_pag = input(f"Número de páginas actual: {pages}\nNuevas páginas (Enter para mantener): ").strip()
        if nuevas_pag:
            pages = int(nuevas_pag)
    except:
        print("Valor inválido, se mantiene el anterior.")
    print(f"\nBúsqueda configurada: '{search_term}' - {pages} páginas")
    return search_term, pages


def main():
    print_header("TECH PRICE PIPELINE - ORQUESTADOR")
    print(f"Iniciando: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)

    # Configuración inicial
    search_term = input("Ingrese el término de búsqueda (ej: 'Laptop Refurbished'): ").strip()
    if not search_term:
        search_term = "Laptop Refurbished"
    try:
        pages = int(input("Número de páginas a scrapear (default 3): ").strip() or "3")
    except:
        pages = 3

    while True:
        mostrar_menu()
        choice = input("Seleccione una opción (1-11): ").strip()

        if choice == '1':
            run_pipeline_completo(search_term, pages)
        elif choice == '2':
            print_header("Ejecutando: Amazon + ETL + Dashboard")
            if run_amazon(search_term, pages):
                run_etl()
                run_dashboard()
        elif choice == '3':
            print_header("Ejecutando: eBay + ETL + Dashboard")
            if run_ebay(search_term, pages):
                run_etl()
                run_dashboard()
        elif choice == '4':
            print_header("Ejecutando: Newegg + ETL + Dashboard")
            if run_newegg(search_term, pages):
                run_etl()
                run_dashboard()
        elif choice == '5':
            run_etl()
        elif choice == '6':
            run_dashboard()
        elif choice == '7':
            run_amazon(search_term, pages)
        elif choice == '8':
            run_ebay(search_term, pages)
        elif choice == '9':
            run_newegg(search_term, pages)
        elif choice == '10':
            search_term, pages = configurar_busqueda(search_term, pages)
        elif choice == '11':
            print("\n[SALIDA] Saliendo del orquestador...")
            break
        else:
            print("\n[ERROR] Opción inválida.")

        input("\nPresione Enter para continuar...")


if __name__ == "__main__":
    main()