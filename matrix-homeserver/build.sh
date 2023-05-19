#!/bin/bash

# Creates the container
docker build -t culture-matrix-server

# Generate configuration files
docker run -it --rm \
    -v /opt/synapse:/data \
    -e SYNAPSE_SERVER_NAME=matrix.iv-labs.org \
    -e SYNAPSE_REPORT_STATS=no \
    matrixdotorg/synapse:latest generate