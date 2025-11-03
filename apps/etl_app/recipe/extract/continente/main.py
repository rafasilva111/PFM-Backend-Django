" Import necessary libraries and modules "
import json
import pickle
import requests
import unidecode
import traceback
import re
from bs4 import BeautifulSoup

" Import custom functions and constants "
from apps.etl_app.functions import start_db, normalize_text
from apps.etl_app.recipe.extract.continente.constants import *
from apps.etl_app.recipe.extract.continente.models import database_proxy, Recipe, RecipeLink, NutritionInformation, Ingredient, Tag, UsefulTool
from apps.etl_app.constants import EXTRACT_CONTINENTE_RECIPES_DB, CONTINENTE_RECIPES_IMAGES_FOLDER


" Define the through model for Recipe and Tag relationship "
recipeTagThrough = Recipe.tags.get_through_model()

" Define the list of models to be used in the extraction process "
models_ = [Ingredient, Recipe, RecipeLink, Tag, NutritionInformation, Ingredient, UsefulTool, recipeTagThrough]

" Define constants for the scraping process "
BASE_URL = "https://feed.continente.pt"
BASE_GRAPHQL_URL = "https://feed.continente.pt/umbraco/api/GraphQL/Post"
BASE_HEADERS = {
    "cookie": "realUserVerifier=Verified;",
}
COMPANY_NAME = "continente"
PAGE_LINKS_OFFSET = 24
DEFAULT_SLEEP_TIME = 2

