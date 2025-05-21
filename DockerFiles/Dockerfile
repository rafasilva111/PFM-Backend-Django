# ---------------------------------------------
#  Base Image
# ---------------------------------------------
FROM python:3.11-alpine

# ---------------------------------------------
#  Install System Dependencies
# ---------------------------------------------
RUN apk update && apk add --no-cache \
    postgresql-dev \
    gcc \
    python3-dev \
    musl-dev \
    icu-data-full \
    firefox \
    geckodriver \
    xvfb \
    dbus \
    ttf-freefont \
    mesa-dri-gallium

# ---------------------------------------------
#  Upgrade pip
# ---------------------------------------------
RUN pip install --upgrade pip

# ---------------------------------------------
#  Set Working Directory
# ---------------------------------------------
WORKDIR /app

# ---------------------------------------------
#  Install Python Dependencies
# ---------------------------------------------
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# ---------------------------------------------
#  Copy Application Files
# ---------------------------------------------
COPY config /app/config
