# === Imports ===
import threading
import json
from playhouse.shortcuts import model_to_dict
import google.generativeai as genai
from peewee import OperationalError
import concurrent.futures

# === Custom Functions and Constants ===
from apps.etl_app.functions import (
    start_db,
    check_if_task_stopped,
    check_task_stopping_condition,
    start_sub_db,
    strip_markdown_json,
    print_header,
    print_sub_header,
    retry_db_operation,
)
from apps.etl_app.constants import TRANSFORM_CONTINENTE_RECIPES_DB, eu_reference_intake
from apps.etl_app.etl.extract.recipe.continente.models import (
    database_proxy as database_proxy_E,
    Recipe as Recipe_E,
    RecipeLink as RecipeLink_E,
    NutritionInformation as NutritionInformation_E,
    Ingredient as Ingredient_E,
    Tag as Tag_E,
    UsefulTool as UsefulTool_E,
)
from apps.etl_app.etl.transform.recipe.models import (
    database_proxy,
    Recipe as Recipe_T,
    NutritionInformation as NutritionInformation_T,
    Ingredient as Ingredient_T,
    Tag as Tag_T,
    IngredientQuantity as IngredientQuantity_T,
    UsefulTool as UsefulTool_T,
)
from apps.etl_app.etl.transform.recipe.continente.functions import (
    normalize_time,
    normalize_portion,
    normalize_quantity,
)
from apps.etl_app.decorators import retry_on_db_lock
import traceback
# === Through Models for M2M Relationships ===
recipeTagThrough_E = Recipe_E.tags.get_through_model()
recipeTagThrough_T = Recipe_T.tags.get_through_model()

# === Model Lists ===
extract_models_ = [
    Recipe_E,
    RecipeLink_E,
    NutritionInformation_E,
    Ingredient_E,
    Tag_E,
    UsefulTool_E,
    recipeTagThrough_E,
]
transform_models_ = [
    Recipe_T,
    Ingredient_T,
    Tag_T,
    IngredientQuantity_T,
    NutritionInformation_T,
    UsefulTool_T,
    recipeTagThrough_T,
]

# === Configuration ===
MAX_THREADS = 2


# === AI Prompt Template ===
# Will be set later with actual input data
input_data = None  

PROMPT_TEMPLATE = """
Act as an expert in parsing and normalizing recipe ingredients to make them suitable for streamlined grocery shopping.

Given the following input JSON object, extract and normalize:
- The quantity as a float in `quantity_normalized`.
- The measurement unit in Portuguese in `units_normalized` (e.g., "unidade", "grama", "ml").
- The mesaurement should also be shortened for example "grama" to "g", "mililitro" to "ml", "unidade" to "unid.".
- If no clear measurement unit is provided, use "q.b.".
- The cleaned and identifiable name of the ingredient in `ingredient_name`.
- If there's "fatias" in ingredient name assume it as units and remove and the name of the ingredient should be the item after "de" or "do" (e.g., "fatias de queijo" should become "queijo").
- Do the same for embala

You should also maintain the original `id` from the input and as int.

## Example Input:
[
  {{
    "id": 22817,
    "quantity_original": "Casca de 1 lima",
    "quantity_tempered": "casca de 1 lima",
    "quantity_normalized": None,
    "units_normalized": None,
    "extra_quantity": None,
    "extra_units": None,
    "ingredient": {{
      "id": 245,
      "name": "Unknown Ingredient"
    }}
  }}
]

## Example Output:
{{
    22817: {{
    "quantity_normalized": 1.0,
    "units_normalized": "unidade",
    "ingredient_name": "lima"
    }}
}}

---

Now, here's the actual input to process:

{input_data}

Only return the JSON output. No explanation.
"""

