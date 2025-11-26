# === Imports ===
import concurrent.futures
import threading
from playhouse.shortcuts import model_to_dict

# === Custom Functions and Constants ===
from apps.common.constants import FIREBASE_STORAGE_COMPANY_BUCKET, COMPANY_CONTINENTE
from apps.common.functions import send_image_to_firebase, lower_and_underscore
from apps.etl_app.recipe.load.functions import create_audit_log, persist_recipe
from apps.etl_app.recipe.transform.models import database_proxy, Recipe as Recipe_T,  NutritionInformation as NutritionInformation_T, Ingredient as Ingredient_T, Tag as Tag_T, UsefulTool as UsefulTool_T, IngredientQuantity as IngredientQuantity_T
from apps.etl_app.models import ProcessType

from apps.recipe_app.models import RecipeAuditLog, Recipe, Tag, UsefulTool, Preparation, Ingredient, IngredientQuantity, NutritionInformation
from apps.user_app.models import Company
from apps.common.constants import COMPANY_CONTINENTE
import pickle
from apps.etl_app.functions import (
    start_db,
    check_if_task_stopped,
    check_task_stopping_condition,
    start_sub_db,
    print_header,
    start_sub_db,
    print_sub_header,
    retry_db_operation,
    update_simple_fields,
    sync_related
)

# === Through Models for M2M Relationships ===
recipeTagThrough_T = Recipe_T.tags.get_through_model()

# === Model Lists ===
transform_models_ = [Recipe_T, Ingredient_T, Tag_T, IngredientQuantity_T, NutritionInformation_T, Ingredient_T, UsefulTool_T, recipeTagThrough_T]

# === Configuration ===
MAX_THREADS = 2

