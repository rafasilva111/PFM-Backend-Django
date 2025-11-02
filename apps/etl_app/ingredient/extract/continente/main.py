
from django.utils import timezone
import requests
import unidecode
from bs4 import BeautifulSoup
from time import sleep	

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from apps.etl_app.functions import start_db
from apps.etl_app.ingredient.extract.continente.models import Tag, Ingredient, database_proxy, IngredientLink, Image, IngredientTagThrough
from apps.etl_app.constants import EXTRACT_CONTINENTE_INGREDIENTS_DB, CONTINENTE_INGREDIENTS_IMAGES_FOLDER
from selenium.common.exceptions import TimeoutException, WebDriverException
from apps.etl_app.functions import create_driver
import time
import traceback
from apps.etl_app.functions import normalize_text
models_ = [Ingredient, Tag, IngredientTagThrough, IngredientLink, Image]

"""
Define constants for the scraping process
"""
BASE_URL = "https://www.continente.pt"
BASE_HEADERS = {
    "cookie": "realUserVerifier=Verified;",
}
COMPANY_NAME = "continente"
PAGE_LINKS_OFFSET = 24
DEFAULT_SLEEP_TIME = 2
FIRST_TIME = True

MAX_THREADS = 2
PAGE_LOAD_TIMEOUT = 60  # seconds
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds
RESET_INTERVAL = 10  # Restart WebDriver after this many items

" Maps "

# Map the Caracteristcs and information to the corresponding attribute in the model
caracteristics_and_info_name_map = {
    'Descrição:': 'description',
    'Tipo de produto:': 'product_type',
    'Informação Adicional:': 'extra_information',
    'Dicas:': 'tips',
    'Conselhos de utilização:': 'using_sugestions',
    'Embalagem:': 'package',
    'Aviso Legal:': 'legal_advise',
}

# Map the nutrient name to the corresponding attribute in the model
nutrient_name_map = {
    'energia': 'energia',
    'lípidos': 'gordura',
    'lípidos > saturados': 'gordura_saturada',
    'hidratos de carbono': 'hidratos_carbonos',
    'hidratos de carbono > açúcares': 'hidratos_carbonos_acucares',
    'proteínas': 'proteina',
    'fibra': 'fibra',
    'sal': 'sal',
}

# Map the legal information to the corresponding attribute in the model
legal_name_map = {
    'Nome do Produtor:': 'productor_name',
    'Morada do Produtor:': 'productor_address',
    'Declaração de Ingredientes:': 'ingredients_declaration',
    'Informação Rotular Obrigatória:': 'rotular_required_information',
    'Nome Regulamentar do Produto:': 'regular_product_name',
}

# Map the aditional information to the corresponding attribute in the model
aditional_information_name_map = {
    'Informação Adicional:': 'productor_name',
    'Embalagem:': 'productor_address',
    'Declaração de Ingredientes:': 'ingredients_declaration',
    'Informação Rotular Obrigatória:': 'rotular_required_information',
    'Nome Regulamentar do Produto:': 'regular_product_name',
}


"""
        Notes:
        
    This scrapper should run more tham one time, extra tabs ( nutritional info, legal info, advises)
    dont always load (their fault).


"""

