import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
import sys
from datetime import datetime
from utils import save_to_json

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

    # Guardando los datos en un archivo JSON
    save_to_json(all_products,'newegg',search_term)

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
        # Argumentos por defecto en caso de no ingresar ninguno desde el orquestador
        search_term = "Laptop Refurbished"
        pages = 3

    scrape_newegg(search_term, pages)