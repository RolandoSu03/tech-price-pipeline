import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import time
import random
import os
import sys
from datetime import datetime

# Escraper de Ebay
def scrape_ebay(search_term, pages):
    """"Realiza el scraping de Ebay para un teermino y cantidad de paginas dadas"""
    print(f"\n{'='*5}INICIANDO SCRAPER EBAY{'='*5}\n")
    
    options = uc.ChromeOptions()
    options.add_argument('--start-maximized')
    options.add_argument('--disable-notifications')
    
    print("Configurando navegador indetectable...")
    driver = uc.Chrome(options=options)
    all_products = []
    
    try:
        for page in range(1, pages + 1):
            url = f"https://www.ebay.com/sch/i.html?_nkw={search_term.replace(' ', '+')}&_pgn={page}"
            
            driver.get(url)
            
            # Esperar a que carguen los productos
            wait = WebDriverWait(driver, 15)
            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".s-item__title, .s-card__title")))
            except:
                print("Tiempo de espera agotado o CAPTCHA detectado.")
                continue
            
            # Scroll aleatorio para simular comportamiento humano
            for _ in range(3):
                driver.execute_script(f"window.scrollBy(0, {random.randint(400, 700)});")
                time.sleep(random.uniform(0.5, 1.2))
            
            # Localizar contenedores de productos
            items = driver.find_elements(By.CSS_SELECTOR, "li.s-item, .s-card")
            print(f"Analizando {len(items)} elementos encontrados...")
            
            current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            page_count = 0
            
            for item in items:
                try:
                    # Titulo con multiples selectores
                    title = ""
                    for selector in [".s-item__title span", ".s-card__title span", "div.su-styled-text"]:
                        try:
                            title_elem = item.find_element(By.CSS_SELECTOR, selector)
                            title = title_elem.text.strip()
                            if title and "Shop on eBay" not in title:
                                break
                        except:
                            continue
                    
                    # Precio con multiples selectores
                    price = ""
                    for selector in [".s-item__price", ".s-card__price", ".s-card_price"]:
                        try:
                            price_elem = item.find_element(By.CSS_SELECTOR, selector)
                            price = price_elem.text.strip()
                            if price:
                                break
                        except:
                            continue
                    
                    # Link del producto
                    link = ""
                    try:
                        link_elem = item.find_element(By.CSS_SELECTOR, "a[href*='/itm/']")
                        link = link_elem.get_attribute("href")
                    except:
                        link = "No disponible"
                    
                    if title and price and len(title) > 10:
                        all_products.append({
                            'title': title,
                            'price_raw': price,
                            'url': link,
                            'platform': 'ebay',
                            'scraped_at': current_date
                        })
                        page_count += 1
                except:
                    continue
            
            print(f"Pagina {page}: {page_count} productos nuevos encontrados.")
            
            if page < pages:
                sleep_time = random.uniform(5, 10)
                print(f"Pausa de seguridad: {sleep_time:.1f}s...")
                time.sleep(sleep_time)
                
    except Exception as e:
        print(f"Error critico: {e}")
        
    finally:
        print("Cerrando navegador...")
        driver.quit()
    
    # Guardar resultados 
    if all_products:
        # Obtener ruta a la carpeta data
        script_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(script_dir, '..', 'data')
        os.makedirs(data_dir, exist_ok=True)
        
        # Nombre del archivo con fecha (igual que Amazon y Newegg)
        date_str = datetime.now().strftime("%Y%m%d")
        safe_name = search_term.replace(' ', '_').lower()
        filename = f"raw_ebay_{safe_name}_{date_str}.json"
        filepath = os.path.join(data_dir, filename)
        
        # Cargar datos existentes para acumular (igual que Amazon y Newegg)
        existing_data = []
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                try:
                    existing_data = json.load(f)
                except:
                    existing_data = []
        
        # Combinar datos existentes con nuevos
        combined_data = existing_data + all_products
        
        # Guardar archivo actualizado
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(combined_data, f, indent=4, ensure_ascii=False)
        
        print(f"\n{'='*5}")
        print(f"Archivo actualizado. Total productos en {filename}: {len(combined_data)}")
        print(f"{'='*5}\n")
    else:
        print("No se encontraron productos para guardar.")
    
    return all_products

if __name__ == "__main__":
    # Leer argumentos de la busqueda
    if len(sys.argv) > 1:
        search_term = sys.argv[1]
        if len(sys.argv) > 2:
            pages = int(sys.argv[2])
        else:
            pages = 3
    else:
        # Argumento por defento en caso de no ingresar ninguno desde el orquestador
        search_term = "Laptop Refurbished"
        pages = 3

    scrape_ebay(search_term, pages)