#!/bin/bash
# Make sure your path to certs is an actual folder within the context of your Dockerfile,
# as docker restricts file access to content within the Dockerfile folder and subfolders.
# This means something that looks like:
# ...
# ├── Dockerfile
# ├── ...
# ├── <CERT LOCATION - Can be nested within folders>
# │   ├── ca.pem
# │   ├── cert.pem
# │   └── key.pem
# ...
docker build -t org/game-relay --build-arg TLS_CERT_PATH=<PATH TO CERTS> \
                               --build-arg DOCKER_HOST_URI=<HOSTNAME:PORT OF DOCKER HOST> .
