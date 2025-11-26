# === IMPORTS ==================================================================
# Standard library imports
import json
import pickle
import requests
import unidecode
import traceback
import threading
import concurrent.futures

# Third-party imports
from bs4 import BeautifulSoup

# Custom app imports
from apps.etl_app.functions import (
    start_db, normalize_text, check_if_task_stopped,
    print_header, print_sub_header, print_minor_header
)
from apps.etl_app.recipe.extract.continente.constants import *
from apps.etl_app.recipe.extract.continente.models import (
    database_proxy, Recipe, RecipeLink, NutritionInformation,
    Ingredient, Tag, UsefulTool
)
from apps.etl_app.constants import (
    EXTRACT_CONTINENTE_RECIPES_DB, CONTINENTE_RECIPES_IMAGES_FOLDER
)

# === MODEL CONFIGURATION ======================================================
# Through model for Recipe <-> Tag relationship
recipeTagThrough = Recipe.tags.get_through_model()

# List of models used in the extraction process
models_ = [
    Ingredient, Recipe, RecipeLink, Tag,
    NutritionInformation, Ingredient, UsefulTool, recipeTagThrough
]

# === CONSTANTS ================================================================
BASE_URL = "https://feed.continente.pt"
BASE_GRAPHQL_URL = "https://feed.continente.pt/umbraco/api/GraphQL/Post"
BASE_HEADERS = {
    "cookie": "realUserVerifier=Verified;",
    "content-type": "application/json"
}
COMPANY_NAME = "continente"
PAGE_LINKS_OFFSET = 24
DEFAULT_SLEEP_TIME = 2
MAX_THREADS = 2

def extract_recipe_data(logger, task, recipe_link):
    """
    Extracts and saves detailed recipe data from a given Continente recipe link.

    Workflow:
        1. Loads the recipe page HTML.
        2. Parses and saves core recipe info (title, company, time, difficulty, portions, description).
        3. Fetches and saves rating data if available.
        4. Downloads and saves recipe image and video link.
        5. Extracts and saves preparation steps.
        6. Extracts and saves nutritional information.
        7. Extracts and saves useful tools.
        8. Extracts and saves ingredients.
        9. Extracts and saves tags.
        10. Handles missing or malformed data gracefully, logging warnings/errors.

    Args:
        logger (logging.Logger): Logger instance for warnings/errors.
        task (Task): ETL task instance for error/warning tracking.
        recipe_link (str): URL of the recipe to extract.

    Returns:
        None

    Notes:
        - All errors and warnings are logged and tracked in the task.
        - The function is robust to missing or dynamically loaded data.
        - Images are downloaded and saved locally.
        - Preparation steps and nutrition info are serialized for DB storage.
    """
    # === STEP 1: INITIALIZE RECIPE OBJECT =====================================
    recipe_db = Recipe()

    # === STEP 2: LOAD RECIPE PAGE HTML ========================================
    base_response = requests.get(recipe_link, headers=BASE_HEADERS)
    html = BeautifulSoup(base_response.content, 'html.parser')

    # Check if page loaded successfully
    if base_response.status_code != 200:
        task.increment_errors(
            logger=logger,
            message=f"Failed to load page: {recipe_link} with status code: {base_response.status_code}",
            stack_trace=None
        )
        return

    # === STEP 3: CORE RECIPE INFO =============================================
    recipe_db.link = recipe_link
    recipe_db.title = html.find('h1', class_='title font-2xl').text.strip()
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
    desc_block = html.find('div', class_='detailsTextBlock')
    if desc_block:
        recipe_db.description = desc_block.find('p', class_='font-m').get_text(separator=' ', strip=True)
    else:
        recipe_db.description = None

    # === STEP 4: RATING =======================================================
    rating_element = html.find('section', attrs={"data-control": "recipeHeader"})
    rating_endpoint = rating_element.get('data-endpoint_averagerating', None) if rating_element else None
    if rating_endpoint:
        rating_url = f"{BASE_URL}{rating_endpoint}"
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
            message=f"No rating endpoint found for {recipe_link}"
        )

    # === STEP 5: IMAGE & VIDEO ================================================
    img_container = html.find('div', class_='recipeHeader__main__right')
    imgs = img_container.find_all('img') if img_container else []
    video_container = img_container.find('button', class_='btn-play--red openModalButton') if img_container else None

    if imgs:
        image_container = imgs[0]
        site_image_source = f"{BASE_URL}{image_container['src']}".replace("&format=webp", "&format=jpg")
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
                stack_trace=traceback.format_exc()
            )
    else:
        task.increment_infos(
            logger=logger,
            message=f"No image found for {recipe_link}"
        )

    if video_container:
        recipe_db.video_link = video_container['data-video']
    else:
        task.increment_infos(
            logger=logger,
            message=f"No video found for {recipe_link}"
        )

    # === STEP 6: PREPARATION STEPS ============================================
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
            message=f"Error extracting preparation steps from {recipe_link}: {e}",
            stack_trace=traceback.format_exc()
        )

    # === STEP 7: NUTRITION INFORMATION ========================================
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
                message=f"Error extracting nutritional information from {recipe_link}: {e}",
                stack_trace=traceback.format_exc()
            )
    else:
        task.increment_infos(
            logger=logger,
            message=f"No nutritional information found for {recipe_link}"
        )

    recipe_db.save()

    # === STEP 8: USEFUL TOOLS =================================================
    useful_tools_container = html.find('div', class_='collapsedContentBox')
    if useful_tools_container:
        useful_tools = useful_tools_container.find('ul', class_='textFormat__list')
        if useful_tools:
            try:
                list_items = useful_tools.find_all('li')
                for li_element in list_items:
                    useful_tool_text = li_element.text.strip()
                    useful_tool = UsefulTool(text=useful_tool_text)
                    useful_tool.recipe = recipe_db.id
                    useful_tool.save()
            except Exception as e:
                task.increment_errors(
                    logger=logger,
                    message=f"Error extracting useful tools from {recipe_link}: {e}",
                    stack_trace=traceback.format_exc()
                )
        else:
            task.increment_infos(
                logger=logger,
                message=f"No useful tools found for {recipe_link}"
            )
    else:
        task.increment_infos(
            logger=logger,
            message=f"No useful tools found for {recipe_link}"
        )

    # === STEP 9: INGREDIENTS ==================================================
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
                    message=f"Error extracting ingredient from {recipe_link}: {e}",
                    stack_trace=traceback.format_exc()
                )
    else:
        task.increment_warnings(
            logger=logger,
            message=f"No ingredients found for {recipe_link}"
        )

    # === STEP 10: TAGS ========================================================
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
                    message=f"Error extracting tag from {recipe_link}: {e}",
                    stack_trace=traceback.format_exc()
                )
    else:
        task.increment_infos(
            logger=logger,
            message=f"No tags found for {recipe_link}"
        )

    # === FINALIZE =============================================================
    recipe_db.save()