@retry_on_db_lock
def transform_recipe(logger, task, instance, stopping_offset, db):
    """
    Transforms a single extracted recipe into the normalized format.

    Workflow:
        1. Checks for stop signal before processing.
        2. Logs the start of transformation for the recipe.
        3. Normalizes recipe time and portion information.
        4. Creates and saves the transformed Recipe_T instance.
        5. Processes and attaches tags to the recipe.
        6. Processes and attaches useful tools to the recipe.
        7. Normalizes and attaches nutrition information if available.
        8. Processes and normalizes each ingredient:
            - Normalizes quantity and units.
            - Handles missing/unknown ingredients.
            - Creates and saves IngredientQuantity_T and Ingredient_T instances.
        9. Returns status flags for completion and stopping condition.

    Args:
        logger (logging.Logger): Logger instance for structured logging.
        task (Task): Task model instance tracking the job's progress, steps, and statistics.
        recipe (Recipe_E): Extracted recipe instance to transform.

    Returns:
        tuple: (success: bool, stopping_condition_triggered: bool)
    """
    from apps.etl_app.models import StoppingConditionTriggered
    
    # === STEP 1: STOP SIGNAL CHECK =============================================
    if check_if_task_stopped(task):
        logger.debug(f"[Thread {threading.current_thread().name}] Stop signal detected, exiting before processing.")
        return False, True

    # Check if the stopping condition offset is reached
    if check_task_stopping_condition(task, stopping_offset):
        logger.info(f"[Thread {threading.current_thread().name}] Stopping condition reached at Recipe ID {instance.id}.")
        return False, True
    try:
        with db.atomic():
            # === STEP 2: LOG START =====================================================
            logger.info(f"[Thread {threading.current_thread().name}] Transforming Recipe {instance.id}.")

            # === STEP 3: NORMALIZE TIME & PORTION ======================================
            _time, _time_units = normalize_time(logger, instance.time)
            _portion_lower_bound, _portion_upper_bound, _portion_units = normalize_portion(logger, instance.portion)
            _source_rating = float(instance.rating) if instance.rating else float(0)

            # === STEP 4: CREATE TRANSFORMED instance =====================================
            _instance = Recipe_T(
                company=task.company.name,
                title=instance.title,
                description=instance.description,
                image=instance.image,
                video_link=instance.video_link,
                difficulty=instance.difficulty,
                time=_time,
                time_units=_time_units,
                portion_lower=_portion_lower_bound,
                portion_upper=_portion_upper_bound,
                portion_units=_portion_units,
                source_rating=_source_rating,
                source_link=instance.link,
                preparation=instance.preparation
            )
            _instance.save()

            # === STEP 5: PROCESS TAGS ==================================================
            for tag in instance.tags:
                _tag, created = Tag_T.get_or_create(text=tag.text)
                if created:
                    _tag.save()
                _tag.recipe.add(_instance)
                _tag.save()

            # === STEP 6: PROCESS USEFUL TOOLS ==========================================
            for useful_tool in instance.useful_tools:
                _useful_tool = UsefulTool_T()
                _useful_tool.text = useful_tool.text
                _useful_tool.recipe = _instance
                _useful_tool.save()

            # === STEP 7: PROCESS NUTRITION INFORMATION =================================
            if instance.nutrition_information:
                _energy_perc = round((float(instance.nutrition_information.energy_kcal) / eu_reference_intake["energy_kcal"]) * 100, 1)
                _carbohydrates_perc = round((float(instance.nutrition_information.carbohydrates_g) / eu_reference_intake["carbohydrates_g"]) * 100, 1)
                _salt_perc = round((float(instance.nutrition_information.salt_g) / eu_reference_intake["salt_g"]) * 100, 1)
                _sugar_perc = round((float(instance.nutrition_information.sugars_g) / eu_reference_intake["sugars_g"]) * 100, 1)
                _fat_perc = round((float(instance.nutrition_information.fat_g) / eu_reference_intake["fat_g"]) * 100, 1)
                _saturates_perc = round((float(instance.nutrition_information.saturates_g) / eu_reference_intake["saturates_g"]) * 100, 1)
                _protein_perc = round((float(instance.nutrition_information.protein_g) / eu_reference_intake["protein_g"]) * 100, 1)

                _nutrition_information = NutritionInformation_T(
                    energy_kcal=instance.nutrition_information.energy_kcal,
                    energy_perc=_energy_perc,
                    carbohydrates_g=instance.nutrition_information.carbohydrates_g,
                    carbohydrates_perc=_carbohydrates_perc,
                    sugars_g=instance.nutrition_information.sugars_g,
                    sugars_perc=_sugar_perc,
                    fat_g=instance.nutrition_information.fat_g,
                    fat_perc=_fat_perc,
                    saturates_g=instance.nutrition_information.saturates_g,
                    saturates_perc=_saturates_perc,
                    protein_g=instance.nutrition_information.protein_g,
                    protein_perc=_protein_perc,
                    salt_g=instance.nutrition_information.salt_g,
                    salt_perc=_salt_perc,
                    fiber_g=instance.nutrition_information.fiber_g
                )
                _nutrition_information.save()
                _instance.nutrition_information = _nutrition_information
                _instance.save()

            # === STEP 8: PROCESS INGREDIENTS ===========================================
            for ingredient in instance.ingredients:
                _ingredient_quantity = IngredientQuantity_T()
                _ingredient_quantity.quantity_original = ingredient.text
                (
                    _ingredient_quantity.quantity_tempered,
                    _ingredient_quantity.units_normalized,
                    _ingredient_quantity.quantity_normalized,
                    _ingredient_quantity.extra_quantity,
                    _ingredient_quantity.extra_units,
                    _ingredient
                ) = normalize_quantity(logger, task, ingredient.text)
                _ingredient_quantity.recipe = _instance

                # Handle missing/unknown ingredient
                if _ingredient is None:
                    task.increment_warnings(
                        logger=logger,
                        message=f"Transformation of Ingredient Quantity ({_ingredient_quantity.quantity_original}) led to a None Ingredient."
                    )
                    _instance.valid = False
                    _instance.save()
                    _ingredient = "Unknown Ingredient"

                _ingredient, created = Ingredient_T.get_or_create(name=_ingredient)
                _ingredient_quantity.ingredient = _ingredient
                _ingredient_quantity.save()
            
            # === STEP 9: FINAL STOP SIGNAL CHECK ======================================
            # Check for stop signal or stopping condition before finalizing writes.
            # ( We do this to prevent writes if a stop is requested during processing. )
            if check_if_task_stopped(task) or check_task_stopping_condition(task, stopping_offset):
                logger.info(f"[Thread {threading.current_thread().name}] Stop or stopping condition detected after processing Recipe ID {task.step}. Rolling back.")
                raise StoppingConditionTriggered()
                
            return True, False
        
    except StoppingConditionTriggered:
        # Peewee automatically rolls back the transaction
        return False, True

    except Exception as e:
        # === STEP 9: HANDLE EXCEPTIONS AND WARNINGS =============================
        task.increment_errors(
            logger=logger,
            message=f"Failed to transform ingredient. Instance: {instance.id}    Error: {e}",
            stack_trace=traceback.format_exc()
        )
        return False, False
    

