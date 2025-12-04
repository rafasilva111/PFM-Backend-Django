from apps.etl_app.etl.extract.ingredient.continente.main import __extract_continente_ingredients
from apps.etl_app.models import ProcessType
from apps.common.constants import COMPANY_CONTINENTE, COMPANY_PINGO_DOCE

def _extract_ingredients(logger, task, resume):
    """
    Extract ingredients for a given task based on the company's name and processes.

    This function determines the appropriate ingredient extraction method based on the
    company associated with the task. It ensures that the company has the required
    processes implemented and logs the extraction process. If the company's ingredient
    extraction process is not implemented, an error is logged.

    Args:
        logger (logging.Logger): The logger instance used for logging messages.
        task (Task): The task object containing information about the company and its processes.
        resume (bool): A flag indicating whether to continue from a previous state.

    Notes:
        - Supports ingredient extraction for specific companies such as Continente.
        - Logs an error if the company's ingredient extraction process is not implemented.
        - Ensures that the company has the required ingredient process before proceeding.
    """
    
    if ProcessType.INGREDIENTS.value not in task.company.processes:
        task.increment_errors(logger, f"Company of task does not have a {ProcessType.INGREDIENTS.value}'s process.")
        return
    
    if task.company.name == COMPANY_CONTINENTE:
        return __extract_continente_ingredients(logger, task, resume)

    else:
        task.increment_errors(logger, f"Company of task does not have a {ProcessType.INGREDIENTS.value}'s process.")
        return