def extract_recipe(logger, task_id, ingredient_link, stopping_offset):
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
    

    # Early stop check before processing
    if check_if_task_stopped(task):
        logger.debug(f"[Thread {threading.current_thread().name}] Stop signal detected, exiting before processing.")
        return False, False
    
    # Check if the stopping condition offset is reached
    if stopping_offset and ingredient_link.id > stopping_offset:
        task.owner_job.create_job_trigger_history(
            type=JobTriggerHistory.Type.STOPPING_CONDITION,
            action=JobTriggerHistory.Action.REST,
        )
        logger.info(f"[Thread {threading.current_thread().name}] Stopping condition reached at Recipe Link ID {ingredient_link.id}.")
        return False, True

    # Early stop check inside the retry loop
    if check_if_task_stopped(task):
        logger.debug(f"[Thread {threading.current_thread().name}] Stop signal detected mid-processing, exiting.")
        return False, False


    # Log the start of the extraction process
    logger.info(f"[Thread {threading.current_thread().name}] Processing Recipe Link ID {ingredient_link.id} from {ingredient_link.link}.")
    
    # Extract ingredient data from the link
    extract_recipe_data(logger, task, ingredient_link.link)
    return True, False



def extract_recipes(logger,task,threads=MAX_THREADS):
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
    
    # === INITIALIZATION ========================================================
    # Initialize control variables
    stopping_condition_triggered = False
    total_processed = 0
    completed = False
    
    # Log the start of the extraction process
    print_sub_header(logger,"Starting Parallel Recipe Extraction")
    
    # === STEP 1: COMPUTE STOPPING OFFSET =======================================
    # Compute stopping offset if a threshold condition is defined
    from apps.etl_app.models import ThresholdCondition, JobTriggerHistory
    OFFSET = None
    if (
        task.owner_job
        and task.owner_job.stopping_condition
        and isinstance(task.owner_job.stopping_condition, ThresholdCondition)
    ):
        OFFSET = task.step + task.owner_job.stopping_condition.threshold_value
        
        
    # === STEP 2: RETRIEVE INGREDIENT LINKS =====================================
    # If resuming a partial task, delete already-processed records beyond last step
    if task.step != 0:
        instances_to_delete = Recipe.select().where(Recipe.id > task.step)
        for recipe in instances_to_delete:
            recipe.tags.clear()
        Recipe.delete().where(Recipe.id > task.step).execute()
        
    # Retrieve ingredient links from the database, starting from the last processed step
    recipe_links =  RecipeLink.select().where(RecipeLink.id > task.step)
    
    # Check if there are any recipes to process
    total_recipes = recipe_links.count()
    if total_recipes == 0:
        logger.info(f"No {task.process} found to {task.type}.")
        return task, True
    
    # Log recipes to process
    logger.info(f"Found {total_recipes} {task.process} to {task.type}.")
    logger.info("")
    
        
    # === STEP 3: PROCESS LINKS IN PARALLEL =====================================
    # Use a ThreadPoolExecutor for parallel processing
    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
        futures = []

        # Submit tasks for each ingredient link
        for link in recipe_links:
            # Check for stop signal before submitting new tasks
            if check_if_task_stopped(task):
                logger.info("Stop signal detected — no new tasks will be submitted.")
                break
            futures.append(executor.submit(extract_recipe, logger, task.id, link, OFFSET))

        try:
            # Process completed futures as they finish
            for future in concurrent.futures.as_completed(futures):
                # Check for stop signal during processing
                if check_if_task_stopped(task):
                    logger.info("Stop signal detected — waiting for running threads to finish...")
                    break

                try:
                    # Retrieve the result of the future
                    result, stopping_condition_triggered = future.result()
                except Exception as e:
                    # Log any exceptions raised during processing
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
            
            # Determine if the process completed successfully
            if not (stopping_condition_triggered or check_if_task_stopped(task)):
                completed = True
                
    # === STEP 4: LOG FINAL STATISTICS ==========================================
    logger.info("")
    print_sub_header(logger,"Parallel Ingredient Extraction Completed")

    return task, completed
    

