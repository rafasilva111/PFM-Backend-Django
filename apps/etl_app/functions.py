# === STANDARD LIBRARY IMPORTS ==================================================
import os
import logging
import unicodedata
import re
from datetime import datetime
from collections import deque
import time

# === THIRD-PARTY IMPORTS =======================================================
import requests
import firebase_admin
from firebase_admin import credentials, initialize_app, storage
from peewee import SqliteDatabase, OperationalError
from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.firefox.service import Service
from selenium.common.exceptions import WebDriverException

# === DJANGO IMPORTS ============================================================
from django.utils import timezone
from django.conf import settings

# === LOCAL IMPORTS =============================================================
from apps.etl_app.constants import JOBS_LOG_DIR, TASKS_LOG_DIR

# === CONSTANTS =================================================================
PAGE_LOAD_TIMEOUT = 60  # seconds

# === FUNCTIONS =================================================================

def configure_logging(log_folder):
    """
    Configures structured logging for a given log folder, creating separate log files for INFO and ERROR levels.

    Workflow:
        1. Format log filenames with the current date.
        2. Ensure the log folder exists.
        3. Build full paths for info and error log files.
        4. Get or create the logger instance.
        5. Clear existing handlers to avoid duplication.
        6. Create and configure handlers for INFO and ERROR levels.
        7. Set logging format and level.
        8. Attach handlers to the logger.
        9. Return the logger and info log filename.

    Args:
        log_folder (str): Relative path to the log folder.

    Returns:
        tuple: (logger, info_log_filename) - Configured logger and path to the info log file.

    Notes:
        - Uses Django settings.BASE_DIR for absolute paths.
        - Ensures logs are separated by level and date.
        - Handlers are cleared before adding new ones to prevent duplicate logs.
    """
    # === STEP 1: FORMAT LOG FILENAMES ==========================================
    date = timezone.now().strftime("%d_%m_%Y")
    info_log_filename = f'{log_folder}/info__{date}.log'

    # === STEP 2: ENSURE LOG FOLDER EXISTS ======================================
    log_folder_path = f"{settings.BASE_DIR}/{log_folder}"
    os.makedirs(log_folder_path, exist_ok=True)

    # === STEP 3: BUILD FULL LOG FILE PATHS =====================================
    _info_log_filename = f"{log_folder_path}/info__{date}.log"
    _error_log_filename = f"{log_folder_path}/errors__{date}.log"

    # === STEP 4: GET LOGGER INSTANCE ===========================================
    logger = logging.getLogger(__name__)

    # === STEP 5: CLEAR EXISTING HANDLERS =======================================
    if logger.hasHandlers():
        logger.handlers.clear()

    # === STEP 6: CREATE AND CONFIGURE HANDLERS =================================
    info_handler = logging.FileHandler(_info_log_filename)
    info_handler.setLevel(logging.INFO)

    error_handler = logging.FileHandler(_error_log_filename)
    error_handler.setLevel(logging.ERROR)

    # === STEP 7: SET LOGGING FORMAT AND LEVEL ==================================
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%d/%m/%Y %H:%M:%S')
    info_handler.setFormatter(formatter)
    error_handler.setFormatter(formatter)

    logger.setLevel(logging.DEBUG)

    # === STEP 8: ATTACH HANDLERS TO LOGGER =====================================
    logger.addHandler(info_handler)
    logger.addHandler(error_handler)

    # === STEP 9: RETURN LOGGER AND INFO LOG PATH ===============================
    return logger, info_log_filename


def configure_job_logging(job):
    """
    Configures logging for a specific job, creating a dedicated log folder and logger.

    Workflow:
        1. Build the log folder path using the job ID.
        2. Call configure_logging to set up the logger and log files.
        3. Return the logger and info log path.

    Args:
        job (Job): Job instance for which logging is configured.

    Returns:
        tuple: (logger, info_log_path) - Configured logger and info log file path.
    """
    # === STEP 1: BUILD LOG FOLDER PATH =========================================
    log_folder = f"{JOBS_LOG_DIR}/{job.id}"

    # === STEP 2: CONFIGURE LOGGING =============================================
    logger, info_log_path = configure_logging(log_folder)

    # === STEP 3: RETURN LOGGER AND INFO LOG PATH ===============================
    return logger, info_log_path


