from django.core.management.base import BaseCommand, CommandError
from apps.etl_app.models import Task
from playhouse.shortcuts import model_to_dict
import json
from apps.etl_app.constants import TRANSFORM_CONTINENTE_RECIPES_DB
from apps.etl_app.recipe.transform.models import database_proxy, Ingredient as Ingredient_T
from apps.etl_app.functions import start_db
from apps.etl_app.recipe.transform.continente.main import transform_models_


class Command(BaseCommand):
    help = 'Create the default company if it does not exist'

    def add_arguments(self, parser):
        parser.add_argument(
            '--task_id',
            type=int,
            default=None,
            help='ID of the Task to use (default: 47)'
        )

    def handle(self, **kwargs):
        
        task_id = kwargs.get('task_id')
        if not task_id:
            raise CommandError('You must provide a task_id argument.')
        
        task = Task.objects.get(id=task_id)
        if task.type != Task.TaskType.TRANSFORM:
            raise CommandError('The task must be of type TRANSFORM.')
        
        start_db(
            logger=None,
            task=task,
            models=transform_models_,
            path=TRANSFORM_CONTINENTE_RECIPES_DB,
            database_proxy=database_proxy,
            reset=False
        )
        
        ingredients = Ingredient_T.select()
        ingredients_list = []
        for ingredient in ingredients:
            ingredient_dict = model_to_dict(ingredient, backrefs=True, recurse=True)

            for item in ingredient_dict['ingredient_base']:
                item.pop('recipe')
                
            ingredients_list.append(ingredient_dict)
                
        with open('ingredients.json', 'w', encoding='utf-8') as f:
            json.dump(ingredients_list, f, ensure_ascii=False, indent=4)