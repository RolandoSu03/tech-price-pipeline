import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import json
import time
import os
from datetime import datetime

# Configuracion de la localizacion de amazon
def set_location(driver, wait):
    try:
        print("Cambiando ubicacion a Miami (33101)...")
        loc_button = wait.until(EC.element_to_be_clickable((By.ID, "nav-global-location-popover-link")))
        loc_button.click()
        time.sleep(2)
        zip_input = wait.until(EC.presence_of_element_located((By.ID, "GLUXZipUpdateInput")))
        zip_input.send_keys("33101")
        time.sleep(1)
        zip_input.send_keys(Keys.ENTER)
        time.sleep(2)
        try:
            done_button = driver.find_element(By.NAME, "glowDoneButton")
            done_button.click()
        except:
            driver.refresh()
        time.sleep(3)
        print("Ubicacion actualizada con exito.")
    except Exception as e:
        print(f"No se pudo cambiar la ubicacion: {e}")

# Scraper de Amazon
def scrape_amazon(search_term, pages=1):
    print(f"\n{'='*5}INICIANDO SCRAPER AMAZON{'='*5}\n")
    
    options = uc.ChromeOptions()
    options.add_argument('--start-maximized')
    options.add_argument('--lang=en-US') 
    driver = uc.Chrome(options=options)
    all_products = []
    
    try:
        wait = WebDriverWait(driver, 20)
        driver.get("https://www.amazon.com/?language=en_US")
        set_location(driver, wait)

        for page in range(1, pages + 1):
            url = f"https://www.amazon.com/s?k={search_term.replace(' ', '+')}&page={page}"
            driver.get(url)
            time.sleep(3) 
            items = driver.find_elements(By.CSS_SELECTOR, "div[data-component-type='s-search-result']")
            current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            for item in items:
                try:
                    title = item.find_element(By.CSS_SELECTOR, "h2").text.strip()
                    price = item.find_element(By.CSS_SELECTOR, ".a-price .a-offscreen").get_attribute("textContent").strip()
                    link = item.find_element(By.CSS_SELECTOR, "h2 a, a[href*='/dp/']").get_attribute("href").split("?")[0]
                    if title:
                        all_products.append({
                            'title': title, 'price_raw': price, 'url': link,
                            'platform': 'amazon', 'scraped_at': current_date
                        })
                except: continue
            print(f"Pagina {page}: {len(all_products)} productos nuevos encontrados.")
    finally:
        driver.quit()

    if all_products:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(script_dir, '..', 'data')
        os.makedirs(data_dir, exist_ok=True)
        
        date_str = datetime.now().strftime("%Y%m%d")
        safe_name = search_term.replace(' ', '_').lower()
        filename = f"raw_amazon_{safe_name}_{date_str}.json"
        filepath = os.path.join(data_dir, filename)
        
        # Logica de acumulacion
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
    scrape_amazon("Laptop Refurbished", pages=3)