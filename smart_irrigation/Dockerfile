ARG BUILD_FROM
FROM $BUILD_FROM

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Install system packages and Python packages available in Alpine
RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-setuptools \
    py3-wheel \
    bash \
    curl \
    # Python packages available in Alpine repos
    py3-flask \
    py3-yaml \
    py3-requests \
    py3-aiohttp \
    py3-dateutil

# Upgrade pip first
RUN python3 -m pip install --upgrade pip

# Install only the schedule package via pip (not available in Alpine)
RUN python3 -m pip install --no-cache-dir schedule==1.2.0

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
