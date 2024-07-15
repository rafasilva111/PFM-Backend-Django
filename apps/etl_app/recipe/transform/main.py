from django.utils import timezone
from apps.etl_app.recipe.transform.functions import  start_recipe_transform_db,start_recipe_extract_db
from apps.etl_app.recipe.extract.pingo_doce.models import Recipe as Recipe_PingoDoce, RecipeSchema
from apps.etl_app.recipe.transform.functions import json_to_recipe_model,normalize_quantity,verify_data_integrity,remove_non_numeric


from apps.etl_app.recipe.transform.models import NutritionInformation, Recipe as Recipe_T, IngredientQuantity, Ingredient, Tag


RecipeTagThrough = Recipe_T.tags.get_through_model()
models_ = [Recipe_T, NutritionInformation, IngredientQuantity, RecipeTagThrough, Ingredient, Tag]


def transform(logger,recipe):

    logger.info(f"Transforming Recipe {recipe.id}")
    recipe_transformed = RecipeSchema().dump(recipe)

    """ Transforming Preparation """
    
    """ Transforming Quantity """
    
    
    for ingredient in recipe_transformed['ingredients']:
        
        quantity_original,normalized_units,normalized_quantity, extra_quantity, extra_units = normalize_quantity(logger,
                                ingredient['quantity_original'])
        ingredient['quantity_original'] = quantity_original
        ingredient['quantity_normalized'] = normalized_quantity
        ingredient['units_normalized'] = normalized_units
        ingredient['extra_quantity'] = extra_quantity
        ingredient['extra_units'] = extra_units

    """ Transforming Rating """
    
    
    if 'Seja o primeiro a avaliar' in recipe_transformed['source_rating']:
        recipe_transformed['source_rating'] = 0
        

    """ Transforming Nutrition Information """

    if recipe_transformed['nutrition_information']:
        for key,value in recipe_transformed['nutrition_information'].items():

            recipe_transformed['nutrition_information'][key] = remove_non_numeric(value)

            if recipe_transformed['nutrition_information'][key] == '':
                recipe_transformed['nutrition_information'][key] = None
        
    
    """ Save record"""
    

    json_to_recipe_model(recipe_transformed)


def transform_recipes(logger,task):
    
    query = Recipe_PingoDoce.select().limit(task.max_records).order_by(Recipe_PingoDoce.id) if task.max_records else Recipe_PingoDoce.select().order_by(Recipe_PingoDoce.id)

    number_of_recipes_already_in_db = Recipe_T.select().count()

    logger.info("Transforming recipes:")
    logger.info(f"Found {number_of_recipes_already_in_db} recipes on DB")
    logger.info("")

    if number_of_recipes_already_in_db > 0:
        query = query.where(Recipe_PingoDoce.id > number_of_recipes_already_in_db)

    for recipe in query:

        transform(logger,recipe)

    


        
def __transform_recipes(logger,task):
    
    # Log the start of the extraction process
    logger.info(f"Transforming all recipes from {task.user.name}...")
    logger.info("")
    
    # Start the recipe transform database
    transform_recipes_db = start_recipe_transform_db(logger,task)
    logger.info("")
    
    # Start the recipe extract database
    extract_recipes_db = start_recipe_extract_db(logger,task)
    logger.info("")
    
    # Transform elements
    transform_recipes(logger,task)
    logger.info("")

    # Verify data integrity
    verify_data_integrity(logger)
    logger.info("")


    # Finish task
    task.finished_at = timezone.now()
    task.status = task.Status.FINISHED
    task.save()
    
    # Log the completion of the extraction process
    logger.info(f"Done...")
    logger.info("")
