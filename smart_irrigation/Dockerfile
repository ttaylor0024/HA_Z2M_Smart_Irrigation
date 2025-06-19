ARG BUILD_FROM
FROM $BUILD_FROM

# Install system dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-setuptools \
    py3-wheel \
    py3-dev \
    gcc \
    musl-dev \
    curl \
    && rm -rf /var/cache/apk/*

# Copy requirements first for better caching
COPY requirements.txt /tmp/

# Install Python packages
RUN pip3 install --no-cache-dir --upgrade pip \
    && pip3 install --no-cache-dir -r /tmp/requirements.txt

# Copy application files
COPY run.sh /
COPY app/ /app/
COPY templates/ /app/templates/
COPY static/ /app/static/

# Set permissions
RUN chmod a+x /run.sh

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/api/status || exit 1

# Run
CMD ["/run.sh"]