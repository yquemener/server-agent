#!/bin/bash

docker run -p 127.0.0.1:8080:8080 -v /home/yves/keys:/app/keys -v /home/yves/Culture/dbs/:/app/db/ agent:0.1
