" Import necessary modules "

" Import custom functions and constants "
from apps.etl_app.functions import start_sub_db
from apps.etl_app.recipe.load.functions import load_recipe, create_audit_log
from apps.recipe_app.models import RecipeAuditLog, Recipe, Tag, UsefulTool, Preparation, Ingredient, IngredientQuantity, NutritionInformation
from apps.etl_app.recipe.transform.models import database_proxy, Recipe as Recipe_T,  NutritionInformation as NutritionInformation_T, Ingredient as Ingredient_T, Tag as Tag_T, UsefulTool as UsefulTool_T, IngredientQuantity as IngredientQuantity_T
from apps.etl_app.models import ProcessType
from apps.user_app.models import Company

" Define the through model for Recipe and Tag relationship "
recipeTagThrough_T = Recipe_T.tags.get_through_model()

" Define the list of models to be used in the extraction process "
transform_models_ = [Recipe_T, Ingredient_T, Tag_T, IngredientQuantity_T, NutritionInformation_T, Ingredient_T, UsefulTool_T, recipeTagThrough_T]



def load_recipes(logger,task, resume):
    " Initialize the warnings and errors "
    __errors = 0
    __warnings = 0
    
    " Deal with the resume "
    if resume:
        logger.info("Resuming the transformation of recipes...")
        logger.info("")
        query = Recipe_T.select().where(Recipe_T.id > task.step).order_by(Recipe_T.id)
    else:
        query = Recipe_T.select().order_by(Recipe_T.id)
    
    logger.info("Loading recipes:")
    logger.info("")
    
    " Obtain the company user "
    try:
        company = query[0].company
        __company = Company.objects.get(name=company)
    except Company.DoesNotExist:
        logger.error(f"Company with name {company} does not exist.")
        task.errors = 1
        task.fail()
        return
    
    for recipe in query:
        __errors, __warnings = load_recipe(logger, task, recipe, __company)
        task.step += 1
        task.save()
        
        
    " Audit the deleted recipes "
    
    logger.info("Auditing deleted recipes...")
    # Identify and delete removed Recipes
    recipe_title_transform_set = {recipe.title for recipe in query}
    recipe_title_load_set = {recipe.title for recipe in Recipe.objects.filter(created_by__company=__company)}
    
    # Detect recipes that are in the load set but not in the transform set
    removed_recipes = Recipe.objects.filter(
        created_by__company=__company, title__in=(recipe_title_load_set - recipe_title_transform_set)
    )
    
    if removed_recipes:
        logger.info("The following recipes are in the load set but not in the transform set:")
        for removed_recipe in removed_recipes:
            create_audit_log(
                log_type=RecipeAuditLog.Type.Delete,
                task=task,
                recipe=removed_recipe,
                details=f"Recipe '{removed_recipe}' was removed."
            )
    
    logger.info(f"Found {removed_recipes.count()} deleted.")
    
    
    
    return __errors, __warnings   

def __load_recipes(logger, task, resume):

    logger.info(f"Loading recipes...")
    logger.info("")
    logger.info("")
    
    " Check if the company has the Recipe process "
    if ProcessType.RECIPES.value not in task.company.processes:
        logger.error(f"Company of task does not have a Recipe's process.")
    
    " Initialize the warnings and errors "
    __errors = 0
    __warnings = 0
        
    " Log the start of the extraction process "
    logger.info(f"Loading all recipes from {task.company.name}...")
    logger.info("")
    
    " Starts the Transform database "
    logger.info("Starting Transform database ...")

    database = start_sub_db(
            logger=logger,
            task=task,
            models=transform_models_,
            database_proxy=database_proxy
            )

    if not database:
        task.errors = 1
        task.fail()
        return

    " Transform elements "
    __errors, __warnings =load_recipes(logger, task, resume)
    logger.info("")

    
    
    " Calculate total summary "
    task.errors = __errors
    task.warnings = __warnings
    task.save()
    
    
    " Log the completion of the Loading process "
    logger.info("Summary:")
    logger.info(f"Recipes Expected: {task.items_expected}")
    logger.info(f"Recipes Processed: {task.items_processed}")
    logger.info("")
    logger.info(f"Total errors: {task.errors}")
    logger.info(f"Total warnings: {task.warnings}")
    
    
    " Finish task "
    task.finish(kill_celery_task=False)
    
    
    " Log the completion of the Loading process "
    logger.info(f"Done...")
    logger.info("")
