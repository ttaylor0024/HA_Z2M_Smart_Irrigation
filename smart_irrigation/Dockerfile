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
COPY app/main.py /app/main.py
COPY templates/ /app/templates/

# Copy rootfs with s6 service definition
COPY rootfs /

# Set permissions and create directories
RUN chmod +x /etc/services.d/irrigation/run && \
    mkdir -p /data /app/logs

WORKDIR /app
EXPOSE 8080