def configure_task_logging(task):
    """
    Configures logging for a specific task, creating a dedicated log folder and logger.

    Workflow:
        1. Build the log folder path using the task ID.
        2. Call configure_logging to set up the logger and log files.
        3. Return the logger and info log path.

    Args:
        task (Task): Task instance for which logging is configured.

    Returns:
        tuple: (logger, info_log_path) - Configured logger and info log file path.
    """
    # === STEP 1: BUILD LOG FOLDER PATH =========================================
    log_folder = f"{TASKS_LOG_DIR}/{task.id}"

    # === STEP 2: CONFIGURE LOGGING =============================================
    logger, info_log_path = configure_logging(log_folder)

    # === STEP 3: RETURN LOGGER AND INFO LOG PATH ===============================
    return logger, info_log_path


def start_db(task, models, path, database_proxy, reset=False, logger=None):
    """
    Orchestrates the initialization and connection to a SQLite database for a given task.

    Workflow:
        1. Log the start of database initialization.
        2. Construct the database file path and update the task's sql_path.
        3. Create a new SQLite database instance and initialize the Peewee proxy.
        4. Connect to the database.
        5. Optionally reset the database by dropping all tables.
        6. Create all required tables for the provided models.
        7. Return the updated task and the database instance.

    Args:
        task (Task): The task object.
        models (list): List of Peewee model classes to create tables for.
        path (str): Directory path where the database file will be stored.
        database_proxy (Proxy): Peewee database proxy to initialize.
        reset (bool, optional): If True, drop all tables before creating them. Defaults to False.
        logger (logging.Logger, optional): Logger for structured logging.

    Returns:
        tuple: (task, SqliteDatabase) - The updated task and the database instance.

    Notes:
        - Updates the task.sql_path to the new database file location.
        - If reset=True, all tables are dropped before creation.
        - All models are bound to the new database via the proxy.
    """
    # === STEP 1: LOG INITIALIZATION ============================================
    if logger:
        logger.info(f"Initializing {task.type} database...")

    # === STEP 2: CONSTRUCT DATABASE PATH & UPDATE TASK =========================
    task_sql_path = f"{path}/db_{task.id}.sql"
    from apps.etl_app.models import Task
    task.sql_path = task_sql_path
    task.save()

    # === STEP 3: CREATE DATABASE INSTANCE & INITIALIZE PROXY ===================
    database = SqliteDatabase(
        task_sql_path,
        pragmas={
            'journal_mode': 'wal',
            'busy_timeout': 5000,
            'foreign_keys': 1,
        }
    )
    database_proxy.initialize(database)

    # === STEP 4: CONNECT TO DATABASE ===========================================
    database.connect()

    # === STEP 5: OPTIONALLY RESET DATABASE =====================================
    if reset:
        if logger:
            logger.info("Resetting Database...")
        database.drop_tables(models)

    # === STEP 6: CREATE TABLES =================================================
    database.create_tables(models)

    # === STEP 7: RETURN UPDATED TASK & DATABASE ================================
    logger.info("")
    return task, database

