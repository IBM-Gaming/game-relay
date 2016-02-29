#!/bin/bash
 docker run -itd -e REDIS_URL=redis://<[PASSWORD@]HOSTNAME:PORT/DB> \
                 -e ROUTING_STORE=<ROUTING TABLE NAME> \
                 -e VERBOSE= <1 IF YES, 0 IF NO> \
                 --name <THE RELAY NAME YOU WANT TO GIVE... IF YOU WANT> \
                 -p <INTERNAL_PORT:EXTERNAL_PORT_ON_HOST> \
                 <RELAY_IMAGE>
