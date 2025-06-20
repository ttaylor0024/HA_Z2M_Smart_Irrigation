ARG BUILD_FROM
FROM $BUILD_FROM

# Install only Alpine packages
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

# Set permissions
RUN chmod +x /run.sh && \
    mkdir -p /data /app/logs

WORKDIR /app
EXPOSE 8080

# Use the s6-overlay compatible CMD format
CMD [ "/run.sh" ]
