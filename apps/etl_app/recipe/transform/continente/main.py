" Import necessary modules "

" Import custom functions and constants "
from apps.etl_app.functions import start_db, start_sub_db
from apps.etl_app.constants import transform_recipes_db, eu_reference_intake
from apps.etl_app.recipe.extract.continente.models import database_proxy as database_proxy_E, Recipe as Recipe_E, RecipeLinks as RecipeLinks_E, NutritionInformation as NutritionInformation_E, Ingredient as Ingredient_E, Tag as Tag_E, UsefulTool as UsefulTool_E
from apps.etl_app.recipe.transform.models import database_proxy, Recipe as Recipe_T,  NutritionInformation as NutritionInformation_T, Ingredient as Ingredient_T, Tag as Tag_T, UsefulTool as UsefulTool_T, IngredientQuantity as IngredientQuantity_T
from apps.etl_app.recipe.transform.continente.functions import normalize_time, normalize_portion, normalize_quantity

" Define the through model for Recipe and Tag relationship "
recipeTagThrough_E = Recipe_E.tags.get_through_model()
recipeTagThrough_T = Recipe_T.tags.get_through_model()

" Define the list of models to be used in the extraction process "
extract_models_ = [Recipe_E, RecipeLinks_E, NutritionInformation_E, Ingredient_E, Tag_E, UsefulTool_E, recipeTagThrough_E]
transform_models_ = [Recipe_T, Ingredient_T, Tag_T, IngredientQuantity_T, NutritionInformation_T, Ingredient_T, UsefulTool_T, recipeTagThrough_T]

def transform_recipe(logger, task, recipe):
    
    " Initialize the warnings and errors "
    __errors = 0
    __warnings = 0
    
    " Recipe "
    logger.info(f"Transforming Recipe {recipe.id}.")
    
    _time, _time_units = normalize_time(logger, recipe.time)
    _portion_lower_bound, _portion_upper_bound, _portion_units = normalize_portion(logger, recipe.portion)
    
    recipe_transformed = Recipe_T(
        company=task.company.name,
        title=recipe.title,
        description=recipe.description,
        image=recipe.img,
        difficulty=recipe.difficulty,
        time=_time,
        time_units=_time_units,
        portion_lower=_portion_lower_bound,
        portion_upper=_portion_upper_bound,
        portion_units=_portion_units,
        source_rating = recipe.rating,
        source_link=recipe.link,
        preparation=recipe.preparation
    )
    
    recipe_transformed.save()
    
    " Tag "
    
    for tag in recipe.tags:
        _tag, created = Tag_T.get_or_create(text = tag.text)
        if created:
            _tag.save()
        _tag.recipe.add(recipe_transformed)
        _tag.save()
    
    " Useful Tool "
    
    for useful_tool in recipe.useful_tools:
        _useful_tool = UsefulTool_T()
        _useful_tool.text = useful_tool.text
        _useful_tool.recipe = recipe_transformed
        _useful_tool.save()
    
    " Nutrition Information "
    if recipe.nutrition_information:
        _energy_perc = round((float(recipe.nutrition_information.energy_kcal) / eu_reference_intake["energy_kcal"]) * 100, 1)
        _carbohydrates_perc = round((float(recipe.nutrition_information.carbohydrates_g) / eu_reference_intake["carbohydrates_g"]) * 100, 1)
        _salt_perc = round((float(recipe.nutrition_information.salt_g) / eu_reference_intake["salt_g"]) * 100, 1)
        _sugar_perc = round((float(recipe.nutrition_information.sugars_g) / eu_reference_intake["sugars_g"]) * 100, 1)
        _fat_perc = round((float(recipe.nutrition_information.fat_g) / eu_reference_intake["fat_g"]) * 100, 1)
        _saturates_perc = round((float(recipe.nutrition_information.saturates_g) / eu_reference_intake["saturates_g"]) * 100, 1)
        _protein_perc = round((float(recipe.nutrition_information.protein_g) / eu_reference_intake["protein_g"]) * 100, 1)
        
        _nutrition_information = NutritionInformation_T(
            energy_kcal = recipe.nutrition_information.energy_kcal,
            energy_perc = _energy_perc,
            carbohydrates_g = recipe.nutrition_information.carbohydrates_g,
            carbohydrates_perc = _carbohydrates_perc,
            sugars_g = recipe.nutrition_information.sugars_g,
            sugars_perc = _sugar_perc,
            fat_g = recipe.nutrition_information.fat_g,
            fat_perc = _fat_perc,
            saturates_g = recipe.nutrition_information.saturates_g,
            saturates_perc = _saturates_perc,
            protein_g = recipe.nutrition_information.protein_g,
            protein_perc = _protein_perc,
            salt_g = recipe.nutrition_information.salt_g,
            salt_perc = _salt_perc,
            fiber_g = recipe.nutrition_information.fiber_g
        )
        _nutrition_information.save()
    
        recipe_transformed.nutrition_information = _nutrition_information
        recipe_transformed.save()   
    
    " Ingredient "
    for ingredient in recipe.ingredients:
        
        
        _ingredient_quantity = IngredientQuantity_T()
        _ingredient_quantity.quantity_original = ingredient.text
        _ingredient_quantity.quantity_tempered,_ingredient_quantity.units_normalized,_ingredient_quantity.quantity_normalized,\
        _ingredient_quantity.extra_quantity,_ingredient_quantity.extra_units, _ingredient, \
        _errors, _warnings = normalize_quantity(logger, ingredient.text)
        _ingredient_quantity.recipe = recipe_transformed
        __errors += _errors
        __warnings += _warnings
        
        _ingredient, created = Ingredient_T.get_or_create(name = _ingredient)
        
        _ingredient_quantity.ingredient = _ingredient
        _ingredient_quantity.save()
        
    
    return __errors, __warnings
    
    
