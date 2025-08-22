from apps.etl_app.recipe.transform.continente.main import __transform_continente_recipes
from apps.etl_app.models import ProcessType
from apps.common.constants import COMPANY_CONTINENTE

def _transform_recipes(logger, task, resume):
    
    if ProcessType.RECIPES.value not in task.company.processes:
        logger.error(f"Company of task does not have a Recipe's process.")
        task.errors += 1
        task.save()
        return
        
    if task.company.name == COMPANY_CONTINENTE:
        return __transform_continente_recipes(logger, task, resume)
    else:
        logger.error(f"Company of task does not have a Recipe's process implemented.")
        task.errors += 1
        task.save()
        return
