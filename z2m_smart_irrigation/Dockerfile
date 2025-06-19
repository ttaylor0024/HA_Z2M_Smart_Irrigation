ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base-python:3.11
FROM ${BUILD_FROM}

# install dependencies
COPY requirements.txt /
RUN pip3 install --no-cache-dir -r /requirements.txt

# copy your code
COPY run.sh /
COPY main.py /
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
