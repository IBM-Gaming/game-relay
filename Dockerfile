
FROM python:3.5-onbuild

MAINTAINER Joir-dan Gumbs <jgumbs@us.ibm.com>

# Container Arguments
# docker-py needs these certs to connect securely to the docker host pointed at by...
ARG TLS_CERT_PATH
# Host URI Relay Server will contact
ARG DOCKER_HOST_URI

# Setting up container docker parameters
ENV DOCKER_CERT_PATH /usr/src/app/testcerts
ENV DOCKER_TLS_VERIFY 1
ENV DOCKER_HOST $DOCKER_HOST_URI
ENV GAME_PORT 7777

# RUNTIME ENV params
# ENV ROUTING_STORE
# ENV REDIS_URL
# ENV VERBOSE

RUN echo ${TLS_CERT_PATH}/ca.pem && echo ${DOCKER_CERT_PATH}/ca.pem

# Add certs found on the host path to the container
COPY ${TLS_CERT_PATH}/ca.pem ${DOCKER_CERT_PATH}/ca.pem
COPY ${TLS_CERT_PATH}/cert.pem ${DOCKER_CERT_PATH}/cert.pem
COPY ${TLS_CERT_PATH}/key.pem ${DOCKER_CERT_PATH}/key.pem

# Have our service listen in on port 8080
EXPOSE 8080

CMD python server.py
