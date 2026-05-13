import pandas as pd
import sqlite3
import glob
import os
import re
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

def parse_to_gb(value_str):
    """Convierte string de capacidad a GB (ej: '1TB' -> 1024)."""
    if not value_str or value_str == "N/A" or pd.isna(value_str):
        return None
    value_str = str(value_str).upper().strip()
    numbers = re.findall(r'(\d+(?:\.\d+)?)', value_str)
    if not numbers:
        return None
    numeric_value = float(numbers[0])
    if "TB" in value_str:
        return int(numeric_value * 1024)
    else:
        return int(numeric_value) if numeric_value > 0 else None


def extract_ram(title):
    """
    Extrae la RAM de forma robusta, evitando confundir con storage o números de modelo.
    - Busca patrones con 'RAM', 'DDR', 'LPDDR', 'SODIMM'
    - Busca el primer número entre 4 y 64 GB que NO esté cerca de 'SSD', 'HDD', 'NVMe'
    - Si solo hay un número y es >=128, no es RAM.
    """
    if not title or pd.isna(title):
        return None

    title_norm = title.upper().replace('GO', 'GB').replace(',', ' ').replace('  ', ' ')

    # Patrones específicos de RAM (muy fiables)
    specific_patterns = [
        r'(\d+)\s*GB\s*RAM',
        r'RAM\s*(\d+)\s*GB',
        r'(\d+)\s*GB\s*(?:DDR\d+|LPDDR\d*|SODIMM)',
        r'(\d+)\s*G\s*RAM',
    ]
    for pat in specific_patterns:
        m = re.search(pat, title_norm)
        if m:
            val = int(m.group(1))
            if 4 <= val <= 128:
                return val

    # Buscar todos los números con GB
    matches = list(re.finditer(r'(\d+)\s*GB\b', title_norm))
    if not matches:
        return None

    # Evaluar cada match de menor a mayor posición
    for m in matches:
        val = int(m.group(1))
        # La RAM suele estar entre 4 y 64 GB (a veces 128 en gama alta, pero raro)
        if val > 128:
            continue  # demasiado grande para RAM
        if val < 4:
            continue

        # Verificar contexto alrededor del número
        start = max(0, m.start() - 15)
        end = min(len(title_norm), m.end() + 15)
        context = title_norm[start:end]

        # Si cerca hay palabras de almacenamiento, no es RAM
        if re.search(r'SSD|HDD|NVME|EMMC|FLASH|STORAGE', context):
            continue
        # Si cerca hay palabras de modelo (como "G7", "G2", "PRO", "BOOK"), podría ser modelo, no RAM
        if re.search(r'G\d+|PROBOOK|ELITEBOOK|LATITUDE|THINKPAD', context):
            # Pero si el número es pequeño (4,8,16) y está aislado, sí puede ser RAM
            if val <= 16:
                # Aún así, verificar que no sea parte de "255 G7" donde 255 es modelo
                if val > 32:
                    continue
                return val
            continue

        # Si llegamos aquí, es candidato
        return val

    return None


def extract_storage(title):
    """
    Extrae el almacenamiento de forma robusta.
    - Busca números con TB/GB cerca de palabras clave (SSD, HDD, NVMe).
    - Si hay múltiples números, toma el último que sea >= 32 GB.
    - Si solo hay un número y es >= 32, es storage.
    - Ignora números pequeños (<32) a menos que tengan palabra clave.
    """
    if not title or pd.isna(title):
        return None

    title_norm = title.upper().replace('GO', 'GB').replace(',', ' ').replace('  ', ' ')

    # Casos sin disco
    if re.search(r'SIN DISCO|NO DRIVE|SANS DISQUE|OHNE FESTPLATTE', title_norm):
        return None

    # Patrones con unidad explícita TB/GB
    matches = list(re.finditer(r'(\d+(?:\.\d+)?)\s*(TB|GB)\b', title_norm))
    if not matches:
        return None

    # Función para validar rango
    def is_valid_storage(val, unit):
        if unit == 'TB':
            return 1 <= val <= 8
        else:  # GB
            return 32 <= val <= 4096

    # Primero buscar matches cerca de palabras clave de almacenamiento
    for m in matches:
        val = float(m.group(1))
        unit = m.group(2)
        if not is_valid_storage(val, unit):
            continue
        start = max(0, m.start() - 10)
        end = min(len(title_norm), m.end() + 10)
        context = title_norm[start:end]
        if re.search(r'SSD|HDD|NVME|EMMC|FLASH|STORAGE|DISCO', context):
            if unit == 'TB':
                return int(val * 1024)
            else:
                return int(val)

    # Si no, tomar el último match que sea >= 32 GB (asumiendo que es storage)
    for m in reversed(matches):
        val = float(m.group(1))
        unit = m.group(2)
        if is_valid_storage(val, unit):
            # Si es un número pequeño (<32) pero es el último, solo si hay palabra clave (ya lo buscamos)
            if val < 32 and unit == 'GB':
                continue
            if unit == 'TB':
                return int(val * 1024)
            else:
                return int(val)

    return None

