ARG BUILD_FROM
FROM $BUILD_FROM

ENV PYTHONUNBUFFERED=1

# Install all dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    bash \
    gcc \
    musl-dev \
    python3-dev

# Copy requirements first
COPY requirements.txt /tmp/
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt

# Copy application files
COPY run.sh /
COPY app/ /app/
COPY templates/ /app/templates/

RUN chmod +x /run.sh && mkdir -p /data /app/logs
WORKDIR /app
EXPOSE 8080
CMD ["/run.sh"]
