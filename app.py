# Copyright 2016 IBM Corp. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from docker import Client
from docker.utils import kwargs_from_env
import errno
from flask.ext.redis import FlaskRedis
from flask import Flask
from flask_restful import Api
import logging
import traceback

import utils
from db import DecodedRedis


def config():
    utils.setup_logging()
    app.config.update(utils.handle_env())


def get_docker_client():
    try:
        # We will attempt to get the cluster info from environment variables
        kwargs = kwargs_from_env()
        logging.debug("getting kwargs")
        kwargs['tls'].assert_hostname = False
        client = Client(**kwargs)
        logging.debug(client.version())
        return client
    except Exception:
        # If for some reason we can not connect, kill the server.
        traceback.print_exc()
        traceback.print_stack()
        logging.critical("Unable to connect to cluster. Exiting")
        exit(errno.ECONNABORTED)


app = Flask(__name__)
config()
api = Api(app)
# Pointing to our docker machine right now.
docker_client = get_docker_client()
# Using Cloudant to store our game-server data
# cloudant_client = cloudant_connect()
redis_client = FlaskRedis.from_custom_provider(DecodedRedis, app)
logging.debug("Initialized objects...")
