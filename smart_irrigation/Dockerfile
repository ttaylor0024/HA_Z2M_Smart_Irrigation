ARG BUILD_FROM
FROM $BUILD_FROM

ENV PYTHONUNBUFFERED=1

RUN apk add --no-cache \
    python3 \
    py3-pip \
    curl \
    bash

RUN pip3 install --no-cache-dir \
    flask==3.0.0 \
    pyyaml==6.0.1 \
    requests==2.31.0 \
    aiohttp==3.9.1 \
    schedule==1.2.0 \
    python-dateutil==2.8.2

COPY run.sh /
COPY app/main.py /app/main.py
COPY templates/ /app/templates/

RUN chmod +x /run.sh && \
    mkdir -p /data /app/logs

WORKDIR /app

EXPOSE 8080

CMD ["python3", "-u", "/app/main.py"]
