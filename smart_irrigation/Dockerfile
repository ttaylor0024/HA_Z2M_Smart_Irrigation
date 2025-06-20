ARG BUILD_FROM
FROM $BUILD_FROM

# Ensure Python prints logs immediately
ENV PYTHONUNBUFFERED=1

# 1) Runtime dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    bash \
    curl \
    libffi \
    openssl

# 2) Build-time dependencies (including Rust for yarl/multidict)
RUN apk add --no-cache --virtual .build-deps \
    build-base \
    python3-dev \
    libffi-dev \
    openssl-dev \
    yaml-dev \
    rust

# 3) Upgrade pip tooling
RUN pip3 install --no-cache-dir --upgrade pip setuptools wheel

# 4) Install your Python libraries
RUN pip3 install --no-cache-dir \
    flask==2.3.3 \
    pyyaml==6.0.1 \
    requests==2.31.0 \
    aiohttp==3.9.1 \
    schedule==1.2.0 \
    python-dateutil==2.8.2

# 5) Remove build dependencies to slim down the image
RUN apk del .build-deps

# 6) Copy in your startup script and application code
COPY run.sh /
COPY app/ /app/
COPY templates/ /app/templates/

# 7) Final prep: make run.sh executable and create needed dirs
RUN chmod +x /run.sh \
 && mkdir -p /data /app/logs

WORKDIR /app
EXPOSE 8080

# 8) s6-overlay (via init: true) will hand off to run.sh
CMD [ "/run.sh" ]
