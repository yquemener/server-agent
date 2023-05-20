#!/bin/bash

docker run -it --rm --name culture-matrix-server \
          -v /opt/synapse:/data \
          -v /etc/letsencrypt/live/matrix.iv-labs.org:/etc/letsencrypt/live/matrix.iv-labs.org \
          -v /etc/letsencrypt/archive/matrix.iv-labs.org:/etc/letsencrypt/archive/matrix.iv-labs.org \
          -e SYNAPSE_SERVER_NAME=matrix.iv-labs.org \
          -e SYNAPSE_REPORT_STATS=no \
          -p 8008:8008 -p 8448:8448 culture-matrix-server
