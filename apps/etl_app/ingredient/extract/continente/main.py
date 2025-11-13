from bs4 import BeautifulSoup
from django.utils import timezone
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from time import sleep
import concurrent.futures
import random
import requests
import threading
import time
import traceback
import unidecode
from queue import Queue



from apps.etl_app.constants import (
    CONTINENTE_INGREDIENTS_IMAGES_FOLDER,
    EXTRACT_CONTINENTE_INGREDIENTS_DB,
)
from apps.etl_app.functions import (
    create_driver,
    normalize_text,
    start_db,
)
from apps.etl_app.ingredient.extract.continente.models import (
    Image,
    Ingredient,
    IngredientLink,
    IngredientTagThrough,
    Tag,
    database_proxy,
)
models_ = [Ingredient, Tag, IngredientTagThrough, IngredientLink, Image]
from apps.etl_app.worker_signals import stop_thread_event

# Define constants for the scraping process
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

TIME_BETWEEN_REQUESTS_LOW_BOUND = 1  # seconds
TIME_BETWEEN_REQUESTS_HIGH_BOUND = 2.5  # seconds

# Maps
caracteristics_and_info_name_map = {
    'Descrição:': 'description',
    'Tipo de produto:': 'product_type',
    'Informação Adicional:': 'extra_information',
    'Dicas:': 'tips',
    'Conselhos de utilização:': 'using_sugestions',
    'Embalagem:': 'package',
    'Aviso Legal:': 'legal_advise',
}

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

legal_name_map = {
    'Nome do Produtor:': 'productor_name',
    'Morada do Produtor:': 'productor_address',
    'Declaração de Ingredientes:': 'ingredients_declaration',
    'Informação Rotular Obrigatória:': 'rotular_required_information',
    'Nome Regulamentar do Produto:': 'regular_product_name',
}

aditional_information_name_map = {
    'Informação Adicional:': 'productor_name',
    'Embalagem:': 'productor_address',
    'Declaração de Ingredientes:': 'ingredients_declaration',
    'Informação Rotular Obrigatória:': 'rotular_required_information',
    'Nome Regulamentar do Produto:': 'regular_product_name',
}

# Thread-local storage for WebDriver and state
thread_local = threading.local()



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
        
        if not image_source_link:
            continue

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
    
