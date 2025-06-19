ARG BUILD_FROM
FROM $BUILD_FROM

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=main.py

# Install system packages
RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-wheel \
    curl \
    bash \
    gcc \
    musl-dev \
    python3-dev

# Create virtual environment and install Python packages
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python packages
RUN pip install --no-cache-dir \
    flask==3.0.0 \
    pyyaml==6.0.1 \
    requests==2.31.0 \
    aiohttp==3.9.1 \
    schedule==1.2.0 \
    python-dateutil==2.8.2

# Copy application files
COPY run.sh /
COPY main.py /app/
COPY templates/ /app/templates/
COPY static/ /app/static/

# Remove duplicate main.py if exists
RUN rm -f /app/app/main.py || true

# Create necessary directories
RUN mkdir -p /data /app/logs && \
    chmod +x /run.sh

# Set working directory
WORKDIR /app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/api/status || exit 1

# Expose port
EXPOSE 8080

# Run
CMD ["/run.sh"]
