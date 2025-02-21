import logging
from os import makedirs,path,rename,listdir, remove
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
from peewee import SqliteDatabase



""" Main Datbase """


    
    
def delete_task_logs(task):
    
    if task.log_path:
        directory_path = path.dirname(task.log_path)
        
        if path.exists(directory_path):
            shutil.rmtree(directory_path)

    
    
    
def configure_logging(log_folder):
    # Create the log folder if it doesn't exist
    makedirs(log_folder, exist_ok=True)
    
    # Define log filenames with the creation date
    date = timezone.now().strftime("%d_%m_%Y")
    info_log_filename = f'{log_folder}/info__{date}.log'
    error_log_filename = f'{log_folder}/errors__{date}.log'
    
    # Get the logger instance
    logger = logging.getLogger(__name__)
    
    # Clear existing handlers to prevent duplication
    if logger.hasHandlers():
        logger.handlers.clear()
    
    # Create different handlers for different log levels
    info_handler = logging.FileHandler(info_log_filename)
    info_handler.setLevel(logging.INFO)

    error_handler = logging.FileHandler(error_log_filename)
    error_handler.setLevel(logging.ERROR)

    # Define the logging format and add it to handlers
    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%d/%m/%Y %H:%M:%S')
    info_handler.setFormatter(formatter)
    error_handler.setFormatter(formatter)

    # Set the logger level to capture all messages
    logger.setLevel(logging.DEBUG)

    # Add handlers to the logger
    logger.addHandler(info_handler)
    logger.addHandler(error_handler)
    
    return logger, info_log_filename

def configure_job_logging(job):
    
    log_folder = settings.JOBS_LOG_DIR / str( job.id)
    
    # Configure the logging
    logger, log_info_path = configure_logging(log_folder)

    return logger, log_info_path

def configure_task_logging(task):
    
    # Define the log folder

    
    log_folder = settings.TASKS_LOG_DIR / str( task.id)
    
    # Configure the logging
    logger, log_info_path = configure_logging(log_folder)

    return logger, log_info_path