def extract_brand(title):
    """Extrae la marca del título."""
    if not title or pd.isna(title):
        return "OTHER"
    title_upper = title.upper()
    brands = {
        'APPLE': ['APPLE', 'MACBOOK', 'MAC'],
        'LENOVO': ['LENOVO', 'THINKPAD', 'IDEAPAD'],
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

def extract_search_term_from_filename(filename):
    """
    Extrae el término de búsqueda desde el nombre del archivo.
    Formato esperado: raw_<plataforma>_<termino>_YYYYMMDD.json
    Ejemplo: raw_amazon_laptop_refurbished_20250613.json -> 'laptop refurbished'
    """
    base = os.path.basename(filename)
    # Eliminar prefijo 'raw_' y sufijo de fecha
    without_prefix = re.sub(r'^raw_', '', base)
    # Eliminar la fecha al final (8 dígitos + .json)
    match = re.search(r'(.+?)_\d{8}\.json$', without_prefix)
    if match:
        term_with_platform = match.group(1)
        # Eliminar el nombre de la plataforma al inicio (amazon_, ebay_, newegg_)
        term = re.sub(r'^(amazon|ebay|newegg)_', '', term_with_platform)
        return term.replace('_', ' ').strip()
    return "unknown"

def get_processed_files(db_path):
    """Retorna un set con los nombres de archivos JSON ya procesados."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS etl_metadata (
            file_name TEXT PRIMARY KEY,
            processed_at DATETIME,
            records_processed INTEGER
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

    print("\n" + "="*50)
    print("PROCESAMIENTO INCREMENTAL DE DATOS - LIMPIEZA Y NORMALIZACION")
    print("="*50)

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
            # Agregar columna search_term derivada del nombre del archivo
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

    # 3. Limpieza y transformación (igual que antes, pero solo sobre datos nuevos)
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

    # Eliminar duplicados dentro del lote nuevo (por URL y por título)
    print("\nPrimera limpieza (dentro del lote): eliminando duplicados por URL...")
    df_new = df_new.sort_values(by=['url', 'scraped_at'], ascending=[True, False])
    df_new = df_new.drop_duplicates('url', keep='first')
    print(f"  Registros después de limpieza por URL: {len(df_new)}")

    df_new = remove_duplicate_titles(df_new)   # función definida más abajo

    print(f"\nDespués de limpieza completa del lote:")
    print(f"  Registros iniciales en lote: {initial_count}")
    print(f"  Registros finales en lote: {len(df_new)}")
    print(f"  Registros descartados en lote: {initial_count - len(df_new)}")

    # 4. Guardar CSV en capa silver (opcional, con todos los datos históricos? Solo los nuevos?
    #    Aquí guardamos solo los nuevos para no duplicar.
    #    Pero si quieres un CSV acumulado, tendrías que leer el anterior y concatenar.
    #    Por simplicidad, guardamos un CSV con timestamp de los nuevos datos.
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

        # Crear tabla products si no existe (sin DROP, conservando datos antiguos)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                brand TEXT,
                ram_gb INTEGER,
                storage_gb INTEGER,
                price REAL,
                url TEXT,
                platform TEXT,
                scraped_at DATETIME,
                last_updated DATETIME,
                search_term TEXT
            )
        ''')
        # Opcional: crear índice para búsquedas rápidas
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_url ON products (url)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_scraped_at ON products (scraped_at)')

        # Seleccionar columnas a insertar
        columns_needed = ['title', 'brand', 'ram_gb', 'storage_gb', 'price', 'url',
                          'platform', 'scraped_at', 'last_updated', 'search_term']
        df_final = df_new[columns_needed].copy()

        # Convertir tipos
        df_final['ram_gb'] = df_final['ram_gb'].astype('Int64')
        df_final['storage_gb'] = df_final['storage_gb'].astype('Int64')
        df_final['price'] = pd.to_numeric(df_final['price'], errors='coerce')

        # Insertar filas (puede haber duplicados de url con diferente fecha; eso es histórico)
        df_final.to_sql('products', conn, if_exists='append', index=False)

        # Marcar cada archivo nuevo como procesado
        for file in new_files:
            # Contar cuántos registros de este archivo se insertaron realmente
            # Podríamos contar desde el df_final filtrado por el término (pero puede haber mezcla)
            # Por simplicidad, registramos el total de registros del archivo original.
            # Para mayor precisión, se podría calcular pero no es crítico.
            with open(file, 'r', encoding='utf-8') as f:
                import json
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

def remove_duplicate_titles(df):
    """Elimina duplicados por título exacto y misma plataforma (dentro del mismo lote)."""
    print("\nEliminando duplicados por título exacto y plataforma...")
    initial_count = len(df)
    df = df.sort_values(by=['scraped_at'], ascending=False)
    df = df.drop_duplicates(subset=['title', 'platform'], keep='first')
    removed_count = initial_count - len(df)
    print(f"  Duplicados eliminados por título+plataforma: {removed_count}")
    return df

def extract_full_specs(title):
    """Wrapper que devuelve (brand, ram, storage)."""
    if not title or pd.isna(title):
        return "OTHER", None, None
    ram = extract_ram(title)
    storage = extract_storage(title)
    brand = extract_brand(title)
    return brand, ram, storage

if __name__ == "__main__":
    normalize_to_silver()