def extract_data_from_link(logger, task, recipe_link):
    """
    Extracts recipe data from a given recipe link and saves it to the database.

    This function performs the following tasks:
        - Extracts the HTML content of the recipe page.
        - Parses and saves the recipe's title, company, time, difficulty, portions, description, and image.
        - Extracts and saves preparation steps, nutritional information, useful tools, ingredients, and tags.
        - Handles missing or dynamically loaded data gracefully, logging warnings and errors as needed.

    Args:
        logger (logging.Logger): Logger instance for structured logging throughout the process.
        task (Task): Current ETL task object tracking process state, errors, and metrics.
        recipe_link (RecipeLink): RecipeLink object containing the URL of the recipe to extract data from.

    Returns:
        None
    """
    # === INITIALIZATION ========================================================
    # Initialize a new Recipe object to store extracted data
    recipe_db = Recipe()

    # === HTML EXTRACTION =======================================================
    # Extract HTML response from the recipe link
    base_response = requests.get(recipe_link.link, headers=BASE_HEADERS)
    html = BeautifulSoup(base_response.content, 'html.parser')

    # Check if the page was successfully loaded
    if base_response.status_code != 200:
        task.increment_errors(
            logger=logger,
            message=f"Failed to load page: {recipe_link.link} with status code: {base_response.status_code}",
            stack_trace=None
        )
        return

    # === BASIC RECIPE DETAILS ==================================================
    # Source Link
    recipe_db.link = recipe_link.link

    # Title
    recipe_db.title = html.find('h1', class_='title font-2xl').text.strip()

    # Company
    recipe_db.company = COMPANY_NAME

    # Time, Difficulty, Portions
    infos = []
    attributes_block = html.find('div', class_='attributesBlock')
    if attributes_block:
        attribute_elements = attributes_block.find_all('div', class_='attribute')
        for attribute_element in attribute_elements:
            if attribute_element.find('i')['title'] != "Custo":
                infos.append(attribute_element.find('strong').text.strip())

    recipe_db.time = infos[0] if len(infos) > 0 else None
    recipe_db.difficulty = infos[1] if len(infos) > 1 else None
    recipe_db.portion = infos[2] if len(infos) > 2 else None

    # Description
    recipe_db.description = html.find('div', class_='detailsTextBlock').find('p', class_='font-m').get_text(
        separator=' ', strip=True)

    # === RATING ================================================================
    # Extract rating information if available
    rating_element = html.find('section', attrs={"data-control": "recipeHeader"})
    rating_endpoint = rating_element.get('data-endpoint_averagerating', None)
    if rating_endpoint:
        rating_url = f"https://feed.continente.pt{rating_endpoint}"
        rating_response = requests.get(rating_url, headers=BASE_HEADERS)
        if rating_response.status_code == 200:
            rating_data = json.loads(rating_response.text)
            recipe_db.rating = rating_data.get('rating_data', None)
        else:
            task.increment_errors(
                logger=logger,
                message=f"Failed to fetch rating data from {rating_url}, status code: {rating_response.status_code}",
                stack_trace=None
            )
    else:
        task.increment_infos(
            logger=logger,
            message=f"No rating endpoint found for {recipe_link.link}"
        )

    # === IMAGE & VIDEO =========================================================
    # Extract image and video information
    img_container = html.find('div', class_='recipeHeader__main__right')
    imgs = img_container.find_all('img') if img_container else None
    video_container = img_container.find('button', class_='btn-play--red openModalButton') if img_container else None

    if imgs:
        image_container = imgs[0]
        site_image_source = f"https://feed.continente.pt{image_container['src']}".replace("&format=webp", "&format=jpg")
        filename = normalize_text(recipe_db.title)
        app_image_source = f'{CONTINENTE_RECIPES_IMAGES_FOLDER}/{filename}.png'
        recipe_db.image = app_image_source
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            with open(app_image_source, "wb") as f:
                response = requests.get(site_image_source, headers=headers)
                if response.status_code == 200:
                    f.write(response.content)
                else:
                    task.increment_errors(
                        logger=logger,
                        message=f"Failed to download image from {site_image_source}, server responded with status code: {response.status_code}",
                        stack_trace=None
                    )
        except Exception as e:
            task.increment_errors(
                logger=logger,
                message=f"Error downloading image from {site_image_source}: {e}",
                stack_trace=traceback.format_exc()
            )
    else:
        task.increment_infos(
            logger=logger,
            message=f"No image found for {recipe_link.link}"
        )

    if video_container:
        recipe_db.video_link = video_container['data-video']
    else:
        task.increment_infos(
            logger=logger,
            message=f"No video found for {recipe_link.link}"
        )

    # === PREPARATION ===========================================================
    # Extract preparation steps
    try:
        recipe_steps_raw = html.find('div', class_='recipeSteps__body')
        preparation = []
        if recipe_steps_raw:
            list_items = recipe_steps_raw.find_all('li')
            section = "main"
            for li_element in list_items:
                if li_element.has_attr('class'):
                    section = li_element.text.strip()
                else:
                    preparation.append({
                        "step": li_element.find('span').text.replace(".", "").strip(),
                        "section": section,
                        "description": li_element.find('p').text.strip()
                    })
        recipe_db.preparation = pickle.dumps(preparation)
    except Exception as e:
        task.increment_errors(
            logger=logger,
            message=f"Error extracting preparation steps from {recipe_link.link}: {e}",
            stack_trace=traceback.format_exc()
        )

    # === NUTRITION INFORMATION =================================================
    # Extract nutritional information
    nutritional_table_raw = html.find('div', class_='recipeNutricionalTable__table')
    nutrition_helper = {}
    if nutritional_table_raw:
        rows = nutritional_table_raw.find_all('div', class_='recipeNutricionalTable__table__row')
        try:
            for row in rows:
                item_elements = row.find_all('p', class_='itemValue')
                for item_element in item_elements:
                    item_title = item_element.find_previous('p', class_='itemTitle').text.strip()
                    item_value = item_element.find('strong').text.replace(",", ".").strip()
                    nutrition_helper.update({item_title: item_value})

            nutrition_information = NutritionInformation(
                energy_kcal=nutrition_helper.get('Calorias'),
                fat_g=nutrition_helper.get('Lípidos'),
                saturates_g=nutrition_helper.get('Saturados'),
                carbohydrates_g=nutrition_helper.get('Hidratos'),
                sugars_g=nutrition_helper.get('Açúcares'),
                fiber_g=nutrition_helper.get('Fibras'),
                protein_g=nutrition_helper.get('Proteínas'),
                salt_g=nutrition_helper.get('Sal'),
            )
            nutrition_information.save()
            recipe_db.nutrition_information = nutrition_information.id
        except Exception as e:
            task.increment_errors(
                logger=logger,
                message=f"Error extracting nutritional information from {recipe_link.link}: {e}",
                stack_trace=traceback.format_exc()
            )
    else:
        task.increment_infos(
            logger=logger,
            message=f"No nutritional information found for {recipe_link.link}"
        )

    # === USEFUL TOOLS ==========================================================
    # Extract useful tools
    useful_tools_container = html.find('div', class_='collapsedContentBox')
    if useful_tools_container:
        useful_tools = useful_tools_container.find('ul', class_='textFormat__list')
        if useful_tools:
            try:
                list_items = useful_tools.find_all('li')
                for li_element in list_items:
                    useful_tool_text = li_element.text.strip()
                    useful_tool = UsefulTool(name=useful_tool_text)
                    useful_tool.recipe = recipe_db.id
                    useful_tool.save()
            except Exception as e:
                task.increment_errors(
                    logger=logger,
                    message=f"Error extracting useful tools from {recipe_link.link}: {e}",
                    stack_trace=traceback.format_exc()
                )
        else:
            task.increment_infos(
                logger=logger,
                message=f"No useful tools found for {recipe_link.link}"
            )
    else:
        task.increment_infos(
            logger=logger,
            message=f"No useful tools found for {recipe_link.link}"
        )

    # === INGREDIENTS ===========================================================
    # Extract ingredients
    ingredient_list_raw = html.find('div', class_='ingredientList__body')
    if ingredient_list_raw:
        list_items = ingredient_list_raw.find_all('li')
        section = "main"
        for li_element in list_items:
            try:
                if li_element.has_attr('class'):
                    section = li_element.text.strip()
                else:
                    ingredient_text = li_element.text.strip()
                    ingredient = Ingredient(text=ingredient_text, section=section)
                    ingredient.recipe = recipe_db.id
                    ingredient.save()
            except Exception as e:
                task.increment_errors(
                    logger=logger,
                    message=f"Error extracting ingredient from {recipe_link.link}: {e}",
                    stack_trace=traceback.format_exc()
                )
    else:
        task.increment_warnings(
            logger=logger,
            message=f"No ingredients found for {recipe_link.link}"
        )

    # === TAGS ==================================================================
    # Extract tags
    tags_raw = html.find('div', class_='tags')
    if tags_raw:
        tags_tag = tags_raw.find('span', class_='categoryTag')
        if tags_tag:
            try:
                tag, created = Tag.get_or_create(text=tags_tag.text.strip())
                tag.save()
                recipe_db.tags.add(tag)
            except Exception as e:
                task.increment_errors(
                    logger=logger,
                    message=f"Error extracting tag from {recipe_link.link}: {e}",
                    stack_trace=traceback.format_exc()
                )
    else:
        task.increment_infos(
            logger=logger,
            message=f"No tags found for {recipe_link.link}"
        )

    # Save the recipe to the database
    recipe_db.save()
    