def extract_recipes_links(logger, task):
    
    # === INITIAL SETUP ========================================================
    # Initialize control variables
    stopping_condition_triggered = False
    total_links_counter = 0
    completed = False
    
    # Log the start of the extraction process
    print_sub_header(logger, "Starting Recipe Link Extraction")
    
    # === STEP 1: DETERMINE STOPPING CONDITION & TASK RESUMPTION ================
    from apps.etl_app.models import ThresholdCondition
    from apps.etl_app.models import ThresholdCondition
    OFFSET = None
    if (
        task.owner_job
        and task.owner_job.stopping_condition
        and isinstance(task.owner_job.stopping_condition, ThresholdCondition)
    ):
        OFFSET = task.step + task.owner_job.stopping_condition.threshold_value
        
    # If resuming a partial task, delete already-processed records beyond last step
    if task.step != 0:
        RecipeLink.delete().where(RecipeLink.id > task.step).execute()
    
    # Clear records from partial pages if resuming 
    page = task.step // PAGE_LINKS_OFFSET + 1
    RecipeLink.delete().where(RecipeLink.page >= page).execute()
        
    # === STEP 2: PROCCESS LINKS ========================================
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

        response = requests.post(BASE_GRAPHQL_URL, json=data, headers=BASE_HEADERS)

        
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
            # Check stopping condition
            if OFFSET and total_links_counter >= OFFSET:
                logger.info("")
                logger.info(f"Stopping condition reached at {total_links_counter} links.")
                logger.info("")
                stopping_condition_triggered = True
                break

            # Skip invalid links
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

    # === STEP 3: FINALIZE JOB ================================================
    task.links = RecipeLink.select().count()
    task.save() 
    
    print_sub_header(logger, "Recipe Link Extraction Completed")
    
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
    print_header(logger, f"{'Resuming' if resume else 'Starting'} {task.type} for all {task.process} from {task.company.name}.")
    logger.info("")

    # Initialize or resume the recipe database
    task, database = start_db(
        logger=logger,
        task=task,
        models=models_,
        path=EXTRACT_CONTINENTE_RECIPES_DB,
        database_proxy=database_proxy,
        reset=not resume  # Reset DB only when not resuming
    )
    
    # Initialize special properties
    task_properties = task.properties
    threads = task_properties.get("Threads", MAX_THREADS)
    logger.info("Task Properties:")
    logger.info(f"  - Threads: {threads}")
    logger.info("")

    # === STEP 1: LINK EXTRACTION ===============================================
    task, l_completed = extract_recipes_links(logger, task)

    # === STEP 2: RECIPE EXTRACTION =============================================
    task, completed = extract_recipes(logger, task, threads)

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
    logger.info("")
    
    return task