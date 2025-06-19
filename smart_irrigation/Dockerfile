ARG BUILD_FROM
FROM $BUILD_FROM

# Install only essential packages
RUN apk add --no-cache \
    python3 \
    py3-pip \
    curl

# Install Python packages one by one to isolate issues
RUN pip3 install --no-cache-dir flask
RUN pip3 install --no-cache-dir pyyaml
RUN pip3 install --no-cache-dir requests
RUN pip3 install --no-cache-dir aiohttp
RUN pip3 install --no-cache-dir schedule

# Copy application files
COPY run.sh /
COPY app/ /app/
COPY templates/ /app/templates/

# Set permissions
RUN chmod a+x /run.sh

# Create directories
RUN mkdir -p /data

# Expose port
EXPOSE 8080

# Run
CMD ["/run.sh"]
