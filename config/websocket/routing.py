from config.websocket.consumers import TaskLogConsumer, JobLogConsumer
from os import environ
from django.urls import path

ENV = environ.get('ENVIROMENT','127.0.0.1:8000')

if ENV == 'prod':
    websocket_urlpatterns = [
        path('wss/task/<int:task_id>/', TaskLogConsumer.as_asgi()),  
        path('wss/job/<int:job_id>/', JobLogConsumer.as_asgi()),
    ]
    
else:
    websocket_urlpatterns = [
        path('ws/task/<int:task_id>/', TaskLogConsumer.as_asgi()),  
        path('ws/job/<int:job_id>/', JobLogConsumer.as_asgi()),
    ]