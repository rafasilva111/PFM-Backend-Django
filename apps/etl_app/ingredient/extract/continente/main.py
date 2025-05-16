"""
Import necessary modules and libraries
"""
from django.utils import timezone
import requests
import unidecode
from bs4 import BeautifulSoup
from time import sleep	

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.firefox.service import Service

"""
Import custom functions and constants
"""
from apps.etl_app.functions import start_db
from apps.etl_app.constants import extract_continente_ingredients_db,continente_ingredients_images_folder	
from apps.etl_app.ingredient.extract.continente.models import Tag, NutritionInformation, Ingredient, database_proxy, IngredientLink

"""
Define the through model for Ingredient and Tag relationship
"""
IngredientTagThrough = Ingredient.tags.get_through_model()

"""
List of models to be used in the extraction process
"""
models_ = [Ingredient, Tag, NutritionInformation, Ingredient, IngredientTagThrough, IngredientLink]

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

    " Brand "
    brand = html.find('a', class_='ct-pdp--brand col-pdp--brand')
    if brand:
        ingredient_db.brand = brand.text.strip()

    " Size "

    text = html.find('span',
                     class_='ct-pdp--unit col-pdp--unit').text.strip()

    text = text.split(" ")
    if len(text) == 2:
        ingredient_db.size = text[1]
    
    if len(text) == 3:
        ingredient_db.size_unit = text[2]

    " Price per unit "

    ingredient_db.price_per_unit = html.find('span',
                                             class_='ct-price-formatted').text.replace("€", "").strip()

    base_html_bulk = html.find('div',
                               class_='pwc-tile--price-secondary col-tile--price-secondary')

    ingredient_db.price_bulk = base_html_bulk.find('span',
                                                   class_='ct-price-value').text.replace("€", "").strip()

    ingredient_db.bulk_unit = base_html_bulk.find('span',
                                                  class_='pwc-m-unit').text.replace("/", "").strip()

    " Description "
    ingredient_db.description = html.find('div',
                                          class_='ct-pdp--short-description col-pdp--short-description').text.strip()

    " Image "

    file_storage = unidecode.unidecode(ingredient_db.title).replace(" ", "_")
    image_source_link = html.find('img', class_='ct-product-image')['src']
    img_source = f'{continente_ingredients_images_folder}/{file_storage}.png'
    ingredient_db.img = img_source
    try:
        with open(img_source, "wb") as f:
            f.write(requests.get(image_source_link).content)
    except Exception as e:
        logger.warning(e)
        warnings = warnings + 1

    " Caracteristicas and  Informação adicional Tab "
    tabs = html.find_all("div", class_="simplebar-content")
    try:

        # Iterate through the values in the list and set the corresponding attributes in the model
        for tab in tabs:
            infos = tab.find_all("p")
            counter = 0
            while counter < (len(infos) - 1):

                title = infos[counter].text.strip()
                text = infos[counter + 1].text.strip()
                # Use the map
                attribute_name = caracteristics_and_info_name_map.get(title)

                # Set the attribute value in the model
                if attribute_name:
                    setattr(ingredient_db, attribute_name, text)
                    counter += 2
                else:
                    counter += 1

    except Exception as e:
        logger.warning("Ingredient doesn't have a caracteristics and info tab.")
        warnings = warnings + 1

    " Informação Nutricional "
    tabs = html.find("div", class_="nutrients-table")
    if tabs:
        try:
            text = tabs.text.split("\n\n\n")

            # Create an instance of the model
            nutrition_info = NutritionInformation()

            # Iterate through the values in the list and set the corresponding attributes in the model
            for value in text[2:]:
                nutrient, quantity, unit = value.strip().split('\n')

                # Use the map
                attribute_name = nutrient_name_map.get(nutrient.lower())

                # Set the attribute value in the model
                if attribute_name:
                    setattr(nutrition_info, attribute_name, quantity)
                nutrition_info.save()
                ingredient_db.nutrition_information = nutrition_info

        except Exception as e:
            logger.warning("Ingredient doesn't have a nutrition tab.")
            warnings = warnings + 1
    else:
        logger.info("Ingredient doesn't have a nutrition tab.")

    " Informação legal "

    tabs = html.find("div", class_="description tab-row-header")
    if tabs:
        try:
            text = tabs.text.replace(" ", " ").strip()
            text = text.split("\n\n\n")

            # Iterate through the values in the list and set the corresponding attributes in the model
            for value in text[1:-1]:
                title, desc = value.strip().split('\n', 1)

                # Use the map
                attribute_name = legal_name_map.get(title)

                # Set the attribute value in the model
                if attribute_name:
                    setattr(ingredient_db, attribute_name, desc)

        except Exception as e:
            logger.warning("Ingredient doesn't have Informação legal tab.")
            warnings = warnings + 1
    else:
        logger.info("Ingredient doesn't have Informação legal tab.")
        
    logger.info("")
    ingredient_db.save()
    
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
    
    
    " Initialize the warnings and errors counters "
    warnings = 0
    errors = 0
    
    logger.info("")
    logger.info("Starting to pull Recipes")
    
    total_recipes = Ingredient.select().count()
    
    logger.info(f"Found {total_recipes} recipes on DB...")
    logger.info("")
    
    service = Service("/app/bin/geckodriver")
    
    firefox_options = webdriver.FirefoxOptions()
    zoom_level = 1.5
    firefox_options.add_argument(f'--zoom={zoom_level}')
    firefox_options.add_argument(f'--headless')

    max_ingredients = -1

    with webdriver.Firefox(service=service,options=firefox_options) as driver:
        driver.maximize_window()

        counter = 0
        for ingredient_link in IngredientLink.select().where(IngredientLink.id > total_recipes):
            if max_ingredients != -1 and counter == max_ingredients:
                break
            else:
                counter += 1

            logger.info(f"Extracting Ingredient {ingredient_link.id} from {ingredient_link.link}")

            warnigs_, errors_ = extract_data_from_link(logger, driver, ingredient_link.link, first_time = counter == 1)
            warnings += warnigs_
            errors += errors_
            
    
    " Update Task Statistics"
    task.items = Ingredient.select().count()
    task.items_warnings = warnings
    task.items_errors = errors
    task.save()
    
    " Log the completion of the extraction process "
    logger.info("All Recipes pulled ...")
    logger.info("")
    logger.info("Pull Recipes summary:")
    logger.info(f"{task.print_items_summary()}")
    logger.info("")


