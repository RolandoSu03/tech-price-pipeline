import subprocess
import sys
import os
import time
from datetime import datetime

def print_header(message):
    """Imprime un encabezado formateado"""
    print("\n" + "="*60)
    print(f"  {message}")
    print("="*60 + "\n")

def run_script(script_path, description):
    """Ejecuta un script Python y maneja errores"""
    print_header(f"Ejecutando: {description}")
    
    try:
        start_time = time.time()
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=False,
            text=True,
            check=False
        )
        
        elapsed_time = time.time() - start_time
        
        if result.returncode == 0:
            print(f"\n[OK] {description} completado en {elapsed_time:.2f} segundos")
            return True
        else:
            print(f"\n[ERROR] {description} fallo con codigo {result.returncode}")
            return False
            
    except Exception as e:
        print(f"\n[ERROR] Ejecutando {description}: {e}")
        return False

def run_amazon():
    """Ejecuta scraper de Amazon"""
    script_path = os.path.join('scrapers', 'amazon_monitor.py')
    if os.path.exists(script_path):
        return run_script(script_path, "Scraper Amazon")
    else:
        print(f"[ERROR] No se encuentra {script_path}")
        return False

def run_ebay():
    """Ejecuta scraper de eBay"""
    script_path = os.path.join('scrapers', 'ebay_monitor.py')
    if os.path.exists(script_path):
        return run_script(script_path, "Scraper eBay")
    else:
        print(f"[ERROR] No se encuentra {script_path}")
        return False

def run_newegg():
    """Ejecuta scraper de Newegg"""
    script_path = os.path.join('scrapers', 'newegg_monitor.py')
    if os.path.exists(script_path):
        return run_script(script_path, "Scraper Newegg")
    else:
        print(f"[ERROR] No se encuentra {script_path}")
        return False

def run_etl():
    """Ejecuta procesamiento ETL"""
    script_path = os.path.join('processing', 'data_cleaning.py')
    if os.path.exists(script_path):
        return run_script(script_path, "Procesamiento ETL")
    else:
        print(f"[ERROR] No se encuentra {script_path}")
        return False

def run_dashboard():
    """Lanza el dashboard de Streamlit"""
    script_path = os.path.join('visualization', 'dashboard.py')
    if os.path.exists(script_path):
        print_header("INICIANDO DASHBOARD")
        print("Abriendo dashboard en Streamlit...")
        subprocess.run([sys.executable, '-m', 'streamlit', 'run', script_path])
        return True
    else:
        print(f"[ERROR] No se encuentra {script_path}")
        return False

def run_pipeline_completo():
    """Ejecuta todos los componentes en secuencia"""
    print_header("PIPELINE COMPLETO")
    
    results = []
    
    # Amazon
    results.append(("Amazon", run_amazon()))
    
    # eBay
    results.append(("eBay", run_ebay()))
    
    # Newegg
    results.append(("Newegg", run_newegg()))
    
    # ETL (solo si algun scraper funciono)
    if any([r[1] for r in results]):
        results.append(("ETL", run_etl()))
    else:
        print("[AVISO] No se ejecuto ETL porque no hay datos nuevos")
    
    # Dashboard
    run_dashboard()
    
    # Resumen
    print_header("RESUMEN DE EJECUCION")
    for name, success in results:
        status = "[OK]" if success else "[FALLIDO]"
        print(f"  {name}: {status}")

def mostrar_menu():
    """Muestra el menu interactivo"""
    print("\n" + "="*60)
    print("  TECH PRICE PIPELINE - ORQUESTADOR INTERACTIVO")
    print("="*60)
    print("\nOpciones disponibles:")
    print("  1. Ejecutar pipeline completo (Amazon + eBay + Newegg + ETL + Dashboard)")
    print("  2. Ejecutar solo Amazon + ETL + Dashboard")
    print("  3. Ejecutar solo eBay + ETL + Dashboard")
    print("  4. Ejecutar solo Newegg + ETL + Dashboard")
    print("  5. Ejecutar solo ETL (procesar JSON existentes)")
    print("  6. Ejecutar solo Dashboard")
    print("  7. Ejecutar solo Amazon")
    print("  8. Ejecutar solo eBay")
    print("  9. Ejecutar solo Newegg")
    print("  10. Salir")
    print("")

def main():
    """Funcion principal con menu interactivo"""
    
    print_header("TECH PRICE PIPELINE - ORQUESTADOR")
    print(f"Iniciando: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Verificar estructura del proyecto
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)
    
    while True:
        mostrar_menu()
        
        choice = input("Seleccione una opcion (1-10): ").strip()
        
        if choice == '1':
            run_pipeline_completo()
        
        elif choice == '2':
            print_header("EJECUTANDO: Amazon + ETL + Dashboard")
            if run_amazon():
                run_etl()
                run_dashboard()
        
        elif choice == '3':
            print_header("EJECUTANDO: eBay + ETL + Dashboard")
            if run_ebay():
                run_etl()
                run_dashboard()
        
        elif choice == '4':
            print_header("EJECUTANDO: Newegg + ETL + Dashboard")
            if run_newegg():
                run_etl()
                run_dashboard()
        
        elif choice == '5':
            print_header("EJECUTANDO: Solo ETL")
            run_etl()
        
        elif choice == '6':
            run_dashboard()
        
        elif choice == '7':
            run_amazon()
        
        elif choice == '8':
            run_ebay()
        
        elif choice == '9':
            run_newegg()
        
        elif choice == '10':
            print("\n[SALIDA] Saliendo del orquestador...")
            print(f"Ejecucion finalizada: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            break
        
        else:
            print("\n[ERROR] Opcion invalida. Por favor, seleccione 1-10.")
        
        # Pausa antes de volver al menu
        input("\nPresione Enter para continuar...")

if __name__ == "__main__":
    main()