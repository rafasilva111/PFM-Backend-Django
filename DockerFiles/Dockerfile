# ---------------------------------------------
#  Base Image
# ---------------------------------------------
FROM python:3.12-slim

# ---------------------------------------------
#  Install System Dependencies
# ---------------------------------------------
RUN apt-get update && apt-get install -y \
    gcc \
    build-essential \
    libpq-dev \
    python3-dev \
    libicu-dev \
    firefox-esr \
    dbus \
    fonts-freefont-ttf \
    mesa-va-drivers \
    mesa-vulkan-drivers \
    && rm -rf /var/lib/apt/lists/*


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