def pull_ingredients_links(logger, task, continue_mode=False):
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


    " Initialize the warnings and errors counters "
    warnings = 0
    errors = 0

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

    if 'Bebé' in categories:
        categories.pop('Bebé')

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
        logger.info("")

        category_response = requests.get(value)
        html = BeautifulSoup(category_response.content, 'html.parser')
        try:
            max_ingredients = int(
            html.find("div", class_="search-results-products-counter d-flex justify-content-center").text.split(" ")[2])
        except Exception:
            warnings += 1
            logger.warning("Unable to Extract this category...")
            continue
        # todo max recipes

        base_data_url = html.find("div", class_="search-view-more-products-btn-wrapper infinite-scroll-placeholder")[
            'data-url']

        " Prepare base url "
        if continue_mode:
            start = IngredientLink.select().where(IngredientLink.category == key).count()
        else:
            start = 0

        size = 24

        base_data_url = base_data_url.split("&")
        base_data_url = f"{base_data_url[0]}&{base_data_url[1]}&sz={size}"

        while start < max_ingredients:

            extra = f"&start={start}"
            base_data_url += extra

            category_response = requests.get(base_data_url)
            html = BeautifulSoup(category_response.content, 'html.parser')

            base_data_url = base_data_url.replace(extra, "")

            ingredients_link = html.find_all("div", class_="ct-pdp-link col-pdp-link")
            
            if not ingredients_link:
                logger.warning(f"No more ingredients found on link {base_data_url}")
                warnings += 1
            
            for ingredient_link in ingredients_link:

                ingredient_link = IngredientLink(
                    link=ingredient_link.find('a')['href'],
                    page=start // size, 
                    base_search_link=value,
                    category = key
                    )
                ingredient_link.save()

            start += size
            logger.info(f"Added {start} ingredients links from page {start // size}")
            
    " Update Task Statistics"
    task.links = IngredientLink.select().count()
    task.links_warnings = warnings
    task.links_errors = errors
    task.save()
    
    " Log the completion of the extraction process "
    logger.info("All Ingredient's Links pulled ...")
    logger.info("")
    logger.info("Pull Ingredient's Links summary:")
    logger.info(f"{task.print_links_summary()}")
    logger.info("")
    




def __extract_continente_ingredients(logger, task, continue_mode):
       
    " Log the start of the extraction process "
    logger.info(f"Extracting all recipes from {task.company}...")
    logger.info("")
        
    " Starts the db "
    logger.info("Starting extract db...")
    start_db(
        logger=logger,
        task=task,
        models=models_,
        path=extract_continente_ingredients_db,
        database_proxy=database_proxy
        )
    

    " Pull all ingredients links "
    pull_ingredients_links(logger, task, continue_mode)
    

    " Pulls ingredient from above links "
    pull_ingredients(logger, task)
    
    " Calculate total summary "
    task.warnings = task.links_warnings + task.items_warnings
    task.errors = task.links_errors + task.items_errors
    task.save()
    
    
    " Log the completion of the extraction process "
    logger.info("Pull links summary:")
    logger.info(f"{task.print_links_summary()}")
    logger.info("")
    
    logger.info("Pull recipes summary:")
    logger.info(f"{task.print_items_summary()}")
    logger.info("")
    
    logger.info("")
    logger.info("Total summary:")
    logger.info(f"{task.print_total_summary()}")
    logger.info("")
    
    
    " Finish task "
    task.finish(kill_celery_task=False)
    
    
    " Log the completion of the extraction process "
    logger.info(f"Done...")
    logger.info("")
    