def start_sub_db(logger, task, models, database_proxy):
    """
    Orchestrates the initialization and connection to a sub-database for a given task, 
    selecting the appropriate parent database file based on task relationships.

    Workflow:
        1. Log the start of sub-database initialization.
        2. Determine the correct parent database file path:
            - If task has a parent task, use its database.
            - If task has an owner job, check for parent job's current task or parent task.
            - If task has a parent job, use its current task's database.
        3. Initialize the Peewee database proxy with the selected database.
        4. Connect to the database, handling errors gracefully.
        5. Create all required tables for the provided models.
        6. Return the updated task and the database instance (or None on error).

    Args:
        logger (logging.Logger): Logger for structured logging.
        task (Task): The task object, which may have parent relationships.
        models (list): List of Peewee model classes to create tables for.
        database_proxy (Proxy): Peewee database proxy to initialize.

    Returns:
        tuple: (task, SqliteDatabase or None) - The updated task and the database instance, or None on error.

    Notes:
        - Handles missing parent relationships and logs errors.
        - Increments task error count and saves state on failure.
        - Returns None for database if initialization fails.
    """
    # === STEP 1: LOG INITIALIZATION ============================================
    if logger:
        logger.info(f"Initializing {task.type} sub-database...")

    # === STEP 2: DETERMINE PARENT DATABASE PATH ================================
    database = None
    if task.parent_task:
        # Use the parent task's database file
        database = SqliteDatabase(task.parent_task.sql_path)

    elif task.owner_job:
        # Owner job may have a parent job or parent task
        if task.owner_job.parent_job:
            # Use parent job's current task database if available
            if task.owner_job.parent_job.current_task:
                database = SqliteDatabase(task.owner_job.parent_job.current_task.sql_path)
            else:
                logger.error("Parent job does not have a current task with a SQL file. Most likely the Job has not been run yet.")
                task.errors += 1
                task.save()
                return task, None

        elif task.owner_job.parent_task:
            # Use parent task's database if available
            if task.owner_job.parent_task.sql_path:
                database = SqliteDatabase(task.owner_job.parent_task.sql_path)
            else:
                logger.error("Parent task does not have a SQL file. Most likely the Task has not been run yet.")
                task.errors += 1
                task.save()
                return task, None
        else:
            logger.error("Task does not have a parent job or parent task.")
            return task, None

    elif task.parent_job:
        # Use the parent job's current task database file
        if task.parent_job.current_task:
            database = SqliteDatabase(task.parent_job.current_task.sql_path)
        else:
            logger.error("Parent job does not have a current task with a SQL file. Most likely the Job has not been run yet.")
            task.errors += 1
            task.save()
            return task, None

    # === STEP 3: INITIALIZE DATABASE PROXY =====================================
    database_proxy.initialize(database)

    # === STEP 4: CONNECT TO DATABASE & HANDLE ERRORS ===========================
    try:
        database.connect()
    except OperationalError as e:
        logger.info("")
        logger.error(f"Error starting sub-database: {e}")
        logger.error(f"Database path: {getattr(task.parent_task, 'sql_path', 'Unknown')}")
        task.errors += 1
        task.save()
        return task, None

    # === STEP 5: CREATE TABLES =================================================
    database.create_tables(models)
    logger.info("")
    
    # === STEP 6: RETURN UPDATED TASK & DATABASE ================================
    return task, database


def create_driver(debug_mode=False):
    """
    Initializes and configures a Selenium Firefox WebDriver for automated browser tasks.

    Workflow:
        1. Determine geckodriver path based on debug mode.
        2. Check for existence of geckodriver and Firefox binary.
        3. Configure Firefox options for headless operation and resource limits.
        4. Set browser preferences for performance and security.
        5. Start the Firefox WebDriver service.
        6. Set page load timeout.
        7. Return the configured driver instance.

    Args:
        debug_mode (bool): If True, use local geckodriver and Firefox for debugging.

    Returns:
        webdriver.Firefox: Configured Firefox WebDriver instance.

    Raises:
        FileNotFoundError: If geckodriver or Firefox binary is missing.
        RuntimeError: If the driver fails to start.

    Notes:
        - Requires geckodriver and Firefox-ESR installed at specified locations.
        - Headless mode is enabled for non-GUI operation.
        - Browser preferences are set for reduced resource usage.
    """
    # === STEP 1: DETERMINE DRIVER PATH =========================================
    driver_path = os.path.join(os.getcwd(), "bin/geckodriver") if debug_mode else "/app/bin/geckodriver"

    # === STEP 2: CHECK DRIVER & FIREFOX EXISTENCE ==============================
    if not os.path.exists(driver_path):
        raise FileNotFoundError(f"Geckodriver not found at path: {driver_path}")

    if not os.path.exists("/usr/bin/firefox-esr"):
        raise FileNotFoundError("Firefox not found at /usr/bin/firefox-esr.")

    # === STEP 3: CONFIGURE FIREFOX OPTIONS =====================================
    options = webdriver.FirefoxOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.binary_location = "/usr/bin/firefox-esr"

    # === STEP 4: SET BROWSER PREFERENCES =======================================
    options.set_preference("dom.ipc.processCount", 1)
    options.set_preference("browser.tabs.remote.autostart", True)
    options.set_preference("browser.tabs.remote.autostart.2", False)
    options.set_preference("permissions.default.stylesheet", 2)
    options.set_preference("dom.ipc.plugins.enabled.libflashplayer.so", False)

    # === STEP 5: START DRIVER SERVICE ===========================================
    service = Service(driver_path)
    try:
        driver = webdriver.Firefox(service=service, options=options)
    except WebDriverException as e:
        raise RuntimeError(f"Failed to start Firefox driver: {e}")

    # === STEP 6: SET PAGE LOAD TIMEOUT ==========================================
    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)

    # === STEP 7: RETURN DRIVER ==================================================
    return driver

