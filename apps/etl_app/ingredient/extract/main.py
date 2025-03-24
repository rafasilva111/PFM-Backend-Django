
from apps.common.constants import COMPANY_CONTINENTE, COMPANY_PINGO_DOCE
from apps.etl_app.ingredient.extract.continente.main import __extract_continente_ingredients
from apps.etl_app.models import ProcessType


def _extract_ingredients(logger, task, continue_mode):
    """
            Extract ingredients
            :param task: task object
            :param continue_mode: if True, it will continue the extraction from the last page
    """

    if ProcessType.INGREDIENTS.value not in task.company.processes:
        logger.error(f"Company of task does not have a Ingredient's process.")
        return
        
    if task.company.name == COMPANY_CONTINENTE:
        __extract_continente_ingredients(logger,task, continue_mode)
    else:
        logger.error(f"Company of task does not have a Ingredient's process implemented.")


           
        
        




