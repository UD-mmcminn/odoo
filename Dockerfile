FROM python:3.12-slim-bookworm

ARG ODOO_UID=1000
ARG ODOO_GID=1000

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    ODOO_RC=/etc/odoo/odoo.conf \
    ODOO_DATA_DIR=/var/lib/odoo

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    curl \
    fontconfig \
    gcc \
    git \
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
    pkg-config \
    tini \
    zlib1g-dev \
 && npm install -g rtlcss \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/odoo
COPY requirements.txt ./
RUN pip install --upgrade pip setuptools wheel \
 && pip install -r requirements.txt

COPY . /opt/odoo

RUN groupadd --gid ${ODOO_GID} odoo \
 && useradd --uid ${ODOO_UID} --gid ${ODOO_GID} --home-dir /var/lib/odoo --create-home --shell /bin/bash odoo \
 && mkdir -p /etc/odoo /var/lib/odoo /var/log/odoo \
 && chown -R odoo:odoo /etc/odoo /var/lib/odoo /var/log/odoo /opt/odoo

COPY docker/entrypoint.sh /usr/local/bin/odoo-entrypoint.sh
RUN chmod +x /usr/local/bin/odoo-entrypoint.sh

EXPOSE 8069 8072

USER odoo
ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/odoo-entrypoint.sh"]
CMD []
