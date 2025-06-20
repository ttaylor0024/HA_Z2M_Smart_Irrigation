ARG BUILD_FROM
FROM $BUILD_FROM

ENV PYTHONUNBUFFERED=1

# 1) Runtime packages
RUN apk add --no-cache \
    python3 \
    py3-pip \
    bash \
    curl \
    libffi \
    openssl

# 2) Build-time deps
RUN apk add --no-cache --virtual .build-deps \
      build-base \
      python3-dev \
      libffi-dev \
      openssl-dev \
      libyaml-dev

# 3) Python libraries (pin Flask to 2.3.x, which exists)
RUN pip3 install --no-cache-dir \
    flask==2.3.3 \
    pyyaml==6.0.1 \
    requests==2.31.0 \
    aiohttp==3.9.1 \
    schedule==1.2.0 \
    python-dateutil==2.8.2

# 4) Remove build deps
RUN apk del .build-deps

# 5) Copy code & make run.sh executable
COPY run.sh /
COPY app/ /app/
COPY templates/ /app/templates/
RUN chmod +x /run.sh && \
    mkdir -p /data /app/logs

WORKDIR /app
EXPOSE 8080
CMD ["/run.sh"]
