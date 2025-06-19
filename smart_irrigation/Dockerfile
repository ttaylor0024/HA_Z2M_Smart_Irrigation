ARG BUILD_FROM
FROM $BUILD_FROM

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Install only essential packages
RUN apk add --no-cache \
    python3 \
    py3-pip \
    curl \
    bash

# Install Python packages directly
RUN pip3 install --no-cache-dir \
    flask==3.0.0 \
    pyyaml==6.0.1 \
    requests==2.31.0 \
    aiohttp==3.9.1 \
    schedule==1.2.0 \
    python-dateutil==2.8.2

# Copy application files - CORRECT PATHS
COPY run.sh /
COPY app/main.py /app/main.py
COPY templates/ /app/templates/
RUN ls -l / | tee /ls_root.txt

# Create necessary directories and set permissions
RUN mkdir -p /data /app/logs && \
    chmod +x /run.sh

# Set working directory
WORKDIR /app

# Expose port
EXPOSE 8080

# Run
CMD ["/run.sh"]
