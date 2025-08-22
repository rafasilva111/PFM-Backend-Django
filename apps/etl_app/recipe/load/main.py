" Import necessary modules "

" Import custom functions and constants "
from apps.etl_app.functions import start_sub_db
from apps.etl_app.recipe.load.functions import load_recipe, create_audit_log
from apps.recipe_app.models import RecipeAuditLog, Recipe, Tag, UsefulTool, Preparation, Ingredient, IngredientQuantity, NutritionInformation
from apps.etl_app.recipe.transform.models import database_proxy, Recipe as Recipe_T,  NutritionInformation as NutritionInformation_T, Ingredient as Ingredient_T, Tag as Tag_T, UsefulTool as UsefulTool_T, IngredientQuantity as IngredientQuantity_T
from apps.etl_app.models import ProcessType
from apps.user_app.models import Company
from apps.common.constants import COMPANY_CONTINENTE

" Define the through model for Recipe and Tag relationship "
recipeTagThrough_T = Recipe_T.tags.get_through_model()

" Define the list of models to be used in the extraction process "
transform_models_ = [Recipe_T, Ingredient_T, Tag_T, IngredientQuantity_T, NutritionInformation_T, Ingredient_T, UsefulTool_T, recipeTagThrough_T]



def load_recipes(logger,task, resume):
    
    " Initialize the control variables "
    OFFSET = None
    
    " Check if we are resuming the task "
    if resume:
        logger.info(f"Recipe Load is on step {task.step}...")
        logger.info("Resuming the Loading of recipes...")
        logger.info("")
    else:
        logger.info("Starting Recipe Loading...")
        logger.info("")
    
    " Get the Threshold Stopping condition"
    from apps.etl_app.models import ThresholdCondition, JobTriggerHistory
    if task.owner_job and task.owner_job.stopping_condition and isinstance(task.owner_job.stopping_condition, ThresholdCondition):
        OFFSET = task.step + task.owner_job.stopping_condition.threshold_value
    
    " Load data from each Transformed recipe "
    query = Recipe_T.select().where(Recipe_T.id > task.step).order_by(Recipe_T.id)
    for recipe in query:
        
        if OFFSET and recipe.id > OFFSET:
            task.owner_job.create_job_trigger_history(
                type=JobTriggerHistory.Type.STOPPING_CONDITION,
                action = JobTriggerHistory.Action.REST,
            )
            logger.info(f"Job Stopping Condition triggered. Paused extraction at {recipe.id}...")
            logger.info("")
            return task, False

        
        load_recipe(logger, task, recipe)
        task.step += 1
        task.items_processed += 1
        task.save()
        
        
    " Audit the deleted recipes "
    logger.info("Auditing deleted recipes...")
    # Identify and delete removed Recipes
    recipe_source_link_transform_set = {recipe.source_link for recipe in query}
    recipe_source_link_load_set = {recipe.source_link for recipe in Recipe.objects.filter(created_by__company=task.company)}
    
    # Detect recipes that are in the load set but not in the transform set
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
    # Note: we don't unverify the deleted recipes
    

    " Log the completion of the extraction process "
    logger.info(f"{task.items_processed} Recipes loaded ...")
    logger.info(f"With {removed_recipes.count()} being deleted.")
    logger.info("")
    
    return task, True

def __load_recipes(logger, task, resume):
    
    " Log the start of the Loading process "
    logger.info(f"Initializing the {task.type} of recipes from {task.company.name}...")
    
    " Starts the Transform database "
    logger.info("Initializing Transform database ...")
    task, database = start_sub_db(
        logger=logger,
        task=task,
        models=transform_models_,
        database_proxy=database_proxy
    )    
    logger.info("")
    
    " Calculate the number of recipes expected to be loaded "
    task.items_expected = Recipe_T.select().count()
    task.save()


    " Transform elements "
    task, completed = load_recipes(logger, task, resume)
    
    
    " Log the completion of the Loading process "
    logger.info("Summary:")
    logger.info(f"Recipes Expected: {task.items_expected}")
    logger.info(f"Recipes Processed: {task.items_processed}")
    logger.info("")
    logger.info(f"Total errors: {task.errors}")
    logger.info(f"Total warnings: {task.warnings}")
    
    
    " Finish task "
    if completed:
        task.finish(kill_celery_task=False)
    else:
        task.pause()
    
    
    " Log the completion of the Loading process "
    logger.info("")
    logger.info(f"> Done...")
    logger.info("")
    
    return task



def _load_recipes(logger, task, resume):
        
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

