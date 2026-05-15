import pandas as pd
import sqlite3
import glob
import os
import re
import json
from datetime import datetime


def clean_price(price_str):
    """Limpia y convierte el precio a float."""
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


def extract_capacities(title):
    """
    Extrae todos los valores de capacidad (RAM o almacenamiento) en GB.
    Retorna lista de enteros ordenada de mayor a menor, ignorando valores fuera de rangos posibles.
    """
    if not title or pd.isna(title):
        return []

    title_norm = title.upper().replace('GO', 'GB').replace(',', ' ').replace('  ', ' ')

    # Buscar todos los números con unidad GB o TB
    pattern = r'(\d+(?:\.\d+)?)\s*(TB|GB)\b'
    matches = re.finditer(pattern, title_norm)

    capacities = []
    for m in matches:
        val = float(m.group(1))
        unit = m.group(2)
        if unit == 'TB':
            val_gb = int(val * 1024)
        else:
            val_gb = int(val)

        # Filtrar rangos realistas (4 GB a 4 TB)
        if 4 <= val_gb <= 4096:
            capacities.append(val_gb)

    # Ordenar de mayor a menor
    capacities.sort(reverse=True)
    return capacities


def extract_ram(title):
    """Extrae la RAM: segundo mayor valor de capacidad (si existe y es <=128)."""
    caps = extract_capacities(title)
    if len(caps) >= 2:
        # La segunda más grande suele ser la RAM (si es <=128)
        candidate = caps[1]
        if 4 <= candidate <= 128:
            return candidate
    # Si no hay segundo valor, intentar con el primero si es pequeño (posible RAM sola)
    if len(caps) == 1 and 4 <= caps[0] <= 32:
        return caps[0]
    return None


def extract_storage(title):
    """Extrae el almacenamiento: el mayor valor de capacidad (>=32)."""
    caps = extract_capacities(title)
    if caps:
        candidate = caps[0]
        if candidate >= 32:
            return candidate
    return None


def extract_brand(title):
    """Extrae la marca del título."""
    if not title or pd.isna(title):
        return "OTHER"
    title_upper = title.upper()
    brands = {
        'APPLE': ['APPLE', 'MACBOOK', 'MAC'],
        'LENOVO': ['LENOVO', 'THINKPAD', 'IDEAPAD'],
        'HP': ['HP', 'HEWLETT PACKARD', 'ELITEBOOK', 'PROBOOK', 'SPECTRE', 'ENVY', 'PAVILION'],
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
    """Wrapper que devuelve (brand, ram, storage)."""
    if not title or pd.isna(title):
        return "OTHER", None, None
    ram = extract_ram(title)
    storage = extract_storage(title)
    brand = extract_brand(title)
    return brand, ram, storage


def extract_search_term_from_filename(filename):
    """
    Extrae el término de búsqueda desde el nombre del archivo.
    Formato esperado: raw_<plataforma>_<termino>_YYYYMMDD.json
    Ejemplo: raw_amazon_laptop_refurbished_20250613.json -> 'laptop refurbished'
    """
    base = os.path.basename(filename)
    without_prefix = re.sub(r'^raw_', '', base)
    match = re.search(r'(.+?)_\d{8}\.json$', without_prefix)
    if match:
        term_with_platform = match.group(1)
        term = re.sub(r'^(amazon|ebay|newegg)_', '', term_with_platform)
        return term.replace('_', ' ').strip()
    return "unknown"


def get_processed_files(db_path):
    """Retorna un set con los nombres de archivos JSON ya procesados."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS etl_metadata
                   (
                       file_name
                       TEXT
                       PRIMARY
                       KEY,
                       processed_at
                       DATETIME,
                       records_processed
                       INTEGER
                   )
                   """)
    cursor.execute("SELECT file_name FROM etl_metadata")
    processed = {row[0] for row in cursor.fetchall()}
    conn.close()
    return processed


def mark_file_processed(db_path, file_name, records_count):
    """Registra un archivo como procesado."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO etl_metadata (file_name, processed_at, records_processed)
        VALUES (?, ?, ?)
    """, (file_name, datetime.now(), records_count))
    conn.commit()
    conn.close()


def remove_duplicate_titles(df):
    """Elimina duplicados por título exacto y misma plataforma (dentro del mismo lote)."""
    print("\nEliminando duplicados por título exacto y plataforma...")
    initial_count = len(df)
    df = df.sort_values(by=['scraped_at'], ascending=False)
    df = df.drop_duplicates(subset=['title', 'platform'], keep='first')
    removed_count = initial_count - len(df)
    print(f"  Duplicados eliminados por título+plataforma: {removed_count}")
    return df


