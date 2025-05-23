import logging
from os import makedirs, path, rename, listdir, remove
from celery import shared_task
from django.utils import timezone
from django.conf import settings

# Description: This file contains all the functions used in the project
import json
import time
import uuid
from datetime import datetime

import shutil

import firebase_admin
import requests
from firebase_admin import credentials, initialize_app, storage
from peewee import SqliteDatabase, OperationalError


""" Main Datbase """


def configure_logging(log_folder):
    

    # Define log filenames with the creation date
    date = timezone.now().strftime("%d_%m_%Y")
    info_log_filename = f'{log_folder}/info__{date}.log' # We need to separate BASE_DIR from the log folder so we can use the same log folder for all tasks in dev and prod
    
    # Create the log folder if it doesn't exist
    log_folder_path = f"{settings.BASE_DIR}/{log_folder}"
    makedirs(log_folder_path, exist_ok=True)
    
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

    log_folder = f"{settings.JOBS_LOG_DIR}/{job.id}"

    # Configure the logging
    logger, info_log_path = configure_logging(log_folder)

    return logger, info_log_path


def configure_task_logging(task):

    # Define the log folder

    log_folder  = f"{settings.TASKS_LOG_DIR}/{task.id}"

    # Configure the logging
    logger, info_log_path = configure_logging(log_folder)

    return logger, info_log_path


def start_db(task, models, path, database_proxy, logger = None,  reset=False):
    """
    Start the recipe extract database.

    Args:
        logger (logging.Logger): The logger object.
        task (Task): The task object.
        reset (bool, optional): Whether to reset the database. Defaults to False.

    Returns:
        SqliteDatabase: The new database instance.
    """

    if not logger:
        logger = logging.getLogger(__name__)
    
    # Save the task with the new sql file name
    task_sql_path = f"{path}/db_{task.id}.sql"

    from apps.etl_app.models import Task

    task.sql_path = task_sql_path
        
    task.save()

    # Create a new database instance
    database = SqliteDatabase(task_sql_path)

    # Initialize the database proxy with the new database instance (This is usefull because models have to have a defined database, here we can dinamically change the database name)
    database_proxy.initialize(database)

    # Connect to the database
    database.connect()

    # If reset is True, drop all tables in the database
    if reset:
        logger.info("Resetting Database...")
        database.drop_tables(models)

    # Create all tables in the database
    database.create_tables(models)
    logger.info("")
    
    # Return the new database instance
    return database

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
    " Initialize the warnings and errors "
    __errors = 0
    __warnings = 0

    # Create a new database instance
    if task.parent_task:
        database = SqliteDatabase(task.parent_task.sql_path)

    elif task.owner_job.parent_job:
        if task.owner_job.parent_job.current_task:
            database = SqliteDatabase(task.owner_job.parent_job.current_task.sql_path)
        else:
            logger.error("Parent job does not have a current task with a SQL file. Most likely the Job has not been run yet.")
            __errors += 1
            return __errors, __warnings, None
        
    elif task.owner_job.parent_task:
        if task.owner_job.parent_task.sql_path:
            database = SqliteDatabase(task.owner_job.parent_task.sql_path)
        else:
            logger.error("Parent task does not have a SQL file. Most likely the Task has not been run yet.")
            __errors += 1
            return __errors, __warnings, None
        
    elif task.parent_job:
        if task.parent_job.current_task:
            database = SqliteDatabase(task.parent_job.current_task.sql_path)
        else:
            logger.error("Parent job does not have a current task with a SQL file. Most likely the Job has not been run yet.")
            __errors += 1
            return __errors, __warnings, None
        
    # Initialize the database proxy with the new database instance (This is usefull because models have to have a defined database, here we can dinamically change the database name)
    database_proxy.initialize(database)

    # Connect to the database
    try:
        database.connect()
    except OperationalError as e:
        logger.info("")
        logger.error(f"Error starting Extract database: {e}")
        logger.error(f"Database path: {task.parent_task.sql_path}")
        __errors += 1
        return __errors, __warnings, None

    # Create all tables in the database
    database.create_tables(models)

    logger.info("")
    # Return the new database instance
    return __errors, __warnings, database