def normalize_text(text):
    """
    Normalizes a string by removing accents, replacing spaces, and cleaning non-alphanumeric characters.

    Workflow:
        1. Normalize Unicode to decompose accents/diacritics.
        2. Remove accent marks.
        3. Replace spaces with underscores.
        4. Remove non-alphanumeric and non-underscore characters.
        5. Convert to lowercase and strip whitespace.

    Args:
        text (str): Input string to normalize.

    Returns:
        str: Normalized string suitable for filenames or identifiers.

    Notes:
        - Useful for generating safe, consistent keys or filenames.
    """
    # === STEP 1: UNICODE NORMALIZATION ==========================================
    normalized = unicodedata.normalize('NFD', text)
    # === STEP 2: REMOVE ACCENTS =================================================
    without_accents = ''.join(
        c for c in normalized if unicodedata.category(c) != 'Mn'
    )
    # === STEP 3: REPLACE SPACES =================================================
    with_underscores = without_accents.replace(' ', '_')
    # === STEP 4: REMOVE NON-ALPHANUMERIC ========================================
    clean_text = re.sub(r'[^\w]', '', with_underscores)
    # === STEP 5: FINAL CLEANUP ==================================================
    return clean_text.strip().lower()

def strip_markdown_json(text):
    """
    Extracts JSON content from a markdown code block.

    Workflow:
        1. Strip leading/trailing whitespace.
        2. Search for a markdown JSON code block using regex.
        3. If found, extract the JSON content.
        4. Return the extracted or original text.

    Args:
        text (str): Input string containing markdown-formatted JSON.

    Returns:
        str: Extracted JSON string or original text if no block found.

    Notes:
        - Useful for parsing JSON responses embedded in markdown.
    """
    # === STEP 1: STRIP WHITESPACE ==============================================
    text = text.strip()
    # === STEP 2: REGEX SEARCH FOR JSON BLOCK ====================================
    m = re.search(r"```json\s*(.*?)```", text, re.DOTALL)
    # === STEP 3: EXTRACT CONTENT IF FOUND =======================================
    if m:
        text = m.group(1)
    # === STEP 4: RETURN RESULT ==================================================
    return text

def tail_colored_log(filepath, offset=0, limit=50):
    """
    Efficiently reads and colorizes the last lines of a log file for HTML display.

    Workflow:
        1. Define color mapping for log levels.
        2. Compile regex patterns for log level highlighting.
        3. Read the last `limit + offset` lines using a deque.
        4. Extract the target lines, skipping `offset` from the end.
        5. Apply color coding to log levels.
        6. Wrap each line in HTML for display.
        7. Return the combined HTML string.

    Args:
        filepath (str): Path to the log file.
        offset (int): Number of lines from the end to skip.
        limit (int): Number of lines to read after offset.

    Returns:
        str: HTML string with colored log lines.

    Notes:
        - Gracefully handles missing files.
        - Designed for efficient reading of large log files.
    """
    # === STEP 1: COLOR MAPPING & PATTERNS =======================================
    COLOR_MAP = {
        "INFO": "#4A90E2",
        "WARNING": "#F5A623",
        "ERROR": "#D0021B"
    }
    PATTERNS = [
        (
            re.compile(fr"(\[{level}\])"),
            rf'<span style="color:{color};font-weight:bold;">\1</span>'
        )
        for level, color in COLOR_MAP.items()
    ]

    # === STEP 2: READ LAST LINES WITH DEQUE =====================================
    target_lines = offset + limit
    dq = deque(maxlen=target_lines)
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                dq.append(line.rstrip("\n"))
    except FileNotFoundError:
        return ""  # Gracefully handle missing file

    # === STEP 3: EXTRACT TARGET LINES ===========================================
    if offset > 0:
        lines = list(dq)[-(limit + offset):-offset]
    else:
        lines = list(dq)[-limit:]

    # === STEP 4: COLORIZE & WRAP IN HTML ========================================
    html_lines = []
    for line in lines:
        current_line = line.lstrip()
        for pattern, replacement in PATTERNS:
            current_line = pattern.sub(replacement, current_line)
        html_lines.append(f'<div style="white-space: nowrap;">{current_line}</div>')

    # === STEP 5: RETURN HTML ====================================================
    return "".join(html_lines)