def normalize_to_silver():
    # Configuración de rutas
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.join(base_dir, '..')
    data_dir = os.path.join(project_root, 'data')
    silver_dir = os.path.join(data_dir, 'silver')
    db_dir = os.path.join(data_dir, 'db')
    db_path = os.path.join(db_dir, 'tech_prices_gold.db')
    os.makedirs(silver_dir, exist_ok=True)
    os.makedirs(db_dir, exist_ok=True)

    print("\n" + "=" * 50)
    print("PROCESAMIENTO INCREMENTAL DE DATOS - LIMPIEZA Y NORMALIZACION")
    print("=" * 50)

    # 1. Obtener archivos JSON nuevos
    all_json_files = glob.glob(os.path.join(data_dir, 'raw_*.json'))
    if not all_json_files:
        print("No hay archivos JSON para procesar.")
        return

    processed_files = get_processed_files(db_path)
    new_files = [f for f in all_json_files if os.path.basename(f) not in processed_files]

    if not new_files:
        print("No hay archivos nuevos. Todos ya fueron procesados anteriormente.")
        return

    print(f"Archivos totales: {len(all_json_files)}")
    print(f"Archivos nuevos: {len(new_files)}")
    for f in new_files:
        print(f"  - {os.path.basename(f)}")

    # 2. Cargar SOLO los archivos nuevos
    list_of_dfs = []
    for file in new_files:
        try:
            df_temp = pd.read_json(file)
            search_term = extract_search_term_from_filename(file)
            df_temp['search_term'] = search_term
            list_of_dfs.append(df_temp)
            print(f"Cargado: {os.path.basename(file)} ({len(df_temp)} registros) - Término: '{search_term}'")
        except Exception as e:
            print(f"Error cargando {file}: {e}")
            continue

    if not list_of_dfs:
        print("No se pudieron cargar los archivos nuevos.")
        return

    df_new = pd.concat(list_of_dfs, ignore_index=True)
    print(f"\nTotal de registros nuevos sin procesar: {len(df_new)}")

    # 3. Limpieza y transformación
    print("\nExtrayendo especificaciones de los títulos...")
    df_new[['brand', 'ram_gb', 'storage_gb']] = df_new.apply(
        lambda row: pd.Series(extract_full_specs(row['title'])), axis=1
    )

    print("Limpiando precios...")
    df_new['price'] = df_new['price_raw'].apply(clean_price)

    initial_count = len(df_new)
    df_new = df_new.dropna(subset=['title', 'url', 'price'])
    df_new = df_new[df_new['price'] > 0]
    df_new['scraped_at'] = pd.to_datetime(df_new['scraped_at'], errors='coerce')
    df_new['last_updated'] = datetime.now()

    # Eliminar duplicados dentro del lote nuevo
    print("\nPrimera limpieza (dentro del lote): eliminando duplicados por URL...")
    df_new = df_new.sort_values(by=['url', 'scraped_at'], ascending=[True, False])
    df_new = df_new.drop_duplicates('url', keep='first')
    print(f"  Registros después de limpieza por URL: {len(df_new)}")

    df_new = remove_duplicate_titles(df_new)

    print(f"\nDespués de limpieza completa del lote:")
    print(f"  Registros iniciales en lote: {initial_count}")
    print(f"  Registros finales en lote: {len(df_new)}")
    print(f"  Registros descartados en lote: {initial_count - len(df_new)}")

    # 4. Guardar CSV en capa silver (solo los nuevos, con timestamp)
    print("\nGuardando archivo CSV en capa silver...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = f"silver_tech_prices_new_{timestamp}.csv"
    csv_path = os.path.join(silver_dir, csv_filename)
    df_new.to_csv(csv_path, index=False, encoding='utf-8')
    print(f"  CSV guardado: {csv_path}")

    # 5. Insertar datos nuevos en la base de datos SQLite (preservando histórico)
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Crear tabla products si no existe
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS products
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           title
                           TEXT,
                           brand
                           TEXT,
                           ram_gb
                           INTEGER,
                           storage_gb
                           INTEGER,
                           price
                           REAL,
                           url
                           TEXT,
                           platform
                           TEXT,
                           scraped_at
                           DATETIME,
                           last_updated
                           DATETIME,
                           search_term
                           TEXT
                       )
                       ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_url ON products (url)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_scraped_at ON products (scraped_at)')

        columns_needed = ['title', 'brand', 'ram_gb', 'storage_gb', 'price', 'url',
                          'platform', 'scraped_at', 'last_updated', 'search_term']
        df_final = df_new[columns_needed].copy()

        df_final['ram_gb'] = df_final['ram_gb'].astype('Int64')
        df_final['storage_gb'] = df_final['storage_gb'].astype('Int64')
        df_final['price'] = pd.to_numeric(df_final['price'], errors='coerce')

        df_final.to_sql('products', conn, if_exists='append', index=False)

        # Marcar cada archivo nuevo como procesado
        for file in new_files:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                records_count = len(data)
            mark_file_processed(db_path, os.path.basename(file), records_count)

        conn.commit()

        # Mostrar estadísticas actualizadas
        cursor.execute('SELECT COUNT(*) FROM products')
        total_count = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(DISTINCT search_term) FROM products')
        distinct_terms = cursor.fetchone()[0]
        cursor.execute('SELECT brand, COUNT(*) FROM products WHERE brand != "OTHER" GROUP BY brand')
        brands = cursor.fetchall()

        conn.close()

        print(f"\nBase de datos actualizada exitosamente (modo histórico).")
        print(f"  Ubicación: {db_path}")
        print(f"  Total de productos en DB: {total_count}")
        print(f"  Términos de búsqueda distintos: {distinct_terms}")
        print(f"\nMarcas detectadas:")
        for brand, count_b in brands:
            print(f"    - {brand}: {count_b} productos")

    except Exception as e:
        print(f"Error al guardar en base de datos: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    normalize_to_silver()