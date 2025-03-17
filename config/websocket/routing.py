from config.websocket.consumers import TaskLogConsumer, JobLogConsumer

from django.urls import path

websocket_urlpatterns = [
    path('ws/task/<int:task_id>/', TaskLogConsumer.as_asgi()),  
    path('ws/job/<int:job_id>/', JobLogConsumer.as_asgi()),
]