def count_lines(filepath):
    """
    Efficiently counts the number of lines in a large file.

    Workflow:
        1. Open the file in binary mode.
        2. Read the file in large blocks.
        3. Count newline characters in each block.
        4. Return the total line count.

    Args:
        filepath (str): Path to the file.

    Returns:
        int: Number of lines in the file.

    Notes:
        - Optimized for large files by reading in blocks.
    """
    # === STEP 1: INITIALIZE COUNTER =============================================
    count = 0
    # === STEP 2: READ BLOCKS & COUNT NEWLINES ===================================
    with open(filepath, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            count += block.count(b"\n")
    # === STEP 3: RETURN COUNT ===================================================
    return count

def check_if_task_stopped(task):
    """
    Checks if a task has been signaled to stop, cancel, or pause.

    Workflow:
        1. Refresh task state from the database.
        2. Check if task status is in stopped/canceled/paused states.
        3. Return True if stopped, otherwise False.

    Args:
        task (Task): Task instance to check.

    Returns:
        bool: True if task is stopped, canceled, or paused.

    Notes:
        - Uses Task.Status enums for comparison.
    """
    # === STEP 1: REFRESH TASK STATE =============================================
    from apps.etl_app.models import Task
    task.refresh_from_db()
    # === STEP 2: CHECK STATUS ===================================================
    return task.status in [Task.Status.CANCELED, Task.Status.STOPPED, Task.Status.PAUSED]

def check_task_stopping_condition(task, stopping_offset, instance):
    # Check if the stopping condition offset is reached
    from apps.etl_app.models import Task, JobTriggerHistory
    if stopping_offset and instance.id > stopping_offset:
        task.owner_job.create_job_trigger_history(
            type=JobTriggerHistory.Type.STOPPING_CONDITION,
            action=JobTriggerHistory.Action.REST,
        )
        return True
    
def print_header(logger, text):
    """
    Logs a formatted header for major process steps.

    Workflow:
        1. Create a separator line based on text length.
        2. Log the separator, header text, and separator.

    Args:
        logger (logging.Logger): Logger instance.
        text (str): Header text to display.

    Returns:
        None

    Notes:
        - Used for visually separating major log sections.
    """
    # === STEP 1: FORMAT & LOG HEADER ============================================
    separator = "=" * (len(text) + 4)
    logger.info(separator)
    logger.info(f"\t| {text} |")
    logger.info(separator)

def print_sub_header(logger, text):
    """
    Logs a formatted subheader for intermediate process steps.

    Workflow:
        1. Format subheader text.
        2. Log the subheader and a blank line.

    Args:
        logger (logging.Logger): Logger instance.
        text (str): Subheader text to display.

    Returns:
        None

    Notes:
        - Used for visually separating intermediate log sections.
    """
    # === STEP 1: FORMAT & LOG SUBHEADER =========================================
    logger.info(f"=== === {text} === ===")
    logger.info("")

def print_minor_header(logger, text):
    """
    Logs a minor header for small process steps.

    Workflow:
        1. Format minor header text.
        2. Log the minor header.

    Args:
        logger (logging.Logger): Logger instance.
        text (str): Minor header text to display.

    Returns:
        None

    Notes:
        - Used for marking small steps or details in logs.
    """
    # === STEP 1: FORMAT & LOG MINOR HEADER ======================================
    logger.info(f"=== {text} ===")


def retry_db_operation(func, retries=5, delay=0.1, backoff=2):
    """
    Executes a database operation with automatic retries on 'database is locked' errors.

    Workflow:
        1. Attempt to execute the provided function.
        2. If an OperationalError occurs and the error message contains 'database is locked':
            - Wait for the specified delay.
            - Increase the delay exponentially using the backoff multiplier.
            - Retry up to the specified number of attempts.
        3. If the error is not 'database is locked', re-raise immediately.
        4. If all retries are exhausted, re-raise the last exception.

    Args:
        func (callable): The database operation to execute.
        retries (int, optional): Maximum number of attempts. Defaults to 5.
        delay (float, optional): Initial delay between retries in seconds. Defaults to 0.5.
        backoff (int or float, optional): Multiplier for exponential backoff. Defaults to 2.

    Returns:
        Any: The result of the successful function call.

    Raises:
        OperationalError: If a non-retryable error occurs or all retries are exhausted.

    Notes:
        - Designed for SQLite 'database is locked' errors, which are transient.
        - Uses exponential backoff to reduce contention.
    """
    for attempt in range(1, retries + 1):
        try:
            return func()
        except OperationalError as e:
            # Only retry on 'database is locked' errors
            if "database is locked" not in str(e):
                raise  # Different error: re-raise immediately

            if attempt == retries:
                raise  # Out of retries: re-raise last exception

            # Wait before retrying, then increase delay for next attempt
            time.sleep(delay)
            delay *= backoff
            
# ----------------------------------------------------------------------
# 1. Load Functions
# ----------------------------------------------------------------------

def update_simple_fields(logger, task,model_obj, new_data, model_cls, changes_dict):
    """
    Compares and updates simple scalar fields on the model.
    Records changes in changes_dict.
    """
    for field, new_value in new_data.items():
        if not hasattr(model_cls, field):
            task.increment_errors(
                logger, f"Unknown field {field} for model {model_cls.__name__}"
            )
            continue

        old_value = getattr(model_obj, field)
        if new_value != old_value:
            setattr(model_obj, field, new_value)
            changes_dict[field] = {"old": old_value, "new": new_value}

    if changes_dict:
        model_obj.save()
        
def sync_related(
        existing_qs,       # Django queryset
        incoming_list,     # list from Peewee (list[dict])
        key,               # unique key in incoming_list (e.g. "step", "text")
        fields,            # fields to compare
        create_fn,         # lambda to create new object
        delete_fn          # lambda to delete/remove
    ):
        """
        Synchronizes related objects (1-to-many or many-to-many).
        Handles creation, update, and deletion, and records changes.
        """
        changes = []
        # Support key as a function or string
        if callable(key):
            existing_map = {key(obj): obj for obj in existing_qs}
            incoming_map = {key(item): item for item in incoming_list}
        else:
            existing_map = {getattr(obj, key): obj for obj in existing_qs}
            incoming_map = {item[key]: item for item in incoming_list}

        # Deleted
        for k, obj in existing_map.items():
            if k not in incoming_map:
                delete_fn(obj)
                changes.append({"deleted": {key: k}})
        
        # Created / Updated
        for k, item in incoming_map.items():
            if k in existing_map:
                obj = existing_map[k]
                for f in fields:
                    old = getattr(obj, f)
                    new = item.get(f)
                    if old != new:
                        setattr(obj, f, new)
                        obj.save()
                        changes.append({"updated": {"field": f, "old": old, "new": new}})
            else:
                create_fn(item)
                changes.append({"created": item})

        return changes
            
def add_many_to_many(item_list, model, field, relation_manager):
        """
        Generic helper to create or fetch M2M objects based on
        a single identifying field (e.g., text=name).
        """
        for item in item_list:
            obj, _ = model.objects.get_or_create(**{field: item[field]})
            relation_manager.add(obj)