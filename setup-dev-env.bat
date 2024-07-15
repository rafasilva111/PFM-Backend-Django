@echo off

REM Start Docker if it is not already running
start "" "c:\Program Files\Docker\Docker\Docker Desktop.exe"
timeout /t 10 /nobreak > nul

REM Open WSL shell and run RabbitMQ in Docker
start wsl.exe bash -c "docker run -d -p 5672:5672 rabbitmq"

REM Open WSL shell and run Celery worker
start wsl.exe bash -c "source venv/bin/activate && celery -A config.celery worker --loglevel=INFO"

REM Open WSL shell and run Celery Flower
start wsl.exe bash -c "source venv/bin/activate && celery -A config.celery flower"

REM Open WSL shell and run Celery Beat
start wsl.exe bash -c "source venv/bin/activate && celery -A config.celery beat --loglevel=INFO"

REM Open code in Visual Studio
start wsl.exe bash -c "source venv/bin/activate && code ."