def extract_data_from_link(logger, task, driver, ingredient_link, sleep_time=DEFAULT_SLEEP_TIME, first_time=True):
    """
    Extracts ingredient data from a given link using Selenium and BeautifulSoup.
    This function navigates to the specified ingredient link, handles potential
    popups (e.g., cookie consent), and extracts various details about the ingredient,
    such as title, brand, size, price, description, image, characteristics, nutritional
    information, and legal information. The extracted data is saved into an `Ingredient`
    model instance.

    The function performs the following tasks:
        1. Navigates to the ingredient link using Selenium.
        2. Handles cookie consent popups if present.
        3. Checks for page redirection or "page not found" errors.
        4. Extracts general ingredient information (e.g., title, brand, size, price).
        5. Downloads and saves the ingredient image locally.
        6. Extracts characteristics and additional information from relevant tabs.
        7. Extracts nutritional information if available.
        8. Extracts legal information if available.
        9. Saves the extracted data into the `Ingredient` model.
        10. Logs warnings and errors for missing or malformed data.

    Args:
        logger (logging.Logger): Logger instance for logging warnings, errors, and info.
        driver (selenium.webdriver): Selenium WebDriver instance for navigating the webpage.
        ingredient_link (str): URL of the ingredient page to extract data from.
        sleep_time (int, optional): Time in seconds to wait for the page to load. Defaults to DEFAULT_SLEEP_TIME.
        first_time (bool, optional): Indicates if this is the first attempt to extract data. Defaults to True.

    Returns:
        tuple: A tuple containing:
            - warnings (int): The number of warnings encountered during extraction.
            - errors (int): The number of errors encountered during extraction.

    Raises:
        Exception: If any unexpected error occurs during the extraction process.

    Notes:
        - The function handles redirections and retries with increased sleep time if necessary.
        - If the page contains a cookie consent popup, it attempts to accept all cookies.
        - Extracted data includes general information, characteristics, nutritional information,
          and legal information, if available.
        - Images are downloaded and saved locally using the ingredient title as the filename.
        - Logs warnings and errors for missing or malformed data.
    """
    
    
    " Load page using selenium as the page have javascript "
    driver.get(ingredient_link)
    
    
    " Check if page was redirected "
    if driver.current_url != ingredient_link:
        task.increment_warnings(
            logger=logger,
            message=f"Page was redirected from {ingredient_link} to {driver.current_url}, skipping this ingredient...",
            stack_trace=None
        )
        return 

    
    
    if False:
        try:
            # Aguarda o popup de cookies aparecer
            cookie_popup_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.ID, "CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll"))
            )

            # Clica no botão "Permitir todos" para aceitar os cookies
            cookie_popup_button.click()
        except Exception as e:
            task.increment_errors(
                logger=logger,
                message="Error while handling cookie popup...",
                stack_trace=traceback.format_exc()
            )

    sleep(sleep_time)
    html = BeautifulSoup(driver.page_source, 'html.parser')

    " Check if page was found "
    page_not_found = html.find('p', class_='notfound-title')
    if page_not_found:
        task.increment_errors(
            logger=logger,
            message=f"Page not found: {ingredient_link}, skipping this ingredient...",
            stack_trace=None
        )	
        logger.info("")
        return

    
    # prepare to deal whit tabs ( check if base_tabs already loaded if not call
    # function again whit more sleep time)
    base_html_tab = html.find('ul',
                        class_='col-sm-4 col-md-3 tabNav mResTabNav')

    if base_html_tab is None:
        return extract_data_from_link(logger, task, driver, ingredient_link, sleep_time + 1, False)
    
    

    """ General info """

    ingredient_db = Ingredient()

    " Source Link "
    ingredient_db.link = ingredient_link

    " Company  "
    ingredient_db.company = COMPANY_NAME

    " Title "
    ingredient_db.title = html.find('h1', class_='pwc-h3 col-h3 product-name pwc-font--primary-extrabold mb-0').text.strip()

    " Category "
    category_elements = html.find_all('li', attrs={'itemprop': 'itemListElement'})
    ingredient_db.category = " > ".join([el.get_text(strip=True) for el in category_elements[1:]])
        
    " Brand "
    brand = html.find('a', class_='ct-pdp--brand col-pdp--brand')
    if brand:
        ingredient_db.brand = brand.text.strip()

    " Size "
    ingredient_db.size = html.find('span',class_='ct-pdp--unit col-pdp--unit').text.strip()


    " Price per unit "
    ingredient_db.price_per_unit = html.find('span', class_='ct-price-formatted').text.strip()

    base_html_bulk = html.find('div',class_='pwc-tile--price-secondary col-tile--price-secondary')

    ingredient_db.price_bulk = base_html_bulk.find('span',class_='ct-price-value').text.strip().replace("€", "")

    ingredient_db.bulk_unit = base_html_bulk.find('span',class_='pwc-m-unit').text.strip().replace("/", "")

    " Description "
    ingredient_db.description = html.find('div',class_='ct-pdp--short-description col-pdp--short-description').text.strip()

    " Tabs "
    tabs = html.find_all('li', class_='mResTabNavTab')
    tabs_ = {}
    for tab in tabs:
        tabs_.update({tab.text.strip(): tab.find('a')['href'][1:]})

    for key, value in tabs_.items():
        
        match key:
            case  "Sobre este Produto":
                tab_container = html.find("div", attrs={'id': value}).find("div", class_="simplebar-content")
                if tab_container:
                    ingredient_db.about_the_product = tab_container.text.strip()

            case "Características":
                tab_container = html.find("div", attrs={'id': value}).find("div", class_="simplebar-content")
                if tab_container:
                    ingredient_db.caracteristics = tab_container.text.strip()
                
            case 'Outras Informações':
                tab_container = html.find("div", attrs={'id': value}).find("div", class_="simplebar-content")
                if tab_container:
                    ingredient_db.other_information = tab_container.text.strip()
                
            case 'Informação Nutricional':
                tab_container = html.find("div", attrs={'id': value}).find("div", class_="nutritional-information-area")
                if tab_container:
                    ingredient_db.nutrition_information = tab_container.text.strip()
                
            case 'Informação Legal':
                tab_container = html.find("div", attrs={'id': value}).find("div", class_="simplebar-content")
                if tab_container:
                    ingredient_db.legal_info = tab_container.text.strip()
                
            case 'Informação Adicional':
                tab_container = html.find("div", attrs={'id': value}).find("div", class_="simplebar-content")
                if tab_container:
                    ingredient_db.legal_info = tab_container.text.strip()
                
            case _:
                logger.warning(f"Tab {key} not implemented, skipping...")

    " Save the Ingredient "
    ingredient_db.save()
    
    
    " Image "
    images_carrousel = html.find('div', class_='row no-gutters product-images-container')
    images = images_carrousel.find_all('img', class_='ct-product-image')
    
    counter = 0
    for image in images:
        
        image_db = Image()
        file_storage = unidecode.unidecode(ingredient_db.title).replace(" ", "_")
        file_storage = file_storage.replace("/", "_")
        if counter > 0:
            file_storage += f"_{counter}"
            
            
        image_source_link = image.get('src',None)
        
        if not image_source_link:
            image_source_link = image.get('data-src',None)
            
        img_source = f'{CONTINENTE_INGREDIENTS_IMAGES_FOLDER}/{file_storage}.png'
        image_db.path = img_source
        try:
            with open(img_source, "wb") as f:
                f.write(requests.get(image_source_link).content)
        except Exception as e:
            task.increment_warnings(
                logger=logger,
                message=f"Error while downloading image from {image_source_link} for ingredient {ingredient_db.title}",
                stack_trace=traceback.format_exc()
            )
            continue
        
        image_db.ingredient = ingredient_db
        image_db.save()
        
        counter += 1
    
    " Tags "
    product_container = html.find('div', class_='product-images--wrapper col-product-images-wrapper')
    tags_container = product_container.find('div', class_='ct-product-tile-badge ct-product-tile-badge--general')
    
    if tags_container:
        tags_container_imgs = tags_container.find_all('img')
        
        for tag_img in tags_container_imgs:
            tag_title = tag_img['data-original-title'].strip()
            if not tag_title:
                continue
            
            # Normalize the tag title
            tag_title = unidecode.unidecode(tag_title).replace(" ", "_").lower()
            
            # Check if the tag already exists
            tag, created = Tag.get_or_create(title=tag_title)
            
            # Add the tag to the ingredient
            ingredient_db.tags.add(tag)
    
    
    
