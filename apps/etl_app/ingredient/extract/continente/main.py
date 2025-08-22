
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



models_ = [Ingredient, Tag, IngredientTagThrough, IngredientLink, Image]

"""
Define constants for the scraping process
"""
BASE_URL = "https://www.continente.pt"
BASE_HEADERS = {
    "cookie": "realUserVerifier=Verified;",
}
COMPANY_NAME = "continente"
DEFAULT_SLEEP_TIME = 2
FIRST_TIME = True

PAGE_LOAD_TIMEOUT = 60  # seconds
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds
RESET_INTERVAL = 1000

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

def extract_data_from_link(logger, driver, ingredient_link, sleep_time=DEFAULT_SLEEP_TIME, first_time=True):
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
    
    
    " Initialize the warnings and errors counters "
    warnings = 0	
    errors = 0
    
    " Load page using selenium as the page have javascript "
    driver.get(ingredient_link)
    
    
    " Check if page was redirected "
    if driver.current_url != ingredient_link:
        logger.error(f"Redirected to: {driver.current_url}, skipping this ingredient...")
        logger.info("")
        errors = errors + 1
        return warnings, errors

    
    
    if first_time:
        try:
            # Aguarda o popup de cookies aparecer
            cookie_popup_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.ID, "CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll"))
            )

            # Clica no botão "Permitir todos" para aceitar os cookies
            cookie_popup_button.click()
        except Exception as e:
            logger.error(f"An error occurred: {e}")
            errors = errors + 1

    sleep(sleep_time)
    html = BeautifulSoup(driver.page_source, 'html.parser')

    " Check if page was found "
    page_not_found = html.find('p', class_='notfound-title')
    if page_not_found:	
        logger.error(f"Page not found: {ingredient_link}, skipping this ingredient...")
        logger.info("")
        errors = errors + 1	
        return warnings, errors
    
    # prepare to deal whit tabs ( check if base_tabs already loaded if not call
    # function again whit more sleep time)
    base_html_tab = html.find('ul',
                        class_='col-sm-4 col-md-3 tabNav mResTabNav')

    if base_html_tab is None:
        return extract_data_from_link(logger, driver, ingredient_link, sleep_time + 1, False)
    
    

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
        if counter > 0:
            file_storage += f"_{counter}"
            
        image_source_link = image['src']
        img_source = f'{CONTINENTE_INGREDIENTS_IMAGES_FOLDER}/{file_storage}.png'
        image_db.path = img_source
        try:
            with open(img_source, "wb") as f:
                f.write(requests.get(image_source_link).content)
        except Exception as e:
            logger.warning(e)
            warnings = warnings + 1
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
    
    
    return warnings, errors