def load_recipe(logger, task, recipe_t, stopping_offset):
    """
    Loads or updates a single transformed recipe into the main Django database.

    Workflow:
        1. Checks for ETL stop signals before processing.
        2. Checks for stopping offset condition.
        3. Validates the recipe; skips if marked invalid.
        4. Converts the Peewee recipe object to a dictionary.
        5. Creates or retrieves the corresponding Django Recipe object.
        6. If new, persists all related data and logs creation.
        7. If existing, compares and updates all fields and related objects:
            - Updates simple fields.
            - Synchronizes preparation steps, ingredients, useful tools, tags, and nutrition information.
        8. Handles audit logging for all detected changes.
        9. Returns status flags for completion, stopping condition, and load type.

    Args:
        logger (logging.Logger): Logger instance for structured logging.
        task (Task): ETL task instance tracking job progress and statistics.
        recipe_t (Recipe_T): Transformed Peewee recipe object to load.
        stopping_offset (int): Optional offset for stopping condition.

    Returns:
        tuple: (result: bool, stopping_condition_triggered: bool, load_type: LoadType)
    """
    from apps.etl_app.models import LoadType

    # === STEP 1: STOP SIGNAL CHECK =============================================
    if check_if_task_stopped(task):
        logger.debug(f"[Thread {threading.current_thread().name}] Stop signal detected, exiting before processing.")
        return False, True, LoadType.NONE

    # === STEP 2: STOPPING OFFSET CHECK =========================================
    if check_task_stopping_condition(task, stopping_offset, recipe_t):
        logger.info(f"[Thread {threading.current_thread().name}] Stopping condition reached at recipe ID {recipe_t.id}.")
        return False, True, LoadType.NONE

    # === STEP 3: VALIDITY CHECK ================================================
    if not recipe_t.valid:
        logger.info(f"[Thread {threading.current_thread().name}] Loading Recipe {recipe_t.id}: Recipe {recipe_t.id} is marked as invalid. Skipping load.")
        return False, False, LoadType.UNCHANGED

    # === STEP 4: CONVERT PEEWEE OBJECT TO DICT =================================
    incoming = model_to_dict(recipe_t, backrefs=True, recurse=True)

    # === STEP 5: CREATE OR RETRIEVE DJANGO RECIPE ==============================
    recipe_obj, created = Recipe.objects.get_or_create(
        created_by=task.company.user_account,
        source_link=recipe_t.source_link
    )

    if created:
        # === STEP 6: PERSIST NEW RECIPE AND RELATED DATA ========================
        logger.info(f"[Thread {threading.current_thread().name}] Loading Recipe {recipe_t.id}: Recipe is new, creating in Main database.")
        persist_recipe(logger, task, recipe_obj, incoming)
        return True, False, LoadType.CREATED

    # === STEP 7: COMPARE AND UPDATE EXISTING RECIPE ============================
    logger.info(f"[Thread {threading.current_thread().name}] Loading Recipe {recipe_t.id}: Recipe already exists, checking for changes...")
    mapped_changes = {}

    # 7.1 Normalize and remove fields that should never be compared
    ignore_fields = {
        "id", "company", "created_date", "updated_date",
        "nutrition_information", "preparation", "ingredients",
        "useful_tools", "tagrecipethrough_set", "valid"
    }
    normalized = {k: v for k, v in incoming.items() if k not in ignore_fields}

    # 7.2 Fix image path
    normalized["image"] = (
        f"{FIREBASE_STORAGE_COMPANY_BUCKET}"
        f"{lower_and_underscore(COMPANY_CONTINENTE)}/recipes/"
        f"{incoming['image'].split('/')[-1]}"
    )

    # 7.3 Update simple fields
    update_simple_fields(logger, task, recipe_obj, normalized, Recipe, mapped_changes)

    # 7.4 Sync preparation steps (1-to-many)
    incoming_preparation = pickle.loads(incoming["preparation"])
    _changes = sync_related(
        existing_qs=recipe_obj.preparation.all(),
        incoming_list=incoming_preparation,
        key="step",
        fields=["description"],
        create_fn=lambda item: Preparation.objects.create(
            recipe=recipe_obj, step=item["step"], description=item.get("description", "")
        ),
        delete_fn=lambda obj: obj.delete()
    )
    if _changes:
        mapped_changes["preparation"] = _changes

    # 7.5 Sync ingredients & quantities (1-to-many)
    incoming_ingredients = incoming["ingredients"]
    _changes = sync_related(
        existing_qs=recipe_obj.ingredients.all(),
        incoming_list=incoming_ingredients,
        key=lambda item: item["ingredient"]["name"] if isinstance(item, dict) else item.ingredient.name,
        fields=[
            "quantity_original",
            "quantity_normalized",
            "units_normalized",
            "extra_quantity",
            "extra_units"
        ],
        create_fn=lambda item: IngredientQuantity.objects.create(
            recipe=recipe_obj,
            ingredient=Ingredient.objects.get_or_create(
                name=item["ingredient"]["name"]
            )[0],
            quantity_original=item.get("quantity_original"),
            quantity_normalized=item.get("quantity_normalized"),
            units_normalized=item.get("units_normalized"),
            extra_quantity=item.get("extra_quantity"),
            extra_units=item.get("extra_units")
        ),
        delete_fn=lambda obj: obj.delete()
    )
    if _changes:
        mapped_changes["ingredients"] = _changes

    # 7.6 Sync useful tools (many-to-many)
    _changes = sync_related(
        existing_qs=recipe_obj.useful_tools.all(),
        incoming_list=incoming["useful_tools"],
        key="text",
        fields=["text"],
        create_fn=lambda item: UsefulTool.objects.get_or_create(text=item["text"])[0]
            .recipes.add(recipe_obj),
        delete_fn=lambda obj: recipe_obj.useful_tools.remove(obj)
    )
    if _changes:
        mapped_changes["useful_tools"] = _changes

    # 7.7 Sync tags (many-to-many)
    _changes = sync_related(
        existing_qs=recipe_obj.tags.all(),
        incoming_list=[i["tag"] for i in incoming["tagrecipethrough_set"]],
        key="text",
        fields=["text"],
        create_fn=lambda item: recipe_obj.tags.add(
            Tag.objects.get_or_create(text=item["text"])[0]
        ),
        delete_fn=lambda obj: recipe_obj.tags.remove(obj)
    )

    # 7.8 Sync nutrition information (one-to-one)
    nutri = incoming["nutrition_information"]
    if nutri:
        nutri.pop("id", None)
        if recipe_obj.nutrition_information:
            for field, new_val in nutri.items():
                new_val = float(new_val)
                old_val = getattr(recipe_obj.nutrition_information, field)
                if new_val != old_val:
                    setattr(recipe_obj.nutrition_information, field, new_val)
                    mapped_changes.setdefault("nutrition_information", []).append({
                        "updated": {"field": field, "old": old_val, "new": new_val}
                    })
            recipe_obj.nutrition_information.save()
        else:
            recipe_obj.nutrition_information = NutritionInformation.objects.create(**nutri)
            mapped_changes["nutrition_information"] = [{"created": nutri}]
            recipe_obj.save()

    # === STEP 8: AUDIT LOG CREATION ===========================================
    if not mapped_changes:
        logger.info(f"[Thread {threading.current_thread().name}] Loading Recipe {recipe_t.id}: No changes detected.\n")
        return True, False, LoadType.UNCHANGED

    logger.info(f"[Thread {threading.current_thread().name}] Loading Recipe {recipe_t.id}: Recipe has changes.")

    if recipe_obj.verified:
        recipe_obj.verified = False
        recipe_obj.save()
        for field, changes in mapped_changes.items():
            for change in changes:
                subtype = (
                    RecipeAuditLog.SubType.Create if "created" in change else
                    RecipeAuditLog.SubType.Delete if "deleted" in change else
                    RecipeAuditLog.SubType.Update
                )
                create_audit_log(
                    RecipeAuditLog.Type.Update,
                    task, recipe_obj,
                    field=field,
                    old_value=change.get("deleted") or change.get("updated", {}).get("old"),
                    new_value=change.get("created") or change.get("updated", {}).get("new"),
                    update_sub_type=subtype
                )
    else:
        # expect exactly 1 non-accepted CREATE log
        count = RecipeAuditLog.objects.filter(
            recipe=recipe_obj,
            type=RecipeAuditLog.Type.Create,
            accepted=False
        ).count()

        if count == 1:
            create_audit_log(RecipeAuditLog.Type.Create, task, recipe_obj)
        else:
            task.increment_errors(
                logger,
                f"Recipe {recipe_t.id} not verified but has {count} CREATE logs (expected 1)."
            )

    logger.info("")
    return True, False, LoadType.CHANGED

