# Use an ultra-light Python 3.9 image based on Alpine Linux
FROM python:3.11-alpine

# Install PostgreSQL development packages and other dependencies
RUN apk update && apk add --no-cache postgresql-dev gcc python3-dev musl-dev

RUN pip install --upgrade pip

# Set the working directory in the container
WORKDIR /app

# Copy only the requirements.txt file to the container
COPY requirements.txt /app/

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the necessary application files
COPY config /app/config

# Define environment variable
ENV PYTHONUNBUFFERED=1

# Run the command to start your application (adjust this to your specific entry point)
#CMD ["celery", "-A", "config.celery", "worker", "--loglevel=INFO"]