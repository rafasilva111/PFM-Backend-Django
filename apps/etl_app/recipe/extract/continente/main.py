" Import necessary libraries and modules "
import json
import pickle
import requests
import unidecode
from bs4 import BeautifulSoup

" Import custom functions and constants "
from apps.etl_app.functions import start_extract_db
from apps.etl_app.recipe.extract.continente.constants import *
from apps.etl_app.recipe.extract.continente.models import database_proxy, Recipe, RecipeLinks, NutritionInformation, Ingredient, Tag, UsefulTool
from apps.etl_app.constants import extract_continente_recipes_db, continente_recipes_images_folder


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
    warnings = 0
    errors = 0
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
        errors += 1

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
        errors += 1
        
    
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

        nutrition_information = NutritionInformation(energia=nutrition_helper['Calorias'],
                                                     energia_perc="0",
                                                     gordura=nutrition_helper['Lípidos'],
                                                     gordura_perc="0",
                                                     gordura_saturada=nutrition_helper['Saturados'],
                                                     gordura_saturada_perc="0",
                                                     hidratos_carbonos=nutrition_helper['Hidratos'],
                                                     hidratos_carbonos_acucares=nutrition_helper['Açúcares'],
                                                     hidratos_carbonos_acucares_perc="0",
                                                     fibra=nutrition_helper['Fibras'],
                                                     fibra_perc="0",
                                                     proteina=nutrition_helper['Proteínas'],
                                                     proteina_perc="0",
                                                     sal=nutrition_helper['Sal'],
                                                     sal_perc="0")
        nutrition_information.save()
        recipe_db.nutrition_information = nutrition_information.id

    else:
        logger.warning("No nutritional information found")
        warnings += 1
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
            tag, created = Tag.get_or_create(title=tags_tag.text.strip())
            tag.save()
            recipe_db.tags.add(tag)

    logger.info("")
    recipe_db.save()
    
    return warnings, errors


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
    warnings = 0
    errors = 0
    
    logger.info("")
    logger.info("Starting to pull Recipes")
    
    total_recipes = Recipe.select().count()
    
    logger.info(f"Found {total_recipes} recipes on DB...")
    logger.info("")
    

    max_ingredients = -1


    counter = 0
    for ingredient_link in RecipeLinks.select().where(RecipeLinks.id > total_recipes):
        if max_ingredients != -1 and counter == max_ingredients:
            break
        else:
            counter += 1

        logger.info(f"Extracting Recipe {ingredient_link.id} from {ingredient_link.link}")

        warnigs_, errors_ = extract_data_from_link(logger, ingredient_link.link)
        warnings += warnigs_
        errors += errors_
    
    " Update Task Statistics"
    task.items = Recipe.select().count()
    task.items_warnings = warnings
    task.items_errors = errors
    task.save()
    
    " Log the completion of the extraction process "
    logger.info("All Recipes pulled ...")
    logger.info("")
    logger.info("Pull Recipes summary:")
    logger.info(f"{task.print_items_summary()}")
    logger.info("")
    

def pull_all_recipes_links(logger, task, continue_mode=False):
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
    warnings = 0
    errors = 0
    

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
    if continue_mode:
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
    task.links_warnings = warnings
    task.links_errors = errors
    task.save()
    
    " Log the completion of the extraction process "
    logger.info("All Recipe's Links pulled ...")
    logger.info("")
    logger.info("Pull Recipe's Links summary:")
    logger.info(f"{task.print_links_summary()}")
    logger.info("")
    

def __extract_continente_recipes(logger, task, continue_mode):
    
    " Log the start of the extraction process"
    logger.info(f"Extracting all recipes from {task.company}...")
    logger.info("")
    

    " Starts the db "
    start_extract_db(
        logger=logger,
        task=task,
        models=models_,
        path=extract_continente_recipes_db,
        database_proxy=database_proxy
        )
    
    
    " Get all recipes links "
    pull_all_recipes_links(logger, task, continue_mode=continue_mode)
    

    " Pulls recipes from above links "
    pull_recipes(logger, task)
    
    
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
