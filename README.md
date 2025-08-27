# 🍽️ GoodBites Backend

Welcome to the backend of **GoodBites**, a modern food-focused platform designed for real-time interaction and efficient task processing.  
This backend is built with Django, PostgreSQL, Celery, Redis, and Channels, and is fully containerized using Docker for ease of development and deployment.

---

## 🔧 Tech Stack

| Technology     | Description                                                                  |
|----------------|------------------------------------------------------------------------------|
| **Django**     | High-level Python web framework for rapid development and clean architecture |
| **Firebase**   | Optional integration for push notifications, analytics, or storage           |
| **PostgreSQL** | Reliable and powerful open-source relational database                        |
| **Celery**     | Asynchronous task queue for background processing and scheduling             |
| **Redis**      | In-memory data store used as Celery broker and for caching                   |
| **Channels**   | Adds WebSocket and async support to Django for real-time features            |
| **Docker**     | Ensures consistent environments for development, testing, and deployment     |
| **WSL**        | Linux environment on Windows for native-like Docker and development support  |
| **VS Code**    | Optional IDE integration for streamlined development                         |

---

## ✨ General Features

- 🔐 **User Authentication & Permissions**
- 🔄 **Real-time Updates via WebSockets**
- 🧠 **Asynchronous Tasks with Celery + Redis**
- 🗓️ **Scheduled Jobs with Celery Beat**
- 🛠️ **Powerful Django Admin Dashboard**
- 🛠️ **ETL Functionality for Data Extraction, Transformation & Loading Workflows**
- 🌐 **Automated Web Scraping with Selenium & BeautifulSoup for Dynamic and Static Content**
- 📦 **Containerized for Easy Setup and Deployment**
- 🔍 **API-ready Architecture (REST)**
- 🧪 **Integrated Testing Tools (Pytest, unittest)**
- 📚 **Well-Structured Developer Documentation with Sphinx**
- 🌐 **DNS Configuration and HTTPS Support for Secure Production Deployment (NameCheap)**
- 📧 **Email Integration for Notifications, Verification & Password Reset (MailTrap)**
- 🔐 **Bot Protection via CAPTCHA Integration (reCAPTCHA)**

## ✨ App Features

- 👤 **User Management (Create, Update, Delete, Block)**
- 🛡️ **Group/Permissions Management**
- ✅ **Task Management**
- 🧑‍💼 **Jobs Management**
- 📖 **Recipes Management**
- 🥕 **Ingredients Management**
- 📅 **Calendar Management**
- 🛒 **Shopping Lists Management**
- 📲 **Notification Lists Management**
- 🧴 **Dispensary Lists Management**


🛠️ Management refers to full CRUD operations (Create, Read, Update, Delete), along with essential supporting functionality such as filtering, searching, sharing, notifications, role-based access control, and any additional domain-specific features required for each entity.

---

## 🧰 Prerequisites

- Python 3.10+
- PostgreSQL (via Docker or local)
- Redis (via Docker or local)
- RabbitMQ (via Docker or local)
- Docker + Docker Compose
- [WSL](https://learn.microsoft.com/en-us/windows/wsl/) for Windows users
- [VS Code](https://code.visualstudio.com/) (optional but recommended)

---

## ⚙️ Local Development Setup

### 1. Setup WSL + System Dependencies

```bash
wsl
sudo apt update
sudo apt install -y python3.10 python3.10-venv libpq-dev gcc postgresql redis rabbitmq
```

#### 1.2. If you encounter errors like:

```
E: Unable to locate package python3.10
E: Couldn't find any package by glob 'python3.10'
E: Unable to locate package python3.10-venv
E: Couldn't find any package by glob 'python3.10-venv'
```

#### Run the following commands first:

```bash
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
```

### 2. Clone the Repository

```bash
git clone https://github.com/rafasilva111/PFM-Backend-Django.git
cd PFM-Backend-Django
```

### 3. Create and Activate Virtual Environment

```bash
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Setup Environment Variables

Copy and modify `.env.dev.full_local` to `.env`:

```bash
cp .env.dev.full_local .env
```

Update values as needed.

### 5. Run Database Service

```bash
sudo service postgresql start
```

### 6. Create PostgreSQL User

```bash
sudo -u postgres psql
```

```sql
\password ( enter "password" or change it on .env file )
```

```sql
\q
```

### 7. Create Database

```bash
psql -U postgresql -h localhost
```

```sql
CREATE DATABASE goodbites;
```

### 8. Run Reddis Service

```bash
sudo service redis-server start
```

### 8. Run RabbitMQ Service

```bash
sudo service rabbitmq-server start
```

### 10. Run Celery Workers ( open new terminal )

```bash
celery -A config.celery worker --loglevel=info
```

### 11. Run Celery Beat Scheduler ( open new terminal )

```bash
celery -A config.celery beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

### 12. Run the Development Server

```bash
python manage.py migrate
python manage.py runserver
```

---

## 🐳 Docker Setup


### 1. Generate SSL Secrets (Optional):

```bash
sh generate_ssl_secrets.sh
```

### 2. Copy and modify `.env.dev.docker` to `.env`:

```bash
cp .env.dev.docker .env
```

### 3. To run the entire stack with Docker:

```bash
docker-compose up -d
```

Access Django at: [http://localhost:8000](http://localhost:8000)

---

## 🧪 Testing

To run tests:

```bash
python manage.py test
```

Or use pytest:

```bash
pytest
```

---

## 📁 VS Code Integration (Optional)

Use `.vscode/launch.json` for debugging and development directly from VS Code. Enable `devcontainers` if using Remote - WSL or Docker.

---

## 💡 Useful Commands

```bash
# Start RabbitMQ (if used)
docker run -d -p 5672:5672 rabbitmq

# Celery workers and beat scheduler
celery -A config.celery worker --loglevel=info
celery -A config.celery beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler

# Access PostgreSQL
psql -U postgres -h localhost -d goodbites

# Access Django shell
docker exec -it django python manage.py shell
```

---

## 📜 License

© 2025 GoodBites. All rights reserved.

This software and all associated files are the exclusive property of Rafael Silva.  
Unauthorized copying, distribution, use, or modification of any part of this project is strictly prohibited without prior written permission.

This code is licensed for private use only.  
Commercial or public use, including derivative works, is not allowed.