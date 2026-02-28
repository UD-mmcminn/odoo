FROM mcr.microsoft.com/devcontainers/python:3-3.12-bookworm

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    libffi-dev \
    libjpeg62-turbo-dev \
    libldap2-dev \
    libpq-dev \
    libsasl2-dev \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    node-less \
    npm \
    postgresql-client \
    zlib1g-dev \
 && npm install -g rtlcss \
 && rm -rf /var/lib/apt/lists/*