def process_ingredient_link(logger, task_id, ingredient_link, first_time, stopping_offset, driver_pool):
    """
    Process a single ingredient link to extract detailed ingredient data.

    This function handles the extraction of ingredient details from a given link using Selenium.
    It manages retries for transient errors, checks for stopping conditions, and respects stop signals.

    Workflow:
        1. Retrieves the task instance associated with the given task ID.
        2. Checks for early stop signals to exit gracefully if requested.
        3. Creates a Selenium WebDriver instance for the current thread.
        4. Attempts to extract ingredient data, retrying on timeouts up to a maximum limit.
        5. Handles stopping conditions based on the ingredient link ID and task configuration.
        6. Logs progress, warnings, and errors during the extraction process.
        7. Cleans up resources, including the WebDriver instance, after processing.

    Args:
        logger (logging.Logger): Logger instance for structured logging.
        task_id (int): ID of the task being processed.
        ingredient_link (IngredientLink): The ingredient link object to process.
        first_time (bool): Indicates if this is the first attempt to process the link.
        stopping_offset (int or None): The stopping condition offset, if applicable.

    Returns:
        bool or None: 
            - True if the ingredient was successfully processed.
            - False if the stopping condition was hit or the link could not be processed.
            - None if the thread was stopped early.

    Notes:
        - The function respects stop signals to allow graceful interruption.
        - Errors during extraction are logged, and the task's error count is incremented.
        - The WebDriver instance is cleaned up after processing to avoid resource leaks.
    """
    from apps.etl_app.models import Task, JobTriggerHistory
    from apps.etl_app.worker_signals import stop_thread_event

    # Retrieve the task instance
    task = Task.objects.get(id=task_id)
    
    # Get a WebDriver instance from the pool
    driver = driver_pool.get()

    # Early stop check before processing
    if stop_thread_event.is_set():
        logger.debug(f"[Thread {threading.current_thread().name}] Stop signal detected, exiting before processing.")
        return None

    # Add a small random delay to mimic human behavior
    time.sleep(random.uniform(TIME_BETWEEN_REQUESTS_LOW_BOUND, TIME_BETWEEN_REQUESTS_HIGH_BOUND))
    
    # Attempt to extract ingredient data with retries
    try:
        for attempt in range(1, MAX_RETRIES + 1):
            # Check if the stopping condition offset is reached
            if stopping_offset and ingredient_link.id > stopping_offset:
                task.owner_job.create_job_trigger_history(
                    type=JobTriggerHistory.Type.STOPPING_CONDITION,
                    action=JobTriggerHistory.Action.REST,
                )
                logger.info(f"[Thread {threading.current_thread().name}] Stopping condition reached at ingredient link ID {ingredient_link.id}.")
                return False

            # Early stop check inside the retry loop
            if stop_thread_event.is_set():
                logger.debug(f"[Thread {threading.current_thread().name}] Stop signal detected mid-processing, exiting.")
                return None

            try:
                # Log the start of the extraction process
                logger.info(f"[Thread {threading.current_thread().name}] Processing ingredient link ID {ingredient_link.id} from {ingredient_link.link}.")
                
                # Extract ingredient data from the link
                extract_data_from_link(logger, task, driver, ingredient_link.link, first_time)
                return True

            except TimeoutException:
                # Handle timeout exceptions with retries
                logger.warning(f"[Thread {threading.current_thread().name}] Timeout on {ingredient_link.link} (Attempt {attempt}/{MAX_RETRIES}).")
                if attempt == MAX_RETRIES:
                    task.increment_errors(logger, f"Timeout: {ingredient_link.link}", None)
                else:
                    time.sleep(RETRY_DELAY)

            except WebDriverException:
                # Handle WebDriver-specific exceptions
                task.increment_errors(logger, f"WebDriver error: {ingredient_link.link}", traceback.format_exc())
                break

            except Exception:
                # Handle unexpected exceptions
                task.increment_errors(logger, f"Unexpected error: {ingredient_link.link}", traceback.format_exc())
                break
    finally:
        # Ensure the WebDriver instance is cleaned up
        driver_pool.put(driver)
        return False

def pull_ingredients(logger, task, max_threads=MAX_THREADS):
    """
    Extract detailed ingredient data in parallel using multiple threads.

    This function processes ingredient links stored in the database, extracting detailed
    information for each ingredient using Selenium and BeautifulSoup. It leverages a 
    thread pool to perform parallel extraction, improving efficiency for large datasets.

    Workflow:
        1. Computes the stopping offset based on the job's threshold condition.
        2. Retrieves ingredient links from the database, starting from the last processed step.
        3. Submits extraction tasks to a thread pool executor for parallel processing.
        4. Monitors for stop signals to gracefully halt new task submissions.
        5. Updates the task's progress, including the number of processed items.
        6. Cleans up resources, including thread-local WebDriver instances.

    Args:
        logger (logging.Logger): Logger instance for structured logging.
        task (Task): Task model instance tracking the job's progress, steps, and statistics.
        max_threads (int, optional): Maximum number of threads to use. Defaults to MAX_THREADS.

    Returns:
        tuple: A tuple containing:
            - task (Task): Updated task instance with progress metrics.
            - completed (bool): True if all ingredients were processed, False otherwise.

    Notes:
        - The function respects stop signals to allow graceful interruption.
        - Thread-local storage is used to manage WebDriver instances per thread.
        - Errors during extraction are logged, and the task's error count is incremented.
    """
    from apps.etl_app.models import ThresholdCondition

    logger.info("")
    logger.info("Starting parallel ingredient extraction")
    logger.info("")

    # Compute stopping offset if a threshold condition is defined
    OFFSET = None
    if (
        task.owner_job
        and task.owner_job.stopping_condition
        and isinstance(task.owner_job.stopping_condition, ThresholdCondition)
    ):
        OFFSET = task.step + task.owner_job.stopping_condition.threshold_value

    # Retrieve ingredient links from the database, starting from the last processed step
    ingredient_links = list(IngredientLink.select().where(IngredientLink.id > task.step))
    FIRST_TIME = True
    total_processed = 0
    
    # Initialize the webdriver pool
    driver_pool = Queue()
    for _ in range(MAX_THREADS):
        driver_pool.put(create_driver(debug_mode=False))

    # Use a ThreadPoolExecutor for parallel processing
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = []

        # Submit tasks for each ingredient link
        for link in ingredient_links:
            # Check for stop signal before submitting new tasks
            if stop_thread_event.is_set():
                logger.info("Stop signal detected — no new tasks will be submitted.")
                break
            futures.append(executor.submit(process_ingredient_link, logger, task.id, link, FIRST_TIME, OFFSET, driver_pool))

        try:
            # Process completed futures as they finish
            for future in concurrent.futures.as_completed(futures):
                # Check for stop signal during processing
                if stop_thread_event.is_set():
                    logger.info("Stop signal detected — waiting for running threads to finish...")
                    break

                try:
                    result = future.result()
                except Exception as e:
                    logger.error(f"Future raised an exception: {e}", exc_info=True)
                    continue

                if result:
                    # Update task progress for successfully processed ingredients
                    total_processed += 1
                    task.step += 1
                    task.items_processed += 1
                    task.save()

        finally:
            # Ensure proper cleanup of the executor
            executor.shutdown(wait=True, cancel_futures=True)
            
            # Clean up the WebDriver instances in the pool
            while not driver_pool.empty():
                driver = driver_pool.get_nowait()
                try:
                    driver.quit()
                except Exception:
                    pass
                
            logger.info(f"Executor shut down. Total processed: {total_processed}")

    logger.info("")
    logger.info(f"{total_processed} ingredients processed.")
    logger.info("")

    # Clean up thread-local WebDriver instances
    #try:
    #    if hasattr(thread_local, "driver"):
    #        thread_local.driver.quit()
    #except Exception:
    #    pass

    return task, True

def pull_ingredients_links(logger, task):
    """
    Extract ingredient links from Continente's website using Selenium with Firefox (headless).

    This function automates browser navigation through Continente's category pages to collect 
    all ingredient (product) links and store them in the database. It leverages a real browser 
    session to bypass anti-bot systems and ensure JavaScript-rendered content is captured.

    Args:
        logger (logging.Logger): Active logger for logging info, warnings, and errors.
        task (Task): Task model instance tracking the job's progress, steps, and statistics.

    Workflow:
        1. Launches a Selenium Firefox driver (headless) for realistic browsing.
        2. Loads the homepage and extracts top-level product categories.
        3. Filters out irrelevant or subcategories and ensures key ones exist.
        4. Iterates through each valid category to extract product/ingredient links:
            - Loads the category page to determine total product count.
            - Builds paginated data URLs.
            - Loops through paginated requests to extract product links.
            - Inserts links into the database and tracks progress.
        5. Monitors for stopping thresholds (from the parent job configuration).
        6. Gracefully shuts down and updates task statistics when complete.

    Returns:
        tuple: (task, completed)
            - task (Task): Updated task with current link count.
            - completed (bool): True if all categories processed, False if stopped early.

    Raises:
        RuntimeError: If the Firefox driver or page loading fails critically.
    """

    # === INITIAL SETUP ========================================================
    stopping_condition_triggered = False
    total_ingredients_links_already_done = None
    total_links_counter = 0
    completed = False

    logger.info("")
    logger.info("=== Starting Ingredient Link Extraction (Selenium Mode) ===")
    logger.info("")

    # Create Selenium WebDriver instance (headless Firefox)
    driver = create_driver(debug_mode=False)

    # === STEP 1: LOAD HOMEPAGE & EXTRACT CATEGORY LINKS =======================
    logger.info("Loading homepage and extracting category links...")
    try:
        driver.get(BASE_URL)
        time.sleep(random.uniform(TIME_BETWEEN_REQUESTS_LOW_BOUND, TIME_BETWEEN_REQUESTS_HIGH_BOUND))  # Add human-like delay
    except TimeoutException:
        raise RuntimeError("Timeout while loading the Continente homepage.")

    html = BeautifulSoup(driver.page_source, "html.parser")
    homepage = html.find("div", class_="container-dropdown-first-column")
    categories = {}

    # Extract top-level category names and URLs
    for item in homepage.find_all("li", class_="dropdown-item dropdown"):
        url = item.find("a", class_="dropdown-link pwc-font--primary-regular-italic col-view-all")
        if not url or url.get("role") != "menuitem":
            continue

        category_text = item.find("div", class_="category-info").text.strip()
        href = url["href"]
        categories[category_text] = href

    # === STEP 2: CLEAN CATEGORY DICTIONARY ====================================
    # Remove nested or unwanted categories
    for key, value in list(categories.items()):
        if value.count("/") != 4:
            categories.pop(key)

    for to_remove in [
        "Destaques", "Loja de Marcas", "Lojas de Marcas", "Jardim, Bricolage e Auto",
        "Brinquedos e Jogos", "Livraria e Papelaria", "Desporto, Bagagens, Roupa",
        "Casa, Mobiliário, Decoração"
    ]:
        categories.pop(to_remove, None)

    # Ensure key categories exist
    categories["Bebé"] = "https://www.continente.pt/bebe/ver-todos/"
    if "Frutas e Legumes" not in categories:
        categories["Frutas e Legumes"] = "https://www.continente.pt/frutas-e-legumes/frutas/"

    logger.info(f"Found {len(categories)} valid categories to process.")
    logger.info("")

    # === STEP 3: DETERMINE STOPPING CONDITION & TASK RESUMPTION ================
    from apps.etl_app.models import ThresholdCondition
    stopping_condition_offset = (
        task.owner_job.stopping_condition.threshold_value
        if task.owner_job and isinstance(task.owner_job.stopping_condition, ThresholdCondition)
        else None
    )

    # If resuming a partial task, delete already-processed records beyond last step
    if task.step != 0:
        IngredientLink.delete().where(IngredientLink.id > task.step).execute()
        total_ingredients_links_already_done = task.step

    logger.info("Starting category-by-category ingredient extraction...")

    last_key = next(reversed(categories))

    # === STEP 4: PROCESS EACH CATEGORY ========================================
    for key, value in categories.items():
    
        if stop_thread_event.is_set():
            break
        
        logger.info("")
        logger.info(f"→ Category: {key}")

        # --- Load category page ---
        try:
            driver.get(value)
            time.sleep(random.uniform(TIME_BETWEEN_REQUESTS_LOW_BOUND, TIME_BETWEEN_REQUESTS_HIGH_BOUND))
        except TimeoutException:
            logger.warning(f"Timeout loading {value}, skipping category.")
            continue

        html = BeautifulSoup(driver.page_source, "html.parser")

        # --- Extract total number of ingredients in this category ---
        try:
            max_ingredients_category = int(
                html.find("div", class_="search-results-products-counter d-flex justify-content-center")
                .text.split(" ")[2]
            )
            logger.info(f"Category contains {max_ingredients_category} ingredients.")
        except Exception:
            task.increment_warnings(
                logger=logger,
                message=f"Could not extract max ingredient count for category '{key}'.",
                stack_trace=None
            )
            continue

        # --- Extract data-url for pagination ---
        data_div = html.find("div", class_="search-view-more-products-btn-wrapper infinite-scroll-placeholder")
        if not data_div or not data_div.get("data-url"):
            logger.warning(f"No pagination data-url found for '{key}', skipping.")
            continue

        base_data_url = data_div["data-url"]
        base_data_url = base_data_url.split("&")
        base_data_url = f"{base_data_url[0]}&{base_data_url[1]}&sz={PAGE_LINKS_OFFSET}"

        # --- Handle task resumption offsets ---
        if total_ingredients_links_already_done:
            if total_ingredients_links_already_done >= max_ingredients_category:
                total_ingredients_links_already_done -= max_ingredients_category
                logger.info("Category already extracted; skipping.")
                continue
            else:
                start = total_ingredients_links_already_done
        else:
            start = 0

        # --- Paginate through ingredient listings ---
        pull_ingredients_retries = 0
        while start < max_ingredients_category:
            if stop_thread_event.is_set():
                logger.warning("Stop signal detected. Exiting before new page.")
                break
            
            pulling_url = f"{base_data_url}&start={start}"

            try:
                driver.get(pulling_url)
                time.sleep(random.uniform(TIME_BETWEEN_REQUESTS_LOW_BOUND, TIME_BETWEEN_REQUESTS_HIGH_BOUND))  # simulate human read time
            except TimeoutException:
                pull_ingredients_retries += 1
                if pull_ingredients_retries >= MAX_RETRIES:
                    logger.warning(f"Max retries reached for {pulling_url}")
                    break
                continue

            html = BeautifulSoup(driver.page_source, "html.parser")
            ingredients_link = html.find_all("div", class_="ct-pdp-link col-pdp-link")

            # Retry if no links found
            if not ingredients_link:
                pull_ingredients_retries += 1
                if pull_ingredients_retries >= MAX_RETRIES:
                    logger.warning(f"No links found after {MAX_RETRIES} retries for {pulling_url}")
                    break
                continue

            # --- Insert links into DB ---
            links_added = 0
            for ing_link in ingredients_link:
                link_url = ing_link.find("a")["href"]
                IngredientLink.create(
                    link=link_url,
                    page=start // PAGE_LINKS_OFFSET,
                    base_search_link=value,
                    category=key
                )
                links_added += 1
                total_links_counter += 1

                # Stop if job threshold reached
                if stopping_condition_offset and total_links_counter >= stopping_condition_offset:
                    logger.info("")
                    logger.info(f"Stopping condition reached at {total_links_counter} links.")
                    logger.info("")
                    stopping_condition_triggered = True
                    break

            if stopping_condition_triggered:
                break

            start += links_added
            logger.info(f"Added {links_added} links; total {start} processed for category.")
            time.sleep(random.uniform(TIME_BETWEEN_REQUESTS_LOW_BOUND, TIME_BETWEEN_REQUESTS_HIGH_BOUND))  # short delay before next batch

        if key == last_key:
            completed = True
        if stopping_condition_triggered:
            break

    # === STEP 5: FINALIZE JOB ================================================
    task.links = IngredientLink.select().count()
    task.save()

    logger.info("")
    logger.info("=== Ingredient Link Extraction Completed Successfully ===")
    logger.info("")

    driver.quit()
    return task, completed

