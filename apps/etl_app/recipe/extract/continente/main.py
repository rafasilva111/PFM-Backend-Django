" Import necessary libraries and modules "
import json
import pickle
import requests
import unidecode
from bs4 import BeautifulSoup

" Import custom functions and constants "
from apps.etl_app.functions import start_db
from apps.etl_app.recipe.extract.continente.constants import *
from apps.etl_app.recipe.extract.continente.models import database_proxy, Recipe, RecipeLinks, NutritionInformation, Ingredient, Tag, UsefulTool
from apps.etl_app.constants import EXTRACT_CONTINENTE_RECIPES_DB, continente_recipes_images_folder


" Define the through model for Recipe and Tag relationship "
recipeTagThrough = Recipe.tags.get_through_model()

" Define the list of models to be used in the extraction process "
models_ = [Ingredient, Recipe, RecipeLinks, Tag, NutritionInformation, Ingredient, UsefulTool, recipeTagThrough]

" Define constants for the scraping process "
BASE_URL = "https://feed.continente.pt"
BASE_GRAPHQL_URL = "https://feed.continente.pt/umbraco/api/GraphQL/Post"
BASE_HEADERS = {
    "cookie": "realUserVerifier=Verified;",
}
COMPANY_NAME = "continente"
OFFSET = 24
DEFAULT_SLEEP_TIME = 2

