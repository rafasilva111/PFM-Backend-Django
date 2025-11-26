# === Imports ===
import threading
import json
import math
import re
import traceback
from fractions import Fraction
from playhouse.shortcuts import model_to_dict
import google.generativeai as genai
import concurrent.futures

# === Custom Functions and Constants ===
from apps.etl_app.constants import TRANSFORM_CONTINENTE_RECIPES_DB, eu_reference_intake
from apps.etl_app.functions import (
    start_db,
    start_sub_db,
    strip_markdown_json,
    check_if_task_stopped,
    print_header,
    print_sub_header,
)
from apps.etl_app.ingredient.extract.continente.models import (
    database_proxy as database_proxy_E,
    Ingredient as Ingredient_E,
    IngredientLink as IngredientLink_E,
    Tag as Tag_E,
    Image as Image_E,
)
from apps.etl_app.ingredient.transform.models import (
    database_proxy,
    Ingredient as Ingredient_T,
    IngredientLink as IngredientLink_T,
    Tag as Tag_T,
    Image as Image_T,
)
from apps.etl_app.recipe.transform.continente.functions import (
    normalize_time,
    normalize_portion,
    normalize_quantity,
)
from apps.ingredient_app.models import Ingredient

# === Through Models for M2M Relationships ===
recipeTagThrough_E = Ingredient_E.tags.get_through_model()
recipeTagThrough_T = Ingredient_T.tags.get_through_model()

# === Model Lists ===
extract_models_ = [Ingredient_E, IngredientLink_E, Tag_E, Image_E, recipeTagThrough_E]
transform_models_ = [Ingredient_T, IngredientLink_T, Tag_T, Image_T, recipeTagThrough_T]

# === Configuration ===
MAX_THREADS = 2

def repair_with_language_model(s: str):
    if "�" not in s:
        return s
    
    from symspellpy import SymSpell, Verbosity
    from django.conf import settings

    # Criar SymSpell
    sym_spell = SymSpell(max_dictionary_edit_distance=2, prefix_length=7)

    # Carregar dicionário português (word frequency list)
    sym_spell.load_dictionary(f"{settings.BASE_DIR}/pt_freq_dictionary.txt", term_index=0, count_index=1)

    # Corrigir palavra
    term = "M�nima"
    suggestions = sym_spell.lookup(term, Verbosity.CLOSEST, max_edit_distance=2)
    print(suggestions[0].term) 


     
