# === Imports ===
import concurrent.futures
import threading
from playhouse.shortcuts import model_to_dict

from apps.common.constants import FIREBASE_STORAGE_COMPANY_BUCKET, COMPANY_CONTINENTE
from apps.common.functions import send_image_to_firebase, lower_and_underscore
from apps.etl_app.ingredient.load.functions import persist_ingredient
from apps.etl_app.ingredient.transform.models import database_proxy, Ingredient as Ingredient_T, Tag as Tag_T
from apps.etl_app.models import ProcessType

from apps.ingredient_app.models import Ingredient, Tag
from apps.user_app.models import Company
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
ingredientTagThrough_T = Ingredient_T.tags.get_through_model()

# === Model Lists ===
transform_models_ = [Ingredient_T, Tag_T, ingredientTagThrough_T]

# === Configuration ===
MAX_THREADS = 2

def load_ingredient(logger, task, ingredient_t, stopping_offset):
    """
    Loads or updates an ingredient in the main Django database from a transformed Peewee ingredient object.
    """
    from apps.etl_app.models import LoadType

    # === STEP 1: STOP SIGNAL CHECK =============================================
    if check_if_task_stopped(task):
        logger.debug(f"[Thread {threading.current_thread().name}] Stop signal detected, exiting before processing.")
        return False, True, LoadType.NONE

    # === STEP 2: STOPPING OFFSET CHECK =========================================
    if check_task_stopping_condition(task, stopping_offset, ingredient_t):
        logger.info(f"[Thread {threading.current_thread().name}] Stopping condition reached at ingredient ID {ingredient_t.id}.")
        return False, True, LoadType.NONE

    # === STEP 3: VALIDITY CHECK ================================================
    if not ingredient_t.valid:
        logger.info(f"[Thread {threading.current_thread().name}] Loading Ingredient {ingredient_t.id}: Ingredient {ingredient_t.id} is marked as invalid. Skipping load.")
        return False, False, LoadType.UNCHANGED

    # === STEP 4: CONVERT PEEWEE OBJECT TO DICT =================================
    incoming = model_to_dict(ingredient_t, backrefs=True, recurse=True)

    # === STEP 5: CREATE OR RETRIEVE DJANGO INGREDIENT ==========================
    ingredient_obj, created = Ingredient.objects.get_or_create(
        created_by=task.company.user_account,
        company=ingredient_t.company,
        source_link=ingredient_t.link
    )

    if created:
        # === STEP 6: PERSIST NEW INGREDIENT AND RELATED DATA ====================
        logger.info(f"[Thread {threading.current_thread().name}] Loading Ingredient {ingredient_t.id}: Ingredient is new, creating in Main database.")
        persist_ingredient(logger, task, ingredient_obj, incoming)
        return True, False, LoadType.CREATED

    # === STEP 7: COMPARE AND UPDATE EXISTING INGREDIENT ========================
    logger.info(f"[Thread {threading.current_thread().name}] Loading Ingredient {ingredient_t.id}: Ingredient already exists, checking for changes...")
    mapped_changes = {}

    # 7.1 Normalize and remove fields that should never be compared
    ignore_fields = {
        "id", "company", "created_date", "updated_date",
        "valid"
    }
    normalized = {k: v for k, v in incoming.items() if k not in ignore_fields}

    # 7.2 Fix image path if applicable
    if "image" in incoming and incoming["image"]:
        normalized["image"] = (
            f"{FIREBASE_STORAGE_COMPANY_BUCKET}"
            f"{lower_and_underscore(COMPANY_CONTINENTE)}/ingredients/"
            f"{incoming['image'].split('/')[-1]}"
        )

    # 7.3 Update simple fields
    update_simple_fields(logger, task, ingredient_obj, normalized, Ingredient, mapped_changes)

    # 7.4 Sync tags (many-to-many)
    if "tagingredientthrough_set" in incoming:
        _changes = sync_related(
            existing_qs=ingredient_obj.tags.all(),
            incoming_list=[i["tag"] for i in incoming["tagingredientthrough_set"]],
            key="text",
            fields=["text"],
            create_fn=lambda item: ingredient_obj.tags.add(
                Tag.objects.get_or_create(text=item["text"])[0]
            ),
            delete_fn=lambda obj: ingredient_obj.tags.remove(obj)
        )
        if _changes:
            mapped_changes["tags"] = _changes

    # === STEP 8: AUDIT LOG CREATION ===========================================
    if not mapped_changes:
        logger.info(f"[Thread {threading.current_thread().name}] Loading Ingredient {ingredient_t.id}: No changes detected.\n")
        return True, False, LoadType.UNCHANGED

    logger.info(f"[Thread {threading.current_thread().name}] Loading Ingredient {ingredient_t.id}: Ingredient has changes.")

    if ingredient_obj.verified:
        ingredient_obj.verified = False
        ingredient_obj.save()
        for field, changes in mapped_changes.items():
            for change in changes:
                subtype = (
                    IngredientAuditLog.SubType.Create if "created" in change else
                    IngredientAuditLog.SubType.Delete if "deleted" in change else
                    IngredientAuditLog.SubType.Update
                )
                create_audit_log(
                    IngredientAuditLog.Type.Update,
                    task, ingredient_obj,
                    field=field,
                    old_value=change.get("deleted") or change.get("updated", {}).get("old"),
                    new_value=change.get("created") or change.get("updated", {}).get("new"),
                    update_sub_type=subtype
                )
    else:
        count = IngredientAuditLog.objects.filter(
            ingredient=ingredient_obj,
            type=IngredientAuditLog.Type.Create,
            accepted=False
        ).count()

        if count == 1:
            create_audit_log(IngredientAuditLog.Type.Create, task, ingredient_obj)
        else:
            task.increment_errors(
                logger,
                f"Ingredient {ingredient_t.id} not verified but has {count} CREATE logs (expected 1)."
            )

    logger.info("")
    return True, False, LoadType.CHANGED