def extract_data_from_link(logger, recipe_link):
    """
    Extracts recipe data from a given recipe link and saves it to the database.
    
    The function performs the following tasks:
        - Extracts the HTML content of the recipe page.
        - Parses and saves the recipe's title, company, time, difficulty, portions, description, and image.
        - Extracts and saves preparation steps, nutritional information, useful tools, ingredients, and tags.
        - Handles missing or dynamically loaded data gracefully, logging warnings and errors as needed.
        
    Args:
        logger (logging.Logger): Logger instance for logging warnings and errors.
        recipe_link (str): URL of the recipe to extract data from.
        
    Returns:
        tuple: A tuple containing:
            - warnings (int): Number of warnings encountered during extraction.
            - errors (int): Number of errors encountered during extraction.
    """
    
    
    " Initialize variables "
    __errors = 0
    __warnings = 0    
    recipe_db = Recipe()
    
    " Extract html response from the recipe link "
    base_response = requests.get(recipe_link, headers=BASE_HEADERS)
    html = BeautifulSoup(base_response.content, 'html.parser')

    " Source Link "
    recipe_db.link = recipe_link

    " Title "
    recipe_db.title = html.find('h1', class_='title font-2xl').text.strip()

    " Company  "
    recipe_db.company = COMPANY_NAME

    " Time, Dificulty, Portions "
    infos = []
    attributes_block = html.find('div', class_='attributesBlock')
    if attributes_block:
        attribute_elements = attributes_block.find_all('div', class_='attribute')

        # Loop through each attribute and extract relevant data
        for attribute_element in attribute_elements:
            if attribute_element.find('i')['title'] != "Custo":
                infos.append(attribute_element.find('strong').text.strip())

    recipe_db.time = infos[0]
    recipe_db.difficulty = infos[1]
    recipe_db.portion = infos[2]

    " Description "

    recipe_db.description = html.find('div', class_='detailsTextBlock').find('p', class_='font-m').get_text(
        separator=' ', strip=True)

    " Rating "

    # impossivel fazer pós a info é carregada após a página ser carregada
    # logo não é possível fazer scraping, apenas com selenium :(

    " Image "

    file_storage = unidecode.unidecode(recipe_db.title).replace(" ", "_")
    recipe_steps_raw = html.find('img', class_='image')
    
    image_source_link = RecipeLinks.get(RecipeLinks.link == recipe_link).image_link
    img_source = f'{continente_recipes_images_folder}/{file_storage}.png'
    recipe_db.img = img_source
    try:
        with open(img_source, "wb") as f:
            f.write(requests.get(image_source_link).content)
    except Exception as e:
        logger.error(f"Error extracting preparation steps: {e}")
        __errors += 1

    " Preparation "

    try:
        # Find the <div> element with the specified class name
        recipe_steps_raw = html.find('div', class_='recipeSteps__body')

        preparation = []
        if recipe_steps_raw:
            list_items = recipe_steps_raw.find_all('li')
            section = "main"
            # Loop through each list item and extract the step information
            for li_element in list_items:
                if li_element.has_attr('class'):
                    section = li_element.text.strip()
                else:
                    preparation.append({"step": li_element.find('span').text.replace(".", "").strip(),
                                        "section": section,
                                        "description": li_element.find('p').text.strip()})

        recipe_db.preparation = pickle.dumps(preparation)
    except Exception as e:
        logger.error(f"Error extracting preparation steps: {e}")
        __errors += 1
        
    
    " Nutrition Information "

    nutritional_table_raw = html.find('div', class_='recipeNutricionalTable__table')

    nutrition_helper = {}
    if nutritional_table_raw:
        rows = nutritional_table_raw.find_all('div', class_='recipeNutricionalTable__table__row')

        for row in rows:
            # Find all <p> elements within the row
            item_elements = row.find_all('p', class_='itemValue')

            # Extract and print the nutritional information
            for item_element in item_elements:
                item_title = item_element.find_previous('p', class_='itemTitle').text.strip()
                item_value = item_element.find('strong').text.replace(",", ".").strip()
                nutrition_helper.update({item_title: item_value})

        nutrition_information = NutritionInformation(
            energy_kcal=nutrition_helper['Calorias'],
            energy_perc="0",
            fat_g=nutrition_helper['Lípidos'],
            fat_perc="0",
            saturates_g=nutrition_helper['Saturados'],
            saturates_perc="0",
            carbohydrates_g=nutrition_helper['Hidratos'],
            carbohydrates_perc="0",
            sugars_g=nutrition_helper['Açúcares'],
            sugars_perc="0",
            fiber_g=nutrition_helper['Fibras'],
            protein_g=nutrition_helper['Proteínas'],
            protein_perc="0",
            salt_g=nutrition_helper['Sal'],
            salt_perc="0"
        )
        nutrition_information.save()
        recipe_db.nutrition_information = nutrition_information.id

    else:
        logger.warning("No nutritional information found")
        __warnings += 1
    recipe_db.save()
    
    " Useful tools "
    
    useful_tools = html.find('ul', class_='textFormat__list')
    
    if useful_tools:
        list_items = useful_tools.find_all('li')
        for li_element in list_items:
            useful_tool_text = li_element.text.strip()
            useful_tool = UsefulTool(text=useful_tool_text)
            useful_tool.recipe = recipe_db.id
            useful_tool.save()

    " Ingredients "

    ingredient_list_raw = html.find('div', class_='ingredientList__body')

    if ingredient_list_raw:
        list_items = ingredient_list_raw.find_all('li')

        section = "main"
        for li_element in list_items:
            if li_element.has_attr('class'):
                section = li_element.text.strip()
            else:
                ingredient_text = li_element.text.strip()
                ingredient = Ingredient(text=ingredient_text, section=section)
                ingredient.recipe = recipe_db.id
                ingredient.save()

    " Tags "

    tags_raw = html.find('div', class_='tags')
    if tags_raw:
        tags_tag = tags_raw.find('span', class_='categoryTag')

        if tags_tag:
            tag, created = Tag.get_or_create(text=tags_tag.text.strip())
            tag.save()
            recipe_db.tags.add(tag)

    logger.info("")
    recipe_db.save()
    
    return __errors, __warnings


