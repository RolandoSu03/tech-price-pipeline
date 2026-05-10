import pandas as pd
import sqlite3
import glob
import os
import re
from datetime import datetime

def clean_price(price_str):
    """Limpia y convierte el precio a float"""
    if pd.isna(price_str) or price_str == "N/A" or price_str == "":
        return None
    
    clean_val = str(price_str)
    clean_val = re.sub(r'[^\d.,]', '', clean_val)
    clean_val = clean_val.replace(',', '')
    
    match = re.search(r'(\d+\.?\d*)', clean_val)
    if match:
        try:
            return float(match.group(1))
        except:
            return None
    return None

def parse_to_gb(value_str):
    """
    Convierte string de capacidad a numero entero en GB.
    Ejemplos: '16GB' -> 16, '1TB' -> 1024, '512GB' -> 512
    """
    if not value_str or value_str == "N/A" or pd.isna(value_str):
        return None
    
    value_str = str(value_str).upper().strip()
    numbers = re.findall(r'(\d+(?:\.\d+)?)', value_str)
    
    if not numbers:
        return None
    
    numeric_value = float(numbers[0])
    
    if "TB" in value_str:
        numeric_value = int(numeric_value * 1024)
    else:
        numeric_value = int(numeric_value)
    
    return numeric_value if numeric_value > 0 else None

def extract_ram(title):
    """
    Extrae la RAM del titulo.
    Patrones: 8GB, 16 GB, 32GB, 64GB
    """
    if not title or pd.isna(title):
        return None
    
    title_upper = title.upper()
    
    patterns = [
        r'(\d+)\s*GB\s*RAM',
        r'RAM\s*(\d+)\s*GB',
        r'(\d+)\s*GB(?:\s*DDR\d)?',
        r'(\d+)\s*GB(?!\s*SSD|\s*HDD|\s*STORAGE)',
        r'(\d+)\s*G\s*RAM',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, title_upper)
        if match:
            ram_value = int(match.group(1))
            if 4 <= ram_value <= 128:
                return ram_value
    
    return None