def normalize_size(ingredient):
    size = ingredient.size
    
    portions = None
    portion_unit = None
    portion_size = None
    portion_price = ingredient.price_per_unit
    
    bulk_price = ingredient.price_bulk
    bulk_unit = ingredient.bulk_unit
    
    size_type = None
    minimum_size_for_bulk = None
    
    # GRATIS
    #emb. 1 kg (1 un)

    
    if "  " in size:
        size = size.replace("  ", " ")
    
    if " x " in size and not " un x " in size:
        size = size.replace(" x ", " un x ")
    
    if "€" in portion_price:
        portion_price = portion_price.replace("€", "").strip()
    
    if " (aprox.)" in size:
        size = size.replace(" (aprox.)", "")
        
    if " (Leve 3 pague 2)" in size:
        size = size.replace(" (Leve 3 pague 2)", "")
        
    # Original pattern: emb.<number> gr
    pattern = r"(emb\.)(\d+(\.\d+)?\s+gr)"

    # Replacement: add a space after 'emb.'
    replacement = r"\1 \2"
    size = re.sub(pattern, replacement, size)
    
    if "emb. " in size:
        size = size.replace("emb. ", "")
    
    # SWAP prices if unit is "un"
    if bulk_unit == "un":
        helper = bulk_price
        bulk_price = portion_price
        portion_price = helper
        bulk_unit = "kg"
    
    # BULK
    if "Quant. Mínima = " in size:
        minimum_size_for_bulk = size.replace("Quant. Mínima = ", "")
        size_type = Ingredient.SizeType.BULK
        size = None
        return size, portions, portion_price, portion_size, portion_unit, bulk_price, bulk_unit, size_type, minimum_size_for_bulk
    
    # PACKAGE
    size_type = Ingredient.SizeType.PACKAGE
    
    if " un x " in size:
        bonus_size = 0
        bonus_unit = None
        
        if " (" and not "gr (" in size:
            size = size.replace(" (", "gr (")
            
        # Pattern: + <number> <unit> GRÁTIS
        pattern = re.compile(
            r'\+\s*(?P<bonus_size>\d+(?:[.,]\d+)?)\s*(?P<bonus_unit>[a-zA-Z]+)\s*GRÁTIS',
            re.IGNORECASE
        )

        match = pattern.search(size)
        if match:
            bonus_size = float(match.group('bonus_size').replace(',', '.'))
            bonus_unit = match.group('bonus_unit')
            
            
        # Pattern: <number> un x <number> <unit> (<number> <unit>)
        pattern = re.compile(
            r'(?P<units>\d+(?:[.,]\d+)?)\s*un\s*x\s*'            # <number> un x
            r'(?P<unit_size>\d+(?:[.,]\d+)?)\s*(?P<unit>[a-zA-Z]+)\s*'  # <number> <unit>
            r'\(\s*(?P<total_size>\d+(?:[.,]\d+)?)\s*(?P<total_unit>[a-zA-Z]+)\s*\)',  # (<number> <unit>)
            re.IGNORECASE
        )

        matches = pattern.search(size)
        
        if matches:
            portions = float(matches.group('units').replace(',', '.'))
            portion_size = float(matches.group('unit_size').replace(',', '.'))
            portion_unit = matches.group('unit')
            size = f"{matches.group('total_size')} {matches.group('total_unit')}"
            
            if bonus_size > 0 and bonus_unit:
                if bonus_unit == "un":
                    total_portions = portions + bonus_size
                    size = f"{total_portions * portion_size} {portion_unit}"
                elif portion_unit == bonus_unit:
                    total_size = (portions * portion_size) + bonus_size
                    size = f"{total_size} {portion_unit}"
                elif portion_unit == "gr" and bonus_unit == "kg":
                    bonus_unit_grams = bonus_size * 1000
                    total_size = (portions * portion_size) + bonus_unit_grams
                    size = f"{total_size} {portion_unit}"
                elif portion_unit == "kg" and bonus_unit == "gr":
                    bonus_unit_kg = bonus_size / 1000
                    total_size = (portions * portion_size) + bonus_unit_kg
                    size = f"{total_size} {portion_unit}"
                elif portion_unit == "ml" and bonus_unit == "l":
                    bonus_unit_ml = bonus_size * 1000
                    total_size = (portions * portion_size) + bonus_unit_ml
                    size = f"{total_size} {portion_unit}"
                elif portion_unit == "l" and bonus_unit == "ml":
                    bonus_unit_l = bonus_size / 1000
                    total_size = (portions * portion_size) + bonus_unit_l
                    size = f"{total_size} {portion_unit}"
                else:
                    print()
            else:
                size = f"{portions * portion_size} {portion_unit}"
            
            return size, portions, portion_price, portion_size, portion_unit, bulk_price, bulk_unit, size_type, minimum_size_for_bulk
        
        # Pattern: <number> un x <number> <unit>
        pattern = re.compile(
            r'(?P<units>\d+(?:[.,]\d+)?)\s*un\s*x\s*'            # <number> un x
            r'(?P<unit_size>\d+(?:[.,]\d+)?)\s*(?P<unit>[a-zA-Z]+)\s*',  # <number> <unit>
            re.IGNORECASE
        )
        matches = pattern.search(size)
        
        if matches:
            portions = int(float(matches.group('units')))
            portion_size = float(matches.group('unit_size'))
            portion_unit = matches.group('unit')
            
            if bonus_size > 0 and bonus_unit:
                if bonus_unit == "un":
                    portions = portions + bonus_size
                    size = f"{portions * portion_size} {portion_unit}"
                elif portion_unit == bonus_unit:
                    total_size = (portions * portion_size) + bonus_size
                    size = f"{total_size} {portion_unit}"
                elif portion_unit == "gr" and bonus_unit == "kg":
                    bonus_unit_grams = bonus_size * 1000
                    total_size = (portions * portion_size) + bonus_unit_grams
                    size = f"{total_size} {portion_unit}"
                elif portion_unit == "kg" and bonus_unit == "gr":
                    bonus_unit_kg = bonus_size / 1000
                    total_size = (portions * portion_size) + bonus_unit_kg
                    size = f"{total_size} {portion_unit}"
                elif portion_unit == "ml" and bonus_unit == "l":
                    bonus_unit_ml = bonus_size * 1000
                    total_size = (portions * portion_size) + bonus_unit_ml
                    size = f"{total_size} {portion_unit}"
                elif portion_unit == "l" and bonus_unit == "ml":
                    bonus_unit_l = bonus_size / 1000
                    total_size = (portions * portion_size) + bonus_unit_l
                    size = f"{total_size} {portion_unit}"
                else:
                    print()
            else:
                size = f"{portions * portion_size} {portion_unit}"
                
                
            return size, portions, portion_price, portion_size, portion_unit, bulk_price, bulk_unit, size_type, minimum_size_for_bulk
    

           
    if " = " in size:
        pattern = re.compile(
            r'^\s*(\d+(?:/\d+)?)\b.*?=\s*([\d]+(?:[.,]\d+)?)\s*([a-zA-Z]+)', 
            re.IGNORECASE
        )
        matches = pattern.search(size)
        
        if matches:
           portions = float(Fraction(matches.group(1))) if '/' in matches.group(1) else matches.group(1)
           size = f"{matches.group(2)} {matches.group(3)}"
    
       
    if " un)" in size:
        matches = re.search(r'\((\d+)\s*un\)', size)
        if matches:
            portions = matches.group(1)
            size = size.replace(f" ({portions} un)", "")
    
    # Pattern: <number> un (<number> <unit>)
    if " un (" in size:
        pattern = re.compile(
            r'(\d+)\s*un\s*\(\s*([\d.,]+)\s*([a-zA-Z]+)\s*\)',
            re.IGNORECASE
        )
        matches = pattern.search(size)
        
        if matches:
            portions = matches.group(1)
            size = f"{matches.group(2)} {matches.group(3)}"
            return size, portions, portion_price, portion_size, portion_unit, bulk_price, bulk_unit, size_type, minimum_size_for_bulk

    # Pattern: <number> un
    if " un" in size:
        pattern = pattern = re.compile(
            r'(?P<units>\d+(?:[.,]\d+)?)\s*un\b',
            re.IGNORECASE
        )
        match = pattern.search(size)
        if match:
            portions = float(match.group('units').replace(',', '.'))
            size = None
            return size, portions, portion_price, portion_size, portion_unit, bulk_price, bulk_unit, size_type, minimum_size_for_bulk
    
    if " doses)" in size:
        matches = re.search(r'\((\d+)\s*doses\)', size)
        if matches:
            portions = matches.group(1)
            size = size.replace(f" ({portions} doses)", "")
    
    # Pattern: <number> <unit> + <number> <unit> GRÁTIS  
    if " + " in size and "GRÁTIS" in size:
        pattern = re.compile(
            r'(?P<main_size>\d+(?:[.,]\d+)?)\s*(?P<main_unit>[a-zA-Z]+)\s*\+\s*'
            r'(?P<bonus_size>\d+(?:[.,]\d+)?)\s*(?P<bonus_unit>[a-zA-Z]+)\s*GRÁTIS',
            re.IGNORECASE
        )

        match = pattern.search(size)
        if match:
            main_size = float(match.group('main_size').replace(',', '.'))
            main_unit = match.group('main_unit')
            bonus_size = float(match.group('bonus_size').replace(',', '.'))
            bonus_unit = match.group('bonus_unit')
            if main_unit == bonus_unit:
                total_size = main_size + bonus_size
                size = f"{total_size} {main_unit}"
            else:
                if main_unit == "kg" and bonus_unit == "g":
                    bonus_size_kg = bonus_size / 1000
                    total_size = main_size + bonus_size_kg
                    size = f"{total_size} {main_unit}"
                elif main_unit == "g" and bonus_unit == "kg":
                    main_size_kg = main_size / 1000
                    total_size = main_size_kg + bonus_size
                    size = f"{total_size} {bonus_unit}"
                else:
                    print()

            return size, portions, portion_price, portion_size, portion_unit, bulk_price, bulk_unit, size_type, minimum_size_for_bulk
    
    # Pattern: <number> <unit> + <number>% GRÁTIS
    if " + " in size and "% GRÁTIS" in size:
        pattern_percent = re.compile(
            r'(?P<main_size>\d+(?:[.,]\d+)?)\s*'    # main number
            r'(?P<main_unit>[a-zA-Z]+)\s*\+\s*'    # main unit
            r'(?P<bonus_percent>\d+(?:[.,]\d+)?)%\s*GRÁTIS',  # bonus percent
            re.IGNORECASE
        )

        match = pattern_percent.search(size)
        if match:
            main_size = float(match.group('main_size').replace(',', '.'))
            bonus_percent = float(match.group('bonus_percent').replace(',', '.'))

            total_size = math.floor(main_size * (1 + bonus_percent / 100))
            size = f"{total_size} {match.group('main_unit')}"

    
    return size, portions, portion_price, portion_size, portion_unit, bulk_price, bulk_unit, size_type, minimum_size_for_bulk

