ARG BUILD_FROM
FROM $BUILD_FROM

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Install system dependencies - both runtime and build
RUN apk add --no-cache \
    python3 \
    py3-pip \
    bash \
    curl \
    # Runtime dependencies
    libffi \
    openssl \
    yaml \
    # Build dependencies (needed for pip install)
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    python3-dev \
    yaml-dev

# Install Python packages
RUN pip3 install --no-cache-dir \
    flask==3.0.0 \
    pyyaml==6.0.1 \
    requests==2.31.0 \
    aiohttp==3.9.1 \
    schedule==1.2.0 \
    python-dateutil==2.8.2

# Copy application files
COPY run.sh /
COPY app/ /app/
COPY templates/ /app/templates/

# Set permissions and create directories
RUN chmod +x /run.sh && \
    mkdir -p /data /app/logs

# Set working directory
WORKDIR /app

# Expose port
EXPOSE 8080

# Run the application
CMD ["/run.sh"]
