# === Imports ===
import threading
import json
import math
import re
import traceback

from playhouse.shortcuts import model_to_dict
import google.generativeai as genai
import concurrent.futures

# === Custom Functions and Constants ===
from apps.etl_app.constants import TRANSFORM_CONTINENTE_INGREDIENTS_DB, eu_reference_intake

from apps.etl_app.functions import (
    start_db,
    start_sub_db,
    strip_markdown_json,
    check_if_task_stopped,
    check_task_stopping_condition,
    print_header,
    print_sub_header,
)
from apps.etl_app.etl.transform.functions import transform
from apps.etl_app.etl.transform.ingredient.continente.functions import normalize_size
from apps.etl_app.etl.extract.ingredient.continente.models import (
    database_proxy as database_proxy_E,
    Ingredient as Ingredient_E,
    IngredientLink as IngredientLink_E,
    Tag as Tag_E,
    Image as Image_E,
)
from apps.etl_app.etl.transform.ingredient.models import (
    database_proxy,
    Ingredient as Ingredient_T,
    IngredientLink as IngredientLink_T,
    Tag as Tag_T,
    Image as Image_T,
)
from apps.etl_app.etl.transform.recipe.continente.functions import (
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
        tuple: (success: bool, stopping_condition_triggered: bool)
    """
    from apps.etl_app.models import StoppingConditionTriggered
    
    # === STEP 1: STOP SIGNAL CHECK =============================================
    # Check is stopping condition alredy triggered
    if check_if_task_stopped(task):
        logger.debug(f"[Thread {threading.current_thread().name}] Stop signal detected, exiting before processing.")
        return False, True

    # Check if the stopping condition offset is reached
    if check_task_stopping_condition(task, stopping_offset):
        logger.info(f"[Thread {threading.current_thread().name}] Stopping condition reached at Recipe ID {instance.id}.")
        return False, True
    

    try:
        # === STEP 2: LOG START =====================================================
        logger.info(f"[Thread {threading.current_thread().name}] Transforming Ingredient {instance.id}.")

        # === STEP 3: NORMALIZE SIZE AND PRICE ===================================
        _old_size = instance.size
        is_valid, (_size, _portions, _portion_price, _portion_size, _portion_unit, _bulk_price, _bulk_unit, _size_type, _minimum_size_for_bulk) = normalize_size(instance)

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
            minimum_size_for_bulk=_minimum_size_for_bulk,
            is_valid=is_valid
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
            
        # === STEP 8: FINAL STOP SIGNAL CHECK ======================================
        if check_if_task_stopped(task) or (stopping_offset and instance.id > stopping_offset):
            logger.info(f"[Thread {threading.current_thread().name}] Stop or stopping condition detected after processing Ingredient ID {instance.id}. Rolling back.")
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


def transform_ingredients(logger, task, threads):
    """
    Specialized transformation for ingredients using the generic transform function.
    """
    from apps.etl_app.models import ThresholdCondition


    offset = (
        task.step + task.owner_job.stopping_condition.threshold_value
        if (
            task.owner_job
            and task.owner_job.stopping_condition
            and isinstance(task.owner_job.stopping_condition, ThresholdCondition)
        )
        else 999999
    )

    def get_instances_to_delete(transform_model, task):
        return transform_model.select().where(transform_model.id > task.step)

    def get_instances_to_process(extract_model, task):
        return extract_model.select().where((extract_model.id > task.step) & (extract_model.id <= offset))

    return transform(
        logger=logger,
        task=task,
        threads=threads,
        extract_model=Ingredient_E,
        transform_model=Ingredient_T,
        transform_instance_fn=transform_ingredient,
        get_instances_to_delete_fn=get_instances_to_delete,
        get_instances_to_process_fn=get_instances_to_process,
        process_name=task.process,
        offset=offset,
        print_start_header=print_sub_header,
        print_end_header=print_sub_header
    )

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
        path=TRANSFORM_CONTINENTE_INGREDIENTS_DB,
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