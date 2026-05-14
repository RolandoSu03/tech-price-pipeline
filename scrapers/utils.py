import json
import os
from datetime import datetime


def save_to_json(new_data, platform, search_term):
    """
    Guarda los datos scrapeados en un archivo JSON, acumulando con datos existentes.
    """
    if not new_data:
        print(f"[{platform.upper()}] No se encontraron productos para guardar.")
        return

    # Obtener ruta a la carpeta data (subiendo un nivel desde scrapers/)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, '..', 'data')
    os.makedirs(data_dir, exist_ok=True)

    # Nombre del archivo con fecha
    date_str = datetime.now().strftime("%Y%m%d")
    safe_name = search_term.replace(' ', '_').lower()
    filename = f"raw_{platform}_{safe_name}_{date_str}.json"
    filepath = os.path.join(data_dir, filename)

    # Cargar datos existentes para acumular
    existing_data = []
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            try:
                existing_data = json.load(f)
            except json.JSONDecodeError:
                existing_data = []

    # Combinar datos existentes con nuevos
    combined_data = existing_data + new_data

    # Guardar archivo actualizado
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(combined_data, f, indent=4, ensure_ascii=False)

    print(f"\n{'=' * 5}")
    print(f"[{platform.upper()}] Archivo actualizado. Total productos en {filename}: {len(combined_data)}")
    print(f"{'=' * 5}\n")