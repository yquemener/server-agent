#!/bin/bash

docker run -p 127.0.0.1:8080:8080 -v /opt/culture_bots/keys:/app/keys -v /opt/culture_bots/db/:/app/db/ agent:0.2
