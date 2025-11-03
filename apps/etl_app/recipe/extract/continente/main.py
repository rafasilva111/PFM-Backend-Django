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
from apps.etl_app.worker_signals import stop_thread_event

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
    
    The function performs the following tasks:
        - Extracts the HTML content of the recipe page.
        - Parses and saves the recipe's title, company, time, difficulty, portions, description, and image.
        - Extracts and saves preparation steps, nutritional information, useful tools, ingredients, and tags.
        - Handles missing or dynamically loaded data gracefully, logging warnings and errors as needed.
        
    Args:
        logger (logging.Logger): Logger instance for logging warnings and errors.
        recipe_link (str): URL of the recipe to extract data from.
        
    """
    
    
    " Initialize variables "
    recipe_db = Recipe()
    
    " Extract html response from the recipe link "
    base_response = requests.get(recipe_link.link, headers=BASE_HEADERS)
    html = BeautifulSoup(base_response.content, 'html.parser')
    
    " Check if page was successfully loaded "
    if base_response.status_code != 200:
        task.increment_errors(
            logger=logger,
            message=f"Failed to load page: {recipe_link.link} with status code: {base_response.status_code}",
            stack_trace=None
        )
        
        return 

    " Source Link "
    recipe_db.link = recipe_link.link

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
    rating_element = html.find('section', attrs={"data-control": "recipeHeader"})
    rating_endpoint = rating_element.get('data-endpoint_averagerating', None)
    if rating_endpoint:
        # Fetch the rating from the endpoint
        rating_url = f"https://feed.continente.pt{rating_endpoint}"
        rating_response = requests.get(rating_url, headers=BASE_HEADERS)
        
        if rating_response.status_code == 200:
            
            # Remove namespace declarations
            rating_data = json.loads(rating_response.text)
            recipe_db.rating = rating_data.get('rating_data',None)
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

    " Image & Video "
    img_containter = html.find('div', class_='recipeHeader__main__right')
    imgs = img_containter.find_all('img')
    video_container = img_containter.find('button', class_='btn-play--red openModalButton')
    
    if imgs:
        image_container = imgs[0]
        
        site_image_source = f"https://feed.continente.pt{image_container['src']}"
        site_image_source = site_image_source.replace("&format=webp","&format=jpg")
        filename = normalize_text(recipe_db.title)
        
        app_image_source = f'{CONTINENTE_RECIPES_IMAGES_FOLDER}/{filename}.png'
        recipe_db.image = app_image_source
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            with open(app_image_source, "wb") as f:
                response = requests.get(site_image_source, headers=headers)
                
                if response.status_code != 200:
                    task.increment_errors(
                        logger=logger,
                        message=f"Failed to download image from {site_image_source}, server responded with status code: {response.status_code}",
                        stack_trace=None
                    )
                else:
                    f.write(response.content)
                
        except Exception as e:
            task.increment_errors(
                logger=logger,
                message=f"Error downloading image from {site_image_source}: {e}",
                stack_trace= traceback.format_exc()
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
        task.increment_errors(
            logger=logger,
            message=f"Error extracting preparation steps from {recipe_link.link}: {e}",
            stack_trace=traceback.format_exc()
        )
        
    
    " Nutrition Information "

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
                energy_kcal=nutrition_helper['Calorias'],
                fat_g=nutrition_helper['Lípidos'],
                saturates_g=nutrition_helper['Saturados'],
                carbohydrates_g=nutrition_helper['Hidratos'],
                sugars_g=nutrition_helper['Açúcares'],
                fiber_g=nutrition_helper['Fibras'],
                protein_g=nutrition_helper['Proteínas'],
                salt_g=nutrition_helper['Sal'],
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

    recipe_db.save()
    
    " Useful tools "
    useful_tools_container = html.find('div', class_='collapsedContentBox')
    
    if not useful_tools_container:
        
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
            
            
    " Ingredients "

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

    " Tags "

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

    recipe_db.save()
    
    
def pull_recipes(logger,task):
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
    

    " Initialize the Control variables "    
    OFFSET = None
    
    logger.info("")
    logger.info("Starting to Pull Recipes")
    logger.info("")
    logger.info(f"Recipe {task.process} is on step {task.step}...")
    logger.info("")
    
    " Get the Threshold Stopping condition"
    from apps.etl_app.models import ThresholdCondition, JobTriggerHistory
    if task.owner_job and task.owner_job.stopping_condition and isinstance(task.owner_job.stopping_condition, ThresholdCondition):
        OFFSET = task.step + task.owner_job.stopping_condition.threshold_value
        
        
    " Check if we are resuming the task, and if so, delete the Recipes that are above the step "
    if task.step != 0:
        instances_to_delete = Recipe.select().where(Recipe.id > task.step)
        for recipe in instances_to_delete:
            recipe.tags.clear()
        Recipe.delete().where(Recipe.id > task.step).execute()
        
    " Extract data from each recipe link "
    for recipe_link in RecipeLink.select().where(RecipeLink.id > task.step):
        
        if stop_thread_event.is_set():
            logger.info("Stop signal detected — no new tasks will be submitted.")
            break

        if OFFSET and recipe_link.id > OFFSET:
            task.owner_job.create_job_trigger_history(
                type=JobTriggerHistory.Type.STOPPING_CONDITION,
                action=JobTriggerHistory.Action.REST,
            )
            logger.info(f"Job Stopping Condition triggered. Paused extraction at {recipe_link.id}...")
            logger.info("")
            return task, False
        
        logger.info(f"Extracting Recipe {recipe_link.id} from {recipe_link.link}")
        extract_data_from_link(logger, task,  recipe_link)
        task.step += 1
        task.items_processed += 1
        task.save()    
    
    " Log the completion of the extraction process "
    logger.info(f"{task.items_processed} Recipes pulled ...")
    logger.info("")
    
    return task, True
    

def pull_all_recipes_links(logger, task):
    
    " Initialize the Control variables "
    stopping_condition_triggered = False
    total_links_counter = 0
    completed = False
    
    " Gets all Recipe's Links from Continente "
    logger.info("")
    logger.info("Starting to Pull Recipe's Links...")
    logger.info("")

    " Base data "
    headers = BASE_HEADERS
    headers.update({
        "content-type": "application/json",
    })

    logger.info(f"Recipe {task.process} is on step {task.step}...")
    logger.info("")
    
    " Get the Threshold Stopping condition"
    from apps.etl_app.models import ThresholdCondition
    stopping_condition_offset = (
        task.step + task.owner_job.stopping_condition.threshold_value
        if task.owner_job and isinstance(task.owner_job.stopping_condition, ThresholdCondition)
        else None
    )
        
    " Check if we are resuming the task, and if so, delete the Recipes that are above the step "
    if task.step != 0:
        RecipeLink.delete().where(RecipeLink.id > task.step).execute()
        
    " Get data "
    page = task.step // PAGE_LINKS_OFFSET + 1
    
    " Clear items based on half filled pages"
    RecipeLink.delete().where(RecipeLink.page >= page).execute()

    
    while True:

        logger.info(f"Added {page * PAGE_LINKS_OFFSET} recipe links from page {page}")
        
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
                "take": PAGE_LINKS_OFFSET,
                "skip": PAGE_LINKS_OFFSET * (page - 1),
            }
        }

        response = requests.post(BASE_GRAPHQL_URL, json=data, headers=headers)

        
        try:
            data_json = response.json()
            recipes = data_json['data']['genericRecipesBy']['recipes']
        except (json.JSONDecodeError, KeyError):
            logger.error("Failed to parse GraphQL response")
            break

        if not recipes:
            logger.info("")
            logger.info("All Recipe Links pulled ...")
            logger.info("")
            completed = True
            break

        for item in recipes:
            " Check stopping condition "
            if stopping_condition_offset and total_links_counter >= stopping_condition_offset:
                logger.info(f"Job Stopping Condition triggered. Paused extraction at {total_links_counter} links...")
                stopping_condition_triggered = True
                break

            " Skip invalid links "
            if not item.get('pageUrl'):
                task.increment_warnings(logger, f"Page URL not found for item: {item}", None)
                continue

            RecipeLink.create(
                link=f"{BASE_URL}{item['pageUrl']}",
                image_link=item['image'],
                base_search_link=BASE_GRAPHQL_URL,
                page=page,
                category=item['category']
            )
            total_links_counter += 1

        if stopping_condition_triggered:
            break

        page += 1

    " Update Task Statistics"
    task.links = RecipeLink.select().count()
    task.save() 
    
    return task, completed
    

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