import concurrent.futures
import threading
import time
import traceback
from selenium.common.exceptions import TimeoutException, WebDriverException


# Thread-local storage for WebDriver and state
thread_local = threading.local()

def process_ingredient_link(logger, task_id, ingredient_link, first_time, stopping_offset):
    from apps.etl_app.models import Task, JobTriggerHistory
    from apps.etl_app.worker_signals import stop_thread_event

    task = Task.objects.get(id=task_id)

    # Early stop check
    if stop_thread_event.is_set():
        # Only log once per thread
        logger.debug(f"Thread {threading.current_thread().name} detected stop signal, exiting.")
        return None

    driver = None
    try:
        driver = create_driver(task.debug_mode)

        for attempt in range(1, MAX_RETRIES + 1):
            # Check stopping offset
            if stopping_offset and ingredient_link.id > stopping_offset:
                task.owner_job.create_job_trigger_history(
                    type=JobTriggerHistory.Type.STOPPING_CONDITION,
                    action=JobTriggerHistory.Action.REST,
                )
                logger.info(f"[Thread {threading.current_thread().name}] Stopping condition hit at {ingredient_link.id}")
                return False

            # Early stop check inside loop
            if stop_thread_event.is_set():
                logger.debug(f"Thread {threading.current_thread().name} detected stop signal mid-processing, exiting.")
                return None

            try:
                logger.info(f"[Thread {threading.current_thread().name}] Extracting Ingredient {ingredient_link.id} from {ingredient_link.link}")
                extract_data_from_link(logger, task, driver, ingredient_link.link, first_time)
                return True

            except TimeoutException:
                logger.warning(f"Timeout on {ingredient_link.link} (Attempt {attempt}/{MAX_RETRIES})")
                if attempt == MAX_RETRIES:
                    task.increment_errors(logger, f"Timeout: {ingredient_link.link}", None)
                else:
                    time.sleep(RETRY_DELAY)

            except WebDriverException:
                task.increment_errors(logger, f"WebDriver error: {ingredient_link.link}", traceback.format_exc())
                break

            except Exception:
                task.increment_errors(logger, f"Unexpected error: {ingredient_link.link}", traceback.format_exc())
                break

        return False

    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

