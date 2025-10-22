import logging
import os
from celery import shared_task
from django.utils import timezone
from django.conf import settings

# Description: This file contains all the functions used in the project
import json
import time
import uuid
from datetime import datetime
import unicodedata
import re

import shutil

import firebase_admin
import requests
from firebase_admin import credentials, initialize_app, storage
from peewee import SqliteDatabase, OperationalError
from apps.etl_app.constants import JOBS_LOG_DIR, TASKS_LOG_DIR


""" Main Datbase """


def configure_logging(log_folder):
    

    # Define log filenames with the creation date
    date = timezone.now().strftime("%d_%m_%Y")
    info_log_filename = f'{log_folder}/info__{date}.log' # We need to separate BASE_DIR from the log folder so we can use the same log folder for all tasks in dev and prod
    
    # Create the log folder if it doesn't exist
    log_folder_path = f"{settings.BASE_DIR}/{log_folder}"
    os.makedirs(log_folder_path, exist_ok=True)
    
    _info_log_filename = f"{log_folder_path}/info__{date}.log"
    _error_log_filename = f"{log_folder_path}/errors__{date}.log"

    # Get the logger instance
    logger = logging.getLogger(__name__)

    # Clear existing handlers to prevent duplication
    if logger.hasHandlers():
        logger.handlers.clear()

    # Create different handlers for different log levels
    info_handler = logging.FileHandler(_info_log_filename)
    info_handler.setLevel(logging.INFO)

    error_handler = logging.FileHandler(_error_log_filename)
    error_handler.setLevel(logging.ERROR)

    # Define the logging format and add it to handlers
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%d/%m/%Y %H:%M:%S')
    info_handler.setFormatter(formatter)
    error_handler.setFormatter(formatter)

    # Set the logger level to capture all messages
    logger.setLevel(logging.DEBUG)

    # Add handlers to the logger
    logger.addHandler(info_handler)
    logger.addHandler(error_handler)

    return logger, info_log_filename


def configure_job_logging(job):

    log_folder = f"{JOBS_LOG_DIR}/{job.id}"

    # Configure the logging
    logger, info_log_path = configure_logging(log_folder)

    return logger, info_log_path


def configure_task_logging(task):

    # Define the log folder

    log_folder  = f"{TASKS_LOG_DIR}/{task.id}"

    # Configure the logging
    logger, info_log_path = configure_logging(log_folder)

    return logger, info_log_path


def start_db(task, models, path, database_proxy, reset=False, logger=None):
    """
    Start the recipe extract database.

    Args:
        logger (logging.Logger): The logger object.
        task (Task): The task object.
        reset (bool, optional): Whether to reset the database. Defaults to False.

    Returns:
        SqliteDatabase: The new database instance.
    """
    
    
    " Save the task with the new sql file name "
    task_sql_path = f"{path}/db_{task.id}.sql"

    from apps.etl_app.models import Task

    task.sql_path = task_sql_path
        
    task.save()

    " Create a new database instance "
    database = SqliteDatabase(task_sql_path)

    " Initialize the database proxy with the new database instance (This is usefull because models have to have a defined database, here we can dinamically change the database name) "
    database_proxy.initialize(database)

    " Connect to the database "
    database.connect()

    " If reset is True, drop all tables in the database "
    if reset:
        if logger:
            logger.info("Resetting Database...")
        else:
            print("Resetting Database...")
            
        database.drop_tables(models)


    " Create all tables in the database "
    database.create_tables(models)
    
    return task, database

def start_sub_db(logger, task, models, database_proxy):
    """
    Start the recipe extract database.

    Args:
        logger (logging.Logger): The logger object.
        task (Task): The task object.
        reset (bool, optional): Whether to reset the database. Defaults to False.

    Returns:
        SqliteDatabase: The new database instance.
    """


    " Create a new database instance "
    if task.parent_task:
        database = SqliteDatabase(task.parent_task.sql_path)

    elif task.owner_job:
        if task.owner_job.parent_job:
            if task.owner_job.parent_job.current_task:
                database = SqliteDatabase(task.owner_job.parent_job.current_task.sql_path)
            else:
                logger.error("Parent job does not have a current task with a SQL file. Most likely the Job has not been run yet.")
                task.errors += 1
                task.save()
                return task, None
        
        elif task.owner_job.parent_task:
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
        if task.parent_job.current_task:
            database = SqliteDatabase(task.parent_job.current_task.sql_path)
        else:
            logger.error("Parent job does not have a current task with a SQL file. Most likely the Job has not been run yet.")
            task.errors += 1
            task.save()
            return task, None
        
    # Initialize the database proxy with the new database instance (This is usefull because models have to have a defined database, here we can dinamically change the database name)
    database_proxy.initialize(database)

    # Connect to the database
    try:
        database.connect()
    except OperationalError as e:
        logger.info("")
        logger.error(f"Error starting Extract database: {e}")
        logger.error(f"Database path: {task.parent_task.sql_path}")
        task.errors += 1
        task.save()
        return task, None

    # Create all tables in the database
    database.create_tables(models)

    logger.info("")
    # Return the new database instance
    return task, database


from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.firefox.service import Service
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
import traceback
PAGE_LOAD_TIMEOUT = 60  # seconds

def create_driver(debug_mode=False):
    driver_path = os.path.join(os.getcwd(), "bin/geckodriver") if debug_mode else "/usr/local/bin/geckodriver"
    if not os.path.exists(driver_path):
        raise FileNotFoundError(f"Geckodriver not found at path: {driver_path}")

    if not os.path.exists("/usr/bin/firefox-esr"):
        raise FileNotFoundError("Firefox not found at /usr/bin/firefox-esr.")

    options = webdriver.FirefoxOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.binary_location = "/usr/bin/firefox-esr"

    # ✅ Limit content processes
    options.set_preference("dom.ipc.processCount", 1)
    options.set_preference("browser.tabs.remote.autostart", True)
    options.set_preference("browser.tabs.remote.autostart.2", False)

    service = Service(driver_path)
    try:
        driver = webdriver.Firefox(service=service, options=options)
    except WebDriverException as e:
        raise RuntimeError(f"Failed to start Firefox driver: {e}")

    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
    return driver

def normalize_text(text):
    # Normalize and remove accents/diacritics
    normalized = unicodedata.normalize('NFD', text)
    without_accents = ''.join(
        c for c in normalized if unicodedata.category(c) != 'Mn'
    )
    # Replace spaces with underscores
    with_underscores = without_accents.replace(' ', '_')
    # Remove any characters that are not alphanumeric or underscore
    clean_text = re.sub(r'[^\w]', '', with_underscores)
    return clean_text.strip().lower()


def strip_markdown_json(text):
        text = text.strip()
        m = re.search(r"```json\s*(.*?)```", text, re.DOTALL)
        if m:
            text = m.group(1)
        return text