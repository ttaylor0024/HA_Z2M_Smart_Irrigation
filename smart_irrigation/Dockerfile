ARG BUILD_FROM
FROM $BUILD_FROM

# Force Python to flush stdout/stderr immediately
ENV PYTHONUNBUFFERED=1

# 1) Runtime dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    bash \
    curl \
    libffi \
    openssl

# 2) Build-time dependencies (for C extensions)
RUN apk add --no-cache --virtual .build-deps \
    build-base \
    python3-dev \
    libffi-dev \
    openssl-dev \
    yaml-dev \
    rust

# 3) Install all Python requirements at once
RUN pip3 install --no-cache-dir \
    flask==2.3.3 \
    pyyaml==6.0.1 \
    requests==2.31.0 \
    aiohttp==3.9.1 \
    schedule==1.2.0 \
    python-dateutil==2.8.2

# 4) Remove build-time deps to slim the image
RUN apk del .build-deps

# 5) Copy in your startup script and application
COPY run.sh /
COPY app/ /app/
COPY templates/ /app/templates/

# 6) Make run.sh executable and prep directories
RUN chmod +x /run.sh \
 && mkdir -p /data /app/logs

WORKDIR /app
EXPOSE 8080

# 7) Launch under s6-overlay (config.yaml has init: true)
CMD ["/run.sh"]