def pull_ingredients(logger, task):
    """
    Extracts ingredient data from a list of links and updates task statistics.
    This function retrieves ingredient links from the database, navigates to each link using a 
    headless Firefox browser, extracts ingredient data, and updates the task statistics with 
    the number of items processed, warnings, and errors encountered.
    Args:
        logger (logging.Logger): Logger instance for logging information, warnings, and errors.
        task (Task): Task object used to track the progress and statistics of the extraction process.
    Workflow:
        1. Logs the start of the ingredient extraction process.
        2. Counts the total number of recipes in the database.
        3. Configures and initializes a headless Firefox browser.
        4. Iterates over ingredient links from the database that have not been processed.
        5. Extracts data from each link and updates warnings and errors counters.
        6. Updates the task statistics with the total items, warnings, and errors.
        7. Logs the completion of the extraction process and provides a summary.
    Notes:
        - The function uses Selenium for web scraping with a headless Firefox browser.
        - The `max_ingredients` variable can be used to limit the number of ingredients processed.
        - The `extract_data_from_link` function is assumed to handle the actual data extraction.
    Raises:
        Any exceptions raised by Selenium or database operations should be handled appropriately 
        outside this function.
    """
    
    
    " Initialize the Control variables "    
    OFFSET = None
    FIRST_TIME = True
    
    logger.info("")
    logger.info("Starting to pull Recipes")
    logger.info("")
    logger.info(f"Recipe {task.process} is on step {task.step}...")
    logger.info("")
    
    " Get the Threshold Stopping condition"
    from apps.etl_app.models import ThresholdCondition, JobTriggerHistory
    if task.owner_job and task.owner_job.stopping_condition and isinstance(task.owner_job.stopping_condition, ThresholdCondition):
        OFFSET = task.step + task.owner_job.stopping_condition.threshold_value
    
    " Check if we are resuming the task, and if so, delete the Recipes that are above the step "
    if task.step != 0:
        instances_in_db = Ingredient.select().count()
        if instances_in_db > task.step:
            # Delete tasks until step matches recipes_in_db
            instances_to_delete = Ingredient.select().order_by(Ingredient.id.desc())
            for t in instances_to_delete:
                if task.step == instances_in_db:
                    break
                t.tags.clear()
                t.delete_instance()
                instances_in_db -= 1
    
    
    " Initialize the Selenium WebDriver and Firefox options "
    
    driver = create_driver(task.debug_mode)  # Initial driver

    for idx, ingredient_link in enumerate(IngredientLink.select().where(IngredientLink.id > task.step)):
        
        # Reset browser at fixed intervals
        if idx > 0 and idx % RESET_INTERVAL == 0:
            logger.info(f"Restarting WebDriver at item {ingredient_link.id}")
            try:
                driver.quit()
            except Exception:
                pass
            driver = create_driver()

        if OFFSET and ingredient_link.id > OFFSET:
            task.owner_job.create_job_trigger_history(
                type=JobTriggerHistory.Type.STOPPING_CONDITION,
                action=JobTriggerHistory.Action.REST,
            )
            logger.info(f"Job Stopping Condition triggered. Paused extraction at {ingredient_link.id}...")
            return task, False

        logger.info(f"Extracting Ingredient {ingredient_link.id} from {ingredient_link.link}")

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                _errors, _warnings = extract_data_from_link(
                    logger, driver, ingredient_link.link, first_time=FIRST_TIME
                )
                task.warnings += _warnings
                task.errors += _errors
                break
            except TimeoutException:
                logger.warning(f"Timeout while extracting {ingredient_link.link} (Attempt {attempt}/{MAX_RETRIES})")
                if attempt == MAX_RETRIES:
                    logger.error(f"Failed to extract {ingredient_link.link} after {MAX_RETRIES} attempts")
                    task.increment_errors()
                else:
                    time.sleep(RETRY_DELAY)
            except WebDriverException as e:
                logger.error(f"WebDriver error while extracting {ingredient_link.link}: {str(e)}")
                task.increment_errors()
                break
            except Exception as e:
                logger.exception(f"Unexpected error while extracting {ingredient_link.link}")
                task.increment_errors()
                break

        task.step += 1
        task.items_processed += 1
        task.save()

        FIRST_TIME = False

    " Final cleanup "
    try:
        driver.quit()
    except Exception:
        pass
    
    " Log the completion of the extraction process "
    logger.info(f"{task.items_processed} Recipes pulled ...")
    logger.info("")
    
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


    " Gets all Ingredients's Links from Continente "
    logger.info("Starting to pull Ingredient's Links...")
    logger.info("")

    " Get Main Category's Pages "
    logger.info("Finding Categories...")
    base_response = requests.get(BASE_URL)
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
    if "Frutas e Legumes" not in categories:
        categories["Frutas e Legumes"] = 'https://www.continente.pt/frutas-e-legumes/frutas/'

    logger.info("")
    logger.info(f"Found {len(categories)} categories")
    logger.info("")

    """ Get all Ingredient's Links for each category """
    logger.info("Finding all ingredients links for each category...")

    for key, value in categories.items():
        
        logger.info("")
        logger.info(f"Extracting Ingredient's Links from category: {key}")
        

        category_response = requests.get(value)
        html = BeautifulSoup(category_response.content, 'html.parser')
        try:
            max_ingredients = int(html.find("div", class_="search-results-products-counter d-flex justify-content-center").text.split(" ")[2])
            logger.info(f"category has {max_ingredients} ingredients")
        except Exception:
            logger.warning("Unable to Extract this category...")
            task.increment_warnings()
            continue
        logger.info("")
        
        base_data_url = html.find("div", class_="search-view-more-products-btn-wrapper infinite-scroll-placeholder")['data-url']
        start = 0
        size = 24

        base_data_url = base_data_url.split("&")
        base_data_url = f"{base_data_url[0]}&{base_data_url[1]}&sz={size}"

        while start < max_ingredients:

            extra = f"&start={start}"
            base_data_url += extra

            category_response = requests.get(base_data_url)
            html = BeautifulSoup(category_response.content, 'html.parser')

            ingredients_link = html.find_all("div", class_="ct-pdp-link col-pdp-link")
            
            if not ingredients_link:
                logger.info(f"No more ingredients found on link {base_data_url}")
                break
            base_data_url = base_data_url.replace(extra, "")
            
            
            links_added = 0
            for ingredient_link in ingredients_link:

                ingredient_link = IngredientLink(
                    link=ingredient_link.find('a')['href'],
                    page=start // size, 
                    base_search_link=value,
                    category = key
                    )
                ingredient_link.save()
                links_added += 1

            start += links_added
            logger.info(f"Added {links_added} ingredients links, total {start} links found so far...")
            
    " Update Task Statistics"
    task.links = IngredientLink.select().count()
    task.save()
    
    " Log the completion of the extraction process "
    logger.info("")
    logger.info("All Ingredient's Links pulled ...")
    logger.info("")
    
    return task
    

def __extract_continente_ingredients(logger, task, resume):
    
    " Log the start of the extraction process"
    logger.info(f"Initializing the {task.type} all {task.process} from {task.company}...")
    
    " Initialize the warnings and errors "
    if resume:
        task.errors = 0
        task.warnings = 0
        

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
    
    

    " Pull all ingredients links "
    # We only want to pull recipes links if step is 0
    # This is because we want to pull all recipes links only once
    if task.step == 0:
        task = pull_ingredients_links(logger, task)
    
    

    " Pulls Ingredients from above links "
    task, completed = pull_ingredients(logger, task)
        
    
    " Log the completion of the extraction process "
    logger.info("Summary:")
    logger.info(f"Ingredients Links Found: {task.links}")
    logger.info(f"Ingredients: {task.items_processed}")
    logger.info("")
    logger.info(f"Total errors: {task.errors}")
    logger.info(f"Total warnings: {task.warnings}")
    
    
    " Finish task "
    if completed:
        task.finish(kill_celery_task=False)
    else:
        task.pause()
    
    
    " Log the completion of the extraction process "
    logger.info("")
    logger.info(f"> Done...")
    logger.info("")
    
    return task

