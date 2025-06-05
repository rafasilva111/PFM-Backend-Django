# GoodBites Backend App

This is the backend application for **GoodBites**, powered by Django, PostgreSQL, and Docker. This setup supports efficient local development and production deployment using Docker, WSL, and optional VS Code integration.

## 🧰 Requirements

* [WSL](https://learn.microsoft.com/en-us/windows/wsl/)
* [Docker](https://www.docker.com/)
* [VS Code](https://code.visualstudio.com/)
* Python 3.10+
* PostgreSQL

---

## ⚙️ Full Local Development Setup

### 1. Prepare WSL Environment

```bash
wsl
```

Install Python and dependencies:

```bash
sudo apt-get update
sudo apt-get install -y python3.10 python3.10-venv libpq-dev gcc postgresql
```

### 2. Clone the Repository

```bash
git clone https://github.com/rafasilva111/PFM-Backend-Django.git
cd PFM-Backend-Django
```

### 3. Python Virtual Environment Setup

```bash
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. VS Code Integration (Optional)

Create `.vscode/launch.json`:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Django",
            "type": "debugpy",
            "request": "launch",
            "program": "${workspaceFolder}/manage.py",
            "args": [
            "runserver",
            "0.0.0.0:8000"
            ],
            "django": true,
            "envFile": "${workspaceFolder}/.env.dev"  // Specify your .env file path ( use .env.dev.full_local as example )
        },
        {
            "name": "Gunicorn ASGI (UvicornWorker)",
            "type": "python",
            "request": "launch",
            "module": "gunicorn",
            "args": [
            "config.asgi:application",
            "--bind", "0.0.0.0:8000",
            "-k", "uvicorn.workers.UvicornWorker",
            "-w", "1"
            ],
            "envFile": "${workspaceFolder}/.env.dev"  // Specify your .env file path ( use .env.dev.full_local as example )
        },
        {
            "name": "Test Command",
            "type": "debugpy",
            "request": "launch",
            "program": "${workspaceFolder}/manage.py",
            "args": [
                "create_groups",
                "--assign-test-users"
            ],
            "django": true,
            "envFile": "${workspaceFolder}/.env.dev"   // Specify your .env file path ( use .env.dev.full_local as example )
        },
        {
            "name": "Run pyTests case",
            "type": "debugpy",
            "request": "launch",
            "program": "${workspaceFolder}/manage.py",
            "args": [
                "test",
                "apps.api.tests.UsersToFollowViewTestCase"
            ],
            "console": "integratedTerminal",
            "envFile": "${workspaceFolder}/.env.dev"   // Specify your .env file path ( use .env.dev.full_local as example )
        }
    ]
}
```

### 5. Database Setup

#### 5.1. Docker Database Setup

Start PostgreSQL:

```bash
sudo service postgresql start
```

Run the database setup script:

```bash
python3.10 create_databases.py
```

#### 5.2. Local Database Setup

Update bash:

```bash
sudo apt update
```

Install PostgreSQL:

```bash
sudo apt install postgresql postgresql-contrib
```

Run PostgreSQL Service:

```bash
sudo service postgresql start
```

Set PostgreSQL Service to start with the machine ( optional ):

```bash
sudo service postgresql enable
```

Run the database setup script:

```bash
python3.10 create_databases.py
```

### 6. Redis Setup

#### 6.1. Docker Redis Setup

Start Redis:

```bash
sudo service Redis start
```

#### 6.2. Local Redis Setup

Update bash:

```bash
sudo apt update
```

Install PostgreSQL:

```bash
sudo apt install postgresql postgresql-contrib
```

Run PostgreSQL Service:

```bash
sudo service postgresql start
```

Set PostgreSQL Service to start with the machine ( optional ):

```bash
sudo service postgresql enable
```


### Shell Access

Django shell:

```bash
docker exec -it django python manage.py shell
```

PostgreSQL access:

```bash
psql -U postgres -h localhost -d goodbites
```

---

## 💡 Useful Commands

Start RabbitMQ:

```bash
docker run -d -p 5672:5672 rabbitmq
```

Start Celery:

```bash
celery -A config.celery worker --loglevel=INFO
celery -A config.celery flower
celery -A config.celery beat --loglevel=debug --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

Reset WSL DNS (if needed):

```bash
sudo rm /etc/resolv.conf
sudo bash -c 'echo "nameserver 8.8.8.8" > /etc/resolv.conf'
sudo bash -c 'echo "[network]" > /etc/wsl.conf'
sudo bash -c 'echo "generateResolvConf = false" >> /etc/wsl.conf'
sudo chattr +i /etc/resolv.conf
```

Transfer file to remote server:

```bash
scp -i ~/.ssh/ssh_key.pem file.json user@host:/tmp
```

List all Docker container IPs:

```bash
docker ps -q | xargs -n 1 docker inspect -f '{{.Name}} - {{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'
```

