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

# Scraper de Newegg
def scrape_newegg(search_term, pages=1):
    """Realiza el scraping de newegg para un termino dado"""
    print(f"\n{'='*5}INICIANDO SCRAPER NEWEGG{'='*5}\n")
    options = uc.ChromeOptions()
    options.add_argument('--start-maximized')
    driver = uc.Chrome(options=options)
    all_products = []
    
    try:
        for page in range(1, pages + 1):
            url = f"https://www.newegg.com/p/pl?d={search_term.replace(' ', '+')}&page={page}"
            driver.get(url)
            wait = WebDriverWait(driver, 15)
            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".item-container")))
            except: continue

            items = driver.find_elements(By.CSS_SELECTOR, ".item-container")
            current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            for item in items:
                try:
                    title = item.find_element(By.CSS_SELECTOR, ".item-title").text.strip()
                    price = item.find_element(By.CSS_SELECTOR, ".price-current").text.strip()
                    link = item.find_element(By.CSS_SELECTOR, "a.item-title").get_attribute("href")
                    if title and price:
                        all_products.append({
                            'title': title, 'price_raw': price, 'url': link,
                            'platform': 'newegg', 'scraped_at': current_date
                        })
                except: continue
            print(f"Pagina {page}: {len(all_products)} productos nuevos encontrados.")
            time.sleep(random.uniform(5, 8))
    finally:
        driver.quit()

    if all_products:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(script_dir, '..', 'data')
        os.makedirs(data_dir, exist_ok=True)
        
        date_str = datetime.now().strftime("%Y%m%d")
        safe_name = search_term.replace(' ', '_').lower()
        filename = f"raw_newegg_{safe_name}_{date_str}.json"
        filepath = os.path.join(data_dir, filename)
        
        existing_data = []
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                try:
                    existing_data = json.load(f)
                except: existing_data = []
        
        combined_data = existing_data + all_products
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(combined_data, f, indent=4, ensure_ascii=False)
        print(f"Archivo actualizado. Total productos en {filename}: {len(combined_data)}")

if __name__ == "__main__":
    # Leer argumentos de la busqueda
    if len(sys.argv) > 1:
        search_term = sys.argv[1]
        if len(sys.argv) > 2:
            pages = int(sys.argv[2])
        else:
            pages = 3
    else:
        # Argumentos por defecto en caso de no ingresar ninguno desde el orquestador
        search_term = "Laptop Refurbished"
        pages = 3

    scrape_newegg(search_term, pages)