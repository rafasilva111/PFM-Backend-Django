from django.utils import timezone

from apps.etl_app.recipe.load.functions import  start_recipe_extract_db
from apps.etl_app.recipe.transform.models import  Recipe as RecipeTransform,RecipeSchema
from apps.recipe_app.serializers import RecipeSerializer
from apps.recipe_app.models import Recipe


def load_recipes(logger,task):
    logger.info("Loading recipes:")
    logger.info("")

    query = RecipeTransform.select().where(RecipeTransform.is_valid == True)

    if task.max_records:
        query.limit(task.max_records)

    for recipe in query:

        logger.info(f"Loading Recipe {recipe.id}")

        if recipe.is_valid == False:
            continue

        try:
            Recipe.objects.get(source_link = recipe.source_link)
        except Recipe.DoesNotExist:
            try:
                recipe_ = RecipeSchema().dump(recipe)
                recipe_serializer = RecipeSerializer(data = recipe_, context={'user': task.company.user_account})
                if not recipe_serializer.is_valid():
                    logger.error(f"Recipe {recipe.source_link} has errors: {recipe_serializer.errors}")
                    continue
                recipe_serializer.save()
            except Exception as e:
                logger.error(f"Recipe {recipe.source_link} has errors: " + str(e))




def __load_recipes(logger,task):

    logger.info(f"Loading all recipes from {task.company.name}...")
    logger.info("")

    # Start the recipe transform database
    start_recipe_extract_db(logger,task)
    logger.info("")

    # Transform elements
    load_recipes(logger,task)
    logger.info("")


    # Finish task
    task.finished_at = timezone.now()
    task.status = task.Status.FINISHED
    task.save()
    
    # Log the completion of the extraction process
    logger.info(f"Done...")
    logger.info("")


