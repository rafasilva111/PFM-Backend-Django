⚙️ Local Development Setup
==========================

1. Setup WSL + System Dependencies
----------------------------------

.. code-block:: bash

   wsl
   sudo apt update
   sudo apt install -y python3.10 python3.10-venv libpq-dev gcc postgresql redis rabbitmq

1.2. If you encounter errors like:
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: text

   E: Unable to locate package python3.10
   E: Couldn't find any package by glob 'python3.10'
   E: Unable to locate package python3.10-venv
   E: Couldn't find any package by glob 'python3.10-venv'

Run the following commands first:
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   sudo apt install -y software-properties-common
   sudo add-apt-repository ppa:deadsnakes/ppa
   sudo apt update

2. Clone the Repository
-----------------------

.. code-block:: bash

   git clone https://github.com/rafasilva111/PFM-Backend-Django.git
   cd PFM-Backend-Django

3. Create and Activate Virtual Environment
------------------------------------------

.. code-block:: bash

   python3.10 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt

4. Setup Environment Variables
------------------------------

Copy and modify `.env.dev.full_local` to `.env`:

.. code-block:: bash

   cp .env.dev.full_local .env

Update values as needed.

5. Run Database Service
-----------------------

.. code-block:: bash

   sudo service postgresql start

6. Create PostgreSQL User
-------------------------

.. code-block:: bash

   sudo -u postgres psql

.. code-block:: sql

   \password  -- ( enter "password" or change it on .env file )
   \q

7. Create Database
------------------

.. code-block:: bash

   psql -U postgresql -h localhost

.. code-block:: sql

   CREATE DATABASE goodbites;

8. Run Redis Service
--------------------

.. code-block:: bash

   sudo service redis-server start

9. Run RabbitMQ Service
-----------------------

.. code-block:: bash

   sudo service rabbitmq-server start

10. Run Celery Workers (open new terminal)
------------------------------------------

.. code-block:: bash

   celery -A config.celery worker --loglevel=info

11. Run Celery Beat Scheduler (open new terminal)
-------------------------------------------------

.. code-block:: bash

   celery -A config.celery beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler

12. Run the Development Server
------------------------------

.. code-block:: bash

   python manage.py migrate
   python manage.py runserver

🐳 Docker Setup
===============

1. Generate SSL Secrets (Optional)
----------------------------------

.. code-block:: bash

   sh generate_ssl_secrets.sh

2. Copy and modify `.env.dev.docker` to `.env`
----------------------------------------------

.. code-block:: bash

   cp .env.dev.docker .env

3. To run the entire stack with Docker
--------------------------------------

.. code-block:: bash

   docker-compose up -d
