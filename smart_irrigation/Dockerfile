ARG BUILD_FROM
FROM $BUILD_FROM

# Install Python and required packages
RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-setuptools \
    py3-wheel \
    && pip3 install --no-cache-dir \
        aiohttp==3.8.5 \
        flask==2.3.3 \
        pyyaml==6.0.1 \
        schedule==1.2.0

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