def transform_ingredient(logger, task, instance, stopping_offset):
    """
    Transforms a single ingredient record from the extraction database into the target format.

    Workflow:
        1. Checks for stop signal before processing.
        2. Logs the start of transformation for the ingredient.
        3. Normalizes size and price fields.
        4. Transforms and saves the ingredient record to the transformation database.
        5. Processes and attaches tags to the ingredient.
        6. Increments processed item count.
        7. Handles and logs any exceptions or warnings.

    Args:
        logger (logging.Logger): Logger for structured logging.
        task (Task): ETL task instance tracking state, errors, and metrics.
        ingredient (Ingredient_E): Ingredient instance from extraction DB.

    Returns:
        Task: Updated task instance.
    """
    # === STEP 1: STOP SIGNAL CHECK =============================================
    if check_if_task_stopped(task):
        logger.debug(f"[Thread {threading.current_thread().name}] Stop signal detected, exiting before processing.")
        return False, True
    
    # Check if the stopping condition offset is reached
    from apps.etl_app.models import Task, JobTriggerHistory
    if stopping_offset and instance.id > stopping_offset:
        task.owner_job.create_job_trigger_history(
            type=JobTriggerHistory.Type.STOPPING_CONDITION,
            action=JobTriggerHistory.Action.REST,
        )
        logger.info(f"[Thread {threading.current_thread().name}] Stopping condition reached.")
        return False, True

    # === STEP 2: LOG START =====================================================
    logger.info(f"[Thread {threading.current_thread().name}] Transforming Ingredient {instance.id}.")

    try:
        # === STEP 3: NORMALIZE SIZE AND PRICE ===================================
        _old_size = instance.size
        _size, _portions, _portion_price, _portion_size, _portion_unit, _bulk_price, _bulk_unit, _size_type, _minimum_size_for_bulk = normalize_size(instance)

        # === STEP 4: TRANSFORM AND SAVE INGREDIENT ==============================
        _category = json.dumps(instance.category.split(" > ")) if instance.category else None

        _ingredient = Ingredient_T(
            company=task.company.name,
            title=instance.title,
            brand=instance.brand,
            description=instance.description,
            source_link=instance.link,
            about_the_product=instance.about_the_product,
            caracteristics=instance.caracteristics,
            other_information=instance.other_information,
            nutrition_information=instance.nutrition_information,
            legal_info=instance.legal_info,
            category=_category,
            old_size=_old_size,
            size=_size,
            portions=_portions,
            portion_size=_portion_size,
            portion_price=_portion_price,
            portion_unit=_portion_unit,
            bulk_price=_bulk_price,
            bulk_unit=_bulk_unit,
            size_type=_size_type,
            minimum_size_for_bulk=_minimum_size_for_bulk
        )
        _ingredient.save()

        # === STEP 5: PROCESS TAGS ===============================================
        for tag in instance.tags:
            _tag, created = Tag_T.get_or_create(text=tag.title)
            if created:
                _tag.save()
            _tag.ingredient.add(_ingredient)
            _tag.save()

        # === STEP 6: INCREMENT PROCESSED COUNT ==================================
        task.items_processed += 1

        # === STEP 7: PROCESS IMAGES ( TODO ) =================================
        for image in instance.images:
            _image = Image_T(
                source_path=image.source_path,
                path=image.path,
                ingredient=_ingredient
            )
            _image.save()

    except Exception as e:
        # === STEP 8: HANDLE EXCEPTIONS AND WARNINGS =============================
        task.increment_errors(
            logger=logger,
            message=f"Failed to transform ingredient. Instance: {instance.id}    Error: {e}",
            stack_trace=traceback.format_exc()
        )

    return True, False
    
    