def pull_recipes(logger,task, max_recipes=-1):
    """
    Extracts recipe data from the Continente website and updates the task statistics.
    This function iterates through recipe links stored in the database, extracts data
    from each link, and updates the task statistics with the number of items processed,
    warnings, and errors encountered during the extraction process.
    Args:
        logger (logging.Logger): Logger instance for logging information, warnings, and errors.
        task (Task): Task object used to track the progress and statistics of the extraction process.
        max_recipes (int, optional): Maximum number of recipes to extract. Defaults to -1, which means no limit.
    Returns:
        None
    """
    
    
    " Initialize the warnings and errors counters "
    task.warnings = 0
    task.errors = 0
    
    OFFSET = None
    
    logger.info("")
    logger.info("Starting to pull Recipes")
    logger.info("")
    logger.info(f"Recipe extraction is on step {task.step}...")
    logger.info("")
    
    " Get the Threshold Stopping condition"
    from apps.etl_app.models import ThresholdCondition, JobTriggerHistory
    if task.owner_job and task.owner_job.stopping_condition and isinstance(task.owner_job.stopping_condition, ThresholdCondition):
        OFFSET = task.step + task.owner_job.stopping_condition.threshold_value
    
    " Check if we are resuming the task, and if so, delete the Recipes that are above the step "
    if task.step != 0:
        recipes_in_db = Recipe.select().count()
        if recipes_in_db > task.step:
            # Delete tasks until step matches recipes_in_db
            tasks_to_delete = Recipe.select().order_by(Recipe.id.desc())
            for t in tasks_to_delete:
                if task.step == recipes_in_db:
                    break
                t.tags.clear()
                t.delete_instance()
                recipes_in_db -= 1
        
    " Extract data from each recipe link "
    for recipe_link in RecipeLinks.select().where(RecipeLinks.id > task.step):
        
        if OFFSET and recipe_link.id > OFFSET:
            task.owner_job.create_job_trigger_history(
                type=JobTriggerHistory.Type.STOPPING_CONDITION,
                action=JobTriggerHistory.Action.REST,
            )
            logger.info(f"Job Stopping Condition triggered. Paused extraction at {recipe_link.id}...")
            logger.info("")
            return task, False
        
        logger.info(f"Extracting Recipe {recipe_link.id} from {recipe_link.link}")
        _errors, _warnings = extract_data_from_link(logger, recipe_link.link)
        task.warnings += _warnings
        task.errors += _errors
        task.step += 1
        task.items_processed += 1
        task.save()    
    
    " Log the completion of the extraction process "
    logger.info(f"{task.items_processed} Recipes pulled ...")
    logger.info("")
    
    return task, False
    

