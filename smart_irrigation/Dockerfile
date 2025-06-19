ARG BUILD_FROM
FROM $BUILD_FROM

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Install system packages
RUN apk add --no-cache \
    python3 \
    py3-pip \
    curl \
    bash

# Install Python packages directly (no requirements.txt)
RUN pip3 install --no-cache-dir \
    flask \
    pyyaml \
    requests \
    aiohttp \
    schedule

# Copy application files
COPY run.sh /
COPY app/ /app/
COPY templates/ /app/templates/

# Create data directory and set permissions
RUN mkdir -p /data && chmod +x /run.sh

# Expose port
EXPOSE 8080

# Run
CMD ["/run.sh"]