def load_ingredients(logger, task, threads):
    """
    Loads all transformed ingredients into the main Django database using parallel threads.
    """
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
    
    print_sub_header(logger, f"Starting Parallel Ingredients Loading")
    
    from apps.etl_app.models import ThresholdCondition
    OFFSET = None
    if (
        task.owner_job
        and task.owner_job.stopping_condition
        and isinstance(task.owner_job.stopping_condition, ThresholdCondition)
    ):
        OFFSET = task.step + task.owner_job.stopping_condition.threshold_value
    
    instances_to_process = Ingredient_T.select().where(Ingredient_T.id > task.step).order_by(Ingredient_T.id)
    total_instances = instances_to_process.count()
    if total_instances == 0:
        logger.info(f"No {task.process} found to {task.type}.")
        return task, True
    
    logger.info(f"Found {total_instances} {task.process} to {task.type}.")
    logger.info("")

    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
        futures = []
        for instance in instances_to_process:
            if check_if_task_stopped(task):
                logger.info("Stop signal detected — no new transformation tasks will be submitted.")
                break
            futures.append(executor.submit(load_ingredient, logger, task, instance, OFFSET))

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
    print_sub_header(logger, "Ingredient Parallel Loading Completed")
          
    # === STEP 4: AUDIT DELETED INGREDIENTS =====================================
    print_sub_header(logger, f"Auditing Deleted Ingredients")
    ingredient_name_transform_set = {ingredient.name for ingredient in instances_to_process}
    ingredient_name_load_set = {ingredient.name for ingredient in Ingredient.objects.filter(created_by__company=task.company)}
    removed_ingredients = Ingredient.objects.filter(
        created_by__company=task.company, name__in=(ingredient_name_load_set - ingredient_name_transform_set)
    )
    if removed_ingredients:
        for removed_ingredient in removed_ingredients:
            create_audit_log(
                type=IngredientAuditLog.Type.Delete,
                task=task,
                ingredient=removed_ingredient
            )
    logger.info(f"  - Found {removed_ingredients.count()} deleted {task.process}.")
    logger.info("")
                
    print_sub_header(logger, f"Deleted Ingredients Auditing completed")
    
    return task, completed, load_statistics

def __load_ingredients(logger, task, resume):
    """
    Orchestrates the loading of all ingredients for a given company and task.
    """
    print_header(logger, f"{'Resuming' if resume else 'Starting'} {task.type} for all {task.process} from {task.company.name}.")
    logger.info("")
    task, database = start_sub_db(
        logger=logger,
        task=task,
        models=transform_models_,
        database_proxy=database_proxy
    ) 
    
    task_properties = task.properties
    threads = task_properties.get("Threads", MAX_THREADS)
    logger.info("Task Properties:")
    logger.info(f"  - Threads: {threads}")
    logger.info("")   
    
    task.items_expected = Ingredient_T.select().where(Ingredient_T.id > task.step).order_by(Ingredient_T.id).count()
    task.save()
    task, completed, load_statistics = load_ingredients(logger, task, threads)
    
    from apps.etl_app.models import LoadType
    valid_ingredients_count = Ingredient_T.select().where(Ingredient_T.id > task.step and (Ingredient_T.valid == True)).order_by(Ingredient_T.id).count()
    invalid_ingredients_count = Ingredient_T.select().where(Ingredient_T.id > task.step and (Ingredient_T.valid == False)).order_by(Ingredient_T.id).count()
    logger.info("")
    logger.info("Loading Summary:")
    logger.info(f"  - Ingredients Expected: {task.items_expected}")
    logger.info(f"  - Ingredients Processed: {task.items_processed}")
    logger.info("")
    logger.info(f"  - Total Errors: {task.errors}")
    logger.info(f"  - Total Warnings: {task.warnings}")
    logger.info("")
    logger.info(f"  - Ingredients Valid: {valid_ingredients_count}")
    logger.info(f"  - Ingredients Unvalid: {invalid_ingredients_count}")
    logger.info("")
    logger.info(f"  - Ingredients Created: {load_statistics[LoadType.CREATED]}")
    logger.info(f"  - Ingredients Changed: {load_statistics[LoadType.CHANGED]}")
    logger.info(f"  - Ingredients Unchanged: {load_statistics[LoadType.UNCHANGED]}")
    logger.info(f"  - Ingredients Deleted: {load_statistics[LoadType.DELETED]}")
    logger.info("")
    
    if completed:
        task.finish(kill_celery_task=False)
        logger.info("✅ Task successfully completed.")
    else:
        task.pause()
        logger.info("⚠️ Task paused before full completion.")
    logger.info("")

    return task

def _load_ingredients(logger, task, resume):
    """
    Entrypoint for loading ingredients for a company, checking if the process is implemented.
    """
    if ProcessType.INGREDIENTS.value not in task.company.processes:
        logger.error(f"Company of task does not have an Ingredient's process.")
        task.errors += 1
        task.save()
        return
        
    if task.company.name == COMPANY_CONTINENTE:
        return __load_ingredients(logger, task, resume)
    else:
        logger.error(f"Company of task does not have an Ingredient's process implemented.")
        task.errors += 1
        task.save()
        return