def transform_recipes(logger, task, threads, database):
    """
    Transform extracted recipes into normalized format using parallel processing.

    This function orchestrates the transformation of all extracted recipes from raw data
    into a standardized format suitable for the application. It leverages a thread pool
    to perform parallel transformation, improving efficiency for large recipe datasets.

    Workflow:
        1. Initializes control variables and computes the stopping offset based on job configuration.
        2. Handles task resumption by cleaning up previously processed data beyond the last step.
        3. Retrieves extracted recipes from the database, starting from the current step.
        4. Submits transformation tasks to a thread pool executor for parallel processing.
        5. Monitors for stop signals to gracefully halt new task submissions and waits for running threads.
        6. Updates the task's progress, including the number of processed items, and handles stopping conditions.
        7. Cleans up resources and provides comprehensive logging of the transformation process.

    Args:
        logger (logging.Logger): Logger instance for structured logging.
        task (Task): Task model instance tracking the job's progress, steps, and statistics.
        resume (bool): Whether to resume from a previous run (cleans up partial data).
        max_threads (int, optional): Maximum number of threads to use. Defaults to 2.

    Returns:
        tuple: A tuple containing:
            - task (Task): Updated task instance with progress metrics.
            - completed (bool): True if all recipes were processed, False otherwise.

    Notes:
        - The function respects stop signals to allow graceful interruption.
        - Supports resumption by cleaning up data beyond the last processed step.
        - Thread-safe operations ensure data integrity during parallel processing.
        - Comprehensive error handling and logging for debugging and monitoring.
    """

    # === INITIALIZATION ========================================================
    # Initialize control variables
    total_processed = 0
    completed = False
    stopping_condition_triggered = False

    # Log the start of the transform process
    print_sub_header(logger, f"Starting Recipe Transformation")

    # === STEP 1: COMPUTE STOPPING OFFSET =======================================
    # Compute stopping offset if a threshold condition is defined
    from apps.etl_app.models import ThresholdCondition
    OFFSET = None
    if (
        task.owner_job
        and task.owner_job.stopping_condition
        and isinstance(task.owner_job.stopping_condition, ThresholdCondition)
    ):
        OFFSET = task.step + task.owner_job.stopping_condition.threshold_value
        
    # === STEP 2: RETRIEVE RECIPES =====================================
    # If resuming a partial task, delete already-processed records beyond last step
    if task.step != 0:
        instances_to_delete = Recipe_T.select().where(Recipe_T.id > task.step)
        for ingredient in instances_to_delete:
            ingredient.tags.clear()
        Recipe_T.delete().where(Recipe_T.id > task.step).execute()

    # Retrieve recipes to process starting from the current step
    instances_to_process = Recipe_E.select().where(Recipe_E.id > task.step)
    
    # Check if there are any recipes to process
    total_instances = instances_to_process.count()
    if total_instances == 0:
        logger.info(f"No {task.process} found to {task.type}.")
        return task, True

    # Log recipes to process
    logger.info(f"Found {total_instances} {task.process} to {task.type}.")
    logger.info("")

    # === STEP 3: PROCESS RECIPES IN PARALLEL ===================================
    # Declare a set for extra thread safety if needed
    processed_instances = set()
    # Use ThreadPoolExecutor for parallel transformation
    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
        futures = []

        # Submit transformation tasks for each recipe
        for instance in instances_to_process:
            # Check for stop signal before submitting new tasks
            if check_if_task_stopped(task):
                logger.info("Stop signal detected — no new transformation tasks will be submitted.")
                break
            
            # Extra check to avoid duplicate submissions
            if instance.id in processed_instances:
                continue
            processed_instances.add(instance.id)
            
            # Add the future to the list
            futures.append(executor.submit(transform_recipe, logger, task, instance, OFFSET, database))

        try:
            # Process completed futures as they finish
            for future in concurrent.futures.as_completed(futures):
                # Check for stop signal during processing
                if check_if_task_stopped(task):
                    logger.info("Stop signal detected — waiting for running transformation threads to finish...")
                    break

                try:
                    # Retrieve the result of the future
                    result, stopping_condition_triggered = future.result()
                except Exception as e:
                    # Log any exceptions raised during transformation
                    logger.error(f"Future raised an exception: {e}", exc_info=True)
                    continue

                if result:
                    # Update task progress for successfully transformed recipes
                    total_processed += 1
                    task.step += 1
                    task.items_processed += 1
                    task.save()

                if stopping_condition_triggered:
                    logger.info("Stopping condition triggered during recipe transformation.")
                    break

        finally:
            # Ensure proper cleanup of the executor
            executor.shutdown(wait=True, cancel_futures=True)
            # Determine if the process completed successfully
            if not (stopping_condition_triggered or check_if_task_stopped(task)):
                completed = True

    # === STEP 5: LOG COMPLETION STATISTICS =====================================
    logger.info("")
    print_sub_header(logger, "Recipe Transformation Completed")
    
    return task, completed