def extract_storage(title):
    """
    Extrae el almacenamiento del titulo.
    Patrones: 256GB, 512 GB, 1TB, 2TB, 512GB SSD, 1TB HDD
    """
    if not title or pd.isna(title):
        return None
    
    title_upper = title.upper()
    
    patterns = [
        r'(\d+(?:\.\d+)?)\s*(TB|GB)\s*(?:SSD|HDD)',
        r'(\d+(?:\.\d+)?)\s*(TB|GB)\s*SSD',
        r'(\d+(?:\.\d+)?)\s*(TB|GB)\s*HDD',
        r'(\d+(?:\.\d+)?)\s*(TB|GB)(?:\s+[A-Z]|$|\)|\,)',
        r'(\d+)\s*(TB|GB)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, title_upper)
        if match:
            value = float(match.group(1))
            unit = match.group(2) if len(match.groups()) > 1 else "GB"
            
            if unit == "TB" and 1 <= value <= 4:
                return int(value * 1024)
            elif unit == "GB" and 32 <= value <= 4096:
                return int(value)
    
    return None

def extract_brand(title):
    """
    Extrae la marca del titulo con mejor precision
    """
    if not title or pd.isna(title):
        return "OTHER"
    
    title_upper = title.upper()
    
    brands = {
        'APPLE': ['APPLE', 'MACBOOK', 'MAC', 'IPAD', 'IPHONE'],
        'LENOVO': ['LENOVO', 'THINKPAD', 'IDEAPAD', 'LEGION'],
        'HP': ['HP', 'Hewlett Packard', 'ELITEBOOK', 'PROBOOK', 'SPECTRE', 'ENVY', 'PAVILION'],
        'DELL': ['DELL', 'XPS', 'LATITUDE', 'INSPIRON', 'PRECISION', 'ALIENWARE'],
        'ASUS': ['ASUS', 'ROG', 'ZENBOOK', 'VIVOBOOK', 'TUF'],
        'ACER': ['ACER', 'PREDATOR', 'ASPIRE', 'SWIFT'],
        'SAMSUNG': ['SAMSUNG', 'GALAXY'],
        'MICROSOFT': ['MICROSOFT', 'SURFACE'],
        'MSI': ['MSI'],
        'GIGABYTE': ['GIGABYTE', 'AORUS']
    }
    
    for brand, keywords in brands.items():
        for keyword in keywords:
            if keyword in title_upper:
                return brand
    
    return "OTHER"

def extract_full_specs(title):
    """
    Extrae todas las especificaciones del titulo
    """
    if not title or pd.isna(title):
        return "OTHER", None, None
    
    ram = extract_ram(title)
    storage = extract_storage(title)
    brand = extract_brand(title)
    
    return brand, ram, storage

def remove_duplicate_titles(df):
    """
    Elimina duplicados basados en titulo exactamente igual y misma plataforma
    Mantiene el registro mas reciente (por scraped_at)
    """
    print("\nEliminando duplicados por titulo exacto y plataforma...")
    
    initial_count = len(df)
    
    # Ordenar por fecha descendente (mas reciente primero)
    df = df.sort_values(by=['scraped_at'], ascending=False)
    
    # Eliminar duplicados por combinacion de titulo y plataforma
    df = df.drop_duplicates(subset=['title', 'platform'], keep='first')
    
    removed_count = initial_count - len(df)
    print(f"  Duplicados eliminados por titulo+plataforma: {removed_count}")
    
    return df

def normalize_to_silver():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.join(base_dir, '..')
    data_dir = os.path.join(project_root, 'data') 
    
    silver_dir = os.path.join(data_dir, 'silver')
    db_dir = os.path.join(data_dir, 'db')
    db_path = os.path.join(db_dir, 'tech_prices_gold.db')
    
    os.makedirs(silver_dir, exist_ok=True)
    os.makedirs(db_dir, exist_ok=True)

    print("\n" + "="*50)
    print("PROCESAMIENTO DE DATOS - LIMPIEZA Y NORMALIZACION")
    print("="*50)

    json_files = glob.glob(os.path.join(data_dir, 'raw_*.json'))
    if not json_files:
        print("No hay archivos JSON para procesar.")
        return

    print(f"Encontrados {len(json_files)} archivos JSON")
    
    list_of_dfs = []
    for file in json_files:
        try:
            df_temp = pd.read_json(file)
            print(f"Cargado: {os.path.basename(file)} ({len(df_temp)} registros)")
            list_of_dfs.append(df_temp)
        except Exception as e:
            print(f"Error cargando {file}: {e}")
            continue

    if not list_of_dfs:
        print("No se pudieron cargar los archivos.")
        return

    df = pd.concat(list_of_dfs, ignore_index=True)
    print(f"\nTotal de registros sin procesar: {len(df)}")

    print("\nExtrayendo especificaciones de los titulos...")
    df[['brand', 'ram_gb', 'storage_gb']] = df.apply(
        lambda row: pd.Series(extract_full_specs(row['title'])), axis=1
    )
    
    print("Limpiando precios...")
    df['price'] = df['price_raw'].apply(clean_price)
    
    initial_count = len(df)
    df = df.dropna(subset=['title', 'url', 'price'])
    df = df[df['price'] > 0]
    
    df['scraped_at'] = pd.to_datetime(df['scraped_at'], errors='coerce')
    df['last_updated'] = datetime.now()
    
    # PRIMERA LIMPIEZA: Eliminar duplicados por URL (mantener el mas reciente)
    print("\nPrimera limpieza: eliminando duplicados por URL...")
    df = df.sort_values(by=['url', 'scraped_at'], ascending=[True, False])
    df = df.drop_duplicates('url', keep='first')
    print(f"  Registros despues de limpieza por URL: {len(df)}")
    
    # SEGUNDA LIMPIEZA: Eliminar duplicados por titulo exacto + plataforma
    df = remove_duplicate_titles(df)
    
    print(f"\nDespues de limpieza completa:")
    print(f"  Registros iniciales: {initial_count}")
    print(f"  Registros finales: {len(df)}")
    print(f"  Registros descartados: {initial_count - len(df)}")
    
    print(f"\nEstadisticas de especificaciones:")
    ram_known = df[df['ram_gb'].notna()]
    storage_known = df[df['storage_gb'].notna()]
    print(f"  RAM detectada: {len(ram_known)}/{len(df)} ({len(ram_known)/len(df)*100:.1f}%)")
    print(f"  Storage detectado: {len(storage_known)}/{len(df)} ({len(storage_known)/len(df)*100:.1f}%)")
    
    # Guardar archivo CSV en carpeta silver
    print("\nGuardando archivo CSV en capa silver...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = f"silver_tech_prices_{timestamp}.csv"
    csv_path = os.path.join(silver_dir, csv_filename)
    
    df.to_csv(csv_path, index=False, encoding='utf-8')
    print(f"  CSV guardado: {csv_path}")
    print(f"  Registros en CSV: {len(df)}")
    
    latest_csv_path = os.path.join(silver_dir, "silver_tech_prices_latest.csv")
    df.to_csv(latest_csv_path, index=False, encoding='utf-8')
    print(f"  CSV latest: {latest_csv_path}")
    
    # Guardar en base de datos SQLite
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('DROP TABLE IF EXISTS products')
        
        cursor.execute('''
            CREATE TABLE products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT, 
                brand TEXT, 
                ram_gb INTEGER, 
                storage_gb INTEGER,
                price REAL, 
                url TEXT UNIQUE, 
                platform TEXT,
                scraped_at DATETIME, 
                last_updated DATETIME
            )
        ''')
        
        columns_needed = ['title', 'brand', 'ram_gb', 'storage_gb', 'price', 'url', 'platform', 'scraped_at', 'last_updated']
        df_final = df[columns_needed].copy()
        
        df_final['ram_gb'] = df_final['ram_gb'].astype('Int64')
        df_final['storage_gb'] = df_final['storage_gb'].astype('Int64')
        df_final['price'] = pd.to_numeric(df_final['price'], errors='coerce')
        
        df_final.to_sql('products', conn, if_exists='append', index=False)
        
        conn.commit()
        
        cursor.execute('SELECT COUNT(*) FROM products')
        count = cursor.fetchone()[0]
        
        cursor.execute('SELECT brand, COUNT(*) FROM products WHERE brand != "OTHER" GROUP BY brand')
        brands = cursor.fetchall()
        
        conn.close()
        
        print(f"\nBase de datos actualizada exitosamente")
        print(f"  Ubicacion: {db_path}")
        print(f"  Productos guardados: {count}")
        print(f"\nMarcas detectadas:")
        for brand, count_b in brands:
            print(f"    - {brand}: {count_b} productos")
            
    except Exception as e:
        print(f"Error al guardar en base de datos: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    normalize_to_silver()