def load_recipes(logger, task, threads):
    """
    Loads all transformed recipes into the main Django database using parallel threads.

    This function orchestrates the parallel loading of normalized recipe data into the main Django database.
    It leverages a thread pool to efficiently process large numbers of recipes, supports graceful interruption,
    and provides comprehensive logging and auditing.

    Workflow:
        1. Initializes control variables and computes the stopping offset based on job configuration.
        2. Retrieves transformed recipes from the database, starting from the current step.
        3. Submits loading tasks to a thread pool executor for parallel processing.
        4. Monitors for stop signals to halt new submissions and waits for running threads to finish.
        5. Updates the task's progress, including processed item counts and statistics.
        6. Audits and logs recipes that have been deleted since the last run.
        7. Cleans up resources and logs a summary of the loading process.

    Args:
        logger (logging.Logger): Logger instance for structured logging.
        task (Task): The ETL task instance tracking job progress and statistics.
        threads (int): Number of threads to use for parallel processing.

    Returns:
        tuple: (task, completed: bool, load_statistics: dict)

    Notes:
        - The function respects stop signals for graceful interruption.
        - Thread-safe operations ensure data integrity during parallel execution.
        - Comprehensive error handling and logging are provided for monitoring and debugging.
    """
    
    # === INITIALIZATION ========================================================
    # Initialize control variables
    from apps.etl_app.models import LoadType
    total_processed = 0
    completed = False
    stopping_condition_triggered = False
    load_statistics = {
        LoadType.CREATED: 0,
        LoadType.CHANGED: 0,
        LoadType.UNCHANGED: 0,
        LoadType.DELETED: 0,
        LoadType.NONE: 0
    }
    
    # Log the start of the transform process
    print_sub_header(logger, f"Starting Parallel Recipes Loading")
    
    # === STEP 1: COMPUTE STOPPING OFFSET =======================================
    from apps.etl_app.models import ThresholdCondition
    OFFSET = None
    if (
        task.owner_job
        and task.owner_job.stopping_condition
        and isinstance(task.owner_job.stopping_condition, ThresholdCondition)
    ):
        OFFSET = task.step + task.owner_job.stopping_condition.threshold_value
    
    # === STEP 2: RETRIEVE RECIPES ==============================================
    instances_to_process = Recipe_T.select().where(Recipe_T.id > task.step).order_by(Recipe_T.id)
    total_instances = instances_to_process.count()
    if total_instances == 0:
        logger.info(f"No {task.process} found to {task.type}.")
        return task, True
    
    logger.info(f"Found {total_instances} {task.process} to {task.type}.")
    logger.info("")

    # === STEP 3: PROCESS RECIPES IN PARALLEL ===================================
    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
        futures = []
        for instance in instances_to_process:
            if check_if_task_stopped(task):
                logger.info("Stop signal detected — no new transformation tasks will be submitted.")
                break
            futures.append(executor.submit(load_recipe, logger, task, instance, OFFSET))

        try:
            for future in concurrent.futures.as_completed(futures):
                if check_if_task_stopped(task):
                    logger.info("Stop signal detected — waiting for running transformation threads to finish...")
                    break

                try:
                    result, stopping_condition_triggered, load_type = future.result()
                except Exception as e:
                    logger.error(f"Future raised an exception: {e}", exc_info=True)
                    continue

                if result:
                    total_processed += 1
                    task.step += 1
                    task.items_processed += 1
                    task.save()
                    load_statistics[load_type] += 1
        finally:
            executor.shutdown(wait=True, cancel_futures=True)
            if not (stopping_condition_triggered or check_if_task_stopped(task)):
                completed = True
    
    logger.info("")
    print_sub_header(logger, "Recipe Parallel Loading Completed")
          
    # === STEP 4: AUDIT DELETED RECIPES ==========================================
    print_sub_header(logger, f"Auditing Deleted Recipes")
    recipe_source_link_transform_set = {recipe.source_link for recipe in instances_to_process}
    recipe_source_link_load_set = {recipe.source_link for recipe in Recipe.objects.filter(created_by__company=task.company)}
    removed_recipes = Recipe.objects.filter(
        created_by__company=task.company, source_link__in=(recipe_source_link_load_set - recipe_source_link_transform_set)
    )
    if removed_recipes:
        for removed_recipe in removed_recipes:
            create_audit_log(
                type=RecipeAuditLog.Type.Delete,
                task=task,
                recipe=removed_recipe
            )
    logger.info(f"  - Found {removed_recipes.count()} deleted {task.process}.")
    logger.info("")
                
    print_sub_header(logger, f"Deleted Recipes Auditing completed")
    
    return task, completed, load_statistics