def __extract_continente_recipes(logger, task, resume=False):
    """
    Main entry point for extracting recipe data from Continente.

    This function orchestrates the full extraction pipeline for the Continente ETL job:
        1. Initializes the database for recipe extraction.
        2. Extracts recipe links from Continente categories.
        3. Extracts detailed recipe information from the collected links.
        4. Handles task completion, pausing, and cleanup depending on results.

    Args:
        logger (logging.Logger): Logger instance for structured logging throughout the process.
        task (Task): Current ETL task object tracking process state, errors, and metrics.
        resume (bool): Whether to resume from a previous run (avoids DB reset).

    Returns:
        Task: Updated task object with metrics and final state.

    Workflow:
        - Resets thread stop events (for graceful interruption handling).
        - Starts or resumes the recipe database.
        - Pulls all recipe links from Continente.
        - Extracts detailed recipe data from the collected links.
        - Updates and finalizes the ETL task.
    """

    # === INITIALIZATION ========================================================
    # Log the start of the extraction process
    logger.info(f"Initializing {task.type} for all {task.process} from {task.company}...")
    logger.info("")

    # Initialize or resume the recipe database
    logger.info(f"Initializing {task.type} database...")
    task, database = start_db(
        logger=logger,
        task=task,
        models=models_,
        path=EXTRACT_CONTINENTE_RECIPES_DB,
        database_proxy=database_proxy,
        reset=not resume  # Reset DB only when not resuming
    )
    logger.info("")

    # === STEP 1: LINK EXTRACTION ===============================================
    logger.info("Starting recipe link extraction phase...")
    task, l_completed = pull_all_recipes_links(logger, task)

    # === STEP 2: RECIPE EXTRACTION =============================================
    logger.info("Starting detailed recipe extraction phase...")
    task, completed = pull_recipes(logger, task)

    # === STEP 3: SUMMARY & LOGGING =============================================
    logger.info("Extraction Summary:")
    logger.info(f"  - Recipe Links: {task.links}")
    logger.info(f"  - Recipes Extracted: {task.items_processed}")
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

    return task