from apps.etl_app.worker_signals import stop_thread_event

def pull_ingredients(logger, task, max_threads=MAX_THREADS):
    from apps.etl_app.models import ThresholdCondition
    logger.info("")
    logger.info("Starting parallel recipe extraction")
    logger.info("")

    # Compute stopping offset if any
    OFFSET = None
    if (
        task.owner_job
        and task.owner_job.stopping_condition
        and isinstance(task.owner_job.stopping_condition, ThresholdCondition)
    ):
        OFFSET = task.step + task.owner_job.stopping_condition.threshold_value

    ingredient_links = list(IngredientLink.select().where(IngredientLink.id > task.step))
    FIRST_TIME = True
    total_processed = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        futures = []

        for link in ingredient_links:
            # Before submitting new tasks, check stop event
            if stop_thread_event.is_set():
                logger.info("Stop signal detected — no new tasks will be submitted.")
                break
            futures.append(executor.submit(process_ingredient_link, logger, task.id, link, FIRST_TIME, OFFSET))

        try:
            for future in concurrent.futures.as_completed(futures):
                # Stop check inside main loop
                if stop_thread_event.is_set():
                    logger.info("Stop signal detected — waiting for running threads to finish...")
                    break

                try:
                    result = future.result()
                except Exception as e:
                    logger.error(f"Future raised an exception: {e}", exc_info=True)
                    continue

                if result:
                    total_processed += 1
                    task.step += 1
                    task.items_processed += 1
                    task.save()

        finally:
            # Proper cleanup
            executor.shutdown(wait=True, cancel_futures=True)
            logger.info(f"Executor shut down. Total processed: {total_processed}")

    logger.info("")
    logger.info(f"{total_processed} ingredients processed.")
    logger.info("")

    # Clean up drivers per thread
    try:
        if hasattr(thread_local, "driver"):
            thread_local.driver.quit()
    except Exception:
        pass

    return task, True


