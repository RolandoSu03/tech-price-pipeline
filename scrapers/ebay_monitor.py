import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
import sys
from datetime import datetime
from utils import save_to_json,logger

# Escraper de Ebay
def scrape_ebay(search_term, pages):
    """"Realiza el scraping de Ebay para un teermino y cantidad de paginas dadas"""
    logger.info(f"Iniciando scraper de eBay para: {search_term}")
    
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

            # Hacer click en el filtro de solo EE. UU
            try:
                # Buscar el enlace o radio button que dice "Sólo EE. UU." o "US Only"
                # Posibles selectores:
                selectores_usa = [
                    "//span[contains(text(),'Sólo EE. UU.')]",
                    "//span[contains(text(),'US Only')]",
                    "//button[contains(@aria-label,'Sólo EE. UU.')]",
                    "//a[contains(text(),'Sólo EE. UU.')]",
                    "//label[contains(text(),'Sólo EE. UU.')]",
                    "//span[contains(text(),'Estados Unidos')]"
                ]
                click_realizado = False
                for selector in selectores_usa:
                    try:
                        elemento = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                        driver.execute_script("arguments[0].scrollIntoView(true);", elemento)
                        time.sleep(0.5)
                        elemento.click()
                        print("Filtro 'Sólo EE. UU.' aplicado correctamente.")
                        click_realizado = True
                        # Esperar a que la página se recargue con el filtro
                        time.sleep(3)
                        break
                    except:
                        continue

                if not click_realizado:
                    logger.info(f"No se encontro el filtro de solo EE UU asi que se continuara sin el")
            except Exception as e:
                logger.error(f"Error al intentar aplicar el filtro de solo EEUU: {e}")
            
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
        logger.error(f"Error crítico en eBay: {e}")
        
    finally:
        logger.info("Cerrando navegador de eBay.")
        driver.quit()
    
    # Guardar resultados 
    save_to_json(all_products,'ebay',search_term)

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