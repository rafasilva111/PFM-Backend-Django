# GoodBites Backend App

Docker will make your life a bit easier when it comes to deployment and CI/CD. This method can be used to deploy most stacks with Nginx and Postgres, ie. Flask, django-rest, FastAPI, NodeJS...

## Installation Dev Usage

Requirements:

code
wsl


### Prepare wsl enviroment
- > Activate wsl

```bash
wsl
```

- > Install python3.10

```bash
sudo apt-get install python3.10
```

- > Install dependencies

```bash
sudo apt-get update && apt-get clean && apt-get install -y libpq-dev && apt-get install -y gcc
```



### Setup Code Python dev setup

```bash
wsl
```

- > Go to dir

```bash
cd path/to/your/PFM-Backend-Django
```

- > Open FLASK_API/app code whit code

```bash
code .
```

- > Create .vscode dir

```bash
mkdir .vscode
```

- > Create launch.json in .vscode like:

```bash
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
              "--noreload",
              "--nothreading"
          ],
          "django": true,
          "env": {
              "SECRET_KEY": "lkdf@###lf583^2#KE-ri1$HkX@90i10",
              "DEBUG": "True",
              "DBNAME": "goodbites",
              "DBUSER": "postgres",
              "DBPASS": "password",
              "DBHOST": "localhost",
              "DBPORT": "5432",
              "STATICFILES": "/static/",
              "MEDIAFILES": "/media/",
              "ACCESS_TOKEN_LIFETIME": "500",
              "REFRESH_TOKEN_LIFETIME": "100",
              "DJANGO_SETTINGS_MODULE": "app.settings"
          }
      }
  ]
}
```

- > Create python interpreter( in code )

```bash
python3.10 -m venv venv
```

- > Exit code and ACTIVATE PYTHON ENV:

```bash
source venv/bin/activate
```

- > Install requirements ( opening agaian code )

```bash
pip install -r requirements.txt
```

- > Select correct interperter in VSCode

on VSCODE toppem search bar

\> Select interpreter

### Create Database

- > activate wsl

```bash
wsl
```

- > install postgresql

```bash
sudo apt-get install python3.10
```

- > activate service

```bash
sudo service postgresql start

```


- > execute script create_databses.py ( sry for the pain )

```bash
python3.10 create_databases.py
```


#### Troubleshooting:

In cade DB user needs to be reseted:

https://stackoverflow.com/questions/10845998/i-forgot-the-password-i-entered-during-postgresql-installation


## Installation Prod Usage

```bash
docker-compose build
docker-compose up -d
```
You would be able to access

[localhost:8008](http://localhost:8008/)

## Usage

Go to django shell
```bash
docker exec -it django python manage.py shell
```

Go to postgresql
```bash

```
wsl --install -d Debian

more at [here](https://docs.docker.com/get-started/overview/)
## Contributing
You can do whatever you want with this repo.


psql -U postgres -h localhost -d goodbites

docker run -d -p 5672:5672 rabbitmq

celery -A config.celery worker --loglevel=INFO

celery -A config.celery flower

celery -A config.celery beat --loglevel=info

celery -A config.celery beat --loglevel=debug --scheduler django_celery_beat.schedulers:DatabaseScheduler

sudo rm /etc/resolv.conf
sudo bash -c 'echo "nameserver 8.8.8.8" > /etc/resolv.conf'
sudo bash -c 'echo "[network]" > /etc/wsl.conf'
sudo bash -c 'echo "generateResolvConf = false" >> /etc/wsl.conf'
sudo chattr +i /etc/resolv.conf

scp -i C:\Users\rafae\.ssh\ssh_key.pem projetofoodmanager-6087f7b4c412.json azureuser@172.162.241.76:/tmp