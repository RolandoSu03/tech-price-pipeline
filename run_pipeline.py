import subprocess
import sys
import os
import time

# Intentamos importar las funciones de tus scrapers ubicados en la carpeta scrapers
try:
    from scrapers.amazon_monitor import scrape_amazon
    from scrapers.ebay_monitor import scrape_ebay
    from scrapers.newegg_monitor import scrape_newegg
except ImportError:
    print("Error: No se pudieron importar los modulos de scraping.")
    print("Asegurate de tener un archivo vacio llamado __init__.py dentro de la carpeta scrapers.")

def ejecutar_limpieza():
    print("\n--- PASO 2: Iniciando limpieza y carga de datos (ETL) ---")
    # Ruta al script de limpieza
    script_path = os.path.join("processing", "data_cleaning.py")
    
    if not os.path.exists(script_path):
        print(f"Error: No se encontro el archivo {script_path}")
        return False
        
    resultado = subprocess.run([sys.executable, script_path], capture_output=False)
    
    if resultado.returncode == 0:
        print("Limpieza completada con exito.")
        return True
    else:
        print("Error durante la limpieza.")
        return False

def lanzar_dashboard():
    print("\n--- PASO 3: Generando Visualizacion en Streamlit ---")
    dashboard_path = os.path.join("visualization", "dashboard.py")
    
    if not os.path.exists(dashboard_path):
        print(f"Error: No se encontro el archivo {dashboard_path}")
        return

    try:
        # Popen inicia el proceso sin bloquear la terminal para que el script pueda finalizar
        subprocess.Popen(["streamlit", "run", dashboard_path])
        print("Dashboard lanzado. El servidor esta corriendo en segundo plano.")
        print("Puedes cerrar esta terminal o seguir usandola.")
    except Exception as e:
        print(f"No se pudo lanzar el dashboard: {e}")

def main():
    print("==========================================")
    print("   PIXOR AUTOMATED DATA PIPELINE v1.0     ")
    print("==========================================")

    # Parametros de busqueda
    busqueda = "Laptop Refurbished"
    paginas = 2
    
    print(f"Iniciando recoleccion para: '{busqueda}'")
    
    try:
        # 1. EJECUCION DE SCRAPERS
        # Se ejecutan uno por uno para evitar sobrecarga de memoria
        scrape_amazon(busqueda, pages=paginas)
        scrape_ebay(busqueda, pages=paginas)
        scrape_newegg(busqueda, pages=paginas)
        print("\n--- Recoleccion de datos crudos finalizada ---")
        
        # 2. PROCESAMIENTO DE DATOS (ETL)
        if ejecutar_limpieza():
            time.sleep(1)
            # 3. LANZAMIENTO DE INTERFAZ
            lanzar_dashboard()
            
    except Exception as e:
        print(f"Fallo critico en el pipeline: {e}")

if __name__ == "__main__":
    main()