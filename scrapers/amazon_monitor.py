import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import time
import sys
from datetime import datetime
from utils import save_to_json,logger

# Configuracion de la localizacion de amazon
def set_location(driver, wait):
    """Configura la localizacion de Amazon en USA especificamente en Miami"""
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
    """Realiza el scraping de amazon para una un producto en una catidad dada de paginas"""
    logger.info(f"Iniciando scraper de Amazon para: {search_term}")
    
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

    except Exception as e:
        logger.error(f"Error crítico en Amazon: {e}")

    finally:
        logger.info("Cerrando navegador de Amazon.")
        driver.quit()

    # Guardando los datos en un archivo JSON
    save_to_json(all_products,'amazon',search_term)

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

    scrape_amazon(search_term, pages)