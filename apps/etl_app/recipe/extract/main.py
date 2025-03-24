from apps.etl_app.recipe.extract.pingo_doce.main import __extract_pingo_doce
from apps.etl_app.recipe.extract.continente.main import __extract_continente_recipes
from apps.etl_app.models import ProcessType
from apps.common.constants import COMPANY_CONTINENTE, COMPANY_PINGO_DOCE

def _extract_recipes(logger,task, continue_mode):
    
    logger.info(f"Extracting all recipes...")
    logger.info("")
    logger.info("")
    
    if ProcessType.RECIPES.value not in task.company.processes:
        logger.error(f"Company of task does not have a Ingredient's process.")
        
    if task.company.name == COMPANY_PINGO_DOCE:
        __extract_pingo_doce(logger,task)
    elif task.company.name == COMPANY_CONTINENTE:
        __extract_continente_recipes(logger, task, continue_mode)
    else:
        logger.error(f"Company of task does not have a Recipe's process implemented.")