def tansform_recipes_ai(logger, task):
    
    logger.info("Starting AI Transformation of invalid Recipes...")
    ingredient_dicts = []
    for recipe in Recipe_T.select().where(Recipe_T.valid == False):
        recipe.valid = True
        recipe.save()
        for ingredient in recipe.ingredients:
            if not ingredient.quantity_normalized and not ingredient.units_normalized:
                # Mark the ingredient for AI
                ingredient.ai = True
                ingredient.save()
                
                ingredient_dict = model_to_dict(ingredient, backrefs=True, recurse=True, exclude=[IngredientQuantity_T.recipe])
                ingredient_dicts.append(ingredient_dict)
                
    if not ingredient_dicts:
        logger.info("No invalid recipes found for AI transformation.")
        logger.info("")
        return task
    
    ingredients_json = json.dumps(ingredient_dicts, ensure_ascii=False, indent=4)
   
    # Configure API Key
    genai.configure(api_key="")

    # Create the model
    model = genai.GenerativeModel(model_name="gemini-1.5-flash")

    # Prompt string
    prompt = PROMPT_TEMPLATE.format(input_data=ingredients_json)
    
    # Make the request
    response = model.generate_content(prompt)
    
    # Parse the response
    clean = strip_markdown_json(response.text)
    result = json.loads(clean)
    
    for key, value in result.items():
        
        ingredient_quantity = IngredientQuantity_T.get_or_none(int(key))
        ingredient_quantity.ai = True
        
        if not ingredient_quantity:
            logger.warning(f"Ingredient Quantity with ID {key} not found in the database.")
            continue
        
        ingredient_quantity.quantity_normalized = value.get("quantity_normalized")
        ingredient_quantity.units_normalized = value.get("units_normalized")
        ingredient, created = Ingredient_T.get_or_create(name = value.get("ingredient_name"))
        ingredient_quantity.ingredient = ingredient
        ingredient_quantity.save()
        
    logger.info("")
    
    return task

