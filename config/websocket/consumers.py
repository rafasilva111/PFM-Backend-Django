###
# General imports
##

## Default
import os
import asyncio
import json

## URL Parsing
from urllib.parse import parse_qs

## Channels
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer
### App-specific imports

## Models
from django.conf import settings

import os
import json
import asyncio
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from asgiref.sync import async_to_sync


class TaskLogConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer for streaming log data from a task to a connected client.

    Attributes:
        task_group_name (str): Group name for the WebSocket channel associated with a task.
        log_file_path (str): Path to the log file of the task.
        log_file (file): File object for the task's log file.
    """

    async def get_task(self, task_id):
        """
        Fetches the Task instance with the specified task ID from the database.

        Args:
            task_id (int): The ID of the task to retrieve.

        Returns:
            Task: The Task instance if found, or None if not found.
        """
        
        from apps.etl_app.models import Task
        
        try:
            task = await Task.objects.aget(id=task_id)
            return task
        except Task.DoesNotExist:
            return None

    async def celery_task_update(self, event):
        """
        Sends a task update message to the WebSocket client.
        """
        await self.send_json({"type": "task_update",
                             "data":event})

    async def connect(self):
        """
        Handles the WebSocket connection by associating the client with a task's log stream.
        """
        task_id = self.scope['url_route']['kwargs']['task_id']
        


        task = await self.get_task(task_id)
        if task is None:
            await self.close()
            return

        self.task_group_name = f"task_{task.id}"
        self.log_file_path = task.log_path
        if self.log_file_path and os.path.isfile(self.log_file_path):
            
            await self.channel_layer.group_add(self.task_group_name, self.channel_name)
            await self.accept()

            self.log_file = open(self.log_file_path, 'r')
            self.log_file.seek(0, os.SEEK_END)

            asyncio.create_task(self.stream_log_data())
        else:
            await self.close()

    async def stream_log_data(self):
        """
        Periodically checks for new lines in the log file and sends them to the client.
        """
        try:
            while True:
                line = self.log_file.readline()
                if line:
                    await self.send_json({
                        "type": "log_line",
                        "line": line
                    })
                else:
                    await asyncio.sleep(1)
        except Exception as e:
            await self.close()

    async def disconnect(self, close_code):
        """
        Handles the WebSocket disconnection by closing the log file if open.
        """
        if hasattr(self, 'log_file') and self.log_file:
            self.log_file.close()

        await self.channel_layer.group_discard(self.task_group_name, self.channel_name)


class JobLogConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer for streaming log data from a job to a connected client.

    Attributes:
        log_file_path (str): Path to the log file of the job.
        log_file (file): File object for the job's log file.
    """

    async def get_job(self, job_id):
        """
        Fetches the Job instance with the specified job ID from the database.

        Args:
            job_id (int): The ID of the job to retrieve.

        Returns:
            Job: The Job instance if found, or None if not found.
        """
        from apps.etl_app.models import  Job
        try:
            job = await Job.objects.aget(id=job_id)
            return job
        except Job.DoesNotExist:
            return None

    async def connect(self):
        """
        Handles the WebSocket connection by associating the client with a job's log stream.
        """
        job_id = self.scope['url_route']['kwargs']['job_id']
        job = await self.get_job(job_id)
        if job is None:
            await self.close()
            return

        self.log_file_path = job.log_path
        
        if self.log_file_path and os.path.isfile(self.log_file_path):
            await self.accept()
            self.log_file = open(self.log_file_path, 'r')
            self.log_file.seek(0, os.SEEK_END)
            asyncio.create_task(self.stream_log_data())
        else:
            await self.close()

    async def stream_log_data(self):
        """
        Periodically checks for new lines in the log file and sends them to the client.
        """
        try:
            while True:
                line = self.log_file.readline()
                if line:
                    await self.send_json({
                        "type": "log_line",
                        "line": line
                    })
                else:
                    await asyncio.sleep(1)
        except Exception as e:
            print(f"Error in stream_log_data: {e}")
            await self.close()

    async def disconnect(self, close_code):
        """
        Handles the WebSocket disconnection by closing the log file if open.
        """
        if hasattr(self, 'log_file') and self.log_file:
            self.log_file.close()
