import os
import asyncio
from urllib.parse import parse_qs
from channels.generic.websocket import AsyncWebsocketConsumer

class LogConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Parse query parameters
        query_string = self.scope['query_string'].decode()
        query_params = parse_qs(query_string)
        log_file_path = query_params.get('file', [None])[0]

        if log_file_path and os.path.isfile(log_file_path):
            self.log_file_path = log_file_path
            await self.accept()
            self.log_file = open(self.log_file_path, 'r')
            self.log_file.seek(0, os.SEEK_END)  # Move to the end of the file

            # Periodically check for new lines in the log file
            while True:
                line = self.log_file.readline()
                if line:
                    # Assuming `send` is an async method for sending data (e.g., in a WebSocket consumer)
                    await self.send(text_data=line)
                else:
                    await asyncio.sleep(1)  #
        else:
            await self.close()

    async def disconnect(self, close_code):
        if hasattr(self, 'log_file'):
            self.log_file.close()