def __extract_continente_ingredients(logger, task, resume):
    """
    Main entry point for extracting ingredient data from Continente.

    This function orchestrates the full extraction pipeline for the Continente ETL job:
        1. Initializes the database for ingredient extraction.
        2. Extracts ingredient links from Continente categories.
        3. Optionally (if enabled) extracts detailed ingredient information.
        4. Handles task completion, pausing, and cleanup depending on results.

    Args:
        logger (logging.Logger): Logger used for structured logging throughout the process.
        task (Task): Current ETL task object tracking process state, errors, and metrics.
        resume (bool): Whether to resume from a previous run (avoids DB reset).

    Returns:
        Task: Updated task object with metrics and final state.

    Workflow:
        - Resets thread stop events (for graceful interruption handling).
        - Starts or resumes the ingredient database.
        - Pulls all product/ingredient links from Continente.
        - Optionally triggers detailed ingredient extraction (currently disabled).
        - Updates and finalizes the ETL task.
        - Cleans up any orphaned browser processes.
    """

    # === INITIALIZATION ========================================================
    # Reset stop event — ensures no leftover cancellation flag from previous run
    stop_thread_event.clear()

    logger.info(f"Initializing {task.type} for all {task.process} from {task.company}...")
    logger.info("")

    # Initialize or resume the ingredient database
    logger.info(f"Initializing {task.type} database...")
    task, database = start_db(
        logger=logger,
        task=task,
        models=models_,
        path=EXTRACT_CONTINENTE_INGREDIENTS_DB,
        database_proxy=database_proxy,
        reset=not resume  # Reset DB only when not resuming
    )
    logger.info("")

    # === STEP 1: LINK EXTRACTION ===============================================
    logger.info("Starting ingredient link extraction phase...")
    task, l_completed = pull_ingredients_links(logger, task)

    # === STEP 2: INGREDIENT EXTRACTION =========================================
    task, completed = pull_ingredients(logger, task)


    # === STEP 3: SUMMARY & LOGGING =============================================
    logger.info("Extraction Summary:")
    logger.info(f"  - Ingredient Links: {task.links}")
    logger.info(f"  - Ingredients Extracted: {task.items_processed}")
    logger.info("")
    logger.info(f"  - Total Errors: {task.errors}")
    logger.info(f"  - Total Warnings: {task.warnings}")
    logger.info("")

    # === STEP 4: FINALIZATION ==================================================
    # Mark task as finished or paused depending on completion state
    if completed and l_completed:
        task.finish(kill_celery_task=False)
        logger.info("✅ Task successfully completed.")
    else:
        task.pause()
        logger.info("⚠️ Task paused before full completion.")

    # Clean up any orphaned Firefox/GeckoDriver processes
    task.kill_orphaned_firefox_instances()

    return task
