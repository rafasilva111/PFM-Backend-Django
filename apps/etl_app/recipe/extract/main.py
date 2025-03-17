from apps.etl_app.recipe.extract.pingo_doce.main import __extract_pingo_doce
from apps.etl_app.models import ProcessType
from apps.common.constants import COMPANY_CONTINENTE, COMPANY_PINGO_DOCE

def _extract_recipes(logger,task):
    
    logger.info(f"Extracting all recipes...")
    logger.info()
    logger.info()
    
    if task.company.processes != ProcessType.INGREDIENTS:
        logger.Error(f"Company of task does not have a Ingredient's process.")
        
    if task.company.name == COMPANY_PINGO_DOCE:
        __extract_pingo_doce(logger,task)
    else:
        logger.Error(f"Company of task does not have a Ingredient's process implemented.")