def pull_ingredients_links(logger, task):
    """
    Extracts ingredient links from the Continente website and stores them in the database.
    This function navigates through the Continente website to retrieve ingredient links 
    categorized by their respective categories. It handles pagination, filters unnecessary 
    categories, and adds missing ones. The extracted links are saved in the database, and 
    the task statistics are updated accordingly.
    Args:
        logger (logging.Logger): Logger instance for logging information, warnings, and errors.
        task (Task): Task object used to track the progress and statistics of the extraction process.
        continue_mode (bool, optional): If True, resumes the extraction process from where it left off. 
                                        Defaults to False.
    Workflow:
        1. Initializes warnings and errors counters.
        2. Retrieves the main categories from the Continente homepage.
        3. Filters out subcategories and unnecessary categories.
        4. Adds any missing necessary categories.
        5. Iterates through each category to extract ingredient links:
            - Handles pagination to retrieve all links.
            - Saves the links to the database.
        6. Updates the task statistics with the number of links, warnings, and errors.
        7. Logs the completion of the extraction process.
    Notes:
        - The function assumes the existence of a `BASE_URL` constant for the Continente website.
        - The `IngredientLink` model is used to store the extracted links in the database.
        - The function logs warnings for categories or pages that cannot be processed.
    Raises:
        Exception: If there are issues with parsing the HTML or extracting data.
    """

    " Initialize the Control variables "
    stopping_condition_triggered = False
    total_ingredients_links_already_done = None
    total_links_counter = 0
    completed = False
    
    " Gets all Ingredients's Links from Continente "
    logger.info("")
    logger.info("Starting to pull Ingredient's Links...")
    logger.info("")

    " Get Main Category's Pages "
    logger.info("Finding Categories...")
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/141.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/avif,image/webp,image/apng,*/*;q=0.8,"
                "application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "pt-PT,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.continente.pt/",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Sec-Ch-Ua": '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Connection": "keep-alive",
        "cookie": "realUserVerifier=Verified;",
    })
    base_response = session.get(BASE_URL)
    html = BeautifulSoup(base_response.content, 'html.parser')
    homepage = html.find('div', class_='container-dropdown-first-column')
    categories = {}

    for item in homepage.find_all('li', class_="dropdown-item dropdown"):
        url = item.find('a', class_='dropdown-link pwc-font--primary-regular-italic col-view-all')

        if url['role'] != 'menuitem':
            continue

        category_text = item.find('div', class_='category-info').text.strip()
        url = url['href']
        
        categories.update({category_text: url})

    " Remove Subcategories "
    for key, value in categories.copy().items():
        if value.count('/') != 4:
            categories.pop(key)

    " Remove unneccessary categories "
    if "Destaques" in categories:
        categories.pop("Destaques")

    if 'Loja de Marcas' in categories:
        categories.pop('Loja de Marcas')

    if 'Lojas de Marcas' in categories:
        categories.pop('Lojas de Marcas')

    if 'Jardim, Bricolage e Auto' in categories:
        categories.pop('Jardim, Bricolage e Auto')

    if 'Brinquedos e Jogos' in categories:
        categories.pop('Brinquedos e Jogos')

    if 'Livraria e Papelaria' in categories:
        categories.pop('Livraria e Papelaria')

    if 'Desporto, Bagagens, Roupa' in categories:
        categories.pop('Desporto, Bagagens, Roupa')

    if 'Casa, Mobiliário, Decoração' in categories:
        categories.pop('Casa, Mobiliário, Decoração')

    " Add neccessary categories "
    categories["Bebé"] = 'https://www.continente.pt/bebe/ver-todos/'
    
    if "Frutas e Legumes" not in categories:
        categories["Frutas e Legumes"] = 'https://www.continente.pt/frutas-e-legumes/frutas/'

    logger.info("")
    logger.info(f"Found {len(categories)} categories")
    logger.info("")
    
    logger.info(f"Ingredient {task.process} is on step {task.step}...")
    logger.info("")
    
    " Get the Threshold Stopping condition"
    from apps.etl_app.models import ThresholdCondition
    stopping_condition_offset = (
        task.owner_job.stopping_condition.threshold_value
        if task.owner_job and isinstance(task.owner_job.stopping_condition, ThresholdCondition)
        else None
    )
        
    " Check if we are resuming the task, and if so, delete the Recipes that are above the step "
    if task.step != 0:
        IngredientLink.delete().where(IngredientLink.id > task.step).execute()
        total_ingredients_links_already_done = task.step

    """ Get all Ingredient's Links for each category """
    logger.info("Finding all ingredients links for each category...")

    last_key = next(reversed(categories)) 
    for key, value in categories.items():
        
        logger.info("")
        logger.info(f"Extracting Ingredient's Links from category: {key}")
        

        category_response = session.get(value)
        html = BeautifulSoup(category_response.content, features= 'html.parser')
        try:
            max_ingredients_category = int(html.find("div", class_="search-results-products-counter d-flex justify-content-center").text.split(" ")[2])
            logger.info(f"Category has {max_ingredients_category} ingredients")
        except Exception:
            task.increment_warnings(
                    logger=logger,
                    message=f"Unable to Extract the Max Recipes from {key} category...",
                    stack_trace=None
                )
            continue
        logger.info("")
        
        base_data_url = html.find("div", class_="search-view-more-products-btn-wrapper infinite-scroll-placeholder")['data-url']
        
        " Skip already extracted categories "
        if total_ingredients_links_already_done:
            if total_ingredients_links_already_done >= max_ingredients_category:
                total_ingredients_links_already_done -= max_ingredients_category
                logger.info(f"Category already extracted, skipping...")
                continue
            else:
                start = total_ingredients_links_already_done
        else:
            start = 0

        base_data_url = base_data_url.split("&")
        base_data_url = f"{base_data_url[0]}&{base_data_url[1]}&sz={PAGE_LINKS_OFFSET}"

        pull_ingredients_retries = 0
        while start < max_ingredients_category:
            
            extra = f"&start={start}"
            pulling_url = f"{base_data_url}{ extra}"
            category_response = requests.get(pulling_url)

            
            html = BeautifulSoup(category_response.content, 'html.parser')

            ingredients_link = html.find_all("div", class_="ct-pdp-link col-pdp-link")
            
            if not ingredients_link:

                if pull_ingredients_retries >= MAX_RETRIES:
                    pull_ingredients_retries = 0
                    logger.info(f"Max retries reached for link {pulling_url}, moving to next category...")
                    with open(f"{normalize_text(key)}.html", "w", encoding="utf-8") as f:
                        f.write(html.prettify())
                    break
                else:
                    pull_ingredients_retries += 1 
                    logger.info(f"Retrying to pull ingredients links from {pulling_url} (Retry {pull_ingredients_retries}/{MAX_RETRIES})...")
                    
                    continue
            
            links_added = 0
            for ingredient_link in ingredients_link:

                ingredient_link = IngredientLink(
                    link=ingredient_link.find('a')['href'],
                    page=start // PAGE_LINKS_OFFSET, 
                    base_search_link=value,
                    category = key
                    )
                ingredient_link.save()
                
                links_added += 1
                total_links_counter += 1
                
                # Check StoppingCondition
                if stopping_condition_offset and total_links_counter >= stopping_condition_offset:
                    logger.info("")
                    logger.info(f"Job Stopping Condition triggered. Paused extraction at {total_links_counter} links...")
                    logger.info("")
                    stopping_condition_triggered = True
                    break
            
            if stopping_condition_triggered:
                break
            
            start += links_added
            logger.info(f"Added {links_added} ingredients links, total {start} links found so far...")
            
        if key == last_key:
                    completed = True
         
        if stopping_condition_triggered:
            break
        
    " Update Task Statistics"
    task.links = IngredientLink.select().count()
    task.save()
    
    " Log the completion of the extraction process "
    logger.info("")
    logger.info("All Ingredient's Links pulled ...")
    logger.info("")
    
    return task, completed
    

def __extract_continente_ingredients(logger, task, resume):
    
    " Reset the stop event ( used to stop threads gracefully on Paused/Canceled ) "
    stop_thread_event.clear()
    
    " Log the start of the extraction process"
    logger.info(f"Initializing the {task.type} all {task.process} from {task.company}...")
    logger.info("")
        

    " Starts the db "
    logger.info(f"Initializing {task.type} database ...")
    task, database = start_db(
        logger=logger,
        task=task,
        models=models_,
        path=EXTRACT_CONTINENTE_INGREDIENTS_DB,
        database_proxy=database_proxy,
        reset=not resume # we want to reset the database if we are not resuming
    )
    logger.info("")
    

    " Pull Ingredients links "
    task, l_completed = pull_ingredients_links(logger, task)
    
    
    " Pulls Ingredients from above links "
    #task, completed = pull_ingredients(logger, task) 
    completed = True
    
    " Log the completion of the extraction process "
    logger.info("Summary:")
    logger.info(f"Ingredients Links: {task.links}")
    logger.info(f"Ingredients: {task.items_processed}")
    logger.info("")
    logger.info(f"Total errors: {task.errors}")
    logger.info(f"Total warnings: {task.warnings}")
    
    
    " Finish task "
    if completed and l_completed:
        task.finish(kill_celery_task=False)
    else:
        task.pause()
    
    " Final cleanup "
    task.kill_orphaned_firefox_instances()
    
    " Log the completion of the extraction process "
    logger.info("")
    logger.info(f"> Done...")
    logger.info("")
    
    return task

