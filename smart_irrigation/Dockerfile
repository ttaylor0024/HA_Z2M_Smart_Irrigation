ARG BUILD_FROM
FROM $BUILD_FROM

# Force Python to flush stdout/stderr immediately
ENV PYTHONUNBUFFERED=1

# 1) Install runtime deps
RUN apk add --no-cache \
    python3 \
    py3-pip \
    bash \
    curl \
    libffi \
    openssl \
    yaml

# 2) Install build-time deps, Python packages, then remove build-time deps
RUN apk add --no-cache --virtual .build-deps \
      build-base \
      python3-dev \
      libffi-dev \
      openssl-dev \
      yaml-dev \
  && pip3 install --no-cache-dir \
      flask==3.0.0 \
      pyyaml==6.0.1 \
      requests==2.31.0 \
      aiohttp==3.9.1 \
      schedule==1.2.0 \
      python-dateutil==2.8.2 \
  && apk del .build-deps

# 3) Copy in your run script and application code
COPY run.sh /
COPY app/ /app/
COPY templates/ /app/templates/

# 4) Mark run.sh executable, prep data directories
RUN chmod +x /run.sh \
 && mkdir -p /data /app/logs

WORKDIR /app

EXPOSE 8080

# 5) Launch under s6-overlay (init: true in config.yaml)
CMD ["/run.sh"]