def __load_recipes(logger, task, resume):
    """
    Loads all recipe records from the extraction database into the normalized target database.

    Workflow:
        1. Logs the start or resumption of the loading process.
        2. Initializes or resumes connections to the extraction and target databases.
        3. Configures threading and task properties for parallel execution.
        4. Calculates the total number of recipes expected for loading.
        5. Loads recipes in parallel threads, handling creation, updates, and deletions.
        6. Logs a summary of the loading process, including errors, warnings, and statistics.
        7. Marks the task as finished or paused depending on completion status.

    Args:
        logger (logging.Logger): Logger instance for structured logging.
        task (Task): Task object containing metadata and state for the loading process.
        resume (bool): Flag indicating whether to resume a previous loading run or start anew.

    Returns:
        Task: The updated task object after loading, with updated status and statistics.
    """
    # === STEP 1: INITIALIZATION =================================================
    print_header(logger, f"{'Resuming' if resume else 'Starting'} {task.type} for all {task.process} from {task.company.name}.")
    logger.info("")
    task, database = start_sub_db(
        logger=logger,
        task=task,
        models=transform_models_,
        database_proxy=database_proxy
    ) 
    
    # === STEP 2: SETUP TASK PROPERTIES ==========================================
    task_properties = task.properties
    threads = task_properties.get("Threads", MAX_THREADS)
    logger.info("Task Properties:")
    logger.info(f"  - Threads: {threads}")
    logger.info("")   
    
    # === STEP 3: LOADING RECIPES ================================================
    task.items_expected = Recipe_T.select().where(Recipe_T.id > task.step).order_by(Recipe_T.id).count()
    task.save()
    task, completed, load_statistics = load_recipes(logger, task, threads)
    
    # === STEP 4: SUMMARY & LOGGING =============================================
    from apps.etl_app.models import LoadType
    valid_recipes_count = Recipe_T.select().where(Recipe_T.id > task.step and (Recipe_T.valid == True)).order_by(Recipe_T.id).count()
    invalid_recipes_count = Recipe_T.select().where(Recipe_T.id > task.step and (Recipe_T.valid == False)).order_by(Recipe_T.id).count()
    logger.info("")
    logger.info("Loading Summary:")
    logger.info(f"  - Recipes Expected: {task.items_expected}")
    logger.info(f"  - Recipes Processed: {task.items_processed}")
    logger.info("")
    logger.info(f"  - Total Errors: {task.errors}")
    logger.info(f"  - Total Warnings: {task.warnings}")
    logger.info("")
    logger.info(f"  - Recipes Valid: {valid_recipes_count}")
    logger.info(f"  - Recipes Unvalid: {invalid_recipes_count}")
    logger.info("")
    logger.info(f"  - Recipes Created: {load_statistics[LoadType.CREATED]}")
    logger.info(f"  - Recipes Changed: {load_statistics[LoadType.CHANGED]}")
    logger.info(f"  - Recipes Unchanged: {load_statistics[LoadType.UNCHANGED]}")
    logger.info(f"  - Recipes Deleted: {load_statistics[LoadType.DELETED]}")
    logger.info("")
    
    # === STEP 5: FINALIZATION ==================================================
    if completed:
        task.finish(kill_celery_task=False)
        logger.info("✅ Task successfully completed.")
    else:
        task.pause()
        logger.info("⚠️ Task paused before full completion.")
    logger.info("")

    return task

def _load_recipes(logger, task, resume):
    """
    Extract recipes for a given task based on the company's name and processes.

    This function determines the appropriate recipe loading method based on the
    company associated with the task. It ensures that the company has the required
    recipe process implemented and logs the loading process. If the company's recipe
    loading process is not implemented, an error is logged and the task is updated.

    Args:
        logger (logging.Logger): The logger instance used for logging messages.
        task (Task): The task object containing information about the company and its processes.
        resume (bool): A flag indicating whether to continue from a previous state.

    Notes:
        - Supports recipe loading for specific companies such as Continente.
        - Logs an error if the company's recipe loading process is not implemented.
        - Ensures that the company has the required recipe process before proceeding.
    """
    if ProcessType.RECIPES.value not in task.company.processes:
        logger.error(f"Company of task does not have a Recipe's process.")
        task.errors += 1
        task.save()
        return
        
    if task.company.name == COMPANY_CONTINENTE:
        return __load_recipes(logger, task, resume)
    else:
        logger.error(f"Company of task does not have a Recipe's process implemented.")
        task.errors += 1
        task.save()
        return
