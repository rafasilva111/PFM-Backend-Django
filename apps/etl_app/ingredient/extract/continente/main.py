import logging
from django.utils import timezone
import requests
import unidecode

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from bs4 import BeautifulSoup
from apps.etl_app.functions import start_extract_db
from apps.etl_app.constants import extract_continente_ingredients_db,continente_images_folder	
from time import sleep	
from selenium.webdriver.firefox.service import Service
from apps.etl_app.ingredient.extract.continente.models import Tag, NutritionInformation, Ingredient, database_proxy, IngredientLink

IngredientTagThrough = Ingredient.tags.get_through_model()

models_ = [Ingredient, Tag, NutritionInformation, Ingredient, IngredientTagThrough, IngredientLink]


"""
        Notes:
        
    This scrapper should run more tham one time, extra tabs ( nutritional info, legal info, advises)
    dont always load (their fault).


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


def extract_data_from_link(logger, driver, ingredient_link, sleep_time=DEFAULT_SLEEP_TIME, first_time=True):
    
    # load page using selenium as the page have javascript
    driver.get(ingredient_link)
    warnings = 0
    
    # check if page was redirected
    if driver.current_url != ingredient_link:
        logger.warning(f"Redirected to: {driver.current_url}, skipping this ingredient...")
        logger.info("")
        warnings = warnings + 1
        return

    
    
    if first_time:
        try:
            # Aguarda o popup de cookies aparecer
            cookie_popup_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.ID, "CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll"))
            )

            # Clica no botão "Permitir todos" para aceitar os cookies
            cookie_popup_button.click()
        except Exception as e:
            logger.warning(f"An error occurred: {e}")
            warnings = warnings + 1

    sleep(sleep_time)
    html = BeautifulSoup(driver.page_source, 'html.parser')

    # check if page was found
    page_not_found = html.find('p', class_='notfound-title')
    if page_not_found:	
        logger.warning(f"Page not found: {ingredient_link}, skipping this ingredient...")
        logger.info("")
        warnings = warnings + 1	
        return
    
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
    img_source = f'{continente_images_folder}/{file_storage}.png'
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

            logger.info(f"Extracting ingredient {ingredient_link.id} from {ingredient_link.link}")

            extract_data_from_link(logger, driver, ingredient_link.link, first_time = counter == 1)

    if counter == 0:
        logger.info("All recipes were imported")
    
    logger.info("")


def pull_ingredients_links(logger, continue_mode=False):
    """
        Pulls links for ingredients from a data source.

        Args:
            max_ingredients (int): Maximum number of ingredients to retrieve. Set to -1 for no limit.
            continue_mode (bool): If True, continues from the last pulled ingredient.

        Returns:
            None: The function does not return a value, but it updates the ingredient links dataset.

        Example:
            pull_ingredients_links(max_ingredients=50, continue_mode=True)
    """

    """ Get all recipes links """

    logger.info("Starting to pull Recipes Links")
    logger.info("")

    """ Get Main Search all Pages """

    logger.info("Finding Categories...")

    base_response = requests.get(BASE_URL)
    html = BeautifulSoup(base_response.content, 'html.parser')
    homepage = html.find('div', class_='container-dropdown-first-column')
    # Get all categories
    categories = {}

    for item in homepage.find_all('li', class_="dropdown-item dropdown"):
        url = item.find('a', class_='dropdown-link pwc-font--primary-regular-italic col-view-all')

        if url['role'] != 'menuitem':
            continue

        category_text = item.find('div', class_='category-info').text.strip()
        url = url['href']

        categories.update({category_text: url})

    # Retirar subcategorias

    for key, value in categories.copy().items():
        if value.count('/') != 4:
            categories.pop(key)

    # Remove unneccessary categories
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

    # add neccessary categories
    if "Frutas e Legumes" not in categories:
        categories["Frutas e Legumes"] = 'https://www.continente.pt/frutas-e-legumes/frutas/'

    logger.info("")
    logger.info(f"Found {len(categories)} categories")
    logger.info("")

    """ Get all ingredients links for each categorie """

    logger.info("Finding all ingredients links for each category...")

    for key, value in categories.items():
        
        logger.info("")
        logger.info(f"Extracting all ingredients from catgory: {key}")
        logger.info("")

        category_response = requests.get(value)
        html = BeautifulSoup(category_response.content, 'html.parser')
        try:
            max_ingredients = int(
            html.find("div", class_="search-results-products-counter d-flex justify-content-center").text.split(" ")[2])
        except Exception:
            logger.info("Unable to Extract this category...",log_level=logging.WARNING)
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
            
    logger.info("All links pulled ...")
    return 0




def __extract_continente_ingredients(logger, task, continue_mode):
    
    
    # Log the start of the extraction process
    logger.info(f"Extracting all recipes from {task.company}...")
    logger.info("")
    
    status = 1
    
    # starts the db
    start_extract_db(
        logger=logger,
        task=task,
        models=models_,
        path=extract_continente_ingredients_db,
        database_proxy=database_proxy
        )
    

    # pull all recipes links
    #pull_ingredients_links(logger, continue_mode)
    

    # pulls recipes from above links
    pull_ingredients(logger, task)
    

    # Finish task
    task.finished_at = timezone.now()
    task.status = task.Status.FINISHED
    task.save()
    
    # Log the completion of the extraction process
    logger.info(f"Done...")
    logger.info("")
    


