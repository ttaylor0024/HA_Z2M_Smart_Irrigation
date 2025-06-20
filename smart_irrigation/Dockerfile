ARG BUILD_FROM
FROM $BUILD_FROM

# Install only Alpine packages - no pip needed
RUN apk add --no-cache \
    python3 \
    py3-flask \
    py3-yaml \
    py3-requests \
    py3-aiohttp \
    py3-dateutil \
    bash

# Copy application files
COPY run.sh /
COPY app/main.py /app/main.py
COPY templates/ /app/templates/

# Set permissions and create directories
RUN chmod +x /run.sh && \
    mkdir -p /data /app/logs

WORKDIR /app
EXPOSE 8080

# IMPORTANT: Don't use CMD - let s6-overlay handle it
# The run.sh will be executed by s6-overlay automatically
