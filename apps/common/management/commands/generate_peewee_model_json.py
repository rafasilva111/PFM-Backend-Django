from django.core.management.base import BaseCommand
from apps.etl_app.models import Task
from playhouse.shortcuts import model_to_dict
import json
from apps.etl_app.constants import transform_recipes_db
from apps.etl_app.recipe.transform.models import database_proxy, Ingredient as Ingredient_T
from apps.etl_app.functions import start_db
from apps.etl_app.recipe.transform.continente.main import transform_models_


class Command(BaseCommand):
    help = 'Create the default company if it does not exist'

    def handle(self, *args, **kwargs):
        
        task_id = 47
        task = Task.objects.get(id = task_id)
        
        start_db(
            task=task,
            models=transform_models_,
            path=transform_recipes_db,
            database_proxy=database_proxy,
            reset=False
        )
        
        ingredients = Ingredient_T.select()
        clients_list= []
        for client in ingredients:
            client_dict = model_to_dict(client, backrefs=True, recurse=True)

            client_dict['ingredient_base']
            
            for item in client_dict['ingredient_base']:
                item.pop('recipe')
                
            clients_list.append(client_dict)
                
        with open('ingredients.json', 'w', encoding='utf-8') as f:
            json.dump(clients_list, f, ensure_ascii=False, indent=4)        # Check if the default company exists