FROM mcr.microsoft.com/playwright/python:v1.35.0-jammy

# set non-interactive environment for apt
ENV DEBIAN_FRONTEND=noninteractive TZ=UTC

# install X11 and display server libraries for headless=false mode
RUN apt-get update && apt-get install -y \
    libx11-6 \
    libxext6 \
    libxrender1 \
    x11-utils \
    xvfb \
    x11vnc \
    && rm -rf /var/lib/apt/lists/*

# install pipenv
RUN pip install pipenv
ENV PIPENV_VENV_IN_PROJECT=1

# create app directory
RUN mkdir -p /app
WORKDIR /app

# install python dependencies
ADD Pipfile .
ADD Pipfile.lock .
RUN pipenv install --system

# copy app
COPY . .

# copy entrypoint script
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh
