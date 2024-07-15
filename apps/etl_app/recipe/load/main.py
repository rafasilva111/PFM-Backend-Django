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
                recipe_serializer = RecipeSerializer(data = recipe_, context={'user': task.user})
                if not recipe_serializer.is_valid():
                    logger.error(f"Recipe {recipe.source_link} has errors: {recipe_serializer.errors}")
                    continue
                recipe_serializer.save()
            except Exception as e:
                logger.error(f"Recipe {recipe.source_link} has errors: " + str(e))




def __load_recipes(logger,task):

    logger.info(f"Loading all recipes from {task.user.name}...")
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



    """" Open Databases connection "
        start_main_db()
        start_firebase()

        Creating Company accounts for all existing recipe's company 

        email, password = create_company_account()

        token = get_user_token(email=email, password=password)
        headers = {
            "Authorization": f"Bearer {str(token['token'])}"
        }

        Exporting recipes 
        print_it()

        counter = 0
        for recipe in Recipe.select():

            print_it(f"Loading {recipe.id}")

            data = RecipeSchema().dump(recipe)

            if send_images_to_firebase:
                image_destination = f'images/company/{recipe.company}/recipes/{data["img_source"].split("/")[-1]}.jpg'
                send_image_to_firebase(image_destination=image_destination, image_source=data["img_source"])
                data["img_source"] = image_destination

            response = requests.post(url=f"http://{SERVER_URL}/api/v1/recipe/company", headers=headers, json=data)

            if response.status_code == 400:
                print_it(f"Response: {response.content}", "E")
            counter += 1
            if counter == max_recipes:
                break

        Close Databaes connection 
        close_firebase()
        close_main_db()

        print_it()
        print_it("Loading done!")
        print_it()
    """