def __transform_continente_recipes(logger, task, resume):
    """
    Transforms all recipe records from the extraction database into the normalized target format.

    Workflow:
        1. Logs the start or resumption of the transformation process.
        2. Initializes or resumes the transformation and extraction databases.
        3. Configures threading and task properties.
        4. Calculates the total number of recipes expected for transformation.
        5. Transforms extracted recipes in parallel using threads.
        6. Optionally applies AI-based transformations for invalid ingredients.
        7. Logs a summary of the transformation process, including errors and warnings.
        8. Marks the task as finished or paused depending on completion.

    Args:
        logger (logging.Logger): Logger instance for structured logging.
        task (Task): Task object containing metadata and state for the transformation process.
        resume (bool): Flag indicating whether to resume a previous transformation or start anew.

    Returns:
        Task: The updated task object after transformation, with updated status and statistics.
    """
    
    # === INITIALIZATION ========================================================
    print_header(logger, f"{'Resuming' if resume else 'Starting'} {task.type} for all {task.process} from {task.company.name}.")
    logger.info("")

    # Initialize or resume the transformation database
    task, database = start_db(
        logger=logger,
        task=task,
        models=transform_models_,
        path=TRANSFORM_CONTINENTE_RECIPES_DB,
        database_proxy=database_proxy,
        reset=not resume
    )

    # Initialize or resume the extraction database
    task, database = start_sub_db(
        logger=logger,
        task=task,
        models=extract_models_,
        database_proxy=database_proxy_E
    )

    # Configure threading and task properties
    task_properties = task.properties
    threads = task_properties.get("Threads", MAX_THREADS)
    logger.info("Task Properties:")
    logger.info(f"  - Threads: {threads}")
    logger.info("")

    # === STEP 1: TRANSFORMATION ================================================
    task.items_expected = Recipe_E.select().count()
    task.save()

    # Transform extracted recipes in parallel
    task, completed = transform_recipes(logger, task, threads, database)

    # Optionally apply AI-based transformations for invalid ingredients
    # task = tansform_recipes_ai(logger, task)

    # === STEP 2: SUMMARY & LOGGING =============================================
    logger.info("Transformation Summary:")
    logger.info(f"  - Recipes Expected: {task.items_expected}")
    logger.info(f"  - Recipes Processed: {task.items_processed}")
    logger.info("")
    logger.info(f"  - Total Errors: {task.errors}")
    logger.info(f"  - Total Warnings: {task.warnings}")
    logger.info("")

    # === STEP 3: FINALIZATION ==================================================
    if completed:
        task.finish(kill_celery_task=False)
        logger.info("✅ Task successfully completed.")
    else:
        task.pause()
        logger.info("⚠️ Task paused before full completion.")
    logger.info("")

    return task
