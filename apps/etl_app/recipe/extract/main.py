from apps.etl_app.recipe.extract.pingo_doce.main import __extract_pingo_doce
from apps.etl_app.recipe.extract.continente.main import __extract_continente_recipes
from apps.etl_app.models import ProcessType
from apps.common.constants import COMPANY_CONTINENTE, COMPANY_PINGO_DOCE

def _extract_recipes(logger, task, resume):
    """
    Extracts recipes for a given task based on the company's name and processes.
    This function handles the extraction of recipes by determining the appropriate
    extraction method based on the company associated with the task. It logs the
    extraction process and ensures that the company has the required processes
    implemented.
    Args:
        logger (logging.Logger): The logger instance used for logging messages.
        task (Task): The task object containing information about the company and its processes.
        continue_mode (bool): A flag indicating whether to continue from a previous state.
    Notes:
        - Supports recipe extraction for specific companies such as Pingo Doce and Continente.
        - Logs an error if the company's recipe extraction process is not implemented.
    """
    
    if ProcessType.RECIPES.value not in task.company.processes:
        task.increment_errors(logger, f"Company of task does not have a Recipe's process.")
        return
        
    if task.company.name == COMPANY_PINGO_DOCE:
        return __extract_pingo_doce(logger,task)

    elif task.company.name == COMPANY_CONTINENTE:
        return __extract_continente_recipes(logger, task, resume)

    else:
        task.increment_errors(logger, f"Company of task does not have a Recipe's process.")
        return
