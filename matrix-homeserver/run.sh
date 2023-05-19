#!/bin/bash

docker run -it --rm --name culture-matrix-server culture-matrix-server     \
    -v /opt/synapse:/data \
    -e SYNAPSE_SERVER_NAME=matrix.iv-labs.org \
    -e SYNAPSE_REPORT_STATS=no