def transform_recipes(logger, task, resume):
    
    " Initialize the warnings and errors counters "
    __warnings = 0
    __errors = 0
    
    OFFSET = None
    
    logger.info("")
    logger.info("Starting to transform Recipes")
    logger.info("")
    logger.info(f"Recipe extraction is on step {task.step}...")
    logger.info("")
    
    " Get the Threshold Stopping condition"
    from apps.etl_app.models import ThresholdCondition, JobTriggerHistory
    if task.parent_job and task.parent_job.stopping_condition and isinstance(task.parent_job.stopping_condition, ThresholdCondition):
        OFFSET = task.step + task.parent_job.stopping_condition
    
    " Check if we are resuming the task, and if so, delete the Recipes that are above the step "
    if task.step != 0:
        recipes_in_db = Recipe_T.select().count()
        if recipes_in_db > task.step:
            # Delete tasks until step matches recipes_in_db
            tasks_to_delete = Recipe_T.select().order_by(Recipe_T.id.desc())
            for t in tasks_to_delete:
                if task.step == recipes_in_db:
                    break
                t.tags.clear()
                t.delete_instance()
                recipes_in_db -= 1
    
    
    
    " Extract data from each extracted recipe "
    for recipe in Recipe_E.select().where(Recipe_E.id > task.step):
        
        if OFFSET and recipe.id > OFFSET:
            task.parent_job.create_job_trigger_history(
                type=JobTriggerHistory.Type.STOPPING_CONDITION,
                status=JobTriggerHistory.Status.SUCCESS,
            )
            logger.info(f"Job Stopping Condition triggered. Paused extraction at {recipe.id}...")
            break
        
        _errors, _warnings = transform_recipe(logger, task, recipe)
        __warnings += _warnings
        __errors += _errors
        task.step += 1
        task.items_processed += 1
        task.save()

    
    " Log the completion of the extraction process "
    logger.info(f"{task.items_processed} Recipes transformed ...")
    logger.info("")
    
    return __errors, __warnings

def __transform_continente_recipes(logger, task, resume):
    
    " Initialize the warnings and errors "
    __errors = 0
    __warnings = 0
        
    " Log the start of the extraction process "
    logger.info(f"Transforming all recipes from {task.company.name}...")
    logger.info("")
    
    " Start the Transform database "
    logger.info("Starting Transform database ...")
    start_db(
        logger=logger,
        task=task,
        models=transform_models_,
        path=transform_recipes_db,
        database_proxy=database_proxy,
        reset= not resume # we want to reset the database if we are not resuming
    )
    

    " Starts the Extract database "
    logger.info("Starting Extract database ...")
    database = start_sub_db(
            logger=logger,
            task=task,
            models=extract_models_,
            database_proxy=database_proxy_E
            )
    
    # This was required in the past, but now it doesn't seem to be necessary
    # it was used because Debug Mode and Prod Mode Database where not in the same path
    #if not database:
    #    task.errors = 1
    #    task.fail()
    #    return
    
    " Transform Elements "
    _errors, _warnings = transform_recipes(logger, task, resume)
    __errors += _errors
    __warnings += _warnings

    # Verify data integrity # TODO: use chatgpt to correct final data integrity
    # verify_data_integrity(logger)
    # logger.info("")

    
    
    " Calculate total summary "
    task.errors = __errors
    task.warnings = __warnings
    task.save()
    
    
    " Log the completion of the Transformation process "
    logger.info("Summary:")
    logger.info(f"Recipes Expected: {task.items_expected}")
    logger.info(f"Recipes Processed: {task.items_processed}")
    logger.info("")
    logger.info(f"Total errors: {task.errors}")
    logger.info(f"Total warnings: {task.warnings}")
    
    
    " Finish task "
    task.finish(kill_celery_task=False)
    
    
    " Log the completion of the Transformation process "
    logger.info(f"Done...")
    logger.info("")