def transform_ingredients(logger, task, threads):
    """
    Transforms all ingredient records from the extraction database into the normalized target format.

    Workflow:
        1. Logs the start or resumption of the ingredient transformation process.
        2. Handles resumption logic and cleans up incomplete data if necessary.
        3. Computes stopping conditions and retrieves ingredients to process.
        4. Transforms extracted ingredients in parallel using threads.
        5. Updates task progress, metrics, and handles stop signals.
        6. Logs a summary of the transformation process, including errors and warnings.
        7. Returns the updated task object and completion status.

    Args:
        logger (logging.Logger): Logger instance for structured logging.
        task (Task): Task object containing metadata and state for the transformation process.
        threads (int): Number of threads to use for parallel transformation.

    Returns:
        Tuple[Task, bool]: The updated task object and a boolean indicating if the transformation was fully completed.
    """

    # === INITIALIZATION ========================================================
    # Initialize control variables
    total_processed = 0
    completed = False
    stopping_condition_triggered = False

    # Log the start of the transform process
    print_sub_header(logger, f"Starting Ingredient Transformation")

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
        instances_to_delete = Ingredient_T.select().where(Ingredient_T.id > task.step)
        for ingredient in instances_to_delete:
            ingredient.tags.clear()
        Ingredient_T.delete().where(Ingredient_T.id > task.step).execute()

    # Retrieve recipes to process starting from the current step
    instances_to_process = Ingredient_E.select().where(Ingredient_E.id > task.step)
    
    # Check if there are any recipes to process
    total_instances = instances_to_process.count()
    if total_instances == 0:
        logger.info(f"No {task.process} found to {task.type}.")
        return task, True

    # Log recipes to process
    logger.info(f"Found {total_instances} {task.process} to {task.type}.")
    logger.info("")

        # === STEP 3: PROCESS RECIPES IN PARALLEL ===================================
    # Use ThreadPoolExecutor for parallel transformation
    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
        futures = []

        # Submit transformation tasks for each recipe
        for instance in instances_to_process:
            # Check for stop signal before submitting new tasks
            if check_if_task_stopped(task):
                logger.info("Stop signal detected — no new transformation tasks will be submitted.")
                break
            
            futures.append(executor.submit(transform_ingredient, logger, task, instance, OFFSET))

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