def pull_all_recipes_links(logger, task):
    """
    Extracts all recipe links from the Continente website using a GraphQL API.
    This function retrieves recipe links in a paginated manner and stores them in the database.
    It also updates the task statistics and logs the progress and summary of the extraction process.
    Args:
        logger (logging.Logger): Logger instance for logging information and progress.
        task (Task): Task object to track the progress and statistics of the extraction process.
        continue_mode (bool, optional): If True, resumes from the last processed page. Defaults to False.
    Raises:
        requests.exceptions.RequestException: If there is an issue with the HTTP request.
        KeyError: If the expected keys are missing in the API response.
    Notes:
        - The function uses a GraphQL query to fetch recipe data.
        - The `OFFSET` constant determines the number of recipes fetched per page.
        - The `BASE_HEADERS` and `BASE_URL` constants are used for API requests and constructing recipe links.
        - The function logs warnings and errors encountered during the process.
    Workflow:
        1. Initializes warnings and errors counters.
        2. Logs the start of the extraction process.
        3. Constructs the GraphQL query and sends paginated requests to the API.
        4. Parses the response and saves recipe links to the database.
        5. Updates task statistics and logs the summary of the extraction process.
    """
    
    
    " Initialize the warnings and errors "
    task.warnings = 0
    task.errors = 0
    

    " Gets all Recipe's Links from Continente "
    logger.info("Starting to get all Recipe's Links...")
    logger.info("")

    " Base data "
    headers = BASE_HEADERS
    headers.update({
        "content-type": "application/json",
    })
    page = 1
    

    " Get data "
    page = RecipeLinks.select().count() // OFFSET + 1

    while True:

        logger.info(f"Added {page * OFFSET} recipe links from page {page}")

        data = {
            "query": """
            query genericRecipesBy($showOnlyVideo: String, $preparationType: String, $category: String, $ratingAverage: String, $preparationTime: String, $difficulty: String, $cost: String, $cookingType: String, $authorName: String, $specialNeeds: String, $geographicalOrigin: String, $sort: Int, $take: Int, $skip: Int,
                      ) {
                          genericRecipesBy(
                            showOnlyVideo: $showOnlyVideo, preparationType: $preparationType, category: $category, ratingAverage: $ratingAverage, preparationTime: $preparationTime, difficulty: $difficulty, cost: $cost, cookingType: $cookingType, authorName: $authorName, specialNeeds: $specialNeeds, geographicalOrigin: $geographicalOrigin, sort: $sort, take: $take, skip: $skip,

                            ) {
                                totalCount,
                                recipes{
                                  alias,
                                  id,
                                  authorOrChef {authorName, image},
                                  category,
                                  cookingType,
                                  pageVertical,
                                  geographicalOrigin,
                                  contentName,
                                  imageOrVideo,
                                  image,
                                  preparationTime,
                                  introduction,
                                  numberOfPortions,
                                  difficulty,
                                  pageUrl 
                                }
                              }
                        }
        """,
            "variables": {
                "take": OFFSET,
                "skip": OFFSET * (page - 1),
            }
        }

        response = requests.post(BASE_GRAPHQL_URL, json=data, headers=headers)

        data_json = json.loads(response.content)
        # check if there are more recipes
        if len(data_json['data']['genericRecipesBy']['recipes']) == 0:
            break

        for item in data_json['data']['genericRecipesBy']['recipes']:
            
            # Prevent empty links
            if 'pageUrl' not in item or item['pageUrl'] == '':
                logger.warning(f"Page URL not found for item:")
                logger.warning(f"{item}")
                task.warnings += 1
                continue
            
            
            data_point = RecipeLinks(
                link = f"{BASE_URL}{item['pageUrl']}",
                image_link = item['image'],
                base_search_link = BASE_GRAPHQL_URL,
                page = page,
                category = item['category'],
            )
            data_point.save()

        page += 1

    " Update Task Statistics"
    task.links = RecipeLinks.select().count()
    task.save()
    
    " Log the completion of the extraction process "
    logger.info("")
    logger.info("All Recipe's Links pulled ...")
    logger.info("")
    
    return task
    

def __extract_continente_recipes(logger, task, resume = False):
    
    " Log the start of the extraction process"
    logger.info(f"Initializing the {task.type} all recipes from {task.company}...")
    
    " Initialize the warnings and errors "
    if resume:
        task.errors = 0
        task.warnings = 0

    " Starts the db "
    logger.info("Initializing Extract database ...")
    task, database = start_db(
        logger=logger,
        task=task,
        models=models_,
        path=EXTRACT_CONTINENTE_RECIPES_DB,
        database_proxy=database_proxy,
        reset=not resume # we want to reset the database if we are not resuming
    )
    logger.info("")
    
    
    " Get all recipes links "
    # We only want to pull recipes links if step is 0
    # This is because we want to pull all recipes links only once
    if task.step == 0:
        task = pull_all_recipes_links(logger, task)

    " Pulls recipes from above links "
    task, completed = pull_recipes(logger, task)
    
    
    " Log the completion of the extraction process "
    logger.info("Summary:")
    logger.info(f"Recipe Links Found: {task.links}")
    logger.info(f"Recipes: {task.items_processed}")
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