def __transform_continente_ingredients(logger, task, resume):
    """
    Transforms all ingredient records from the extraction database into the normalized target format.

    Workflow:
        1. Logs the start or resumption of the transformation process.
        2. Initializes or resumes the transformation and extraction databases.
        3. Configures threading and task properties.
        4. Calculates the total number of ingredients expected for transformation.
        5. Transforms extracted ingredients in parallel using threads.
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

    # ============ INITIALIZATION ============
    print_header(logger, f"{'Resuming' if resume else 'Starting'} {task.type} for all {task.process} from {task.company.name}.")
    logger.info("")

    # Initialize or resume the transformation database
    task, database = start_db(
        logger=logger,
        task=task,
        models=transform_models_,
        path=TRANSFORM_CONTINENTE_RECIPES_DB,
        database_proxy=database_proxy,
        reset=not resume  # Reset DB only when not resuming
    )

    # Initialize the extraction database
    task, database = start_sub_db(
        logger=logger,
        task=task,
        models=extract_models_,
        database_proxy=database_proxy_E
    )
    
    # Initialize special properties
    task_properties = task.properties
    threads = task_properties.get("Threads", MAX_THREADS)
    logger.info("Task Properties:")
    logger.info(f"  - Threads: {threads}")
    logger.info("")

    # ============ STEP 1: TRANSFORMATION ============
    # Calculate total items expected for transformation
    task.items_expected = Ingredient_E.select().count()
    task.save()

    # Transform extracted ingredient data
    task, completed = transform_ingredients(logger, task, threads)

    # Optionally apply AI-based transformations for invalid ingredients

    # ============ STEP 2: SUMMARY & LOGGING ============
    logger.info("Transformation Summary:")
    logger.info(f"  - Ingredients Expected: {task.items_expected}")
    logger.info(f"  - Ingredients Processed: {task.items_processed}")
    logger.info("")
    logger.info(f"  - Total Errors: {task.errors}")
    logger.info(f"  - Total Warnings: {task.warnings}")
    logger.info("")

    # ============ STEP 3: FINALIZATION ============
    # Mark task as finished or paused depending on completion state
    if completed:
        task.finish(kill_celery_task=False)
        logger.info("✅ Task successfully completed.")
    else:
        task.pause()
        logger.info("⚠️ Task paused before full completion.")
    logger.info("")

    return task